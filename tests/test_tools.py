"""Tests for MCP tools implementation.

This module contains unit tests for the anime search and details MCP tools,
including parameter validation, response formatting, and error handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from src.mcp_server_anime.core.models import (
    AnimeCreator,
    AnimeDetails,
    AnimeSearchResult,
    AnimeTitle,
    APIError,
    RelatedAnime,
)
from src.mcp_server_anime.tools import (
    _format_anime_details,
    _format_anime_search_result,
    _validate_search_parameters,
    register_anime_tools,
)


def setup_service_mock(sample_results=None, side_effect=None):
    """Helper function to set up service mocks consistently."""
    mock_service = AsyncMock()
    if side_effect:
        mock_service.search_anime.side_effect = side_effect
    elif sample_results:
        mock_service.search_anime.return_value = sample_results

    mock_service.__aenter__.return_value = mock_service
    mock_service.__aexit__.return_value = None
    return mock_service


class TestAnimeSearchTool:
    """Test cases for the anime_search MCP tool."""

    @pytest.fixture
    def mcp_server(self) -> FastMCP:
        """Create a FastMCP server instance for testing."""
        mcp = FastMCP("test-server")
        register_anime_tools(mcp)
        return mcp

    @pytest.fixture
    def sample_search_results(self) -> list[AnimeSearchResult]:
        """Sample anime search results for testing."""
        return [
            AnimeSearchResult(
                aid=30, title="Neon Genesis Evangelion", type="TV Series", year=1995
            ),
            AnimeSearchResult(
                aid=2759,
                title="Evangelion: 1.0 You Are (Not) Alone",
                type="Movie",
                year=2007,
            ),
        ]

    @pytest.mark.asyncio
    async def test_anime_search_success(
        self, mcp_server: FastMCP, sample_search_results: list[AnimeSearchResult]
    ) -> None:
        """Test successful anime search with valid parameters."""
        with patch(
            "src.mcp_server_anime.tools.get_search_service"
        ) as mock_get_search_service:
            # Setup mocks
            mock_search_service = AsyncMock()
            mock_search_service.search_anime.return_value = sample_search_results
            mock_get_search_service.return_value = mock_search_service

            # Get the registered tool function
            tools = mcp_server._tool_manager._tools
            assert "anime_search" in tools
            anime_search_func = tools["anime_search"].fn

            # Call the tool
            result = await anime_search_func(query="evangelion", limit=10)

            # Verify result format
            assert isinstance(result, list)
            assert len(result) == 2

            # Check first result
            first_result = result[0]
            assert first_result["aid"] == 30
            assert first_result["title"] == "Neon Genesis Evangelion"
            assert first_result["type"] == "TV Series"
            assert first_result["year"] == 1995

            # Check second result
            second_result = result[1]
            assert second_result["aid"] == 2759
            assert second_result["title"] == "Evangelion: 1.0 You Are (Not) Alone"
            assert second_result["type"] == "Movie"
            assert second_result["year"] == 2007

            # Verify service was called correctly
            mock_search_service.search_anime.assert_called_once_with(
                "evangelion", 10, client_id="mcp_tool"
            )

    @pytest.mark.asyncio
    async def test_anime_search_empty_query(self, mcp_server: FastMCP) -> None:
        """Test anime search with empty query raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await anime_search_func(query="", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_whitespace_query(self, mcp_server: FastMCP) -> None:
        """Test anime search with whitespace-only query raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await anime_search_func(query="   ", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_short_query(self, mcp_server: FastMCP) -> None:
        """Test anime search with too short query raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(
            ValueError, match="Search query must be at least 2 characters long"
        ):
            await anime_search_func(query="a", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_invalid_limit_zero(self, mcp_server: FastMCP) -> None:
        """Test anime search with zero limit raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(ValueError, match="Limit must be at least 1"):
            await anime_search_func(query="evangelion", limit=0)

    @pytest.mark.asyncio
    async def test_anime_search_invalid_limit_negative(
        self, mcp_server: FastMCP
    ) -> None:
        """Test anime search with negative limit raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(ValueError, match="Limit must be at least 1"):
            await anime_search_func(query="evangelion", limit=-5)

    @pytest.mark.asyncio
    async def test_anime_search_limit_too_high(self, mcp_server: FastMCP) -> None:
        """Test anime search with limit exceeding maximum raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_search_func = tools["anime_search"].fn

        with pytest.raises(
            ValueError, match="Limit cannot exceed 20 for MCP tool usage"
        ):
            await anime_search_func(query="evangelion", limit=25)

    @pytest.mark.asyncio
    async def test_anime_search_api_validation_error(self, mcp_server: FastMCP) -> None:
        """Test anime search with API validation error converts to ValueError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="INVALID_QUERY",
                message="Query validation failed",
                details="Query too short",
            )
            mock_service = setup_service_mock(side_effect=api_error)
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_search_func = tools["anime_search"].fn

            # The error handling logic converts APIError to RuntimeError, not ValueError
            # because it's not a DataValidationError
            with pytest.raises(
                RuntimeError,
                match=r"Anime search failed: INVALID_QUERY: Query validation failed \| Details: Query too short",
            ):
                await anime_search_func(query="evangelion", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_api_runtime_error(self, mcp_server: FastMCP) -> None:
        """Test anime search with API runtime error converts to RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="API_ERROR",
                message="API request failed",
                details="Network timeout",
            )
            mock_service = setup_service_mock(side_effect=api_error)
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_search_func = tools["anime_search"].fn

            with pytest.raises(
                RuntimeError,
                match=r"Anime search failed: API_ERROR: API request failed \| Details: Network timeout",
            ):
                await anime_search_func(query="evangelion", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_unexpected_error(self, mcp_server: FastMCP) -> None:
        """Test anime search with unexpected error converts to RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = setup_service_mock(side_effect=Exception("Unexpected error"))
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_search_func = tools["anime_search"].fn

            with pytest.raises(
                RuntimeError, match="Anime search failed: Unexpected error"
            ):
                await anime_search_func(query="evangelion", limit=10)

    @pytest.mark.asyncio
    async def test_anime_search_default_limit(
        self, mcp_server: FastMCP, sample_search_results: list[AnimeSearchResult]
    ) -> None:
        """Test anime search uses default limit when not specified."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = AsyncMock()
            mock_service.search_anime.return_value = sample_search_results
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_search_func = tools["anime_search"].fn

            # Call without limit parameter
            result = await anime_search_func(query="evangelion")

            # Verify default limit was used
            mock_service.search_anime.assert_called_once_with("evangelion", 10)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_anime_search_strips_whitespace(
        self, mcp_server: FastMCP, sample_search_results: list[AnimeSearchResult]
    ) -> None:
        """Test anime search strips whitespace from query."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = AsyncMock()
            mock_service.search_anime.return_value = sample_search_results
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_search_func = tools["anime_search"].fn

            # Call with whitespace-padded query
            result = await anime_search_func(query="  evangelion  ", limit=5)

            # Verify whitespace was stripped
            mock_service.search_anime.assert_called_once_with("evangelion", 5)
            assert len(result) == 2


class TestFormatAnimeSearchResult:
    """Test cases for the _format_anime_search_result helper function."""

    def test_format_complete_result(self) -> None:
        """Test formatting a complete anime search result."""
        result = AnimeSearchResult(
            aid=30, title="Neon Genesis Evangelion", type="TV Series", year=1995
        )

        formatted = _format_anime_search_result(result)

        assert formatted == {
            "aid": 30,
            "title": "Neon Genesis Evangelion",
            "type": "TV Series",
            "year": 1995,
        }

    def test_format_result_without_year(self) -> None:
        """Test formatting anime search result without year."""
        result = AnimeSearchResult(aid=123, title="Test Anime", type="OVA", year=None)

        formatted = _format_anime_search_result(result)

        assert formatted == {
            "aid": 123,
            "title": "Test Anime",
            "type": "OVA",
            "year": None,
        }


class TestValidateSearchParameters:
    """Test cases for the _validate_search_parameters helper function."""

    def test_valid_parameters(self) -> None:
        """Test validation with valid parameters."""
        # Should not raise any exception
        _validate_search_parameters("evangelion", 10)
        _validate_search_parameters("ab", 1)
        _validate_search_parameters("test query", 20)

    def test_empty_query(self) -> None:
        """Test validation with empty query."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            _validate_search_parameters("", 10)

    def test_whitespace_query(self) -> None:
        """Test validation with whitespace-only query."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            _validate_search_parameters("   ", 10)

    def test_short_query(self) -> None:
        """Test validation with too short query."""
        with pytest.raises(
            ValueError, match="Search query must be at least 2 characters long"
        ):
            _validate_search_parameters("a", 10)

    def test_zero_limit(self) -> None:
        """Test validation with zero limit."""
        with pytest.raises(ValueError, match="Limit must be at least 1"):
            _validate_search_parameters("evangelion", 0)

    def test_negative_limit(self) -> None:
        """Test validation with negative limit."""
        with pytest.raises(ValueError, match="Limit must be at least 1"):
            _validate_search_parameters("evangelion", -5)

    def test_high_limit(self) -> None:
        """Test validation with limit exceeding maximum."""
        with pytest.raises(
            ValueError, match="Limit cannot exceed 20 for MCP tool usage"
        ):
            _validate_search_parameters("evangelion", 25)

    def test_boundary_limits(self) -> None:
        """Test validation with boundary limit values."""
        # Should not raise exceptions
        _validate_search_parameters("evangelion", 1)  # Minimum valid
        _validate_search_parameters("evangelion", 20)  # Maximum valid


class TestAnimeDetailsTool:
    """Test cases for the anime_details MCP tool."""

    @pytest.fixture
    def mcp_server(self) -> FastMCP:
        """Create a FastMCP server instance for testing."""
        mcp = FastMCP("test-server")
        register_anime_tools(mcp)
        return mcp

    @pytest.fixture
    def sample_anime_details(self) -> AnimeDetails:
        """Sample anime details for testing."""
        return AnimeDetails(
            aid=30,
            title="Neon Genesis Evangelion",
            type="TV Series",
            episode_count=26,
            start_date=datetime(1995, 10, 4),
            end_date=datetime(1996, 3, 27),
            titles=[
                AnimeTitle(title="Neon Genesis Evangelion", language="en", type="main"),
                AnimeTitle(
                    title="新世紀エヴァンゲリオン", language="ja", type="official"
                ),
                AnimeTitle(title="NGE", language="en", type="short"),
            ],
            synopsis="Fifteen years after a worldwide cataclysm, pilot Ikari Shinji is recruited by his father to join NERV and pilot a giant mecha called Evangelion to fight mysterious beings known as Angels.",
            url="https://www.gainax.co.jp/anime/eva/",
            creators=[
                AnimeCreator(name="Anno Hideaki", id=5468, type="Direction"),
                AnimeCreator(name="Sagisu Shiro", id=5469, type="Music"),
            ],
            related_anime=[
                RelatedAnime(
                    aid=64, title="Evangelion: Death & Rebirth", type="Summary"
                ),
                RelatedAnime(aid=65, title="The End of Evangelion", type="Sequel"),
            ],
            restricted=False,
        )

    @pytest.mark.asyncio
    async def test_anime_details_success(
        self, mcp_server: FastMCP, sample_anime_details: AnimeDetails
    ) -> None:
        """Test successful anime details retrieval with valid AID."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = AsyncMock()
            mock_service.get_anime_details.return_value = sample_anime_details
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            # Get the registered tool function
            tools = mcp_server._tool_manager._tools
            assert "anime_details" in tools
            anime_details_func = tools["anime_details"].fn

            # Call the tool
            result = await anime_details_func(aid=30)

            # Verify result format
            assert isinstance(result, dict)

            # Check basic fields
            assert result["aid"] == 30
            assert result["title"] == "Neon Genesis Evangelion"
            assert result["type"] == "TV Series"
            assert result["episode_count"] == 26
            assert result["start_date"] == "1995-10-04T00:00:00"
            assert result["end_date"] == "1996-03-27T00:00:00"
            assert (
                result["synopsis"]
                == "Fifteen years after a worldwide cataclysm, pilot Ikari Shinji is recruited by his father to join NERV and pilot a giant mecha called Evangelion to fight mysterious beings known as Angels."
            )
            assert result["url"] == "https://www.gainax.co.jp/anime/eva/"
            assert result["restricted"] is False

            # Check titles array
            assert len(result["titles"]) == 3
            assert result["titles"][0] == {
                "title": "Neon Genesis Evangelion",
                "language": "en",
                "type": "main",
            }
            assert result["titles"][1] == {
                "title": "新世紀エヴァンゲリオン",
                "language": "ja",
                "type": "official",
            }
            assert result["titles"][2] == {
                "title": "NGE",
                "language": "en",
                "type": "short",
            }

            # Check creators array
            assert len(result["creators"]) == 2
            assert result["creators"][0] == {
                "name": "Anno Hideaki",
                "id": 5468,
                "type": "Direction",
            }
            assert result["creators"][1] == {
                "name": "Sagisu Shiro",
                "id": 5469,
                "type": "Music",
            }

            # Check related anime array
            assert len(result["related_anime"]) == 2
            assert result["related_anime"][0] == {
                "aid": 64,
                "title": "Evangelion: Death & Rebirth",
                "type": "Summary",
            }
            assert result["related_anime"][1] == {
                "aid": 65,
                "title": "The End of Evangelion",
                "type": "Sequel",
            }

            # Verify service was called correctly
            mock_service.get_anime_details.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_anime_details_minimal_data(self, mcp_server: FastMCP) -> None:
        """Test anime details with minimal data (no optional fields)."""
        minimal_details = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="OVA",
            episode_count=1,
            start_date=None,
            end_date=None,
            titles=[],
            synopsis=None,
            url=None,
            creators=[],
            related_anime=[],
            restricted=True,
        )

        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = AsyncMock()
            mock_service.get_anime_details.return_value = minimal_details
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            # Call the tool
            result = await anime_details_func(aid=123)

            # Verify minimal result format
            assert result["aid"] == 123
            assert result["title"] == "Test Anime"
            assert result["type"] == "OVA"
            assert result["episode_count"] == 1
            assert result["start_date"] is None
            assert result["end_date"] is None
            assert result["synopsis"] is None
            assert result["url"] is None
            assert result["restricted"] is True
            assert result["titles"] == []
            assert result["creators"] == []
            assert result["related_anime"] == []

    @pytest.mark.asyncio
    async def test_anime_details_invalid_aid_type(self, mcp_server: FastMCP) -> None:
        """Test anime details with non-integer AID raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_details_func = tools["anime_details"].fn

        with pytest.raises(ValueError, match="Anime ID must be an integer, got str"):
            await anime_details_func(aid="30")

    @pytest.mark.asyncio
    async def test_anime_details_invalid_aid_zero(self, mcp_server: FastMCP) -> None:
        """Test anime details with zero AID raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_details_func = tools["anime_details"].fn

        with pytest.raises(
            ValueError, match="Anime ID must be a positive integer, got 0"
        ):
            await anime_details_func(aid=0)

    @pytest.mark.asyncio
    async def test_anime_details_invalid_aid_negative(
        self, mcp_server: FastMCP
    ) -> None:
        """Test anime details with negative AID raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_details_func = tools["anime_details"].fn

        with pytest.raises(
            ValueError, match="Anime ID must be a positive integer, got -5"
        ):
            await anime_details_func(aid=-5)

    @pytest.mark.asyncio
    async def test_anime_details_aid_out_of_range(self, mcp_server: FastMCP) -> None:
        """Test anime details with AID out of valid range raises ValueError."""
        tools = mcp_server._tool_manager._tools
        anime_details_func = tools["anime_details"].fn

        with pytest.raises(
            ValueError,
            match="Anime ID appears to be out of valid range \\(1-999999\\), got 1000000",
        ):
            await anime_details_func(aid=1000000)

    @pytest.mark.asyncio
    async def test_anime_details_not_found(self, mcp_server: FastMCP) -> None:
        """Test anime details with non-existent AID raises RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="ANIME_NOT_FOUND",
                message="Anime with ID 99999 not found",
                details="The specified anime ID does not exist in the database",
            )
            mock_service = AsyncMock()
            mock_service.get_anime_details.side_effect = api_error
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            with pytest.raises(
                RuntimeError, match="Anime not found: Anime with ID 99999 not found"
            ):
                await anime_details_func(aid=99999)

    @pytest.mark.asyncio
    async def test_anime_details_api_validation_error(
        self, mcp_server: FastMCP
    ) -> None:
        """Test anime details with API validation error converts to ValueError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="INVALID_AID_VALUE",
                message="Anime ID must be a positive integer",
                details="Provided aid: -1",
            )
            mock_service = AsyncMock()
            mock_service.get_anime_details.side_effect = api_error
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            # The error handling logic converts APIError to RuntimeError, not ValueError
            # because it's not a DataValidationError
            with pytest.raises(
                RuntimeError,
                match=r"Anime details fetch failed: INVALID_AID_VALUE: Anime ID must be a positive integer \| Details: Provided aid: -1",
            ):
                await anime_details_func(aid=30)

    @pytest.mark.asyncio
    async def test_anime_details_client_banned_error(self, mcp_server: FastMCP) -> None:
        """Test anime details with client banned error converts to RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="CLIENT_BANNED",
                message="Client is banned from API",
                details="API access has been restricted for this client",
            )
            mock_service = AsyncMock()
            mock_service.get_anime_details.side_effect = api_error
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            with pytest.raises(
                RuntimeError,
                match="Anime details fetch failed: CLIENT_BANNED: Client is banned from API",
            ):
                await anime_details_func(aid=30)

    @pytest.mark.asyncio
    async def test_anime_details_api_runtime_error(self, mcp_server: FastMCP) -> None:
        """Test anime details with API runtime error converts to RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            api_error = APIError(
                code="API_ERROR",
                message="API request failed",
                details="Network timeout",
            )
            mock_service = AsyncMock()
            mock_service.get_anime_details.side_effect = api_error
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            with pytest.raises(
                RuntimeError,
                match="Anime details fetch failed: API_ERROR: API request failed",
            ):
                await anime_details_func(aid=30)

    @pytest.mark.asyncio
    async def test_anime_details_unexpected_error(self, mcp_server: FastMCP) -> None:
        """Test anime details with unexpected error converts to RuntimeError."""
        with (
            patch("src.mcp_server_anime.tools.load_config") as mock_load_config,
            patch(
                "src.mcp_server_anime.tools.create_anidb_service"
            ) as mock_create_service,
        ):
            # Setup mocks
            mock_config = Mock()
            mock_load_config.return_value = mock_config

            mock_service = AsyncMock()
            mock_service.get_anime_details.side_effect = Exception("Unexpected error")
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            mock_create_service.return_value = mock_service

            tools = mcp_server._tool_manager._tools
            anime_details_func = tools["anime_details"].fn

            with pytest.raises(
                RuntimeError, match="Anime details fetch failed: Unexpected error"
            ):
                await anime_details_func(aid=30)


class TestFormatAnimeDetails:
    """Test cases for the _format_anime_details helper function."""

    def test_format_complete_details(self) -> None:
        """Test formatting complete anime details."""
        details = AnimeDetails(
            aid=30,
            title="Neon Genesis Evangelion",
            type="TV Series",
            episode_count=26,
            start_date=datetime(1995, 10, 4),
            end_date=datetime(1996, 3, 27),
            titles=[
                AnimeTitle(title="Neon Genesis Evangelion", language="en", type="main"),
                AnimeTitle(
                    title="新世紀エヴァンゲリオン", language="ja", type="official"
                ),
            ],
            synopsis="Test synopsis",
            url="https://example.com",
            creators=[AnimeCreator(name="Anno Hideaki", id=5468, type="Direction")],
            related_anime=[RelatedAnime(aid=64, title="Related Anime", type="Sequel")],
            restricted=False,
        )

        formatted = _format_anime_details(details)

        # Check basic fields
        assert formatted["aid"] == 30
        assert formatted["title"] == "Neon Genesis Evangelion"
        assert formatted["type"] == "TV Series"
        assert formatted["episode_count"] == 26
        assert formatted["start_date"] == "1995-10-04T00:00:00"
        assert formatted["end_date"] == "1996-03-27T00:00:00"
        assert formatted["synopsis"] == "Test synopsis"
        assert formatted["url"] == "https://example.com/"
        assert formatted["restricted"] is False

        # Check arrays
        assert len(formatted["titles"]) == 2
        assert formatted["titles"][0] == {
            "title": "Neon Genesis Evangelion",
            "language": "en",
            "type": "main",
        }
        assert formatted["titles"][1] == {
            "title": "新世紀エヴァンゲリオン",
            "language": "ja",
            "type": "official",
        }

        assert len(formatted["creators"]) == 1
        assert formatted["creators"][0] == {
            "name": "Anno Hideaki",
            "id": 5468,
            "type": "Direction",
        }

        assert len(formatted["related_anime"]) == 1
        assert formatted["related_anime"][0] == {
            "aid": 64,
            "title": "Related Anime",
            "type": "Sequel",
        }

    def test_format_minimal_details(self) -> None:
        """Test formatting anime details with minimal data."""
        details = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="OVA",
            episode_count=1,
            start_date=None,
            end_date=None,
            titles=[],
            synopsis=None,
            url=None,
            creators=[],
            related_anime=[],
            restricted=True,
        )

        formatted = _format_anime_details(details)

        assert formatted["aid"] == 123
        assert formatted["title"] == "Test Anime"
        assert formatted["type"] == "OVA"
        assert formatted["episode_count"] == 1
        assert formatted["start_date"] is None
        assert formatted["end_date"] is None
        assert formatted["synopsis"] is None
        assert formatted["url"] is None
        assert formatted["restricted"] is True
        assert formatted["titles"] == []
        assert formatted["creators"] == []
        assert formatted["related_anime"] == []

    def test_format_details_with_empty_synopsis(self) -> None:
        """Test formatting anime details with empty synopsis."""
        details = AnimeDetails(
            aid=456,
            title="Another Anime",
            type="Movie",
            episode_count=1,
            synopsis="",  # Empty string
            restricted=False,
        )

        formatted = _format_anime_details(details)

        assert formatted["synopsis"] is None
        assert formatted["aid"] == 456


