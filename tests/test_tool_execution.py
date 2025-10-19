"""Tests for tool creation and formatting functions."""

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.providers.base import (
    AnimeDataProvider,
    ProviderCapabilities,
    ProviderInfo,
)
from src.mcp_server_anime.providers.tools import (
    _format_anime_details_with_provider,
    create_details_tool,
    create_search_tool,
    register_all_provider_tools,
)


class MockTestProvider(AnimeDataProvider):
    """Test provider for tool creation testing."""

    def __init__(self):
        super().__init__()
        self._initialized = True

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="test_provider",
            display_name="Test Provider",
            version="1.0.0",
            description="Test provider for tool creation",
            capabilities=ProviderCapabilities(
                supports_search=True,
                supports_details=True,
                supports_recommendations=False,
                max_search_results=50,
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
        return [
            AnimeSearchResult(
                aid=1,
                title=f"Test Anime {query}",
                type="TV Series",
                episode_count=12,
                year=2023,
                rating=8.5,
            )
        ]

    async def _get_anime_details_impl(
        self, anime_id: str | int, **kwargs
    ) -> AnimeDetails:
        aid = int(anime_id) if isinstance(anime_id, str) else anime_id
        return AnimeDetails(
            aid=aid,
            title=f"Test Anime Details {aid}",
            type="TV Series",
            episode_count=24,
            year=2023,
            rating=9.0,
            description="Test anime description",
            genres=["Action", "Adventure"],
            status="Completed",
        )


class TestToolCreation:
    """Test tool creation functions."""

    @pytest.fixture
    def provider(self):
        """Create test provider."""
        return MockTestProvider()

    @pytest.fixture
    def mock_mcp(self):
        """Create mock FastMCP server."""
        mcp = MagicMock(spec=FastMCP)
        mcp.tool = MagicMock()
        return mcp

    def test_search_tool_creation(self, mock_mcp, provider):
        """Test search tool creation and registration."""
        # Create the search tool
        create_search_tool(mock_mcp, provider, "anime_search_test")

        # Verify tool was registered
        assert mock_mcp.tool.called

        # Verify the tool decorator was called with the correct name
        call_args = mock_mcp.tool.call_args
        assert call_args[1]["name"] == "anime_search_test"

    def test_details_tool_creation(self, mock_mcp, provider):
        """Test details tool creation and registration."""
        # Create the details tool
        create_details_tool(mock_mcp, provider, "anime_details_test")

        # Verify tool was registered
        assert mock_mcp.tool.called

        # Verify the tool decorator was called with the correct name
        call_args = mock_mcp.tool.call_args
        assert call_args[1]["name"] == "anime_details_test"

    def test_format_anime_details_with_provider(self, provider):
        """Test anime details formatting with provider info."""
        details = AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV Series",
            episode_count=12,
            synopsis="Test synopsis",
        )

        result = _format_anime_details_with_provider(details, "test_provider")

        assert result["aid"] == 1
        assert result["title"] == "Test Anime"
        assert result["provider"] == "test_provider"
        assert result["synopsis"] == "Test synopsis"
        assert result["type"] == "TV Series"
        assert result["episode_count"] == 12
        assert result["titles"] == []  # Empty list by default
        assert result["creators"] == []  # Empty list by default
        assert result["related_anime"] == []  # Empty list by default
        assert result["restricted"] is False  # Default value

    def test_register_all_provider_tools_with_error(self, mock_mcp):
        """Test register_all_provider_tools with provider error."""
        from unittest.mock import patch

        from src.mcp_server_anime.providers.registry import ProviderRegistry

        # Create a mock registry
        mock_registry = MagicMock(spec=ProviderRegistry)

        # Create a provider that will raise an error during tool registration
        error_provider = MockTestProvider()

        # Mock the registry to return our error provider
        mock_registry.get_enabled_providers.return_value = {
            "error_provider": error_provider
        }

        # Mock register_provider_tools to raise an exception
        with patch(
            "src.mcp_server_anime.providers.tools.register_provider_tools"
        ) as mock_register:
            mock_register.side_effect = Exception("Test error during tool registration")

            # This should handle the exception gracefully
            result = register_all_provider_tools(mock_mcp, mock_registry)

            # Should return empty dict since registration failed
            assert result == {}

            # Verify the register function was called
            mock_register.assert_called_once_with(mock_mcp, error_provider)

    def test_register_all_provider_tools_uninitialized_provider(self, mock_mcp):
        """Test register_all_provider_tools with uninitialized provider."""
        from src.mcp_server_anime.providers.registry import ProviderRegistry

        # Create a mock registry
        mock_registry = MagicMock(spec=ProviderRegistry)

        # Create an uninitialized provider
        uninitialized_provider = MockTestProvider()
        uninitialized_provider._initialized = False

        # Mock the registry to return our uninitialized provider
        mock_registry.get_enabled_providers.return_value = {
            "uninitialized_provider": uninitialized_provider
        }

        # This should skip the uninitialized provider
        result = register_all_provider_tools(mock_mcp, mock_registry)

        # Should return empty dict since provider was skipped
        assert result == {}
