"""Comprehensive API response mocking for integration tests.

This module provides mock responses and helper functions for testing
AniDB API interactions without making real network requests. Updated
to support the new database integration components.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult


class MockAPIResponse:
    """Mock API response data container."""

    def __init__(
        self,
        status_code: int = 200,
        content: str = "",
        headers: dict[str, str] | None = None,
        delay: float = 0.0,
    ) -> None:
        """Initialize mock response.

        Args:
            status_code: HTTP status code
            content: Response body content
            headers: Response headers
            delay: Artificial delay to simulate network latency
        """
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.delay = delay

    @property
    def text(self) -> str:
        """Get response text content."""
        return self.content


class APIResponseMocker:
    """Comprehensive API response mocker for AniDB service testing."""

    def __init__(self) -> None:
        """Initialize the API response mocker."""
        self._search_responses: dict[str, MockAPIResponse] = {}
        self._details_responses: dict[int, MockAPIResponse] = {}
        self._default_search_response: MockAPIResponse | None = None
        self._default_details_response: MockAPIResponse | None = None
        self._request_log: list[dict[str, Any]] = []

    def setup_search_response(
        self,
        query: str,
        response: MockAPIResponse,
    ) -> None:
        """Set up mock response for specific search query.

        Args:
            query: Search query string
            response: Mock response to return
        """
        self._search_responses[query.lower().strip()] = response

    def setup_details_response(
        self,
        aid: int,
        response: MockAPIResponse,
    ) -> None:
        """Set up mock response for specific anime ID.

        Args:
            aid: Anime ID
            response: Mock response to return
        """
        self._details_responses[aid] = response

    def setup_default_search_response(self, response: MockAPIResponse) -> None:
        """Set up default response for unmatched search queries.

        Args:
            response: Default mock response
        """
        self._default_search_response = response

    def setup_default_details_response(self, response: MockAPIResponse) -> None:
        """Set up default response for unmatched anime IDs.

        Args:
            response: Default mock response
        """
        self._default_details_response = response

    def get_search_response(self, query: str) -> MockAPIResponse:
        """Get mock response for search query.

        Args:
            query: Search query string

        Returns:
            Mock response for the query

        Raises:
            KeyError: If no response configured for query
        """
        normalized_query = query.lower().strip()

        if normalized_query in self._search_responses:
            return self._search_responses[normalized_query]

        if self._default_search_response:
            return self._default_search_response

        raise KeyError(f"No mock response configured for search query: {query}")

    def get_details_response(self, aid: int) -> MockAPIResponse:
        """Get mock response for anime details.

        Args:
            aid: Anime ID

        Returns:
            Mock response for the anime ID

        Raises:
            KeyError: If no response configured for anime ID
        """
        if aid in self._details_responses:
            return self._details_responses[aid]

        if self._default_details_response:
            return self._default_details_response

        raise KeyError(f"No mock response configured for anime ID: {aid}")

    def log_request(
        self,
        url: str,
        params: dict[str, Any],
        response: MockAPIResponse,
    ) -> None:
        """Log a mock request for debugging.

        Args:
            url: Request URL
            params: Request parameters
            response: Mock response returned
        """
        self._request_log.append(
            {
                "url": url,
                "params": params,
                "status_code": response.status_code,
                "content_length": len(response.content),
            }
        )

    def get_request_log(self) -> list[dict[str, Any]]:
        """Get log of all mock requests."""
        return self._request_log.copy()

    def clear_request_log(self) -> None:
        """Clear the request log."""
        self._request_log.clear()

    def reset(self) -> None:
        """Reset all mock responses and logs."""
        self._search_responses.clear()
        self._details_responses.clear()
        self._default_search_response = None
        self._default_details_response = None
        self._request_log.clear()


# Global mocker instance for tests
_api_mocker = APIResponseMocker()


def get_api_mocker() -> APIResponseMocker:
    """Get the global API response mocker instance."""
    return _api_mocker


# Pre-defined mock responses for common test scenarios
MOCK_RESPONSES = {
    # Successful search responses
    "evangelion_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="30" type="TV Series" year="1995">
    <title>Neon Genesis Evangelion</title>
  </anime>
  <anime aid="32" type="Movie" year="1997">
    <title>Neon Genesis Evangelion: Death &amp; Rebirth</title>
  </anime>
  <anime aid="39" type="Movie" year="1997">
    <title>Neon Genesis Evangelion: The End of Evangelion</title>
  </anime>
</anime>""",
    ),
    "cowboy_bebop_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="23" type="TV Series" year="1998">
    <title>Cowboy Bebop</title>
  </anime>
  <anime aid="5" type="Movie" year="2001">
    <title>Cowboy Bebop: Tengoku no Tobira</title>
  </anime>