class TestRegisterAnimeTools:
    """Test cases for the register_anime_tools function."""

    def test_register_tools(self) -> None:
        """Test that anime tools are properly registered."""
        mcp = FastMCP("test-server")

        # Initially no tools
        assert len(mcp._tool_manager._tools) == 0

        # Register anime tools
        register_anime_tools(mcp)

        # Verify anime_search tool is registered
        assert "anime_search" in mcp._tool_manager._tools

        # Verify anime_details tool is registered
        assert "anime_details" in mcp._tool_manager._tools

        # Verify anime_search tool has correct metadata
        anime_search_tool = mcp._tool_manager._tools["anime_search"]
        assert anime_search_tool.name == "anime_search"
        assert callable(anime_search_tool.fn)

        # Verify anime_details tool has correct metadata
        anime_details_tool = mcp._tool_manager._tools["anime_details"]
        assert anime_details_tool.name == "anime_details"
        assert callable(anime_details_tool.fn)

        # Verify tool function signatures
        import inspect

        # Check anime_search signature
        search_sig = inspect.signature(anime_search_tool.fn)
        search_params = list(search_sig.parameters.keys())
        assert "query" in search_params
        assert "limit" in search_params

        # Check anime_details signature
        details_sig = inspect.signature(anime_details_tool.fn)
        details_params = list(details_sig.parameters.keys())
        assert "aid" in details_params
