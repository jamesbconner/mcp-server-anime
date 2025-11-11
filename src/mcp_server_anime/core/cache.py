"""In-memory caching mechanism with TTL support for API responses.

This module provides a thread-safe, TTL-based caching system for storing and retrieving
anime data from API responses. It includes automatic expiration, size management,
and cache key generation based on request parameters.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheEntry(BaseModel, Generic[T]):
    """Represents a single cache entry with TTL support.

    Attributes:
        value: The cached value
        created_at: Timestamp when the entry was created
        ttl: Time-to-live in seconds
        access_count: Number of times this entry has been accessed
        last_accessed: Timestamp of last access
    """

    value: T
    created_at: float = Field(default_factory=time.time)
    ttl: float
    access_count: int = Field(default=0)
    last_accessed: float = Field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired.

        Returns:
            True if the entry has expired, False otherwise
        """
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """Update access statistics for the cache entry."""
        self.access_count += 1
        self.last_accessed = time.time()

    def age(self) -> float:
        """Get the age of the cache entry in seconds.

        Returns:
            Age in seconds since creation
        """
        return time.time() - self.created_at

    def time_to_expiry(self) -> float:
        """Get the time remaining until expiry in seconds.

        Returns:
            Seconds until expiry (negative if already expired)
        """
        return self.ttl - self.age()


class CacheStats(BaseModel):
    """Statistics about cache performance and usage.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted due to size limits
        expirations: Number of entries that expired naturally
        total_entries: Current number of entries in cache
        max_size: Maximum cache size
        hit_rate: Cache hit rate as a percentage
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_entries: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage.

        Returns:
            Hit rate percentage (0.0 to 100.0)
        """
        total_requests = self.hits + self.misses
        if total_requests == 0:
            return 0.0
        return (self.hits / total_requests) * 100.0


class TTLCache:
    """Thread-safe in-memory cache with TTL support and size management.

    This cache provides automatic expiration of entries based on TTL (time-to-live),
    size-based eviction using LRU policy, and comprehensive statistics tracking.

    Example:
        >>> cache = TTLCache(max_size=1000, default_ttl=3600)
        >>> await cache.set("key1", {"data": "value"}, ttl=1800)
        >>> result = await cache.get("key1")
        >>> if result is not None:
        ...     print(f"Cached data: {result}")
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0) -> None:
        """Initialize the TTL cache.

        Args:
            max_size: Maximum number of entries to store (default: 1000)
            default_ttl: Default TTL in seconds for entries (default: 3600)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry[Any]] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats(max_size=max_size)

        logger.info(
            f"TTL cache initialized with max_size={max_size}, default_ttl={default_ttl}"
        )

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                logger.debug(f"Cache miss for key: {key}")
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                self._stats.total_entries = len(self._cache)
                logger.debug(f"Cache entry expired for key: {key}")
                return None

            # Update access statistics
            entry.touch()
            self._stats.hits += 1
            logger.debug(f"Cache hit for key: {key} (age: {entry.age():.1f}s)")
            return entry.value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        async with self._lock:
            # If key already exists, just update it
            if key in self._cache:
                entry = CacheEntry(value=value, ttl=ttl)
                self._cache[key] = entry
            else:
                # Check if we need to evict entries to make room for new key
                if len(self._cache) >= self.max_size:
                    await self._evict_lru()

                # Create new cache entry
                entry = CacheEntry(value=value, ttl=ttl)
                self._cache[key] = entry

            self._stats.total_entries = len(self._cache)
            logger.debug(f"Cached value for key: {key} (ttl: {ttl}s)")

    async def delete(self, key: str) -> bool:
        """Remove a specific key from the cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was found and removed, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.total_entries = len(self._cache)
                logger.debug(f"Deleted cache entry for key: {key}")
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._stats.total_entries = 0
            logger.info(f"Cleared {cleared_count} entries from cache")

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.expirations += 1

            self._stats.total_entries = len(self._cache)

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    async def _evict_lru(self) -> None:
        """Evict the least recently used entry to make room for new entries."""
        if not self._cache:
            return

        # Find the entry with the oldest last_accessed time
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]
        self._stats.evictions += 1
        self._stats.total_entries = len(self._cache)
        logger.debug(f"Evicted LRU cache entry: {lru_key}")

    async def get_stats(self) -> CacheStats:
        """Get current cache statistics.

        Returns:
            CacheStats object with current statistics
        """
        async with self._lock:
            self._stats.total_entries = len(self._cache)
            return self._stats.model_copy()

    async def get_keys(self) -> list[str]:
        """Get all cache keys (for debugging/monitoring).

        Returns:
            List of all cache keys
        """
        async with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """Get current number of entries in cache.

        Returns:
            Number of entries currently in cache
        """
        return len(self._cache)


def generate_cache_key(method: str, **params: Any) -> str:
    """Generate a consistent cache key from method name and parameters.

    Creates a deterministic cache key by combining the method name with
    a hash of the sorted parameters. This ensures that identical requests
    produce the same cache key regardless of parameter order.

    Note: MD5 is used for cache key generation only (non-cryptographic purpose).
    This is safe as cache keys don't require cryptographic security.

    Args:
        method: Name of the method/operation being cached
        **params: Parameters to include in the cache key

    Returns:
        Generated cache key string

    Example:
        >>> key1 = generate_cache_key("search_anime", query="evangelion", limit=10)
        >>> key2 = generate_cache_key("search_anime", limit=10, query="evangelion")
        >>> assert key1 == key2  # Same key regardless of parameter order
    """
    # Sort parameters to ensure consistent key generation
    sorted_params = dict(sorted(params.items()))

    # Create a JSON representation of the parameters
    params_json = json.dumps(sorted_params, sort_keys=True, separators=(",", ":"))

    # Generate hash of the parameters (MD5 used for non-cryptographic cache key generation)
    params_hash = hashlib.md5(
        params_json.encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:16]

    # Combine method name with parameter hash
    cache_key = f"{method}:{params_hash}"

    logger.debug(
        f"Generated cache key: {cache_key} for method: {method}, params: {sorted_params}"
    )
    return cache_key


async def create_cache(max_size: int = 1000, default_ttl: float = 3600.0) -> TTLCache:
    """Create and return a configured TTL cache instance.

    Args:
        max_size: Maximum number of entries to store
        default_ttl: Default TTL in seconds for entries

    Returns:
        Configured TTLCache instance

    Example:
        >>> cache = await create_cache(max_size=500, default_ttl=1800)
        >>> await cache.set("test_key", {"data": "value"})
    """
    return TTLCache(max_size=max_size, default_ttl=default_ttl)