</anime>""",
    ),
    "akira_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="28" type="Movie" year="1988">
    <title>Akira</title>
  </anime>
</anime>""",
    ),
    "naruto_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="239" type="TV Series" year="2002">
    <title>Naruto</title>
  </anime>
  <anime aid="1735" type="TV Series" year="2007">
    <title>Naruto: Shippuuden</title>
  </anime>
</anime>""",
    ),
    "bleach_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="2369" type="TV Series" year="2004">
    <title>Bleach</title>
  </anime>
</anime>""",
    ),
    "one_piece_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="69" type="TV Series" year="1999">
    <title>One Piece</title>
  </anime>
</anime>""",
    ),
    "ghost_in_the_shell_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="61" type="Movie" year="1995">
    <title>Ghost in the Shell</title>
  </anime>
  <anime aid="467" type="TV Series" year="2002">
    <title>Ghost in the Shell: Stand Alone Complex</title>
  </anime>
</anime>""",
    ),
    "totoro_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <anime aid="523" type="Movie" year="1988">
    <title>Tonari no Totoro</title>
  </anime>
</anime>""",
    ),
    # Empty search result
    "empty_search": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime>
  <!-- No anime results -->
</anime>""",
    ),
    # Successful anime details responses
    "evangelion_details": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<anime aid="30" restricted="false">
  <type>TV Series</type>
  <episodecount>26</episodecount>
  <title>Neon Genesis Evangelion</title>
  <startdate>1995-10-04</startdate>
  <enddate>1996-03-27</enddate>
  <description>At the age of 14 Shinji Ikari is summoned by his father to the city of Neo Tokyo-3 after several years of separation.</description>
  <url>http://www.gainax.co.jp/anime/eva/</url>
  <titles>
    <title type="main" lang="en">Neon Genesis Evangelion</title>
    <title type="official" lang="ja">新世紀エヴァンゲリオン</title>
    <title type="synonym" lang="en">Evangelion</title>
    <title type="short" lang="en">NGE</title>
  </titles>
  <creators>
    <creator id="5111" type="Direction">
      <name>Anno Hideaki</name>
    </creator>
    <creator id="5112" type="Music">
      <name>Sagisu Shirou</name>
    </creator>
  </creators>
  <relatedanime>
    <anime aid="32" type="Sequel">
      <title>Neon Genesis Evangelion: Death &amp; Rebirth</title>
    </anime>
    <anime aid="39" type="Sequel">
      <title>Neon Genesis Evangelion: The End of Evangelion</title>
    </anime>
  </relatedanime>
</anime>""",
    ),
    # Error responses
    "anime_not_found": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<error>No such anime</error>""",
    ),
    "invalid_request": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<error>Invalid request parameters</error>""",
    ),
    "client_banned": MockAPIResponse(
        status_code=200,
        content="""<?xml version="1.0" encoding="UTF-8"?>
