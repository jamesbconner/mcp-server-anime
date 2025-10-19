"""Multi-provider database manager for anime data.

This module provides a SQLite database manager that supports multiple anime data providers
with provider-specific tables, metadata management, and cross-provider functionality.
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError, DatabaseError
from .logging_config import get_logger
from .security import SecureQueryHelper, SecurityLogger, TableNameValidator

logger = get_logger(__name__)


class MultiProviderDatabase:
    """Multi-provider SQLite database manager for anime data.

    This class manages a SQLite database with provider-specific tables and metadata,
    supporting multiple anime data sources while maintaining data isolation and
    consistent schema patterns.
    """

    def __init__(self, db_path: str | None = None):
        """Initialize the multi-provider database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use user's cache directory
            cache_dir = Path.home() / ".cache" / "mcp-server-anime"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "anime_multi_provider.db"

        self.db_path = str(db_path)
        self._connection_pool: dict[str, sqlite3.Connection] = {}
        self._lock = asyncio.Lock()
        self._initialized_providers: set[str] = set()

        # Initialize core database structure
        self._init_core_database()

    def _init_core_database(self) -> None:
        """Initialize the core database structure with shared tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Create search transactions table (shared across providers)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS search_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        provider TEXT NOT NULL,
                        query TEXT NOT NULL,
                        result_count INTEGER NOT NULL,
                        response_time_ms REAL NOT NULL,
                        client_identifier TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for search transactions
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_transactions_provider 
                    ON search_transactions(provider)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_transactions_timestamp 
                    ON search_transactions(timestamp)
                """)

                # Create database metadata table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS database_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create persistent cache table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS persistent_cache (
                        cache_key TEXT PRIMARY KEY,
                        method_name TEXT NOT NULL,
                        parameters_json TEXT NOT NULL,
                        xml_content TEXT,
                        parsed_data_json TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        expires_at DATETIME NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed DATETIME NOT NULL,
                        data_size INTEGER NOT NULL
                    )
                """)

                # Create indexes for persistent cache
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persistent_cache_expires_at 
                    ON persistent_cache(expires_at)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persistent_cache_method 
                    ON persistent_cache(method_name)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persistent_cache_created_at 
                    ON persistent_cache(created_at)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persistent_cache_access_count 
                    ON persistent_cache(access_count)
                """)

                # Store database version
                conn.execute("""
                    INSERT OR REPLACE INTO database_metadata (key, value)
                    VALUES ('schema_version', '1.1')
                """)

                conn.commit()
                logger.info("Core database structure initialized successfully")

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize core database: {e}") from e

    async def initialize_provider(self, provider_name: str) -> None:
        """Initialize provider-specific tables and metadata.

        Args:
            provider_name: Name of the provider (e.g., 'anidb', 'anilist')

        Raises:
            DatabaseError: If provider initialization fails
            ConfigurationError: If provider name is invalid
        """
        if not provider_name or not provider_name.isalnum():
            raise ConfigurationError(
                f"Invalid provider name: {provider_name}. Must be alphanumeric."
            )

        async with self._lock:
            if provider_name in self._initialized_providers:
                logger.debug(f"Provider {provider_name} already initialized")
                return

            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Enable foreign keys
                    conn.execute("PRAGMA foreign_keys = ON")

                    # Create provider-specific titles table
                    titles_table = TableNameValidator.validate_table_name(
                        f"{provider_name}_titles", provider_name
                    )
                    conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {titles_table} (
                            aid INTEGER NOT NULL,
                            title_type INTEGER NOT NULL,
                            language TEXT NOT NULL,
                            title TEXT NOT NULL,
                            title_normalized TEXT NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (aid, title_type, language, title)
                        )
                    """)

                    # Create indexes for fast searching
                    conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{provider_name}_titles_normalized 
                        ON {titles_table}(title_normalized)
                    """)

                    conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{provider_name}_titles_aid 
                        ON {titles_table}(aid)
                    """)

                    conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{provider_name}_titles_type 
                        ON {titles_table}(title_type)
                    """)

                    # Create composite index for search performance
                    conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{provider_name}_search_composite
                        ON {titles_table}(title_normalized, title_type, language)
                    """)

                    # Create covering index for search results
                    conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{provider_name}_search_covering
                        ON {titles_table}(title_normalized, aid, title, title_type)
                    """)

                    # Create provider-specific metadata table
                    metadata_table = TableNameValidator.validate_table_name(
                        f"{provider_name}_metadata", provider_name
                    )
                    conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {metadata_table} (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Initialize provider metadata
                    conn.execute(
                        f"""
                        INSERT OR REPLACE INTO {metadata_table} (key, value)
                        VALUES ('provider_initialized', ?)
                    """,
                        (datetime.now().isoformat(),),
                    )

                    conn.commit()

                    self._initialized_providers.add(provider_name)
                    logger.info(f"Provider {provider_name} initialized successfully")

            except sqlite3.Error as e:
                raise DatabaseError(
                    f"Failed to initialize provider {provider_name}: {e}"
                ) from e

    async def get_provider_metadata(self, provider_name: str, key: str) -> str | None:
        """Get provider-specific metadata value.

        Args:
            provider_name: Name of the provider
            key: Metadata key to retrieve

        Returns:
            Metadata value or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        if provider_name not in self._initialized_providers:
            await self.initialize_provider(provider_name)

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Validate table name for security
                metadata_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_metadata", provider_name
                )
                
                # Use secure query helper
                query, params = SecureQueryHelper.build_metadata_query(metadata_table, key)
                cursor = conn.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else None

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to get metadata for {provider_name}.{key}: {e}"
            ) from e

    async def set_provider_metadata(
        self, provider_name: str, key: str, value: str
    ) -> None:
        """Set provider-specific metadata value.

        Args:
            provider_name: Name of the provider
            key: Metadata key to set
            value: Metadata value to store

        Raises:
            DatabaseError: If database operation fails
        """
        if provider_name not in self._initialized_providers:
            await self.initialize_provider(provider_name)

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Validate table name for security
                metadata_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_metadata", provider_name
                )
                conn.execute(
                    f"""
                    INSERT OR REPLACE INTO {metadata_table} (key, value, updated_at)
                    VALUES (?, ?, ?)
                """,
                    (key, value, datetime.now().isoformat()),
                )
                conn.commit()

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to set metadata for {provider_name}.{key}: {e}"
            ) from e

    async def search_titles(
        self, provider_name: str, query: str, limit: int = 10
    ) -> list[tuple[int, str, str, int]]:
        """Search for anime titles in provider-specific table.

        Args:
            provider_name: Name of the provider to search
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of tuples: (aid, title, language, title_type)
            Sorted by relevance (exact matches first, then partial matches)

        Raises:
            DatabaseError: If search operation fails
        """
        if not query or len(query.strip()) < 2:
            return []

        if provider_name not in self._initialized_providers:
            await self.initialize_provider(provider_name)

        query_lower = query.strip().lower()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Validate table name for security
                titles_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_titles", provider_name
                )

                # First, try exact matches using secure query helper
                exact_query, exact_params = SecureQueryHelper.build_select_query(
                    titles_table,
                    ["DISTINCT aid", "title", "language", "title_type"],
                    where_clause="title_normalized = ?",
                    order_by="title_type ASC, language ASC",
                    limit=limit
                )
                exact_results = conn.execute(
                    exact_query, [query_lower] + exact_params
                ).fetchall()

                if len(exact_results) >= limit:
                    return exact_results

                # Then try prefix matches using secure query helper
                remaining_limit = limit - len(exact_results)
                prefix_query, prefix_params = SecureQueryHelper.build_select_query(
                    titles_table,
                    ["DISTINCT aid", "title", "language", "title_type"],
                    where_clause="title_normalized LIKE ? AND title_normalized != ?",
                    order_by="title_type ASC, language ASC",
                    limit=remaining_limit
                )
                prefix_results = conn.execute(
                    prefix_query, [f"{query_lower}%", query_lower] + prefix_params
                ).fetchall()

                # Combine results
                all_results = exact_results + prefix_results
                if len(all_results) >= limit:
                    return all_results[:limit]

                # Finally, try substring matches using secure query helper
                remaining_limit = limit - len(all_results)
                substring_query, substring_params = SecureQueryHelper.build_select_query(
                    titles_table,
                    ["DISTINCT aid", "title", "language", "title_type"],
                    where_clause="title_normalized LIKE ? AND title_normalized NOT LIKE ? AND title_normalized != ?",
                    order_by="title_type ASC, language ASC",
                    limit=remaining_limit
                )
                substring_results = conn.execute(
                    substring_query, 
                    [f"%{query_lower}%", f"{query_lower}%", query_lower] + substring_params
                ).fetchall()

                return (all_results + substring_results)[:limit]

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Search failed for provider {provider_name}: {e}"
            ) from e

    async def bulk_insert_titles(
        self, provider_name: str, titles: list[tuple[int, int, str, str]]
    ) -> int:
        """Bulk insert titles for a provider.

        Args:
            provider_name: Name of the provider
            titles: List of tuples (aid, title_type, language, title)

        Returns:
            Number of titles inserted

        Raises:
            DatabaseError: If bulk insert fails
        """
        if provider_name not in self._initialized_providers:
            await self.initialize_provider(provider_name)

        if not titles:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Validate table name for security
                titles_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_titles", provider_name
                )

                # Clear existing data for this provider using secure query helper
                delete_query, delete_params = SecureQueryHelper.build_delete_query(titles_table)
                conn.execute(delete_query, delete_params)

                # Prepare data with normalized titles
                normalized_titles = []
                for aid, title_type, language, title in titles:
                    title_normalized = title.lower()
                    normalized_titles.append(
                        (aid, title_type, language, title, title_normalized)
                    )

                # Bulk insert
                conn.executemany(
                    f"""
                    INSERT OR IGNORE INTO {titles_table} 
                    (aid, title_type, language, title, title_normalized)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    normalized_titles,
                )

                # Update metadata with insert timestamp
                metadata_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_metadata", provider_name
                )
                conn.execute(
                    f"""
                    INSERT OR REPLACE INTO {metadata_table} (key, value, updated_at)
                    VALUES ('last_titles_update', ?, ?)
                """,
                    (datetime.now().isoformat(), datetime.now().isoformat()),
                )

                conn.commit()

                inserted_count = len(normalized_titles)
                logger.info(
                    f"Bulk inserted {inserted_count} titles for provider {provider_name}"
                )
                return inserted_count

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Bulk insert failed for provider {provider_name}: {e}"
            ) from e

    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics.

        Returns:
            Dictionary with database statistics including provider-specific data

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {
                    "database_path": self.db_path,
                    "initialized_providers": list(self._initialized_providers),
                    "providers": {},
                    "search_transactions": {},
                }

                # Get provider-specific stats
                for provider_name in self._initialized_providers:
                    # Validate table names for security
                    titles_table = TableNameValidator.validate_table_name(
                        f"{provider_name}_titles", provider_name
                    )
                    metadata_table = TableNameValidator.validate_table_name(
                        f"{provider_name}_metadata", provider_name
                    )

                    # Get title counts using secure query helper
                    count_query, count_params = SecureQueryHelper.build_count_query(titles_table)
                    total_titles = conn.execute(count_query, count_params).fetchone()[0]
                    
                    # Get unique anime count using secure query helper
                    unique_query, unique_params = SecureQueryHelper.build_select_query(
                        titles_table, ["COUNT(DISTINCT aid)"]
                    )
                    unique_anime = conn.execute(unique_query, unique_params).fetchone()[0]

                    # Get last update time using secure query helper
                    update_query, update_params = SecureQueryHelper.build_metadata_query(
                        metadata_table, 'last_titles_update'
                    )
                    last_update_result = conn.execute(update_query, update_params).fetchone()
                    last_update = last_update_result[0] if last_update_result else None

                    stats["providers"][provider_name] = {
                        "total_titles": total_titles,
                        "unique_anime": unique_anime,
                        "last_update": last_update,
                    }

                # Get search transaction stats
                total_searches = conn.execute(
                    "SELECT COUNT(*) FROM search_transactions"
                ).fetchone()[0]
                stats["search_transactions"]["total_searches"] = total_searches

                # Get search stats by provider
                provider_search_stats = conn.execute("""
                    SELECT provider, COUNT(*) as search_count, AVG(response_time_ms) as avg_response_time
                    FROM search_transactions
                    GROUP BY provider
                """).fetchall()

                stats["search_transactions"]["by_provider"] = {
                    provider: {
                        "search_count": count,
                        "avg_response_time_ms": round(avg_time, 2) if avg_time else 0,
                    }
                    for provider, count, avg_time in provider_search_stats
                }

                return stats

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get database stats: {e}") from e

    async def cleanup_old_transactions(self, retention_days: int = 30) -> int:
        """Clean up old search transactions.

        Args:
            retention_days: Number of days to retain transactions

        Returns:
            Number of transactions deleted

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_date = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                cutoff_date = cutoff_date.replace(day=cutoff_date.day - retention_days)

                cursor = conn.execute(
                    """
                    DELETE FROM search_transactions 
                    WHERE created_at < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old search transactions")

                return deleted_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to cleanup old transactions: {e}") from e

    # Persistent Cache Methods

    async def get_cache_entry(self, cache_key: str) -> tuple | None:
        """Get a cache entry from the database.

        Args:
            cache_key: The cache key to retrieve

        Returns:
            Database row tuple or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT cache_key, method_name, parameters_json, xml_content, 
                           parsed_data_json, created_at, expires_at, access_count, 
                           last_accessed, data_size
                    FROM persistent_cache 
                    WHERE cache_key = ?
                """,
                    (cache_key,),
                )
                return cursor.fetchone()

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get cache entry {cache_key}: {e}") from e

    async def set_cache_entry(
        self,
        cache_key: str,
        method_name: str,
        parameters_json: str,
        parsed_data_json: str,
        expires_at: datetime,
        xml_content: str | None = None,
        data_size: int | None = None,
    ) -> None:
        """Store a cache entry in the database.

        Args:
            cache_key: Unique cache key
            method_name: Name of the method that generated this cache
            parameters_json: JSON string of parameters
            parsed_data_json: JSON string of parsed data
            expires_at: Expiration timestamp
            xml_content: Optional raw XML content
            data_size: Size of cached data in bytes

        Raises:
            DatabaseError: If database operation fails
        """
        if data_size is None:
            # Calculate data size
            data_size = len(parsed_data_json.encode('utf-8'))
            if xml_content:
                data_size += len(xml_content.encode('utf-8'))

        now = datetime.now()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO persistent_cache 
                    (cache_key, method_name, parameters_json, xml_content, 
                     parsed_data_json, created_at, expires_at, access_count, 
                     last_accessed, data_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        cache_key,
                        method_name,
                        parameters_json,
                        xml_content,
                        parsed_data_json,
                        now.isoformat(),
                        expires_at.isoformat(),
                        0,  # Initial access count
                        now.isoformat(),
                        data_size,
                    ),
                )
                conn.commit()

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to set cache entry {cache_key}: {e}") from e

    async def update_cache_access(self, cache_key: str) -> None:
        """Update access statistics for a cache entry.

        Args:
            cache_key: The cache key to update

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE persistent_cache 
                    SET access_count = access_count + 1, 
                        last_accessed = ?
                    WHERE cache_key = ?
                """,
                    (datetime.now().isoformat(), cache_key),
                )
                conn.commit()

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to update cache access for {cache_key}: {e}") from e

    async def delete_cache_entry(self, cache_key: str) -> bool:
        """Delete a specific cache entry.

        Args:
            cache_key: The cache key to delete

        Returns:
            True if entry was deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM persistent_cache WHERE cache_key = ?",
                    (cache_key,),
                )
                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to delete cache entry {cache_key}: {e}") from e

    async def clear_cache(self) -> int:
        """Clear all cache entries from the database.

        Returns:
            Number of entries deleted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM persistent_cache")
                conn.commit()
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Cleared {deleted_count} cache entries from database")
                
                return deleted_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to clear cache: {e}") from e

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries from the database.

        Returns:
            Number of expired entries removed

        Raises:
            DatabaseError: If cleanup operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                cursor = conn.execute(
                    "DELETE FROM persistent_cache WHERE expires_at <= ?",
                    (now,),
                )
                conn.commit()
                expired_count = cursor.rowcount
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired cache entries")
                
                return expired_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to cleanup expired cache entries: {e}") from e

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics from the database.

        Returns:
            Dictionary with cache statistics

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get total entries
                total_entries = conn.execute(
                    "SELECT COUNT(*) FROM persistent_cache"
                ).fetchone()[0]

                # Get expired entries count
                now = datetime.now().isoformat()
                expired_entries = conn.execute(
                    "SELECT COUNT(*) FROM persistent_cache WHERE expires_at <= ?",
                    (now,),
                ).fetchone()[0]

                # Get total data size
                total_size = conn.execute(
                    "SELECT COALESCE(SUM(data_size), 0) FROM persistent_cache"
                ).fetchone()[0]

                # Get method breakdown
                method_stats = conn.execute("""
                    SELECT method_name, COUNT(*) as count, 
                           COALESCE(SUM(data_size), 0) as total_size,
                           COALESCE(SUM(access_count), 0) as total_accesses
                    FROM persistent_cache
                    GROUP BY method_name
                """).fetchall()

                # Get database file size
                db_file_size = 0
                try:
                    from pathlib import Path
                    db_file_size = Path(self.db_path).stat().st_size
                except (OSError, FileNotFoundError):
                    pass

                return {
                    "total_entries": total_entries,
                    "expired_entries": expired_entries,
                    "active_entries": total_entries - expired_entries,
                    "total_data_size": total_size,
                    "db_file_size": db_file_size,
                    "methods": {
                        method: {
                            "count": count,
                            "total_size": size,
                            "total_accesses": accesses,
                        }
                        for method, count, size, accesses in method_stats
                    },
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get cache stats: {e}") from e

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        async with self._lock:
            for conn in self._connection_pool.values():
                try:
                    conn.close()
                except sqlite3.Error:
                    pass  # Ignore errors during cleanup

            self._connection_pool.clear()
            logger.debug("Database connections closed")


# Global database instance
_database_instance: MultiProviderDatabase | None = None


def get_multi_provider_database(db_path: str | None = None) -> MultiProviderDatabase:
    """Get the global multi-provider database instance.

    Args:
        db_path: Optional database path (only used for first call)

    Returns:
        MultiProviderDatabase instance
    """
    global _database_instance
    if _database_instance is None:
        _database_instance = MultiProviderDatabase(db_path)
    return _database_instance


async def initialize_database_for_provider(
    provider_name: str, db_path: str | None = None
) -> MultiProviderDatabase:
    """Initialize database for a specific provider.

    Args:
        provider_name: Name of the provider to initialize
        db_path: Optional database path

    Returns:
        Initialized MultiProviderDatabase instance
    """
    db = get_multi_provider_database(db_path)
    await db.initialize_provider(provider_name)
    return db
