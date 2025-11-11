"""Search service for AniDB using local titles database.

This module provides anime search functionality using a local database
of AniDB titles, with automatic updates and fallback mechanisms.
"""

import asyncio
from datetime import datetime

from mcp_server_anime.core.exceptions import DatabaseError, ServiceError
from mcp_server_anime.core.logging_config import get_logger
from mcp_server_anime.core.models import AnimeSearchResult
from mcp_server_anime.core.multi_provider_db import get_multi_provider_database
from mcp_server_anime.core.security import SecurityLogger
from mcp_server_anime.core.transaction_logger import log_search_transaction

from .titles_downloader import TitlesDownloader

logger = get_logger(__name__)


class AniDBSearchService:
    """Search service for AniDB anime titles."""

    def __init__(self, auto_update: bool = True):
        """Initialize the search service.

        Args:
            auto_update: Whether to automatically update the titles database
        """
        self.auto_update = auto_update
        self.db = get_multi_provider_database()
        self.downloader = TitlesDownloader()
        self.provider_name = "anidb"
        self._update_lock = asyncio.Lock()

    async def ensure_database_ready(self) -> bool:
        """Ensure the titles database is ready for searching.

        Returns:
            True if database is ready, False if update failed
        """
        async with self._update_lock:
            try:
                # Initialize provider in database
                await self.db.initialize_provider(self.provider_name)

                # Check if database needs updating
                stats = await self.db.get_database_stats()
                provider_stats = stats.get("providers", {}).get(self.provider_name, {})

                if not self.auto_update or provider_stats.get("total_titles", 0) > 0:
                    if provider_stats.get("total_titles", 0) > 0:
                        logger.debug(
                            f"Database ready: {provider_stats['unique_anime']} anime, {provider_stats['total_titles']} titles"
                        )
                        return True

                # Try to update database
                logger.info("Database needs updating, checking download status...")

                # Check if we can download
                can_download, error_message = await self.downloader.can_download()
                if not can_download:
                    logger.warning(f"Cannot download titles file: {error_message}")
                    # Check if existing database is usable
                    if provider_stats.get("total_titles", 0) > 0:
                        logger.info("Using existing database despite being outdated")
                        return True
                    else:
                        logger.error("No usable database and cannot download")
                        return False

                # Download and update
                logger.info("Downloading titles file...")
                success = await self.downloader.download_titles_file()

                if success:
                    logger.info("Loading titles into database...")
                    titles_loaded = await self._load_titles_from_file()
                    logger.info(
                        f"Database updated successfully: {titles_loaded} titles loaded"
                    )
                    return True
                else:
                    logger.error("Failed to download titles file")
                    return False

            except Exception as e:
                logger.error(f"Failed to ensure database ready: {e}")
                # Try to use existing database if available
                try:
                    stats = await self.db.get_database_stats()
                    provider_stats = stats.get("providers", {}).get(
                        self.provider_name, {}
                    )
                    if provider_stats.get("total_titles", 0) > 0:
                        logger.info("Using existing database despite update failure")
                        return True
                except Exception as fallback_error:
                    # Log the fallback database check failure but continue
                    SecurityLogger.log_exception_with_context(
                        fallback_error,
                        {
                            "operation": "fallback_database_check",
                            "provider": self.provider_name,
                            "original_error": str(e),
                        },
                    )
                    logger.debug(
                        f"Could not check existing database stats: {fallback_error}"
                    )
                return False

    async def search_anime(
        self, query: str, limit: int = 10, client_id: str | None = None
    ) -> list[AnimeSearchResult]:
        """Search for anime by title with transaction logging.

        Args:
            query: Search query string
            limit: Maximum number of results
            client_id: Optional client identifier for tracking

        Returns:
            List of AnimeSearchResult objects

        Raises:
            ServiceError: If search fails
        """
        if not query or len(query.strip()) < 2:
            return []

        # Track search performance
        start_time = datetime.now()
        search_results = []

        try:
            # Ensure database is ready
            if not await self.ensure_database_ready():
                raise ServiceError(
                    "Search database is not available. Please try again later.",
                    service_name="anidb_search",
                    operation="search_anime",
                )

            # Perform search using multi-provider database
            results = await self.db.search_titles(
                self.provider_name, query.strip(), limit
            )

            # Convert to AnimeSearchResult objects
            seen_aids = set()

            for aid, title, _language, _title_type in results:
                # Avoid duplicates (same anime with different titles)
                if aid in seen_aids:
                    continue
                seen_aids.add(aid)

                # Determine anime type (we don't have this info in titles file)
                # This would need to be enhanced with additional data or API calls
                anime_type = "Unknown"
                year = None  # Not available in titles file

                search_result = AnimeSearchResult(
                    aid=aid, title=title, type=anime_type, year=year
                )
                search_results.append(search_result)

            # Calculate response time
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log the search transaction
            try:
                await log_search_transaction(
                    provider=self.provider_name,
                    query=query.strip(),
                    result_count=len(search_results),
                    response_time_ms=response_time_ms,
                    client_id=client_id,
                )
            except Exception as log_error:
                # Don't fail the search if logging fails
                logger.warning(f"Failed to log search transaction: {log_error}")

            logger.info(
                f"Search for '{query}' returned {len(search_results)} results in {response_time_ms:.1f}ms"
            )
            return search_results

        except DatabaseError as e:
            raise ServiceError(
                f"Database error during search: {e}",
                service_name="anidb_search",
                operation="search_anime",
                cause=e,
            ) from e
        except Exception as e:
            raise ServiceError(
                f"Unexpected error during search: {e}",
                service_name="anidb_search",
                operation="search_anime",
                cause=e,
            ) from e

    async def _load_titles_from_file(self) -> int:
        """Load titles from downloaded file into the multi-provider database.

        Returns:
            Number of titles loaded
        """
        import gzip

        # Get the titles file path from downloader
        titles_file_path = self.downloader.titles_file_path

        if not titles_file_path.exists():
            raise ServiceError(
                f"Titles file not found: {titles_file_path}",
                service_name="anidb_search",
                operation="load_titles",
            )

        titles_data = []

        try:
            with gzip.open(titles_file_path, "rt", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    try:
                        parts = line.split("|", 3)
                        if len(parts) != 4:
                            logger.warning(f"Invalid line {line_num}: {line}")
                            continue

                        aid = int(parts[0])
                        title_type = int(parts[1])
                        language = parts[2]
                        title = parts[3]

                        titles_data.append((aid, title_type, language, title))

                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse line {line_num}: {line} - {e}")
                        continue

            # Bulk insert into database
            titles_loaded = await self.db.bulk_insert_titles(
                self.provider_name, titles_data
            )
            logger.info(
                f"Loaded {titles_loaded} titles into {self.provider_name} database"
            )
            return titles_loaded

        except Exception as e:
            raise ServiceError(
                f"Failed to load titles from file: {e}",
                service_name="anidb_search",
                operation="load_titles",
                cause=e,
            ) from e

    async def get_titles_for_anime(self, aid: int) -> list[tuple[str, str, int]]:
        """Get all titles for a specific anime.

        Args:
            aid: Anime ID

        Returns:
            List of tuples: (title, language, type)
        """
        # This would require a more sophisticated query method in the multi-provider DB
        # For now, return empty list as this is not a critical feature
        return []

    async def get_search_stats(self) -> dict:
        """Get search service statistics.

        Returns:
            Dictionary with service statistics
        """
        db_stats = await self.db.get_database_stats()
        download_status = await self.downloader.get_download_status()

        provider_stats = db_stats.get("providers", {}).get(self.provider_name, {})

        return {
            "database": provider_stats,
            "download": download_status,
            "service_ready": provider_stats.get("total_titles", 0) > 0,
        }

    async def force_update(self) -> bool:
        """Force an update of the titles database.

        This bypasses the daily download limit check - use with caution!

        Returns:
            True if update was successful
        """
        async with self._update_lock:
            try:
                logger.warning("Forcing database update (bypassing rate limits)")

                success = await self.downloader.download_titles_file(force=True)
                if success:
                    titles_loaded = await self._load_titles_from_file()
                    logger.info(
                        f"Forced update completed: {titles_loaded} titles loaded"
                    )
                    return True
                else:
                    logger.error("Forced update failed")
                    return False

            except Exception as e:
                logger.error(f"Forced update failed: {e}")
                return False


# Global search service instance
_search_service: AniDBSearchService | None = None


def get_search_service() -> AniDBSearchService:
    """Get the global search service instance.

    Returns:
        AniDBSearchService instance
    """
    global _search_service
    if _search_service is None:
        _search_service = AniDBSearchService()
    return _search_service


async def search_anime_titles(query: str, limit: int = 10) -> list[AnimeSearchResult]:
    """Convenience function to search anime titles.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of AnimeSearchResult objects
    """
    service = get_search_service()
    return await service.search_anime(query, limit)