<error>Client banned</error>""",
    ),
    "server_error": MockAPIResponse(
        status_code=500,
        content="Internal Server Error",
    ),
    "timeout_error": MockAPIResponse(
        status_code=408,
        content="Request Timeout",
    ),
}


async def mock_http_get(
    url: str,
    params: dict[str, Any] | None = None,
    **kwargs: Any,
) -> MockAPIResponse:
    """Mock HTTP GET request handler.

    Args:
        url: Request URL
        params: Request parameters
        **kwargs: Additional request arguments

    Returns:
        Mock API response

    Raises:
        KeyError: If no mock response configured for the request
    """
    params = params or {}
    mocker = get_api_mocker()

    # Determine request type and get appropriate response
    if "request" in params and params["request"] == "anime":
        if "search" in params:
            # Search request
            query = params["search"]
            response = mocker.get_search_response(query)
        elif "aid" in params:
            # Details request
            aid = int(params["aid"])
            response = mocker.get_details_response(aid)
        else:
            raise KeyError("Unknown anime request type")
    else:
        raise KeyError(f"Unknown request type for URL: {url}")

    # Log the request
    mocker.log_request(url, params, response)

    # Simulate network delay if specified
    if response.delay > 0:
        await asyncio.sleep(response.delay)

    return response


def setup_common_mocks() -> None:
    """Set up common mock responses for typical test scenarios."""
    mocker = get_api_mocker()

    # Set up search responses
    mocker.setup_search_response("evangelion", MOCK_RESPONSES["evangelion_search"])
    mocker.setup_search_response(
        "neon genesis evangelion", MOCK_RESPONSES["evangelion_search"]
    )
    mocker.setup_search_response("cowboy bebop", MOCK_RESPONSES["cowboy_bebop_search"])
    mocker.setup_search_response("akira", MOCK_RESPONSES["akira_search"])
    mocker.setup_search_response("naruto", MOCK_RESPONSES["naruto_search"])
    mocker.setup_search_response("bleach", MOCK_RESPONSES["bleach_search"])
    mocker.setup_search_response("one piece", MOCK_RESPONSES["one_piece_search"])
    mocker.setup_search_response(
        "ghost in the shell", MOCK_RESPONSES["ghost_in_the_shell_search"]
    )
    mocker.setup_search_response("totoro", MOCK_RESPONSES["totoro_search"])
    mocker.setup_search_response(
        "xyzabc123nonexistentanime999", MOCK_RESPONSES["empty_search"]
    )

    # Set up details responses
    mocker.setup_details_response(30, MOCK_RESPONSES["evangelion_details"])

    # Set up error responses for invalid IDs
    mocker.setup_details_response(999999999, MOCK_RESPONSES["anime_not_found"])

    # Set up default responses
    mocker.setup_default_search_response(MOCK_RESPONSES["empty_search"])
    mocker.setup_default_details_response(MOCK_RESPONSES["anime_not_found"])


def setup_error_scenarios() -> None:
    """Set up mock responses for error testing scenarios."""
    mocker = get_api_mocker()

    # Set up various error responses
    mocker.setup_search_response("server_error_test", MOCK_RESPONSES["server_error"])
    mocker.setup_search_response("timeout_test", MOCK_RESPONSES["timeout_error"])
    mocker.setup_search_response("banned_test", MOCK_RESPONSES["client_banned"])

    mocker.setup_details_response(500, MOCK_RESPONSES["server_error"])
    mocker.setup_details_response(408, MOCK_RESPONSES["timeout_error"])


def setup_rate_limiting_mocks() -> None:
    """Set up mock responses with artificial delays for rate limiting tests."""
    mocker = get_api_mocker()

    # Add delays to simulate rate limiting
    delayed_responses = {
        "evangelion": MockAPIResponse(
            status_code=200,
            content=MOCK_RESPONSES["evangelion_search"].content,
            delay=0.1,  # Small delay for testing
        ),
        "cowboy bebop": MockAPIResponse(
            status_code=200,
            content=MOCK_RESPONSES["cowboy_bebop_search"].content,
            delay=0.1,
        ),
        "akira": MockAPIResponse(
            status_code=200,
            content=MOCK_RESPONSES["akira_search"].content,
            delay=0.1,
        ),
    }

    for query, response in delayed_responses.items():
        mocker.setup_search_response(query, response)


@pytest.fixture
def api_mocker() -> APIResponseMocker:
    """Pytest fixture providing a clean API response mocker."""
    mocker = get_api_mocker()
    mocker.reset()
    return mocker


@pytest.fixture
def mock_http_client(api_mocker: APIResponseMocker) -> AsyncMock:
    """Pytest fixture providing a mocked HTTP client."""
    mock_client = AsyncMock()

    async def mock_get(
        url: str, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> Mock:
        response = await mock_http_get(url, params, **kwargs)

        mock_response = Mock()
        mock_response.status_code = response.status_code
        mock_response.text = response.content
        mock_response.headers = response.headers

        return mock_response

    mock_client.get = mock_get
    mock_client.is_closed.return_value = False
    mock_client.close = AsyncMock()

    return mock_client


@pytest.fixture
def setup_integration_mocks(api_mocker: APIResponseMocker) -> None:
    """Pytest fixture that sets up all common integration test mocks."""
    setup_common_mocks()
    setup_error_scenarios()


# Enhanced mocks for database integration testing
@pytest.fixture
def mock_database_search_service():
    """Mock database search service for testing local database integration."""
    mock_service = AsyncMock()

    # Default search results
    mock_service.search_anime.return_value = [
        AnimeSearchResult(aid=1, title="Test Anime 1", type="TV Series", year=2020),
        AnimeSearchResult(aid=2, title="Test Anime 2", type="Movie", year=2021),
    ]

    # Default anime details
    mock_service.get_anime_details.return_value = AnimeDetails(
        aid=1,
        title="Test Anime",
        type="TV Series",
        episode_count=12,
        titles=[],
        creators=[],
        related_anime=[],
    )

    return mock_service


@pytest.fixture
def mock_titles_downloader():
    """Mock titles downloader for testing database updates."""
    mock_downloader = AsyncMock()

    # Mock successful download
    mock_downloader.download_titles.return_value = b"mock titles data"
    mock_downloader.get_download_info.return_value = {
        "size": 1024,
        "last_modified": "2023-01-01T00:00:00Z",
        "etag": "mock-etag",
    }

    return mock_downloader


@pytest.fixture
def patch_database_components():
    """Patch database components for integration testing."""
    patches = {}

    # Import the database mocks
    from tests.fixtures.database_mocks import (
        MockAnalyticsScheduler,
        MockMaintenanceScheduler,
        MockMultiProviderDatabase,
        MockSchemaManager,
        MockTitlesDatabase,
        MockTransactionLogger,
    )

    # Create mock instances
    mock_titles_db = MockTitlesDatabase()
    mock_multi_db = MockMultiProviderDatabase()
    mock_schema_mgr = MockSchemaManager()
    mock_transaction_logger = MockTransactionLogger()
    mock_maintenance_scheduler = MockMaintenanceScheduler()
    mock_analytics_scheduler = MockAnalyticsScheduler()

    # Set up patches
    patches["titles_database"] = patch(
        "src.mcp_server_anime.core.titles_db.TitlesDatabase",
        return_value=mock_titles_db,
    )
    patches["multi_provider_database"] = patch(
        "src.mcp_server_anime.core.multi_provider_db.MultiProviderDatabase",
        return_value=mock_multi_db,
    )
    patches["schema_manager"] = patch(
        "src.mcp_server_anime.core.schema_manager.SchemaManager",
        return_value=mock_schema_mgr,
    )
    patches["transaction_logger"] = patch(
        "src.mcp_server_anime.core.transaction_logger.TransactionLogger",
        return_value=mock_transaction_logger,
    )
    patches["maintenance_scheduler"] = patch(
        "src.mcp_server_anime.core.maintenance_scheduler.MaintenanceScheduler",
        return_value=mock_maintenance_scheduler,
    )
    patches["analytics_scheduler"] = patch(
        "src.mcp_server_anime.core.analytics_scheduler.AnalyticsScheduler",
        return_value=mock_analytics_scheduler,
    )

    # Start all patches
    for patch_obj in patches.values():
        patch_obj.start()

    yield {
        "titles_database": mock_titles_db,
        "multi_provider_database": mock_multi_db,
        "schema_manager": mock_schema_mgr,
        "transaction_logger": mock_transaction_logger,
        "maintenance_scheduler": mock_maintenance_scheduler,
        "analytics_scheduler": mock_analytics_scheduler,
    }

    # Stop all patches
    for patch_obj in patches.values():
        patch_obj.stop()


@pytest.fixture
def enhanced_integration_mocks(
    api_mocker: APIResponseMocker,
    mock_database_search_service: AsyncMock,
    mock_titles_downloader: AsyncMock,
    patch_database_components: dict[str, Any],
) -> dict[str, Any]:
    """Enhanced integration mocks including database components."""
    setup_common_mocks()
    setup_error_scenarios()

    return {
        "api_mocker": api_mocker,
        "database_search_service": mock_database_search_service,
        "titles_downloader": mock_titles_downloader,
        **patch_database_components,
    }
