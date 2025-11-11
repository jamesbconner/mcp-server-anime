"""AniDB service layer for anime data retrieval.

This module provides the main service interface for interacting with the AniDB HTTP API.
It integrates the HTTP client, XML parsing, and caching to provide high-level methods
for searching anime and retrieving detailed anime information.
"""

import time
from typing import Any
from urllib.parse import urljoin

from mcp_server_anime.core.cache import generate_cache_key
from mcp_server_anime.core.error_handler import with_error_handling, with_retry
from mcp_server_anime.core.exceptions import (
    APIError,
    DataValidationError,
    ServiceError,
    XMLParsingError,
)
from mcp_server_anime.core.http_client import HTTPClient, create_http_client
from mcp_server_anime.core.logging_config import (
    get_logger,
    log_cache_operation,
    log_performance,
    set_request_context,
)
from mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from mcp_server_anime.core.persistent_cache import (
    PersistentCache,
    create_persistent_cache,
)
from mcp_server_anime.core.security import ensure_not_none

from .config import AniDBConfig, load_config
from .search_service import get_search_service
from .xml_parser import parse_anime_details

logger = get_logger(__name__)


class AniDBService:
    """Service for interacting with the AniDB HTTP API.

    This service provides high-level methods for searching anime and retrieving
    detailed anime information. It handles URL construction, parameter validation,
    HTTP requests, XML parsing, and error handling.

    Example:
        >>> config = load_config()
        >>> async with AniDBService(config) as service:
        ...     results = await service.search_anime("evangelion")
        ...     details = await service.get_anime_details(results[0].aid)
    """

    def __init__(self, config: AniDBConfig | None = None) -> None:
        """Initialize the AniDB service.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or load_config()
        self._http_client: HTTPClient | None = None
        self._cache: PersistentCache | None = None
        self._closed = False

        logger.info("AniDB service initialized")

    async def __aenter__(self) -> "AniDBService":
        """Async context manager entry."""
        self._ensure_http_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def _ensure_http_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._http_client is None or self._http_client.is_closed():
            self._http_client = create_http_client(
                rate_limit_delay=self.config.rate_limit_delay,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
                headers=self.config.get_http_headers(),
            )

    async def _ensure_cache(self) -> None:
        """Ensure cache is initialized (persistent or memory-only based on config)."""
        if self._cache is None:
            # Always use persistent cache for now, but make it configurable in the future
            # The persistent cache gracefully falls back to memory-only if DB fails
            self._cache = await create_persistent_cache(
                provider_source="anidb",
                db_path=self.config.cache_db_path,
                memory_ttl=float(self.config.cache_ttl),
                persistent_ttl=float(self.config.persistent_cache_ttl),
                max_memory_size=self.config.memory_cache_size,
            )
            logger.debug(
                f"Persistent cache initialized with memory_ttl={self.config.cache_ttl}s, "
                f"persistent_ttl={self.config.persistent_cache_ttl}s, "
                f"max_memory_size={self.config.memory_cache_size}, "
                f"enabled={self.config.persistent_cache_enabled}"
            )

    async def close(self) -> None:
        """Close the service and clean up resources."""
        if self._http_client and not self._http_client.is_closed():
            await self._http_client.close()
        # Note: We don't clear the cache here as it's meant to persist across service instances
        # The persistent cache is shared and should only be cleared explicitly via clear_cache()
        self._closed = True
        logger.debug("AniDB service closed")

    def _validate_search_params(self, query: str, limit: int) -> None:
        """Validate search parameters.

        Args:
            query: Search query string
            limit: Maximum number of results

        Raises:
            DataValidationError: If parameters are invalid
        """
        if not query or not query.strip():
            raise DataValidationError(
                "Search query cannot be empty",
                field_name="query",
                field_value=query,
                code="INVALID_QUERY",
            )

        if len(query.strip()) < 2:
            raise DataValidationError(
                "Search query must be at least 2 characters long",
                field_name="query",
                field_value=query,
                code="QUERY_TOO_SHORT",
            )

        if limit < 1:
            raise DataValidationError(
                "Limit must be at least 1",
                field_name="limit",
                field_value=limit,
                code="INVALID_LIMIT",
            )

        if limit > 100:
            raise DataValidationError(
                "Limit cannot exceed 100",
                field_name="limit",
                field_value=limit,
                code="LIMIT_TOO_HIGH",
            )

    def _validate_anime_id(self, aid: int) -> None:
        """Validate anime ID parameter.

        Args:
            aid: Anime ID to validate

        Raises:
            DataValidationError: If anime ID is invalid
        """
        if not isinstance(aid, int):
            raise DataValidationError(
                "Anime ID must be an integer",
                field_name="aid",
                field_value=aid,
                code="INVALID_AID_TYPE",
            )

        if aid < 1:
            raise DataValidationError(
                "Anime ID must be a positive integer",
                field_name="aid",
                field_value=aid,
                code="INVALID_AID_VALUE",
            )

        # AniDB anime IDs are typically in a reasonable range
        if aid > 999999:
            raise DataValidationError(
                "Anime ID appears to be out of valid range (1-999999)",
                field_name="aid",
                field_value=aid,
                code="AID_OUT_OF_RANGE",
            )

    def _build_search_url(self, query: str, limit: int) -> tuple[str, dict[str, str]]:
        """Build URL and parameters for anime search request.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Tuple of (URL, parameters dict)
        """
        url = urljoin(self.config.base_url, "")

        # Build request parameters
        params = {
            **self.config.to_client_params(),
            "request": "anime",
            "aname": query.strip(),
        }

        return url, params

    def _build_details_url(self, aid: int) -> tuple[str, dict[str, str]]:
        """Build URL and parameters for anime details request.

        Args:
            aid: Anime ID

        Returns:
            Tuple of (URL, parameters dict)
        """
        url = urljoin(self.config.base_url, "")

        # Build request parameters
        params = {
            **self.config.to_client_params(),
            "request": "anime",
            "aid": str(aid),
        }

        return url, params

    @with_error_handling("search_anime", service="anidb_api")
    async def search_anime(
        self, query: str, limit: int = 10
    ) -> list[AnimeSearchResult]:
        """Search for anime by title using local AniDB titles database.

        Args:
            query: Search term for anime title
            limit: Maximum number of results to return (default: 10, max: 100)

        Returns:
            List of AnimeSearchResult objects matching the search query

        Raises:
            DataValidationError: If parameters are invalid
            ServiceError: If service is closed or search database unavailable

        Example:
            >>> service = AniDBService()
            >>> results = await service.search_anime("evangelion", limit=5)
            >>> for result in results:
            ...     print(f"{result.title} ({result.aid})")
        """
        start_time = time.time()
        set_request_context(operation="search_anime")

        if self._closed:
            raise ServiceError(
                "Service has been closed",
                service_name="AniDBService",
                operation="search_anime",
                code="SERVICE_CLOSED",
            )

        # Validate parameters
        self._validate_search_params(query, limit)

        # Ensure cache is available
        await self._ensure_cache()
        ensure_not_none(self._cache, "cache")

        # Generate cache key for this search request
        cache_key = generate_cache_key("search_anime", query=query.strip(), limit=limit)

        # Try to get cached result first
        cached_result = await self._cache.get(cache_key)
        if cached_result is not None:
            log_cache_operation("get", cache_key, hit=True)
            logger.info(
                "Search result retrieved from cache",
                query=query,
                limit=limit,
                result_count=len(cached_result),
            )
            return cached_result

        log_cache_operation("get", cache_key, hit=False)

        logger.info(
            "Searching anime using local database",
            query=query,
            limit=limit,
        )

        # Use the search service
        search_service = get_search_service()
        results = await search_service.search_anime(query.strip(), limit)

        # Cache the results
        await self._cache.set(cache_key, results)
        log_cache_operation("set", cache_key)

        # Log performance metrics
        duration = time.time() - start_time
        log_performance(
            "search_anime",
            duration,
            query=query,
            limit=limit,
            result_count=len(results),
        )

        logger.info(
            "Search completed successfully",
            query=query,
            limit=limit,
            result_count=len(results),
        )

        return results

    @with_error_handling("get_anime_details", service="anidb_api")
    async def get_anime_details(self, aid: int) -> AnimeDetails:
        """Get detailed information about a specific anime.

        Args:
            aid: AniDB anime ID

        Returns:
            AnimeDetails object with comprehensive anime information

        Raises:
            DataValidationError: If anime ID is invalid
            ServiceError: If service is closed or unavailable
            APIError: If the request fails or anime is not found

        Example:
            >>> service = AniDBService()
            >>> details = await service.get_anime_details(1)
            >>> print(f"{details.title} - {details.episode_count} episodes")
        """
        start_time = time.time()
        set_request_context(operation="get_anime_details")

        if self._closed:
            raise ServiceError(
                "Service has been closed",
                service_name="AniDBService",
                operation="get_anime_details",
                code="SERVICE_CLOSED",
            )

        # Validate parameters
        self._validate_anime_id(aid)

        # Ensure HTTP client and cache are available
        self._ensure_http_client()
        await self._ensure_cache()
        ensure_not_none(self._http_client, "HTTP client")
        ensure_not_none(self._cache, "cache")

        # Generate cache key for this anime details request
        cache_key = generate_cache_key("get_anime_details", aid=aid)

        # Try to get cached result first
        cached_result = await self._cache.get(cache_key)
        if cached_result is not None:
            log_cache_operation("get", cache_key, hit=True)
            logger.info(
                "Returning cached anime details",
                aid=aid,
                title=cached_result.title,
            )
            return cached_result

        log_cache_operation("get", cache_key, hit=False)

        # Build request URL and parameters
        url, params = self._build_details_url(aid)

        logger.info(
            "Fetching anime details",
            aid=aid,
            url=url,
        )

        async def _perform_details_fetch() -> AnimeDetails:
            # Make HTTP request
            response = await self._http_client.get(url, params=params)

            # Check for API-specific errors in response
            if response.status_code == 404:
                raise APIError(
                    f"Anime with ID {aid} not found",
                    code="ANIME_NOT_FOUND",
                    status_code=404,
                    request_url=url,
                )

            if response.status_code != 200:
                raise APIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                    request_url=url,
                    request_params=params,
                )

            # Get response content and log details for debugging
            xml_content = response.text
            content_length = len(xml_content) if xml_content else 0
            content_encoding = response.headers.get("content-encoding", "none")

            logger.debug(
                f"API Response details - Status: {response.status_code}, "
                f"Content-Length: {content_length}, "
                f"Content-Encoding: {content_encoding}, "
                f"Headers: {dict(response.headers)}"
            )

            if content_length > 0:
                logger.debug(f"Response content preview: {xml_content[:500]}...")

            if not xml_content:
                raise APIError(
                    "Received empty response from API",
                    code="EMPTY_RESPONSE",
                    request_url=url,
                    response_headers=dict(response.headers),
                )

            # Check for API error responses in XML
            xml_lower = xml_content.lower()

            # Check for specific error patterns (not just any occurrence of "error")
            if (
                "no such anime" in xml_lower
                or "not found" in xml_lower
                or "invalid anime id" in xml_lower
            ):
                raise APIError(
                    f"Anime with ID {aid} not found in AniDB",
                    code="ANIME_NOT_FOUND",
                    response_body=xml_content[:1000],  # Limit response body size
                )
            elif "banned" in xml_lower:
                raise APIError(
                    "Client is banned from AniDB API",
                    code="CLIENT_BANNED",
                    response_body=xml_content[:1000],
                )
            elif "invalid request" in xml_lower or "invalid client" in xml_lower:
                raise APIError(
                    f"Invalid request or client not registered: {aid}",
                    code="INVALID_REQUEST",
                    response_body=xml_content[:1000],
                )
            elif xml_content.strip().startswith("<?xml") and "<error" in xml_lower:
                # Only treat as error if it's an actual XML error element
                raise APIError(
                    f"AniDB API error: {xml_content[:200]}",
                    code="API_ERROR",
                    response_body=xml_content,
                )

            # Parse XML response
            try:
                details = parse_anime_details(xml_content)
                logger.info(
                    "Successfully parsed anime details",
                    aid=aid,
                    title=details.title,
                    episode_count=details.episode_count,
                )

                # Cache the successful result with source data (XML for AniDB)
                await self._cache.set(cache_key, details, source_data=xml_content)
                log_cache_operation("set", cache_key)

                return details

            except XMLParsingError as e:
                logger.error(
                    "XML parsing failed for anime details",
                    aid=aid,
                    xml_length=len(xml_content),
                    error=str(e),
                )
                raise

        # Execute details fetch with retry logic
        details = await with_retry(_perform_details_fetch)

        # Log performance metrics
        duration = time.time() - start_time
        log_performance(
            "get_anime_details",
            duration,
            aid=aid,
            title=details.title,
        )

        return details

    async def get_cache_stats(self) -> dict[str, Any] | None:
        """Get cache statistics for monitoring and debugging.

        Returns:
            Dictionary with cache statistics or None if cache not initialized

        Example:
            >>> service = AniDBService()
            >>> stats = await service.get_cache_stats()
            >>> if stats:
            ...     print(f"Cache hit rate: {stats['hit_rate']:.1f}%")
        """
        if self._cache is None:
            return None

        stats = await self._cache.get_stats()
        return {
            "memory_hits": stats.memory_hits,
            "memory_misses": stats.memory_misses,
            "memory_entries": stats.memory_entries,
            "db_hits": stats.db_hits,
            "db_misses": stats.db_misses,
            "db_entries": stats.db_entries,
            "total_hits": stats.total_hits,
            "total_misses": stats.total_misses,
            "hit_rate": stats.hit_rate,
            "memory_hit_rate": stats.memory_hit_rate,
            "db_hit_rate": stats.db_hit_rate,
            "avg_memory_access_time": stats.avg_memory_access_time,
            "avg_db_access_time": stats.avg_db_access_time,
            "db_size_bytes": stats.db_size_bytes,
            "memory_size_estimate": stats.memory_size_estimate,
            "db_available": stats.db_available,
        }

    async def clear_cache(self) -> None:
        """Clear all cached data.

        This method removes all entries from the cache, which can be useful
        for testing or when you want to force fresh data retrieval.

        Example:
            >>> service = AniDBService()
            >>> await service.clear_cache()
        """
        if self._cache is not None:
            await self._cache.clear()
            logger.info("Cache cleared manually")

    async def cleanup_expired_cache(self) -> int:
        """Remove expired entries from the cache.

        Returns:
            Number of expired entries removed

        Example:
            >>> service = AniDBService()
            >>> expired_count = await service.cleanup_expired_cache()
            >>> print(f"Removed {expired_count} expired entries")
        """
        if self._cache is None:
            return 0

        return await self._cache.cleanup_expired()

    async def invalidate_cache_key(self, method: str, **params: Any) -> bool:
        """Invalidate a specific cache entry.

        Args:
            method: Method name (e.g., "search_anime", "get_anime_details")
            **params: Parameters used to generate the cache key

        Returns:
            True if cache entry was found and removed, False otherwise

        Example:
            >>> service = AniDBService()
            >>> # Invalidate cached search results
            >>> await service.invalidate_cache_key("search_anime", query="evangelion", limit=10)
            >>> # Invalidate cached anime details
            >>> await service.invalidate_cache_key("get_anime_details", aid=1)
        """
        if self._cache is None:
            return False

        cache_key = generate_cache_key(method, **params)
        return await self._cache.delete(cache_key)


async def create_anidb_service(config: AniDBConfig | None = None) -> AniDBService:
    """Create and return a configured AniDB service.

    Args:
        config: Configuration object. If None, loads from environment.

    Returns:
        Configured AniDBService instance

    Example:
        >>> config = load_config()
        >>> async with create_anidb_service(config) as service:
        ...     results = await service.search_anime("evangelion")
    """
    return AniDBService(config)
