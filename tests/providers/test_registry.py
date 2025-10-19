"""Tests for the provider registry system."""

import pytest

from src.mcp_server_anime.core.exceptions import ProviderError
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.providers.base import (
    AnimeDataProvider,
    ProviderCapabilities,
    ProviderInfo,
)
from src.mcp_server_anime.providers.registry import (
    ProviderRegistry,
    get_provider_registry,
    reset_provider_registry,
)


class MockProvider(AnimeDataProvider):
    """Mock provider for testing registry functionality."""

    def __init__(self, name="mock", supports_search=True, supports_details=True):
        super().__init__()
        self._name = name
        self._supports_search = supports_search
        self._supports_details = supports_details
        self._initialize_called = False
        self._cleanup_called = False
        self._should_fail_init = False

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self._name,
            display_name=f"Mock Provider {self._name}",
            version="1.0.0",
            description=f"Mock provider {self._name} for testing",
            capabilities=ProviderCapabilities(
                supports_search=self._supports_search,
                supports_details=self._supports_details,
            ),
        )

    async def initialize(self) -> None:
        self._initialize_called = True
        if self._should_fail_init:
            raise Exception("Mock initialization failure")
        self._initialized = True

    async def cleanup(self) -> None:
        self._cleanup_called = True
        self._initialized = False

    async def _search_anime_impl(
        self, query: str, limit: int, **kwargs
    ) -> list[AnimeSearchResult]:
        return []

    async def _get_anime_details_impl(
        self, anime_id: str | int, **kwargs
    ) -> AnimeDetails:
        return AnimeDetails(aid=1, title="Mock", type="TV", episode_count=1)

    def set_should_fail_init(self, should_fail: bool) -> None:
        """Set whether initialization should fail."""
        self._should_fail_init = should_fail


