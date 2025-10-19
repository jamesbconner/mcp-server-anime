"""Tests for custom exception classes."""

from src.mcp_server_anime.core.exceptions import (
    APIError,
    AuthenticationError,
    CacheError,
    ConfigurationError,
    DataValidationError,
    MCPServerAnimeError,
    MCPToolError,
    NetworkError,
    RateLimitError,
    ServiceError,
    XMLParsingError,
    create_api_error,
    create_network_error,
    create_validation_error,
)


class TestMCPServerAnimeError:
    """Test the base exception class."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = MCPServerAnimeError("Test message")

        assert error.message == "Test message"
        assert error.code == "MCPSERVERANIMEERROR"
        assert error.details is None
        assert error.context == {}
        assert error.cause is None
        assert str(error) == "MCPSERVERANIMEERROR: Test message"

    def test_full_initialization(self):
        """Test exception initialization with all parameters."""
        context = {"key": "value"}
        cause = ValueError("Original error")

        error = MCPServerAnimeError(
            "Test message",
            code="CUSTOM_CODE",
            details="Additional details",
            context=context,
            cause=cause,
        )

        assert error.message == "Test message"
        assert error.code == "CUSTOM_CODE"
        assert error.details == "Additional details"
        assert error.context == context
        assert error.cause == cause
        assert "CUSTOM_CODE: Test message | Details: Additional details" in str(error)

    def test_add_context(self):
        """Test adding context to exception."""
        error = MCPServerAnimeError("Test message")
        result = error.add_context("key", "value")

        assert result is error  # Should return self for chaining
        assert error.context["key"] == "value"

    def test_to_dict(self):
        """Test converting exception to dictionary."""
        cause = ValueError("Original error")
        error = MCPServerAnimeError(
            "Test message",
            code="TEST_CODE",
            details="Test details",
            context={"key": "value"},
            cause=cause,
        )

        result = error.to_dict()

        assert result["error_type"] == "MCPServerAnimeError"
        assert result["code"] == "TEST_CODE"
        assert result["message"] == "Test message"
        assert result["details"] == "Test details"
        assert result["context"] == {"key": "value"}
        assert result["cause"] == "Original error"

    def test_repr(self):
        """Test string representation."""
        error = MCPServerAnimeError(
            "Test message",
            code="TEST_CODE",
            details="Test details",
            context={"key": "value"},
        )

        repr_str = repr(error)
        assert "MCPServerAnimeError" in repr_str
        assert "Test message" in repr_str
        assert "TEST_CODE" in repr_str


class TestConfigurationError:
    """Test configuration error class."""

    def test_initialization_with_config_context(self):
        """Test initialization with configuration-specific context."""
        error = ConfigurationError(
            "Invalid config value",
            config_key="api_key",
            expected_type="str",
            actual_value=123,
        )

        assert error.message == "Invalid config value"
        assert error.context["config_key"] == "api_key"
        assert error.context["expected_type"] == "str"
        assert error.context["actual_value"] == 123


class TestAPIError:
    """Test API error class."""

    def test_initialization_with_api_context(self):
        """Test initialization with API-specific context."""
        error = APIError(
            "API request failed",
            status_code=404,
            response_body="Not found",
            request_url="https://api.example.com/test",
            request_params={"param": "value"},
        )

        assert error.message == "API request failed"
        assert error.context["status_code"] == 404
        assert error.context["response_body"] == "Not found"
        assert error.context["request_url"] == "https://api.example.com/test"
        assert error.context["request_params"] == {"param": "value"}


class TestNetworkError:
    """Test network error class."""

    def test_initialization_with_network_context(self):
        """Test initialization with network-specific context."""
        error = NetworkError(
            "Connection timeout",
            timeout_duration=30.0,
            retry_count=3,
        )

        assert error.message == "Connection timeout"
        assert error.context["timeout_duration"] == 30.0
        assert error.context["retry_count"] == 3


class TestRateLimitError:
    """Test rate limit error class."""

    def test_initialization_with_rate_limit_context(self):
        """Test initialization with rate limit-specific context."""
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=60.0,
            rate_limit="100 requests per hour",
        )

        assert error.message == "Rate limit exceeded"
        assert error.context["retry_after"] == 60.0
        assert error.context["rate_limit"] == "100 requests per hour"


class TestAuthenticationError:
    """Test authentication error class."""

    def test_initialization_with_auth_context(self):
        """Test initialization with authentication-specific context."""
        error = AuthenticationError(
            "Invalid API key",
            auth_method="api_key",
        )

        assert error.message == "Invalid API key"
        assert error.context["auth_method"] == "api_key"


class TestDataValidationError:
    """Test data validation error class."""

    def test_initialization_with_validation_context(self):
        """Test initialization with validation-specific context."""
        validation_errors = ["Field is required", "Invalid format"]
        error = DataValidationError(
            "Validation failed",
            field_name="email",
            field_value="invalid-email",
            validation_errors=validation_errors,
        )

        assert error.message == "Validation failed"
        assert error.context["field_name"] == "email"
        assert error.context["field_value"] == "invalid-email"
        assert error.context["validation_errors"] == validation_errors


class TestXMLParsingError:
    """Test XML parsing error class."""

    def test_initialization_with_xml_context(self):
        """Test initialization with XML-specific context."""
        xml_content = "<invalid>xml</broken>"
        error = XMLParsingError(
            "XML parsing failed",
            xml_content=xml_content,
            xpath="//anime",
            line_number=5,
        )

        assert error.message == "XML parsing failed"
        assert error.context["xml_content"] == xml_content
        assert error.context["xpath"] == "//anime"
        assert error.context["line_number"] == 5

    def test_xml_content_truncation(self):
        """Test that long XML content is truncated."""
        long_xml = "x" * 1000
        error = XMLParsingError(
            "XML parsing failed",
            xml_content=long_xml,
        )

        # Should be truncated to 500 chars + "..."
        assert len(error.context["xml_content"]) == 503
        assert error.context["xml_content"].endswith("...")


class TestCacheError:
    """Test cache error class."""

    def test_initialization_with_cache_context(self):
        """Test initialization with cache-specific context."""
        error = CacheError(
            "Cache operation failed",
            cache_key="anime:search:evangelion",
            operation="get",
        )

        assert error.message == "Cache operation failed"
        assert error.context["cache_key"] == "anime:search:evangelion"
        assert error.context["operation"] == "get"


class TestServiceError:
    """Test service error class."""

    def test_initialization_with_service_context(self):
        """Test initialization with service-specific context."""
        error = ServiceError(
            "Service unavailable",
            service_name="AniDBService",
            operation="search_anime",
        )

        assert error.message == "Service unavailable"
        assert error.context["service_name"] == "AniDBService"
        assert error.context["operation"] == "search_anime"


class TestMCPToolError:
    """Test MCP tool error class."""

    def test_initialization_with_tool_context(self):
        """Test initialization with MCP tool-specific context."""
        parameters = {"query": "evangelion", "limit": 10}
        error = MCPToolError(
            "Tool execution failed",
            tool_name="anime_search",
            parameters=parameters,
        )

        assert error.message == "Tool execution failed"
        assert error.context["tool_name"] == "anime_search"
        assert error.context["parameters"] == parameters


class TestConvenienceFunctions:
    """Test convenience functions for creating exceptions."""

    def test_create_api_error(self):
        """Test create_api_error convenience function."""
        cause = ValueError("Original error")
        error = create_api_error(
            "API failed",
            status_code=500,
            response_body="Internal server error",
            cause=cause,
        )

        assert isinstance(error, APIError)
        assert error.message == "API failed"
        assert error.context["status_code"] == 500
        assert error.context["response_body"] == "Internal server error"
        assert error.cause == cause

    def test_create_validation_error(self):
        """Test create_validation_error convenience function."""
        cause = ValueError("Invalid value")
        error = create_validation_error(
            "Validation failed",
            field_name="email",
            field_value="invalid",
            cause=cause,
        )

        assert isinstance(error, DataValidationError)
        assert error.message == "Validation failed"
        assert error.context["field_name"] == "email"
        assert error.context["field_value"] == "invalid"
        assert error.cause == cause

    def test_create_network_error(self):
        """Test create_network_error convenience function."""
        cause = ConnectionError("Connection failed")
        error = create_network_error(
            "Network error",
            timeout_duration=30.0,
            retry_count=3,
            cause=cause,
        )

        assert isinstance(error, NetworkError)
        assert error.message == "Network error"
        assert error.context["timeout_duration"] == 30.0
        assert error.context["retry_count"] == 3
        assert error.cause == cause


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from MCPServerAnimeError."""
        exceptions = [
            ConfigurationError("test"),
            APIError("test"),
            NetworkError("test"),
            RateLimitError("test"),
            AuthenticationError("test"),
            DataValidationError("test"),
            XMLParsingError("test"),
            CacheError("test"),
            ServiceError("test"),
            MCPToolError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, MCPServerAnimeError)
            assert isinstance(exc, Exception)

    def test_api_error_inheritance(self):
        """Test that API-related errors inherit from APIError."""
        api_errors = [
            NetworkError("test"),
            RateLimitError("test"),
            AuthenticationError("test"),
        ]

        for exc in api_errors:
            assert isinstance(exc, APIError)
            assert isinstance(exc, MCPServerAnimeError)
