"""Tests for the anime data provider base classes and interfaces."""

from unittest.mock import AsyncMock

import pytest

from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.providers.base import (
    AnimeDataProvider,
    ProviderCapabilities,
    ProviderInfo,
)


class MockProvider(AnimeDataProvider):
    """Mock provider for testing base functionality."""

    def __init__(self, config=None, supports_search=True, supports_details=True):
        super().__init__(config)
        self._supports_search = supports_search
        self._supports_details = supports_details
        self._search_impl = AsyncMock()
        self._details_impl = AsyncMock()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="mock",
            display_name="Mock Provider",
            version="1.0.0",
            description="Mock provider for testing",
            capabilities=ProviderCapabilities(
                supports_search=self._supports_search,
                supports_details=self._supports_details,
                max_search_results=20,
                min_search_length=2,
            ),
        )

    async def initialize(self) -> None:
        self._initialized = True

    async def cleanup(self) -> None:
        self._initialized = False

    async def _search_anime_impl(
        self, query: str, limit: int, **kwargs
    ) -> list[AnimeSearchResult]:
        return await self._search_impl(query, limit, **kwargs)

    async def _get_anime_details_impl(
        self, anime_id: str | int, **kwargs
    ) -> AnimeDetails:
        return await self._details_impl(anime_id, **kwargs)


class TestProviderCapabilities:
    """Test ProviderCapabilities model."""

    def test_default_capabilities(self):
        """Test default capability values."""
        capabilities = ProviderCapabilities()

        assert capabilities.supports_search is True
        assert capabilities.supports_details is True
        assert capabilities.supports_recommendations is False
        assert capabilities.supports_seasonal is False
        assert capabilities.supports_trending is False
        assert capabilities.max_search_results == 20
        assert capabilities.min_search_length == 2
        assert capabilities.rate_limit_per_second is None
        assert capabilities.rate_limit_per_minute is None

    def test_custom_capabilities(self):
        """Test custom capability configuration."""
        capabilities = ProviderCapabilities(
            supports_search=False,
            supports_recommendations=True,
            max_search_results=50,
            min_search_length=1,
            rate_limit_per_second=2.0,
            rate_limit_per_minute=120,
        )

        assert capabilities.supports_search is False
        assert capabilities.supports_recommendations is True
        assert capabilities.max_search_results == 50
        assert capabilities.min_search_length == 1
        assert capabilities.rate_limit_per_second == 2.0
        assert capabilities.rate_limit_per_minute == 120

    def test_validation_constraints(self):
        """Test validation constraints on capabilities."""
        # Test max_search_results constraint
        with pytest.raises(ValueError):
            ProviderCapabilities(max_search_results=0)

        # Test min_search_length constraint
        with pytest.raises(ValueError):
            ProviderCapabilities(min_search_length=0)

        # Test rate_limit_per_second constraint
        with pytest.raises(ValueError):
            ProviderCapabilities(rate_limit_per_second=0.05)

        # Test rate_limit_per_minute constraint
        with pytest.raises(ValueError):
            ProviderCapabilities(rate_limit_per_minute=0)


class TestProviderInfo:
    """Test ProviderInfo model."""

    def test_required_fields(self):
        """Test that required fields are validated."""
        # Valid provider info
        info = ProviderInfo(
            name="test",
            display_name="Test Provider",
            version="1.0.0",
            description="Test provider description",
        )

        assert info.name == "test"
        assert info.display_name == "Test Provider"
        assert info.version == "1.0.0"
        assert info.description == "Test provider description"
        assert info.base_url is None
        assert info.requires_auth is False
        assert info.auth_env_vars == []

    def test_field_validation(self):
        """Test field validation constraints."""
        # Test empty name
        with pytest.raises(ValueError):
            ProviderInfo(
                name="",
                display_name="Test",
                version="1.0.0",
                description="Test",
            )

        # Test name too long
        with pytest.raises(ValueError):
            ProviderInfo(
                name="a" * 51,
                display_name="Test",
                version="1.0.0",
                description="Test",
            )

    def test_optional_fields(self):
        """Test optional field configuration."""
        info = ProviderInfo(
            name="test",
            display_name="Test Provider",
            version="1.0.0",
            description="Test provider",
            base_url="https://api.example.com",
            requires_auth=True,
            auth_env_vars=["API_KEY", "SECRET"],
        )

        assert info.base_url == "https://api.example.com"
        assert info.requires_auth is True
        assert info.auth_env_vars == ["API_KEY", "SECRET"]