class TestProviderRegistry:
    """Test ProviderRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return ProviderRegistry()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""
        return MockProvider()

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry._providers) == 0
        assert len(registry._enabled_providers) == 0
        assert not registry._initialized

    def test_register_provider(self, registry, mock_provider):
        """Test provider registration."""
        config = {"key": "value"}

        registry.register_provider(mock_provider, config, enabled=True)

        assert "mock" in registry._providers
        assert registry._providers["mock"] == mock_provider
        assert "mock" in registry._enabled_providers
        assert registry._provider_configs["mock"] == config

    def test_register_provider_disabled(self, registry, mock_provider):
        """Test registering a disabled provider."""
        registry.register_provider(mock_provider, enabled=False)

        assert "mock" in registry._providers
        assert "mock" not in registry._enabled_providers

    def test_register_duplicate_provider(self, registry, mock_provider):
        """Test registering a provider with duplicate name."""
        registry.register_provider(mock_provider)

        # Try to register another provider with the same name
        duplicate_provider = MockProvider("mock")

        with pytest.raises(ProviderError) as exc_info:
            registry.register_provider(duplicate_provider)

        assert "already registered" in str(exc_info.value)

    def test_unregister_provider(self, registry, mock_provider):
        """Test provider unregistration."""
        registry.register_provider(mock_provider)

        registry.unregister_provider("mock")

        assert "mock" not in registry._providers
        assert "mock" not in registry._enabled_providers
        assert "mock" not in registry._provider_configs

    def test_unregister_nonexistent_provider(self, registry):
        """Test unregistering a non-existent provider."""
        with pytest.raises(ProviderError) as exc_info:
            registry.unregister_provider("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_enable_provider(self, registry, mock_provider):
        """Test enabling a provider."""
        registry.register_provider(mock_provider, enabled=False)

        registry.enable_provider("mock")

        assert "mock" in registry._enabled_providers

    def test_enable_nonexistent_provider(self, registry):
        """Test enabling a non-existent provider."""
        with pytest.raises(ProviderError) as exc_info:
            registry.enable_provider("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_disable_provider(self, registry, mock_provider):
        """Test disabling a provider."""
        registry.register_provider(mock_provider, enabled=True)

        registry.disable_provider("mock")

        assert "mock" not in registry._enabled_providers

    def test_disable_nonexistent_provider(self, registry):
        """Test disabling a non-existent provider."""
        with pytest.raises(ProviderError) as exc_info:
            registry.disable_provider("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_is_provider_enabled(self, registry, mock_provider):
        """Test checking if provider is enabled."""
        registry.register_provider(mock_provider, enabled=True)

        assert registry.is_provider_enabled("mock") is True

        registry.disable_provider("mock")
        assert registry.is_provider_enabled("mock") is False

        assert registry.is_provider_enabled("nonexistent") is False

    def test_get_provider(self, registry, mock_provider):
        """Test getting a provider."""
        registry.register_provider(mock_provider, enabled=True)

        retrieved = registry.get_provider("mock")
        assert retrieved == mock_provider

        # Disabled provider should return None
        registry.disable_provider("mock")
        assert registry.get_provider("mock") is None

        # Non-existent provider should return None
        assert registry.get_provider("nonexistent") is None

    def test_get_enabled_providers(self, registry):
        """Test getting all enabled providers."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")
        provider3 = MockProvider("provider3")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=False)
        registry.register_provider(provider3, enabled=True)

        enabled = registry.get_enabled_providers()

        assert len(enabled) == 2
        assert "provider1" in enabled
        assert "provider3" in enabled
        assert "provider2" not in enabled

    def test_get_all_providers(self, registry):
        """Test getting all providers."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=False)

        all_providers = registry.get_all_providers()

        assert len(all_providers) == 2
        assert "provider1" in all_providers
        assert "provider2" in all_providers

    def test_get_provider_info(self, registry, mock_provider):
        """Test getting provider info."""
        registry.register_provider(mock_provider)

        info = registry.get_provider_info("mock")
        assert info is not None
        assert info.name == "mock"

        assert registry.get_provider_info("nonexistent") is None

    def test_list_providers(self, registry):
        """Test listing providers with status."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=False)

        providers_list = registry.list_providers()

        assert len(providers_list) == 2

        # Find provider1 in the list
        provider1_info = next(p for p in providers_list if p["name"] == "provider1")
        assert provider1_info["enabled"] is True
        assert provider1_info["initialized"] is False

        # Find provider2 in the list
        provider2_info = next(p for p in providers_list if p["name"] == "provider2")
        assert provider2_info["enabled"] is False

    def test_get_providers_by_capability(self, registry):
        """Test getting providers by capability."""
        provider1 = MockProvider(
            "provider1", supports_search=True, supports_details=False
        )
        provider2 = MockProvider(
            "provider2", supports_search=False, supports_details=True
        )
        provider3 = MockProvider(
            "provider3", supports_search=True, supports_details=True
        )

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=True)
        registry.register_provider(provider3, enabled=False)  # Disabled

        search_providers = registry.get_providers_by_capability("search")
        assert len(search_providers) == 1  # Only enabled providers
        assert "provider1" in search_providers

        details_providers = registry.get_providers_by_capability("details")
        assert len(details_providers) == 1
        assert "provider2" in details_providers

    @pytest.mark.asyncio
    async def test_initialize_all_providers(self, registry):
        """Test initializing all providers."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")
        provider3 = MockProvider("provider3")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=True)
        registry.register_provider(
            provider3, enabled=False
        )  # Should not be initialized

        results = await registry.initialize_all_providers()

        assert len(results) == 2  # Only enabled providers
        assert results["provider1"] is True
        assert results["provider2"] is True
        assert "provider3" not in results

        assert provider1._initialize_called
        assert provider2._initialize_called
        assert not provider3._initialize_called

        assert registry._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_providers_with_failure(self, registry):
        """Test initializing providers when some fail."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")
        provider2.set_should_fail_init(True)

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=True)

        results = await registry.initialize_all_providers()

        assert results["provider1"] is True
        assert results["provider2"] is False

        # Failed provider should be disabled
        assert "provider2" not in registry._enabled_providers

    @pytest.mark.asyncio
    async def test_cleanup_all_providers(self, registry):
        """Test cleaning up all providers."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(provider2, enabled=True)

        # Initialize first
        await registry.initialize_all_providers()

        # Then cleanup
        await registry.cleanup_all_providers()

        assert provider1._cleanup_called
        assert provider2._cleanup_called
        assert not provider1._initialized
        assert not provider2._initialized
        assert not registry._initialized

    @pytest.mark.asyncio
    async def test_health_check_all_providers(self, registry):
        """Test health check for all providers."""
        provider1 = MockProvider("provider1")
        provider2 = MockProvider("provider2")

        registry.register_provider(provider1, enabled=True)
        registry.register_provider(
            provider2, enabled=False
        )  # Disabled, should not be checked

        await registry.initialize_all_providers()

        health_results = await registry.health_check_all_providers()

        assert len(health_results) == 1  # Only enabled providers
        assert "provider1" in health_results
        assert health_results["provider1"]["status"] == "healthy"


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_provider_registry(self):
        """Test getting global registry."""
        # Reset first to ensure clean state
        reset_provider_registry()

        registry1 = get_provider_registry()
        registry2 = get_provider_registry()

        # Should return the same instance
        assert registry1 is registry2
        assert isinstance(registry1, ProviderRegistry)

    def test_reset_provider_registry(self):
        """Test resetting global registry."""
        registry1 = get_provider_registry()
        reset_provider_registry()
        registry2 = get_provider_registry()

        # Should be different instances after reset
        assert registry1 is not registry2
