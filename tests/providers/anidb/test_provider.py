"""Tests for the AniDB provider implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_server_anime.core.exceptions import ProviderError
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.providers.anidb import AniDBProvider, create_anidb_provider
from src.mcp_server_anime.providers.anidb.config import AniDBConfig
from src.mcp_server_anime.providers.base import ProviderCapabilities, ProviderInfo


class TestAniDBProvider:
    """Test AniDB provider implementation."""

    @pytest.fixture
    def provider(self):
        """Create an AniDB provider for testing."""
        return AniDBProvider()

    def test_provider_info(self, provider):
        """Test provider information."""
        info = provider.info

        assert isinstance(info, ProviderInfo)
        assert info.name == "anidb"
        assert info.display_name == "AniDB"
        assert info.version == "1.0.0"
        assert "AniDB anime database" in info.description
        assert info.base_url == "http://api.anidb.net:9001/httpapi"
        assert info.requires_auth is False
        assert info.auth_env_vars == []

        # Check capabilities
        capabilities = info.capabilities
        assert isinstance(capabilities, ProviderCapabilities)
        assert capabilities.supports_search is True
        assert capabilities.supports_details is True
        assert capabilities.supports_recommendations is False
        assert capabilities.supports_seasonal is False
        assert capabilities.supports_trending is False
        assert capabilities.max_search_results == 100
        assert capabilities.min_search_length == 2
        assert capabilities.rate_limit_per_second == 0.5

    def test_initialization_default_config(self, provider):
        """Test provider initialization with default configuration."""
        assert provider._anidb_config is None
        assert provider._service is None
        assert not provider.is_initialized

    def test_initialization_custom_config(self):
        """Test provider initialization with custom configuration."""
        config = {
            "anidb_config": {
                "client_name": "test-client",
                "rate_limit_delay": 1.0,
            }
        }
        provider = AniDBProvider(config)

        assert provider._config == config

    @pytest.mark.asyncio
    @patch("src.mcp_server_anime.providers.anidb.provider.load_config")
    @patch("src.mcp_server_anime.providers.anidb.provider.create_anidb_service")
    async def test_initialize_success(
        self, mock_create_service, mock_load_config, provider
    ):
        """Test successful provider initialization."""
        # Mock configuration
        mock_config = MagicMock(spec=AniDBConfig)
        mock_config.base_url = "http://api.anidb.net:9001/httpapi"
        mock_config.client_name = "test-client"
        mock_load_config.return_value = mock_config

        # Mock service
        mock_service = AsyncMock()
        mock_service._ensure_http_client = AsyncMock()
        mock_service._ensure_cache = AsyncMock()
        mock_create_service.return_value = mock_service

        # Initialize provider
        await provider.initialize()

        # Verify initialization
        assert provider.is_initialized
        assert provider._anidb_config == mock_config
        assert provider._service == mock_service

        # Verify service setup was called
        mock_service._ensure_http_client.assert_called_once()
        mock_service._ensure_cache.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.mcp_server_anime.providers.anidb.load_config")
    async def test_initialize_failure(self, mock_load_config, provider):
        """Test provider initialization failure."""
        # Mock configuration loading to fail
        mock_load_config.side_effect = Exception("Config loading failed")

        # Initialize should raise ProviderError
        with pytest.raises(ProviderError) as exc_info:
            await provider.initialize()

        assert "AniDB provider initialization failed" in str(exc_info.value)
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, provider):
        """Test provider cleanup."""
        # Mock service
        mock_service = AsyncMock()
        provider._service = mock_service
        provider._anidb_config = MagicMock()
        provider._initialized = True

        # Cleanup
        await provider.cleanup()

        # Verify cleanup
        assert not provider.is_initialized
        assert provider._service is None
        assert provider._anidb_config is None
        mock_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self, provider):
        """Test provider cleanup with exception."""
        # Mock service that raises exception on close
        mock_service = AsyncMock()
        mock_service.close.side_effect = Exception("Close failed")
        provider._service = mock_service
        provider._initialized = True

        # Cleanup should not raise exception
        await provider.cleanup()

        # Should still reset state despite exception
        assert not provider.is_initialized

    @pytest.mark.asyncio
    async def test_search_anime_success(self, provider):
        """Test successful anime search."""
        # Setup initialized provider
        mock_service = AsyncMock()
        expected_results = [
            AnimeSearchResult(aid=1, title="Test Anime", type="TV", year=2023)
        ]
        mock_service.search_anime.return_value = expected_results
        provider._service = mock_service
        provider._initialized = True

        # Perform search
        results = await provider._search_anime_impl("test", 10)

        # Verify results
        assert results == expected_results
        mock_service.search_anime.assert_called_once_with("test", 10)

    @pytest.mark.asyncio
    async def test_search_anime_not_initialized(self, provider):
        """Test anime search when provider not initialized."""
        with pytest.raises(ProviderError) as exc_info:
            await provider._search_anime_impl("test", 10)

        assert "AniDB provider not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_anime_service_failure(self, provider):
        """Test anime search when service fails."""
        # Setup provider with failing service
        mock_service = AsyncMock()
        mock_service.search_anime.side_effect = Exception("Service failed")
        provider._service = mock_service
        provider._initialized = True

        with pytest.raises(ProviderError) as exc_info:
            await provider._search_anime_impl("test", 10)

        assert "AniDB anime search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_anime_details_success(self, provider):
        """Test successful anime details retrieval."""
        # Setup initialized provider
        mock_service = AsyncMock()
        expected_details = AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV",
            episode_count=12,
        )
        mock_service.get_anime_details.return_value = expected_details
        provider._service = mock_service
        provider._initialized = True

        # Get details with integer ID
        details = await provider._get_anime_details_impl(1)
        assert details == expected_details
        mock_service.get_anime_details.assert_called_once_with(1)

        # Get details with string ID
        mock_service.reset_mock()
        details = await provider._get_anime_details_impl("123")
        assert details == expected_details
        mock_service.get_anime_details.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_anime_details_invalid_id(self, provider):
        """Test anime details retrieval with invalid ID."""
        # Setup initialized provider
        provider._service = AsyncMock()
        provider._initialized = True

        with pytest.raises(ProviderError) as exc_info:
            await provider._get_anime_details_impl("invalid")

        assert "Invalid AniDB anime ID format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_anime_details_not_initialized(self, provider):
        """Test anime details retrieval when provider not initialized."""
        with pytest.raises(ProviderError) as exc_info:
            await provider._get_anime_details_impl(1)

        assert "AniDB provider not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_anime_details_service_failure(self, provider):
        """Test anime details retrieval when service fails."""
        # Setup provider with failing service
        mock_service = AsyncMock()
        mock_service.get_anime_details.side_effect = Exception("Service failed")
        provider._service = mock_service
        provider._initialized = True

        with pytest.raises(ProviderError) as exc_info:
            await provider._get_anime_details_impl(1)

        assert "AniDB anime details retrieval failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, provider):
        """Test health check when provider not initialized."""
        health = await provider.health_check()

        assert health["provider"] == "anidb"
        assert health["status"] == "not_initialized"
        assert health["service_initialized"] is False
        assert health["config_loaded"] is False

    @pytest.mark.asyncio
    async def test_health_check_initialized(self, provider):
        """Test health check when provider is initialized."""
        # Setup initialized provider
        mock_service = AsyncMock()
        mock_service.get_cache_stats.return_value = {"hits": 10, "misses": 5}
        mock_service._http_client = MagicMock()
        mock_service._http_client.is_closed.return_value = False

        provider._service = mock_service
        provider._anidb_config = MagicMock()
        provider._initialized = True

        health = await provider.health_check()

        assert health["provider"] == "anidb"
        assert health["status"] == "healthy"
        assert health["service_initialized"] is True
        assert health["config_loaded"] is True
        assert health["cache_stats"] == {"hits": 10, "misses": 5}
        assert health["http_client_available"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_service_error(self, provider):
        """Test health check when service operations fail."""
        # Setup provider with service that fails health checks
        mock_service = AsyncMock()
        mock_service.get_cache_stats.side_effect = Exception("Cache error")

        provider._service = mock_service
        provider._anidb_config = MagicMock()
        provider._initialized = True

        health = await provider.health_check()

        assert health["provider"] == "anidb"
        assert health["status"] == "healthy"  # Base health check still passes
        assert "health_check_error" in health


class TestAniDBProviderFactory:
    """Test AniDB provider factory function."""

    def test_create_anidb_provider_default(self):
        """Test creating AniDB provider with default config."""
        provider = create_anidb_provider()

        assert isinstance(provider, AniDBProvider)
        assert provider._config == {}

    def test_create_anidb_provider_custom_config(self):
        """Test creating AniDB provider with custom config."""
        config = {"anidb_config": {"client_name": "test"}}
        provider = create_anidb_provider(config)

        assert isinstance(provider, AniDBProvider)
        assert provider._config == config
