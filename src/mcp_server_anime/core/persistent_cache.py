"""Persistent cache implementation with hybrid memory/database storage.

This module provides a two-tier caching system that combines fast in-memory caching
with persistent SQLite database storage for durability across service restarts.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

from .cache import TTLCache, generate_cache_key
from .exceptions import DatabaseError
from .logging_config import get_logger, log_cache_operation
from .models import AnimeDetails, AnimeSearchResult
from .multi_provider_db import MultiProviderDatabase, get_multi_provider_database
from .persistent_cache_models import (
    CacheSerializer,
    PersistentCacheEntry,
    PersistentCacheStats,
)

logger = get_logger(__name__)


class PersistentCache:
    """Hybrid cache with in-memory and SQLite persistence.
    
    This cache implements a two-tier strategy:
    1. L1 Cache (Memory): Fast TTLCache for immediate access
    2. L2 Cache (SQLite): Persistent storage for durability across restarts
    
    The cache automatically promotes database hits to memory cache and handles
    graceful degradation when database operations fail.
    
    Example:
        >>> cache = PersistentCache(
        ...     memory_ttl=3600.0,      # 1 hour memory cache
        ...     persistent_ttl=172800.0, # 48 hour database cache
        ...     max_memory_size=1000
        ... )
        >>> await cache.set("key", anime_details, xml_content="<xml>...")
        >>> result = await cache.get("key")
    """

    def __init__(
        self,
        provider_source: str = "anidb",
        db_path: str | None = None,
        memory_ttl: float = 3600.0,  # 1 hour for memory cache
        persistent_ttl: float = 172800.0,  # 48 hours for DB cache
        max_memory_size: int = 1000,
    ) -> None:
        """Initialize the persistent cache.

        Args:
            provider_source: Source provider name (e.g., "anidb", "anilist")
            db_path: Path to SQLite database file. If None, uses default location.
            memory_ttl: TTL for memory cache in seconds (default: 1 hour)
            persistent_ttl: TTL for database cache in seconds (default: 48 hours)
            max_memory_size: Maximum number of entries in memory cache (default: 1000)
        """
        self.provider_source = provider_source
        self.memory_ttl = memory_ttl
        self.persistent_ttl = persistent_ttl
        self.max_memory_size = max_memory_size

        # Initialize memory cache
        self._memory_cache = TTLCache(
            max_size=max_memory_size, default_ttl=memory_ttl
        )

        # Initialize database
        self._db = get_multi_provider_database(db_path)
        self._db_available = True

        # Thread safety
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats = PersistentCacheStats()
        self._memory_access_times: list[float] = []
        self._db_access_times: list[float] = []

        logger.info(
            f"Persistent cache initialized: memory_ttl={memory_ttl}s, "
            f"persistent_ttl={persistent_ttl}s, max_memory_size={max_memory_size}"
        )

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache using two-tier lookup.

        First checks the memory cache for fastest access. If not found,
        checks the database cache and promotes hits to memory cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if found and not expired, None otherwise
        """
        async with self._lock:
            # L1: Check memory cache first
            start_time = time.time()
            memory_result = await self._memory_cache.get(key)
            memory_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self._memory_access_times.append(memory_time)

            if memory_result is not None:
                self._stats.memory_hits += 1
                self._stats.total_hits += 1
                log_cache_operation("get", key, hit=True, source="memory")
                logger.debug(f"Memory cache hit for key: {key}")
                return memory_result

            self._stats.memory_misses += 1
            log_cache_operation("get", key, hit=False, source="memory")

            # L2: Check database cache
            if not self._db_available:
                self._stats.db_misses += 1
                self._stats.total_misses += 1
                return None

            try:
                start_time = time.time()
                db_row = await self._db.get_cache_entry(key)
                db_time = (time.time() - start_time) * 1000
                self._db_access_times.append(db_time)

                if db_row is None:
                    self._stats.db_misses += 1
                    self._stats.total_misses += 1
                    log_cache_operation("get", key, hit=False, source="database")
                    return None

                # Parse database entry
                cache_entry = PersistentCacheEntry.from_db_row(db_row)

                # Check if expired
                if cache_entry.is_expired():
                    # Remove expired entry
                    await self._db.delete_cache_entry(key)
                    self._stats.db_misses += 1
                    self._stats.total_misses += 1
                    log_cache_operation("get", key, hit=False, source="database", reason="expired")
                    logger.debug(f"Database cache entry expired for key: {key}")
                    return None

                # Deserialize the cached data
                parsed_data = self._deserialize_cached_data(
                    cache_entry.method_name, cache_entry.parsed_data_json
                )

                # Update access statistics in database
                await self._db.update_cache_access(key)

                # Promote to memory cache for future speed
                await self._memory_cache.set(key, parsed_data)

                self._stats.db_hits += 1
                self._stats.total_hits += 1
                log_cache_operation("get", key, hit=True, source="database")
                logger.debug(
                    f"Database cache hit for key: {key}, promoted to memory cache"
                )
                return parsed_data

            except DatabaseError as e:
                logger.warning(f"Database cache get failed for key {key}: {e}")
                self._handle_db_error("get", e)
                self._stats.db_misses += 1
                self._stats.total_misses += 1
                return None

    async def set(
        self, key: str, value: Any, xml_content: str | None = None
    ) -> None:
        """Store a value in both memory and database caches.

        Args:
            key: Cache key
            value: Value to cache (AnimeDetails or list of AnimeSearchResult)
            xml_content: Optional raw XML content for debugging
        """
        async with self._lock:
            # Store in memory cache
            await self._memory_cache.set(key, value)

            # Store in database cache if available
            if self._db_available:
                try:
                    # Determine method name and serialize data
                    method_name, parameters = self._parse_cache_key(key)
                    parameters_json = CacheSerializer.serialize_parameters(parameters)
                    parsed_data_json = self._serialize_cached_data(value)

                    # Calculate expiration time
                    expires_at = datetime.now() + timedelta(seconds=self.persistent_ttl)

                    # Calculate data size
                    data_size = CacheSerializer.calculate_data_size(
                        parsed_data_json, xml_content
                    )

                    # Store in database
                    await self._db.set_cache_entry(
                        cache_key=key,
                        provider_source=self.provider_source,
                        method_name=method_name,
                        parameters_json=parameters_json,
                        parsed_data_json=parsed_data_json,
                        expires_at=expires_at,
                        xml_content=xml_content,
                        data_size=data_size,
                    )

                    log_cache_operation("set", key, source="both")
                    logger.debug(
                        f"Cached value for key: {key} in both memory and database"
                    )

                except DatabaseError as e:
                    logger.warning(f"Database cache set failed for key {key}: {e}")
                    self._handle_db_error("set", e)
                    log_cache_operation("set", key, source="memory_only")
                    logger.debug(f"Cached value for key: {key} in memory only")
            else:
                log_cache_operation("set", key, source="memory_only")
                logger.debug(f"Cached value for key: {key} in memory only (DB unavailable)")

    async def delete(self, key: str) -> bool:
        """Remove a specific key from both caches.

        Args:
            key: Cache key to remove

        Returns:
            True if key was found and removed from either cache, False otherwise
        """
        async with self._lock:
            memory_deleted = await self._memory_cache.delete(key)
            db_deleted = False

            if self._db_available:
                try:
                    db_deleted = await self._db.delete_cache_entry(key)
                except DatabaseError as e:
                    logger.warning(f"Database cache delete failed for key {key}: {e}")
                    self._handle_db_error("delete", e)

            deleted = memory_deleted or db_deleted
            if deleted:
                logger.debug(f"Deleted cache entry for key: {key}")

            return deleted

    async def clear(self) -> None:
        """Clear all entries from both caches."""
        async with self._lock:
            await self._memory_cache.clear()

            if self._db_available:
                try:
                    cleared_count = await self._db.clear_cache()
                    logger.info(f"Cleared {cleared_count} entries from persistent cache")
                except DatabaseError as e:
                    logger.warning(f"Database cache clear failed: {e}")
                    self._handle_db_error("clear", e)
            else:
                logger.info("Cleared memory cache only (database unavailable)")

    async def cleanup_expired(self) -> int:
        """Remove expired entries from both caches.

        Returns:
            Number of expired entries removed from database
        """
        async with self._lock:
            # Memory cache handles expiration automatically
            memory_cleaned = await self._memory_cache.cleanup_expired()

            db_cleaned = 0
            if self._db_available:
                try:
                    db_cleaned = await self._db.cleanup_expired_cache()
                except DatabaseError as e:
                    logger.warning(f"Database cache cleanup failed: {e}")
                    self._handle_db_error("cleanup", e)

            total_cleaned = memory_cleaned + db_cleaned
            if total_cleaned > 0:
                logger.info(
                    f"Cleaned up {total_cleaned} expired entries "
                    f"(memory: {memory_cleaned}, database: {db_cleaned})"
                )

            return db_cleaned

    async def get_stats(self) -> PersistentCacheStats:
        """Get comprehensive cache statistics.

        Returns:
            PersistentCacheStats object with current statistics
        """
        async with self._lock:
            # Update memory cache stats
            memory_stats = await self._memory_cache.get_stats()
            self._stats.memory_entries = memory_stats.total_entries

            # Update database cache stats
            if self._db_available:
                try:
                    db_stats = await self._db.get_cache_stats()
                    self._stats.db_entries = db_stats["active_entries"]
                    self._stats.db_size_bytes = db_stats["db_file_size"]
                except DatabaseError as e:
                    logger.warning(f"Failed to get database cache stats: {e}")
                    self._handle_db_error("stats", e)

            # Calculate average access times
            if self._memory_access_times:
                self._stats.avg_memory_access_time = sum(self._memory_access_times) / len(
                    self._memory_access_times
                )
                # Keep only recent measurements (last 100)
                self._memory_access_times = self._memory_access_times[-100:]

            if self._db_access_times:
                self._stats.avg_db_access_time = sum(self._db_access_times) / len(
                    self._db_access_times
                )
                # Keep only recent measurements (last 100)
                self._db_access_times = self._db_access_times[-100:]

            # Estimate memory size (rough calculation)
            self._stats.memory_size_estimate = self._stats.memory_entries * 15000  # ~15KB per entry

            # Update totals
            self._stats.total_hits = self._stats.memory_hits + self._stats.db_hits
            self._stats.total_misses = self._stats.memory_misses + self._stats.db_misses

            # Update database availability status
            self._stats.db_available = self._db_available

            return self._stats.model_copy()

    def _serialize_cached_data(self, value: Any) -> str:
        """Serialize cached data to JSON string.

        Args:
            value: Value to serialize (AnimeDetails or list of AnimeSearchResult)

        Returns:
            JSON string representation

        Raises:
            ValueError: If serialization fails
        """
        if isinstance(value, AnimeDetails):
            return CacheSerializer.serialize_anime_details(value)
        elif isinstance(value, list) and all(
            isinstance(item, AnimeSearchResult) for item in value
        ):
            return CacheSerializer.serialize_search_results(value)
        else:
            raise ValueError(f"Unsupported cache value type: {type(value)}")

    def _deserialize_cached_data(self, method_name: str, json_str: str) -> Any:
        """Deserialize cached data from JSON string.

        Args:
            method_name: Name of the method that generated the cache
            json_str: JSON string to deserialize

        Returns:
            Deserialized object (AnimeDetails or list of AnimeSearchResult)

        Raises:
            ValueError: If deserialization fails
        """
        if method_name == "get_anime_details":
            return CacheSerializer.deserialize_anime_details(json_str)
        elif method_name == "search_anime":
            return CacheSerializer.deserialize_search_results(json_str)
        else:
            raise ValueError(f"Unknown method name for deserialization: {method_name}")

    def _parse_cache_key(self, cache_key: str) -> tuple[str, dict[str, Any]]:
        """Parse cache key to extract method name and parameters.

        Args:
            cache_key: Cache key in format "method_name:hash"

        Returns:
            Tuple of (method_name, parameters_dict)
        """
        if ":" not in cache_key:
            raise ValueError(f"Invalid cache key format: {cache_key}")

        method_name = cache_key.split(":", 1)[0]

        # For now, we'll extract basic parameters from common method names
        # This could be enhanced to store original parameters if needed
        if method_name == "get_anime_details":
            # Extract AID from cache key if possible, otherwise use placeholder
            return method_name, {"method": method_name}
        elif method_name == "search_anime":
            return method_name, {"method": method_name}
        else:
            return method_name, {"method": method_name}

    def _handle_db_error(self, operation: str, error: Exception) -> None:
        """Handle database errors gracefully.

        Args:
            operation: The operation that failed
            error: The exception that occurred
        """
        logger.warning(f"Database cache {operation} failed: {error}")

        # Mark database as unavailable for future operations
        if isinstance(error, DatabaseError):
            self._db_available = False
            logger.info("Database cache marked as unavailable, falling back to memory-only mode")

    async def invalidate_cache_key(self, method: str, **params: Any) -> bool:
        """Invalidate a specific cache entry by regenerating its key.

        Args:
            method: Method name (e.g., "search_anime", "get_anime_details")
            **params: Parameters used to generate the cache key

        Returns:
            True if cache entry was found and removed, False otherwise
        """
        cache_key = generate_cache_key(method, **params)
        return await self.delete(cache_key)


async def create_persistent_cache(
    provider_source: str = "anidb",
    db_path: str | None = None,
    memory_ttl: float = 3600.0,
    persistent_ttl: float = 172800.0,
    max_memory_size: int = 1000,
) -> PersistentCache:
    """Create and return a configured persistent cache instance.

    Args:
        provider_source: Source provider name (e.g., "anidb", "anilist")
        db_path: Path to SQLite database file
        memory_ttl: TTL for memory cache in seconds
        persistent_ttl: TTL for database cache in seconds
        max_memory_size: Maximum entries in memory cache

    Returns:
        Configured PersistentCache instance

    Example:
        >>> cache = await create_persistent_cache(
        ...     provider_source="anidb",
        ...     memory_ttl=1800,      # 30 minutes
        ...     persistent_ttl=86400, # 24 hours
        ...     max_memory_size=500
        ... )
    """
    cache = PersistentCache(
        provider_source=provider_source,
        db_path=db_path,
        memory_ttl=memory_ttl,
        persistent_ttl=persistent_ttl,
        max_memory_size=max_memory_size,
    )

    # Perform initial cleanup of expired entries
    try:
        await cache.cleanup_expired()
    except Exception as e:
        logger.warning(f"Initial cache cleanup failed: {e}")

    return cache