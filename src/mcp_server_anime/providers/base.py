"""Abstract base classes for anime data providers.

This module defines the core interfaces and abstract base classes that all anime data
providers must implement to integrate with the MCP server extensibility framework.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult


class ProviderCapabilities(BaseModel):
    """Defines the capabilities supported by an anime data provider.

    This model specifies which operations a provider supports, allowing the
    framework to determine which tools to register for each provider.
    """

    supports_search: bool = Field(
        default=True,
        description="Whether the provider supports anime search functionality",
    )
    supports_details: bool = Field(
        default=True,
        description="Whether the provider supports detailed anime information retrieval",
    )
    supports_recommendations: bool = Field(
        default=False, description="Whether the provider supports anime recommendations"
    )
    supports_seasonal: bool = Field(
        default=False,
        description="Whether the provider supports seasonal anime listings",
    )
    supports_trending: bool = Field(
        default=False,
        description="Whether the provider supports trending anime listings",
    )

    # Search-specific capabilities
    max_search_results: int = Field(
        default=20,
        ge=1,
        description="Maximum number of search results the provider can return",
    )
    min_search_length: int = Field(
        default=2,
        ge=1,
        description="Minimum search query length required by the provider",
    )

    # Rate limiting information
    rate_limit_per_second: float | None = Field(
        default=None,
        ge=0.1,
        description="Maximum requests per second allowed by the provider",
    )
    rate_limit_per_minute: int | None = Field(
        default=None,
        ge=1,
        description="Maximum requests per minute allowed by the provider",
    )


class ProviderInfo(BaseModel):
    """Information about an anime data provider.

    This model contains metadata about a provider including its name, version,
    description, and capabilities.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique name identifier for the provider",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable display name for the provider",
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Version string for the provider implementation",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Brief description of the provider and its data source",
    )
    base_url: str | None = Field(
        default=None, description="Base URL of the provider's API (if applicable)"
    )
    capabilities: ProviderCapabilities = Field(
        default_factory=ProviderCapabilities,
        description="Capabilities supported by this provider",
    )
    requires_auth: bool = Field(
        default=False, description="Whether the provider requires authentication"
    )
    auth_env_vars: list[str] = Field(
        default_factory=list,
        description="List of environment variables required for authentication",
    )