class TestAnimeDataProvider:
    """Test AnimeDataProvider abstract base class."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""
        return MockProvider()

    def test_initialization(self, mock_provider):
        """Test provider initialization."""
        assert mock_provider._config == {}
        assert mock_provider._initialized is False
        assert mock_provider.is_initialized is False

    def test_initialization_with_config(self):
        """Test provider initialization with config."""
        config = {"key": "value", "timeout": 30}
        provider = MockProvider(config)

        assert provider._config == config

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self, mock_provider):
        """Test provider initialization and cleanup."""
        # Initially not initialized
        assert not mock_provider.is_initialized

        # Initialize
        await mock_provider.initialize()
        assert mock_provider.is_initialized

        # Cleanup
        await mock_provider.cleanup()
        assert not mock_provider.is_initialized

    @pytest.mark.asyncio
    async def test_search_anime_supported(self, mock_provider):
        """Test search_anime when supported."""
        # Mock the implementation
        expected_results = [
            AnimeSearchResult(aid=1, title="Test Anime", type="TV", year=2023)
        ]
        mock_provider._search_impl.return_value = expected_results

        # Call search_anime
        results = await mock_provider.search_anime("test", 10)

        # Verify
        assert results == expected_results
        mock_provider._search_impl.assert_called_once_with("test", 10)

    @pytest.mark.asyncio
    async def test_search_anime_not_supported(self):
        """Test search_anime when not supported."""
        provider = MockProvider(supports_search=False)

        with pytest.raises(NotImplementedError) as exc_info:
            await provider.search_anime("test", 10)

        assert "does not support search functionality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_anime_details_supported(self, mock_provider):
        """Test get_anime_details when supported."""
        # Mock the implementation
        expected_details = AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV",
            episode_count=12,
        )
        mock_provider._details_impl.return_value = expected_details

        # Call get_anime_details
        details = await mock_provider.get_anime_details(1)

        # Verify
        assert details == expected_details
        mock_provider._details_impl.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_anime_details_not_supported(self):
        """Test get_anime_details when not supported."""
        provider = MockProvider(supports_details=False)

        with pytest.raises(NotImplementedError) as exc_info:
            await provider.get_anime_details(1)

        assert "does not support details functionality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_recommendations_not_implemented(self, mock_provider):
        """Test get_recommendations default implementation."""
        with pytest.raises(NotImplementedError) as exc_info:
            await mock_provider.get_recommendations(1, 10)

        assert "does not support recommendations functionality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_seasonal_anime_not_implemented(self, mock_provider):
        """Test get_seasonal_anime default implementation."""
        with pytest.raises(NotImplementedError) as exc_info:
            await mock_provider.get_seasonal_anime(2023, "spring", 10)

        assert "does not support seasonal functionality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_trending_anime_not_implemented(self, mock_provider):
        """Test get_trending_anime default implementation."""
        with pytest.raises(NotImplementedError) as exc_info:
            await mock_provider.get_trending_anime(10)

        assert "does not support trending functionality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check(self, mock_provider):
        """Test health_check method."""
        # Before initialization
        health = await mock_provider.health_check()
        assert health["provider"] == "mock"
        assert health["status"] == "not_initialized"
        assert "capabilities" in health

        # After initialization
        await mock_provider.initialize()
        health = await mock_provider.health_check()
        assert health["status"] == "healthy"

    def test_provider_info_property(self, mock_provider):
        """Test provider info property."""
        info = mock_provider.info

        assert isinstance(info, ProviderInfo)
        assert info.name == "mock"
        assert info.display_name == "Mock Provider"
        assert info.version == "1.0.0"
        assert info.description == "Mock provider for testing"
