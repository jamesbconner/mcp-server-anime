"""Unit tests for AniDB service layer.

This module contains comprehensive unit tests for the AniDBService class,
including parameter validation, URL construction, HTTP client integration,
XML parsing integration, and error handling scenarios.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_server_anime.core.exceptions import (
    DataValidationError,
    ServiceError,
    XMLParsingError,
)
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult, APIError
from src.mcp_server_anime.providers.anidb.config import AniDBConfig
from src.mcp_server_anime.providers.anidb.service import (
    AniDBService,
    create_anidb_service,
)


class TestAniDBService:
    """Test cases for AniDBService class."""

    @pytest.fixture
    def config(self) -> AniDBConfig:
        """Create test configuration."""
        return AniDBConfig(
            client_name="test-client",
            client_version=1,
            protocol_version=1,
            base_url="http://test.api.com/httpapi",
            rate_limit_delay=0.1,  # Faster for tests
            max_retries=2,
            cache_ttl=300,
            timeout=10.0,
        )

    @pytest.fixture
    def service(self, config: AniDBConfig) -> AniDBService:
        """Create test service instance."""
        return AniDBService(config)

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create mock HTTP client."""
        client = AsyncMock()
        client.is_closed = Mock(return_value=False)  # Make is_closed a regular method
        return client

    def test_init_with_config(self, config: AniDBConfig) -> None:
        """Test service initialization with config."""
        service = AniDBService(config)
        assert service.config == config
        assert service._http_client is None
        assert not service._closed

    def test_init_without_config(self) -> None:
        """Test service initialization without config loads from environment."""
        with patch(
            "src.mcp_server_anime.providers.anidb.service.load_config"
        ) as mock_load:
            mock_config = Mock()
            mock_load.return_value = mock_config

            service = AniDBService()
            assert service.config == mock_config
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test async context manager functionality."""
        with patch(
            "src.mcp_server_anime.providers.anidb.service.create_http_client",
            return_value=mock_http_client,
        ):
            async with service:
                assert service._http_client == mock_http_client

            mock_http_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test service close method."""
        service._http_client = mock_http_client

        await service.close()

        assert service._closed
        mock_http_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_client(self, service: AniDBService) -> None:
        """Test close method when no HTTP client exists."""
        await service.close()
        assert service._closed

    def test_validate_search_params_valid(self, service: AniDBService) -> None:
        """Test search parameter validation with valid inputs."""
        # Should not raise any exceptions
        service._validate_search_params("evangelion", 10)
        service._validate_search_params("a" * 100, 1)
        service._validate_search_params("test query", 100)

    def test_validate_search_params_empty_query(self, service: AniDBService) -> None:
        """Test search parameter validation with empty query."""
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("", 10)

        assert exc_info.value.code == "INVALID_QUERY"
        assert "empty" in exc_info.value.message.lower()

    def test_validate_search_params_whitespace_query(
        self, service: AniDBService
    ) -> None:
        """Test search parameter validation with whitespace-only query."""
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("   ", 10)

        assert exc_info.value.code == "INVALID_QUERY"

    def test_validate_search_params_short_query(self, service: AniDBService) -> None:
        """Test search parameter validation with too short query."""
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("a", 10)

        assert exc_info.value.code == "QUERY_TOO_SHORT"
        assert "2 characters" in exc_info.value.message

    def test_validate_search_params_invalid_limit(self, service: AniDBService) -> None:
        """Test search parameter validation with invalid limits."""
        # Test zero limit
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("test", 0)
        assert exc_info.value.code == "INVALID_LIMIT"

        # Test negative limit
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("test", -1)
        assert exc_info.value.code == "INVALID_LIMIT"

        # Test too high limit
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_search_params("test", 101)
        assert exc_info.value.code == "LIMIT_TOO_HIGH"

    def test_validate_anime_id_valid(self, service: AniDBService) -> None:
        """Test anime ID validation with valid inputs."""
        # Should not raise any exceptions
        service._validate_anime_id(1)
        service._validate_anime_id(12345)
        service._validate_anime_id(999999)

    def test_validate_anime_id_invalid_type(self, service: AniDBService) -> None:
        """Test anime ID validation with invalid types."""
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_anime_id("123")  # type: ignore
        assert exc_info.value.code == "INVALID_AID_TYPE"

        with pytest.raises(DataValidationError) as exc_info:
            service._validate_anime_id(123.45)  # type: ignore
        assert exc_info.value.code == "INVALID_AID_TYPE"

    def test_validate_anime_id_invalid_value(self, service: AniDBService) -> None:
        """Test anime ID validation with invalid values."""
        # Test zero
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_anime_id(0)
        assert exc_info.value.code == "INVALID_AID_VALUE"

        # Test negative
        with pytest.raises(DataValidationError) as exc_info:
            service._validate_anime_id(-1)
        assert exc_info.value.code == "INVALID_AID_VALUE"

    def test_build_search_url(self, service: AniDBService) -> None:
        """Test search URL construction."""
        url, params = service._build_search_url("evangelion", 10)

        assert url == service.config.base_url
        assert params["request"] == "anime"
        assert params["aname"] == "evangelion"
        assert params["client"] == service.config.client_name
        assert params["clientver"] == service.config.client_version
        assert params["protover"] == service.config.protocol_version

    def test_build_search_url_strips_whitespace(self, service: AniDBService) -> None:
        """Test search URL construction strips whitespace from query."""
        url, params = service._build_search_url("  evangelion  ", 5)

        assert params["aname"] == "evangelion"

    def test_build_details_url(self, service: AniDBService) -> None:
        """Test details URL construction."""
        url, params = service._build_details_url(123)

        assert url == service.config.base_url
        assert params["request"] == "anime"
        assert params["aid"] == "123"
        assert params["client"] == service.config.client_name
        assert params["clientver"] == service.config.client_version
        assert params["protover"] == service.config.protocol_version

    @pytest.mark.asyncio
    async def test_search_anime_success(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test successful anime search."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <anime>
            <anime aid="1" type="TV Series" year="1995">
                <title>Neon Genesis Evangelion</title>
            </anime>
        </anime>"""

        mock_http_client.get.return_value = mock_response

        # Mock XML parser
        expected_results = [
            AnimeSearchResult(
                aid=1, title="Neon Genesis Evangelion", type="TV Series", year=1995
            )
        ]

        # Mock the search service instead of HTTP client
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = expected_results

        # Mock transaction logger for database integration
        mock_transaction_logger = AsyncMock()

        with (
            patch(
                "src.mcp_server_anime.providers.anidb.service.get_search_service",
                return_value=mock_search_service,
            ),
            patch(
                "src.mcp_server_anime.core.transaction_logger.TransactionLogger",
                return_value=mock_transaction_logger,
            ),
        ):
            results = await service.search_anime("evangelion", 10)

            assert len(results) == 1
            assert results[0].aid == 1
            assert results[0].title == "Neon Genesis Evangelion"

            # Verify search service was called correctly
            mock_search_service.search_anime.assert_called_once_with("evangelion", 10)

    @pytest.mark.asyncio
    async def test_search_anime_closed_service(self, service: AniDBService) -> None:
        """Test search anime with closed service."""
        service._closed = True

        with pytest.raises(ServiceError) as exc_info:
            await service.search_anime("test", 10)

        assert exc_info.value.code == "SERVICE_CLOSED"

    @pytest.mark.asyncio
    async def test_search_anime_invalid_params(self, service: AniDBService) -> None:
        """Test search anime with invalid parameters."""
        with pytest.raises(DataValidationError) as exc_info:
            await service.search_anime("", 10)
        assert exc_info.value.code == "INVALID_QUERY"

        with pytest.raises(DataValidationError) as exc_info:
            await service.search_anime("test", 0)
        assert exc_info.value.code == "INVALID_LIMIT"

    @pytest.mark.asyncio
    async def test_search_anime_http_error(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test search anime with search service error."""
        # Mock the search service to raise an error
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.side_effect = ServiceError(
            "Search service error", code="SEARCH_ERROR"
        )

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            with pytest.raises(ServiceError) as exc_info:
                await service.search_anime("test", 10)

            assert exc_info.value.code == "SEARCH_ERROR"
            assert "Search service error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_search_anime_empty_response(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test search anime with empty results."""
        # Mock the search service to return empty results
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = []

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            results = await service.search_anime("test", 10)

            assert len(results) == 0
            mock_search_service.search_anime.assert_called_once_with("test", 10)

    @pytest.mark.asyncio
    async def test_search_anime_api_error_response(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test search anime with API error from search service."""
        # Mock the search service to raise an API error
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.side_effect = APIError(
            "Client banned", code="CLIENT_BANNED"
        )

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            with pytest.raises(APIError) as exc_info:
                await service.search_anime("test", 10)

            assert exc_info.value.code == "CLIENT_BANNED"
            assert "banned" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_search_anime_xml_parsing_error(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test search anime with XML parsing error."""
        mock_response = Mock()
        # Mock the search service to raise an XML parsing error
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.side_effect = XMLParsingError("Parse failed")

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            with pytest.raises(XMLParsingError) as exc_info:
                await service.search_anime("test", 10)

            assert "Parse failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_anime_details_success(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test successful anime details retrieval."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="1" restricted="false">
            <type>TV Series</type>
            <episodecount>26</episodecount>
            <title>Neon Genesis Evangelion</title>
        </anime>"""

        mock_http_client.get.return_value = mock_response

        # Mock XML parser
        expected_details = AnimeDetails(
            aid=1, title="Neon Genesis Evangelion", type="TV Series", episode_count=26
        )

        with (
            patch(
                "src.mcp_server_anime.providers.anidb.service.create_http_client",
                return_value=mock_http_client,
            ),
            patch(
                "src.mcp_server_anime.providers.anidb.service.parse_anime_details",
                return_value=expected_details,
            ),
        ):
            details = await service.get_anime_details(1)

            assert details.aid == 1
            assert details.title == "Neon Genesis Evangelion"
            assert details.episode_count == 26

            # Verify HTTP client was called correctly
            mock_http_client.get.assert_called_once()
            call_args = mock_http_client.get.call_args
            assert "aid" in call_args[1]["params"]
            assert call_args[1]["params"]["aid"] == "1"

    @pytest.mark.asyncio
    async def test_get_anime_details_closed_service(
        self, service: AniDBService
    ) -> None:
        """Test get anime details with closed service."""
        service._closed = True

        with pytest.raises(ServiceError) as exc_info:
            await service.get_anime_details(1)

        assert exc_info.value.code == "SERVICE_CLOSED"

    @pytest.mark.asyncio
    async def test_get_anime_details_invalid_id(self, service: AniDBService) -> None:
        """Test get anime details with invalid ID."""
        with pytest.raises(DataValidationError) as exc_info:
            await service.get_anime_details(0)
        assert exc_info.value.code == "INVALID_AID_VALUE"

        with pytest.raises(DataValidationError) as exc_info:
            await service.get_anime_details(-1)
        assert exc_info.value.code == "INVALID_AID_VALUE"

    @pytest.mark.asyncio
    async def test_get_anime_details_not_found(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test get anime details with not found response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_http_client.get.return_value = mock_response

        with patch(
            "src.mcp_server_anime.providers.anidb.service.create_http_client",
            return_value=mock_http_client,
        ):
            with pytest.raises(APIError) as exc_info:
                await service.get_anime_details(999999)

            assert exc_info.value.code == "ANIME_NOT_FOUND"
            assert "999999" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_anime_details_api_error_not_found(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test get anime details with 'not found' in XML response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<error>No such anime</error>"
        mock_http_client.get.return_value = mock_response

        with patch(
            "src.mcp_server_anime.providers.anidb.service.create_http_client",
            return_value=mock_http_client,
        ):
            with pytest.raises(APIError) as exc_info:
                await service.get_anime_details(1)

            assert exc_info.value.code == "ANIME_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_anime_details_api_error_banned(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test get anime details with 'banned' in XML response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<error>Client banned</error>"
        mock_http_client.get.return_value = mock_response

        with patch(
            "src.mcp_server_anime.providers.anidb.service.create_http_client",
            return_value=mock_http_client,
        ):
            with pytest.raises(APIError) as exc_info:
                await service.get_anime_details(1)

            assert exc_info.value.code == "CLIENT_BANNED"

    @pytest.mark.asyncio
    async def test_get_anime_details_xml_parsing_error(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test get anime details with XML parsing error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "valid xml"
        mock_http_client.get.return_value = mock_response

        with (
            patch(
                "src.mcp_server_anime.providers.anidb.service.create_http_client",
                return_value=mock_http_client,
            ),
            patch(
                "src.mcp_server_anime.providers.anidb.service.parse_anime_details",
                side_effect=XMLParsingError("Parse failed"),
            ),
        ):
            with pytest.raises(XMLParsingError) as exc_info:
                await service.get_anime_details(1)

            assert "Parse failed" in str(exc_info.value)


class TestCreateAniDBService:
    """Test cases for create_anidb_service function."""

    @pytest.mark.asyncio
    async def test_create_with_config(self) -> None:
        """Test creating service with provided config."""
        config = AniDBConfig(client_name="test")
        service = await create_anidb_service(config)

        assert isinstance(service, AniDBService)
        assert service.config == config

    @pytest.mark.asyncio
    async def test_create_without_config(self) -> None:
        """Test creating service without config."""
        with patch(
            "src.mcp_server_anime.providers.anidb.service.load_config"
        ) as mock_load:
            mock_config = Mock()
            mock_load.return_value = mock_config

            service = await create_anidb_service()

            assert isinstance(service, AniDBService)
            assert service.config == mock_config
            mock_load.assert_called_once()


class TestAniDBServiceCaching:
    """Test cases for AniDBService caching functionality."""

    @pytest.fixture
    def config(self) -> AniDBConfig:
        """Create test configuration with short cache TTL."""
        return AniDBConfig(
            client_name="test-client",
            client_version=1,
            protocol_version=1,
            base_url="http://test.api.com/httpapi",
            rate_limit_delay=0.1,
            max_retries=2,
            cache_ttl=60,  # Minimum allowed TTL
            timeout=10.0,
        )

    @pytest.fixture
    def service(self, config: AniDBConfig) -> AniDBService:
        """Create test service instance."""
        return AniDBService(config)

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create mock HTTP client."""
        client = AsyncMock()
        client.is_closed = Mock(return_value=False)
        return client

    @pytest.fixture
    def sample_search_results(self) -> list[AnimeSearchResult]:
        """Create sample search results for testing."""
        return [
            AnimeSearchResult(aid=1, title="Test Anime 1", type="TV Series", year=2020),
            AnimeSearchResult(aid=2, title="Test Anime 2", type="Movie", year=2021),
        ]

    @pytest.fixture
    def sample_anime_details(self) -> AnimeDetails:
        """Create sample anime details for testing."""
        return AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV Series",
            episode_count=12,
            titles=[],
            creators=[],
            related_anime=[],
        )

    @pytest.mark.asyncio
    async def test_cache_initialization(self, service: AniDBService) -> None:
        """Test that cache is properly initialized."""
        # Cache should be None initially
        assert service._cache is None

        # Ensure cache gets initialized
        await service._ensure_cache()
        assert service._cache is not None
        assert service._cache.default_ttl == service.config.cache_ttl

    @pytest.mark.asyncio
    async def test_search_anime_caching(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test that search results are properly cached."""
        # Mock the search service
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # First call should hit the search service
            result1 = await service.search_anime("test query", 10)
            assert result1 == sample_search_results
            assert mock_search_service.search_anime.call_count == 1

            # Second call should be served from cache
            result2 = await service.search_anime("test query", 10)
            assert result2 == sample_search_results
            # Should still be 1 because second call was served from cache
            assert mock_search_service.search_anime.call_count == 1

    @pytest.mark.asyncio
    async def test_get_anime_details_caching(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test that anime details are properly cached."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<anime>test xml</anime>"
        mock_http_client.get.return_value = mock_response

        with (
            patch(
                "src.mcp_server_anime.providers.anidb.service.create_http_client",
                return_value=mock_http_client,
            ),
            patch(
                "src.mcp_server_anime.providers.anidb.service.parse_anime_details",
                return_value=sample_anime_details,
            ),
        ):
            # First call should hit the API
            result1 = await service.get_anime_details(1)
            assert result1 == sample_anime_details
            assert mock_http_client.get.call_count == 1

            # Second call should use cache
            result2 = await service.get_anime_details(1)
            assert result2 == sample_anime_details
            assert mock_http_client.get.call_count == 1  # No additional API call

            # Verify cache stats
            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["total_entries"] == 1

    @pytest.mark.asyncio
    async def test_different_parameters_different_cache_keys(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test that different parameters create different cache entries."""
        # Mock the search service instead of HTTP client for search operations
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # Different queries should create separate cache entries
            await service.search_anime("query1", 10)
            await service.search_anime("query2", 10)
            await service.search_anime("query1", 20)  # Same query, different limit

            # Should have made 3 search calls (no cache hits)
            assert mock_search_service.search_anime.call_count == 3

            # Verify cache has 3 entries
            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 3
            assert stats["hits"] == 0
            assert stats["misses"] == 3

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test that cache entries expire after TTL."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<anime>test xml</anime>"
        # Mock the search service instead of HTTP client for search operations
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # Initialize cache with short TTL for this test
            await service._ensure_cache()
            assert service._cache is not None

            # Manually set a short TTL entry for testing
            from src.mcp_server_anime.core.cache import generate_cache_key

            cache_key = generate_cache_key("search_anime", query="test query", limit=10)
            await service._cache.set(
                cache_key, sample_search_results, ttl=0.1
            )  # 100ms TTL

            # First call should use cached data
            result1 = await service.search_anime("test query", 10)
            assert result1 == sample_search_results
            assert (
                mock_search_service.search_anime.call_count == 0
            )  # No search service call yet

            # Wait for cache to expire
            import asyncio

            await asyncio.sleep(0.15)

            # Second call should hit search service due to expiration
            await service.search_anime("test query", 10)
            assert mock_search_service.search_anime.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_error_not_cached(
        self, service: AniDBService, mock_http_client: AsyncMock
    ) -> None:
        """Test that API errors are not cached."""
        # Mock search service to raise an error
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.side_effect = ServiceError("Search failed")

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # First call should fail
            with pytest.raises(ServiceError):
                await service.search_anime("test query", 10)

            # Second call should also hit search service (error not cached)
            with pytest.raises(ServiceError):
                await service.search_anime("test query", 10)

            assert mock_search_service.search_anime.call_count == 2

            # Cache should be empty
            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_clear_cache(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test manual cache clearing."""
        # Mock the search service
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # Add some cached data
            await service.search_anime("test query", 10)

            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 1

            # Clear cache
            await service.clear_cache()

            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 0

            # Next call should hit search service again
            await service.search_anime("test query", 10)
            assert mock_search_service.search_anime.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test manual cleanup of expired cache entries."""
        # Initialize cache
        await service._ensure_cache()
        assert service._cache is not None

        # Manually add expired entry for testing
        from src.mcp_server_anime.core.cache import generate_cache_key

        cache_key = generate_cache_key("search_anime", query="test query", limit=10)
        await service._cache.set(cache_key, sample_search_results, ttl=0.1)  # 100ms TTL

        stats = await service.get_cache_stats()
        assert stats is not None
        assert stats["total_entries"] == 1

        # Wait for expiration
        import asyncio

        await asyncio.sleep(0.15)

        # Cleanup expired entries
        expired_count = await service.cleanup_expired_cache()
        assert expired_count == 1

        stats = await service.get_cache_stats()
        assert stats is not None
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_invalidate_cache_key(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test invalidating specific cache keys."""
        # Mock the search service
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # Add cached data
            await service.search_anime("test query", 10)

            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 1

            # Invalidate specific cache key
            invalidated = await service.invalidate_cache_key(
                "search_anime", query="test query", limit=10
            )
            assert invalidated is True

            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 0

            # Try to invalidate non-existent key
            invalidated = await service.invalidate_cache_key(
                "search_anime", query="non-existent", limit=10
            )
            assert invalidated is False

    @pytest.mark.asyncio
    async def test_cache_stats_without_cache(self, service: AniDBService) -> None:
        """Test getting cache stats when cache is not initialized."""
        stats = await service.get_cache_stats()
        assert stats is None

    @pytest.mark.asyncio
    async def test_cache_operations_without_cache(self, service: AniDBService) -> None:
        """Test cache operations when cache is not initialized."""
        # These should not raise errors
        await service.clear_cache()

        expired_count = await service.cleanup_expired_cache()
        assert expired_count == 0

        invalidated = await service.invalidate_cache_key("test_method", param="value")
        assert invalidated is False

    @pytest.mark.asyncio
    async def test_service_close_clears_cache(
        self,
        service: AniDBService,
        mock_http_client: AsyncMock,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test that closing service clears the cache."""
        # Mock HTTP response
        mock_response = Mock()
        # Mock the search service
        mock_search_service = AsyncMock()
        mock_search_service.search_anime.return_value = sample_search_results

        with patch(
            "src.mcp_server_anime.providers.anidb.service.get_search_service",
            return_value=mock_search_service,
        ):
            # Add cached data
            await service.search_anime("test query", 10)

            stats = await service.get_cache_stats()
            assert stats is not None
            assert stats["total_entries"] == 1

            # Close service
            await service.close()

            # Cache should be cleared (but we can't check stats after close)
            assert service._closed is True