class AnimeDataProvider(ABC):
    """Abstract base class for anime data providers.

    This class defines the interface that all anime data providers must implement
    to integrate with the MCP server. Providers can implement different subsets
    of functionality based on their capabilities.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider with optional configuration.

        Args:
            config: Optional configuration dictionary specific to the provider
        """
        self._config = config or {}
        self._initialized = False

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Get provider information and capabilities.

        Returns:
            ProviderInfo object containing provider metadata and capabilities
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider and establish any necessary connections.

        This method should perform any setup required by the provider, such as
        validating configuration, establishing HTTP clients, or testing API connectivity.

        Raises:
            ProviderError: If initialization fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up provider resources and close connections.

        This method should properly close any open connections, clean up resources,
        and perform any necessary shutdown procedures.
        """
        pass

    @property
    def is_initialized(self) -> bool:
        """Check if the provider has been initialized.

        Returns:
            True if the provider is initialized and ready to use
        """
        return self._initialized

    async def search_anime(
        self, query: str, limit: int = 10, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Search for anime by title.

        Args:
            query: Search term for anime title
            limit: Maximum number of results to return
            **kwargs: Additional provider-specific search parameters

        Returns:
            List of AnimeSearchResult objects matching the search query

        Raises:
            NotImplementedError: If the provider doesn't support search functionality
            ProviderError: If the search operation fails
        """
        if not self.info.capabilities.supports_search:
            raise NotImplementedError(
                f"Provider '{self.info.name}' does not support search functionality"
            )

        return await self._search_anime_impl(query, limit, **kwargs)

    async def get_anime_details(
        self, anime_id: str | int, **kwargs: Any
    ) -> AnimeDetails:
        """Get detailed information about a specific anime.

        Args:
            anime_id: Unique identifier for the anime (format depends on provider)
            **kwargs: Additional provider-specific parameters

        Returns:
            AnimeDetails object with comprehensive anime information

        Raises:
            NotImplementedError: If the provider doesn't support details functionality
            ProviderError: If the details operation fails
        """
        if not self.info.capabilities.supports_details:
            raise NotImplementedError(
                f"Provider '{self.info.name}' does not support details functionality"
            )

        return await self._get_anime_details_impl(anime_id, **kwargs)

    async def get_recommendations(
        self, anime_id: str | int, limit: int = 10, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Get anime recommendations based on a specific anime.

        Args:
            anime_id: Unique identifier for the reference anime
            limit: Maximum number of recommendations to return
            **kwargs: Additional provider-specific parameters

        Returns:
            List of recommended anime as AnimeSearchResult objects

        Raises:
            NotImplementedError: If the provider doesn't support recommendations
            ProviderError: If the recommendations operation fails
        """
        if not self.info.capabilities.supports_recommendations:
            raise NotImplementedError(
                f"Provider '{self.info.name}' does not support recommendations functionality"
            )

        return await self._get_recommendations_impl(anime_id, limit, **kwargs)

    async def get_seasonal_anime(
        self, year: int, season: str, limit: int = 20, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Get anime from a specific season.

        Args:
            year: Year of the season
            season: Season name (spring, summer, fall, winter)
            limit: Maximum number of results to return
            **kwargs: Additional provider-specific parameters

        Returns:
            List of seasonal anime as AnimeSearchResult objects

        Raises:
            NotImplementedError: If the provider doesn't support seasonal listings
            ProviderError: If the seasonal operation fails
        """
        if not self.info.capabilities.supports_seasonal:
            raise NotImplementedError(
                f"Provider '{self.info.name}' does not support seasonal functionality"
            )

        return await self._get_seasonal_anime_impl(year, season, limit, **kwargs)

    async def get_trending_anime(
        self, limit: int = 20, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Get currently trending anime.

        Args:
            limit: Maximum number of results to return
            **kwargs: Additional provider-specific parameters

        Returns:
            List of trending anime as AnimeSearchResult objects

        Raises:
            NotImplementedError: If the provider doesn't support trending listings
            ProviderError: If the trending operation fails
        """
        if not self.info.capabilities.supports_trending:
            raise NotImplementedError(
                f"Provider '{self.info.name}' does not support trending functionality"
            )

        return await self._get_trending_anime_impl(limit, **kwargs)

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the provider.

        Returns:
            Dictionary containing health status information
        """
        return {
            "provider": self.info.name,
            "status": "healthy" if self.is_initialized else "not_initialized",
            "capabilities": self.info.capabilities.model_dump(),
        }

    # Abstract methods that providers must implement

    @abstractmethod
    async def _search_anime_impl(
        self, query: str, limit: int, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Implementation-specific anime search logic.

        This method should be implemented by concrete provider classes to perform
        the actual search operation using their specific API or data source.
        """
        pass

    @abstractmethod
    async def _get_anime_details_impl(
        self, anime_id: str | int, **kwargs: Any
    ) -> AnimeDetails:
        """Implementation-specific anime details retrieval logic.

        This method should be implemented by concrete provider classes to perform
        the actual details retrieval using their specific API or data source.
        """
        pass

    async def _get_recommendations_impl(
        self, anime_id: str | int, limit: int, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Implementation-specific recommendations logic.

        Default implementation raises NotImplementedError. Providers that support
        recommendations should override this method.
        """
        raise NotImplementedError("Recommendations not implemented by this provider")

    async def _get_seasonal_anime_impl(
        self, year: int, season: str, limit: int, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Implementation-specific seasonal anime logic.

        Default implementation raises NotImplementedError. Providers that support
        seasonal listings should override this method.
        """
        raise NotImplementedError("Seasonal anime not implemented by this provider")

    async def _get_trending_anime_impl(
        self, limit: int, **kwargs: Any
    ) -> list[AnimeSearchResult]:
        """Implementation-specific trending anime logic.

        Default implementation raises NotImplementedError. Providers that support
        trending listings should override this method.
        """
        raise NotImplementedError("Trending anime not implemented by this provider")
