"""AniDB provider implementation for the extensibility framework.

This module implements the AniDB anime data provider using the existing AniDB service
and integrates it with the extensibility framework.
"""

from typing import Any

from mcp_server_anime.core.exceptions import ProviderError
from mcp_server_anime.core.logging_config import get_logger
from mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult

from .anidb.config import AniDBConfig, load_config
from .anidb.service import AniDBService, create_anidb_service
from .base import AnimeDataProvider, ProviderCapabilities, ProviderInfo

logger = get_logger(__name__)


class AniDBProvider(AnimeDataProvider):
    """AniDB anime data provider implementation.

    This provider wraps the existing AniDB service to integrate it with the
    extensibility framework, allowing it to work alongside other anime data providers.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the AniDB provider.

        Args:
            config: Optional configuration dictionary for the provider
        """
        super().__init__(config)
        self._anidb_config: AniDBConfig | None = None
        self._service: AniDBService | None = None

    @property
    def info(self) -> ProviderInfo:
        """Get AniDB provider information and capabilities.

        Returns:
            ProviderInfo object containing AniDB provider metadata and capabilities
        """
        return ProviderInfo(
            name="anidb",
            display_name="AniDB",
            version="1.0.0",
            description="Official AniDB anime database with comprehensive anime information",
            base_url="http://api.anidb.net:9001/httpapi",
            capabilities=ProviderCapabilities(
                supports_search=True,
                supports_details=True,
                supports_recommendations=False,
                supports_seasonal=False,
                supports_trending=False,
                max_search_results=100,
                min_search_length=2,
                rate_limit_per_second=0.5,  # 1 request per 2 seconds
            ),
            requires_auth=False,
            auth_env_vars=[],
        )

    async def initialize(self) -> None:
        """Initialize the AniDB provider and establish connections.

        Raises:
            ProviderError: If initialization fails
        """
        try:
            logger.info("Initializing AniDB provider")

            # Load AniDB configuration
            if "anidb_config" in self._config:
                # Use provided AniDB config
                anidb_config_dict = self._config["anidb_config"]
                self._anidb_config = AniDBConfig(**anidb_config_dict)
            else:
                # Load from environment variables
                self._anidb_config = load_config()

            # Create AniDB service
            self._service = await create_anidb_service(self._anidb_config)

            # Initialize the service (this will set up HTTP client and cache)
            await self._service._ensure_http_client()
            await self._service._ensure_cache()

            self._initialized = True

            logger.info(
                "AniDB provider initialized successfully",
                base_url=self._anidb_config.base_url,
                client_name=self._anidb_config.client_name,
            )

        except Exception as e:
            logger.error(
                "Failed to initialize AniDB provider",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ProviderError(
                f"AniDB provider initialization failed: {e}",
                provider_name="anidb",
                operation="initialize",
                cause=e,
            )

    async def cleanup(self) -> None:
        """Clean up AniDB provider resources and close connections."""
        try:
            logger.info("Cleaning up AniDB provider")

            if self._service:
                await self._service.close()

            logger.info("AniDB provider cleanup completed")

        except Exception as e:
            logger.error(
                "Error during AniDB provider cleanup",
                error=str(e),
                error_type=type(e).__name__,
            )
        finally:
            # Always reset state, even if cleanup fails
            self._service = None
            self._anidb_config = None
            self._initialized = False

    async def _search_anime_impl(
        self, query: str, limit: int, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Implementation-specific anime search logic for AniDB.

        Args:
            query: Search term for anime title
            limit: Maximum number of results to return
            **kwargs: Additional search parameters (ignored for AniDB)

        Returns:
            List of AnimeSearchResult objects matching the search query

        Raises:
            ProviderError: If the search operation fails
        """
        if not self._service:
            raise ProviderError(
                "AniDB provider not initialized",
                provider_name="anidb",
                operation="search_anime",
            )

        try:
            logger.debug(
                "Performing AniDB anime search",
                query=query,
                limit=limit,
            )

            # Use the existing AniDB service to perform the search
            results = await self._service.search_anime(query, limit)

            logger.debug(
                "AniDB anime search completed",
                query=query,
                result_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "AniDB anime search failed",
                query=query,
                limit=limit,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ProviderError(
                f"AniDB anime search failed: {e}",
                provider_name="anidb",
                operation="search_anime",
                cause=e,
            )

    async def _get_anime_details_impl(
        self, anime_id: str | int, **kwargs: Any
    ) -> AnimeDetails:
        """Implementation-specific anime details retrieval logic for AniDB.

        Args:
            anime_id: AniDB anime ID (must be an integer)
            **kwargs: Additional parameters (ignored for AniDB)

        Returns:
            AnimeDetails object with comprehensive anime information

        Raises:
            ProviderError: If the details operation fails
        """
        if not self._service:
            raise ProviderError(
                "AniDB provider not initialized",
                provider_name="anidb",
                operation="get_anime_details",
            )

        try:
            # Convert anime_id to integer if it's a string
            if isinstance(anime_id, str):
                try:
                    aid = int(anime_id)
                except ValueError:
                    raise ProviderError(
                        f"Invalid AniDB anime ID format: {anime_id}. Must be an integer.",
                        provider_name="anidb",
                        operation="get_anime_details",
                    )
            else:
                aid = anime_id

            logger.debug(
                "Fetching AniDB anime details",
                aid=aid,
            )

            # Use the existing AniDB service to get anime details
            details = await self._service.get_anime_details(aid)

            logger.debug(
                "AniDB anime details retrieved",
                aid=aid,
                title=details.title,
            )

            return details

        except Exception as e:
            logger.error(
                "AniDB anime details retrieval failed",
                anime_id=anime_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ProviderError(
                f"AniDB anime details retrieval failed: {e}",
                provider_name="anidb",
                operation="get_anime_details",
                cause=e,
            )

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the AniDB provider.

        Returns:
            Dictionary containing health status information
        """
        base_health = await super().health_check()

        # Add AniDB-specific health information
        anidb_health = {
            **base_health,
            "service_initialized": self._service is not None,
            "config_loaded": self._anidb_config is not None,
        }

        if self._service:
            try:
                # Get cache statistics if available
                cache_stats = await self._service.get_cache_stats()
                if cache_stats:
                    anidb_health["cache_stats"] = cache_stats

                # Check if HTTP client is available
                anidb_health["http_client_available"] = (
                    self._service._http_client is not None
                    and not self._service._http_client.is_closed()
                )

            except Exception as e:
                anidb_health["health_check_error"] = str(e)

        return anidb_health


def create_anidb_provider(config: dict[str, Any] | None = None) -> AniDBProvider:
    """Create and return an AniDB provider instance.

    Args:
        config: Optional configuration dictionary for the provider

    Returns:
        Configured AniDBProvider instance
    """
    return AniDBProvider(config)
