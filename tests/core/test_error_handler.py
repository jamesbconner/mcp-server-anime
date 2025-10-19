"""Tests for error handling and graceful degradation."""

import asyncio
import time
from unittest.mock import Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from src.mcp_server_anime.core.error_handler import (
    ErrorHandler,
    create_fallback_response,
    error_handler,
    handle_mcp_tool_error,
    with_error_handling,
    with_retry,
)
from src.mcp_server_anime.core.exceptions import (
    APIError,
    AuthenticationError,
    CacheError,
    DataValidationError,
    MCPServerAnimeError,
    MCPToolError,
    NetworkError,
    RateLimitError,
    ServiceError,
    XMLParsingError,
)


class TestErrorHandler:
    """Test the ErrorHandler class."""

    def setup_method(self):
        """Set up test error handler."""
        self.handler = ErrorHandler()

    def test_handle_http_timeout_error(self):
        """Test handling HTTP timeout errors."""
        timeout_error = httpx.TimeoutException("Request timeout")
        timeout_error.timeout = 30.0

        result = self.handler.handle_http_error(
            timeout_error,
            "test_operation",
            "https://api.example.com/test",
            {"param": "value"},
        )

        assert isinstance(result, NetworkError)
        assert "Request timeout during test_operation" in result.message
        assert result.context["timeout_duration"] == 30.0
        assert result.context["url"] == "https://api.example.com/test"
        assert result.context["params"] == {"param": "value"}
        assert result.cause == timeout_error

    def test_handle_http_network_error(self):
        """Test handling HTTP network errors."""
        network_error = httpx.NetworkError("Connection failed")

        result = self.handler.handle_http_error(
            network_error,
            "test_operation",
            "https://api.example.com/test",
        )

        assert isinstance(result, NetworkError)
        assert "Network error during test_operation" in result.message
        assert result.cause == network_error

    def test_handle_http_status_error_401(self):
        """Test handling HTTP 401 status errors."""
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized"

        status_error = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=response
        )

        result = self.handler.handle_http_error(status_error, "test_operation")

        assert isinstance(result, AuthenticationError)
        assert "Authentication failed during test_operation" in result.message
        assert result.context["status_code"] == 401
        assert result.context["response_body"] == "Unauthorized"

    def test_handle_http_status_error_403(self):
        """Test handling HTTP 403 status errors."""
        response = Mock()
        response.status_code = 403
        response.text = "Forbidden"

        status_error = httpx.HTTPStatusError(
            "403 Forbidden", request=Mock(), response=response
        )

        result = self.handler.handle_http_error(status_error, "test_operation")

        assert isinstance(result, AuthenticationError)
        assert "Access forbidden during test_operation" in result.message
        assert result.context["status_code"] == 403

    def test_handle_http_status_error_429(self):
        """Test handling HTTP 429 rate limit errors."""
        response = Mock()
        response.status_code = 429
        response.text = "Rate limit exceeded"
        response.headers = {"Retry-After": "60"}

        status_error = httpx.HTTPStatusError(
            "429 Too Many Requests", request=Mock(), response=response
        )

        result = self.handler.handle_http_error(status_error, "test_operation")

        assert isinstance(result, RateLimitError)
        assert "Rate limit exceeded during test_operation" in result.message
        assert result.context["retry_after"] == 60.0

    def test_handle_http_status_error_500(self):
        """Test handling HTTP 500 server errors."""
        response = Mock()
        response.status_code = 500
        response.text = "Internal server error"

        status_error = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=response
        )

        result = self.handler.handle_http_error(status_error, "test_operation")

        assert isinstance(result, APIError)
        assert "HTTP 500 error during test_operation" in result.message
        assert result.context["status_code"] == 500

    def test_handle_validation_error(self):
        """Test handling Pydantic validation errors."""
        # Create a mock validation error
        validation_error = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("field1",),
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "string_type",
                    "loc": ("field2",),
                    "msg": "Input should be a valid string",
                    "input": 123,
                },
            ],
        )

        result = self.handler.handle_validation_error(
            validation_error,
            "test_operation",
            {"invalid": "data"},
        )

        assert isinstance(result, DataValidationError)
        assert "Data validation failed during test_operation" in result.message
        assert "field1: Field required" in result.context["validation_errors"]
        assert (
            "field2: Input should be a valid string"
            in result.context["validation_errors"]
        )
        assert result.context["data"] == {"invalid": "data"}

    def test_handle_xml_parsing_error(self):
        """Test handling XML parsing errors."""
        xml_error = Exception("Invalid XML syntax")
        xml_content = "<invalid>xml</broken>"

        result = self.handler.handle_xml_parsing_error(
            xml_error,
            "test_operation",
            xml_content,
        )

        assert isinstance(result, XMLParsingError)
        assert "XML parsing failed during test_operation" in result.message
        assert result.context["xml_content"] == xml_content
        assert result.cause == xml_error

    def test_handle_cache_error(self):
        """Test handling cache errors."""
        cache_error = Exception("Cache connection failed")

        result = self.handler.handle_cache_error(
            cache_error,
            "cache_get",
            "cache:key:123",
        )

        assert isinstance(result, CacheError)
        assert "Cache error during cache_get" in result.message
        assert result.context["cache_key"] == "cache:key:123"
        assert result.context["operation"] == "cache_get"
        assert result.cause == cache_error

    def test_circuit_breaker_tracking(self):
        """Test circuit breaker error tracking."""
        service = "test_service"

        # Record errors below threshold
        for _ in range(4):
            self.handler.record_error(service)

        assert not self.handler.should_circuit_break(service)
        assert not self.handler.is_circuit_broken(service)

        # Record one more error to exceed threshold
        self.handler.record_error(service)

        assert self.handler.should_circuit_break(service)

        # Activate circuit breaker
        self.handler.activate_circuit_breaker(service)

        assert self.handler.is_circuit_broken(service)

    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset."""
        service = "test_service"

        # Activate circuit breaker
        self.handler.activate_circuit_breaker(service)
        assert self.handler.is_circuit_broken(service)

        # Reset circuit breaker
        self.handler.reset_circuit_breaker(service)
        assert not self.handler.is_circuit_broken(service)
        assert self.handler.error_counts.get(service, 0) == 0

    def test_circuit_breaker_time_window(self):
        """Test circuit breaker time window reset."""
        service = "test_service"

        # Record errors
        for _ in range(5):
            self.handler.record_error(service)

        assert self.handler.should_circuit_break(service)

        # Simulate time passing by directly modifying the last error time
        # This is more reliable than mocking time.time()
        original_time = self.handler.last_error_times[service]
        self.handler.last_error_times[service] = (
            original_time - 400
        )  # Make it 400 seconds ago

        # Should not circuit break due to time window reset
        assert not self.handler.should_circuit_break(service)


class TestWithErrorHandlingDecorator:
    """Test the with_error_handling decorator."""

    def test_sync_function_success(self):
        """Test decorator with successful sync function."""

        @with_error_handling("test_operation")
        def test_function(value: int) -> int:
            return value * 2

        result = test_function(5)
        assert result == 10

    def test_sync_function_error_reraise(self):
        """Test decorator with sync function error (reraise=True)."""

        @with_error_handling("test_operation", reraise=True)
        def test_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(MCPServerAnimeError) as exc_info:
            test_function()

        assert "Unexpected error during test_operation" in str(exc_info.value)
        assert isinstance(exc_info.value.cause, ValueError)

    def test_sync_function_error_fallback(self):
        """Test decorator with sync function error (reraise=False)."""

        @with_error_handling("test_operation", fallback_value="fallback", reraise=False)
        def test_function() -> str:
            raise ValueError("Test error")

        result = test_function()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with successful async function."""

        @with_error_handling("test_operation")
        async def test_function(value: int) -> int:
            return value * 2

        result = await test_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_function_error_reraise(self):
        """Test decorator with async function error (reraise=True)."""

        @with_error_handling("test_operation", reraise=True)
        async def test_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(MCPServerAnimeError) as exc_info:
            await test_function()

        assert "Unexpected error during test_operation" in str(exc_info.value)
        assert isinstance(exc_info.value.cause, ValueError)

    @pytest.mark.asyncio
    async def test_async_function_error_fallback(self):
        """Test decorator with async function error (reraise=False)."""

        @with_error_handling("test_operation", fallback_value="fallback", reraise=False)
        async def test_function() -> str:
            raise ValueError("Test error")

        result = await test_function()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_circuit_breaker_active(self):
        """Test decorator with active circuit breaker."""
        # Activate circuit breaker
        error_handler.activate_circuit_breaker("test_service")

        try:

            @with_error_handling(
                "test_operation",
                service="test_service",
                fallback_value="fallback",
                reraise=False,
            )
            async def test_function() -> str:
                return "success"

            result = await test_function()
            assert result == "fallback"
        finally:
            # Reset circuit breaker
            error_handler.reset_circuit_breaker("test_service")

    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activation after errors."""
        service = "test_service_activation"

        # Reset any existing state
        error_handler.reset_circuit_breaker(service)

        @with_error_handling("test_operation", service=service, reraise=False)
        async def test_function() -> None:
            raise ValueError("Test error")

        # Call function multiple times to trigger circuit breaker
        for i in range(6):  # Exceed the default threshold of 5
            try:
                await test_function()
            except ServiceError:
                # Circuit breaker activated, this is expected
                break

        # Circuit breaker should now be active
        assert error_handler.is_circuit_broken(service)

        # Reset for cleanup
        error_handler.reset_circuit_breaker(service)


class TestWithRetry:
    """Test the with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_function(self):
        """Test retry with successful function."""
        call_count = 0

        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(test_function)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_function_succeeds_after_retries(self):
        """Test retry with function that succeeds after failures."""
        call_count = 0

        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Network error")
            return "success"

        result = await with_retry(test_function, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_function_fails_all_retries(self):
        """Test retry with function that always fails."""
        call_count = 0

        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            raise NetworkError("Network error")

        with pytest.raises(NetworkError):
            await with_retry(test_function, max_retries=2, base_delay=0.01)

        assert call_count == 3  # Initial call + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test retry with non-retryable exception."""
        call_count = 0

        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            await with_retry(test_function, max_retries=3, base_delay=0.01)

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_rate_limit_retry_after(self):
        """Test retry with rate limit error containing retry_after."""
        call_count = 0

        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limited", retry_after=0.01)
            return "success"

        start_time = time.time()
        result = await with_retry(test_function, base_delay=0.001)
        end_time = time.time()

        assert result == "success"
        assert call_count == 2
        # Should have waited at least the retry_after time
        assert end_time - start_time >= 0.01

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        delays = []

        async def test_function() -> str:
            raise NetworkError("Network error")

        # Mock asyncio.sleep to capture delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay: float) -> None:
            delays.append(delay)
            await original_sleep(0.001)  # Very short actual delay for testing

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(NetworkError):
                await with_retry(
                    test_function,
                    max_retries=3,
                    base_delay=1.0,
                    exponential_base=2.0,
                )

        # Should have 3 delays (for 3 retries)
        assert len(delays) == 3
        assert delays[0] == 1.0  # 1.0 * 2^0
        assert delays[1] == 2.0  # 1.0 * 2^1
        assert delays[2] == 4.0  # 1.0 * 2^2


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_fallback_response(self):
        """Test creating fallback response."""
        error = ValueError("Test error")

        response = create_fallback_response(
            "test_operation",
            error,
            {"default": "data"},
        )

        assert response["success"] is False
        assert response["error"]["operation"] == "test_operation"
        assert response["error"]["message"] == "Test error"
        assert response["error"]["type"] == "ValueError"
        assert response["error"]["fallback"] is True
        assert response["data"] == {"default": "data"}
        assert "timestamp" in response

    def test_handle_mcp_tool_error_with_mcp_error(self):
        """Test handling MCP tool error with MCPServerAnimeError."""
        original_error = APIError(
            "API failed",
            code="API_ERROR",
            details="API details",
            context={"key": "value"},
        )

        result = handle_mcp_tool_error(
            original_error,
            "anime_search",
            {"query": "test", "limit": 10},
        )

        assert isinstance(result, MCPToolError)
        assert "Tool anime_search failed: API failed" in result.message
        assert result.context["tool_name"] == "anime_search"
        assert result.context["parameters"] == {"query": "test", "limit": 10}
        assert result.code == "API_ERROR"
        assert result.details == "API details"
        assert result.context["key"] == "value"  # Inherited from original error
        assert result.cause == original_error

    def test_handle_mcp_tool_error_with_generic_error(self):
        """Test handling MCP tool error with generic exception."""
        original_error = ValueError("Generic error")

        result = handle_mcp_tool_error(
            original_error,
            "anime_details",
            {"aid": 123},
        )

        assert isinstance(result, MCPToolError)
        assert "Tool anime_details failed: Generic error" in result.message
        assert result.context["tool_name"] == "anime_details"
        assert result.context["parameters"] == {"aid": 123}
        assert result.cause == original_error


class TestGlobalErrorHandler:
    """Test the global error handler instance."""

    def test_global_error_handler_exists(self):
        """Test that global error handler instance exists."""
        assert error_handler is not None
        assert isinstance(error_handler, ErrorHandler)

    def test_global_error_handler_state_isolation(self):
        """Test that global error handler state is properly isolated."""
        # Reset state
        error_handler.error_counts.clear()
        error_handler.last_error_times.clear()
        error_handler.circuit_breaker_states.clear()

        # Record error for one service
        error_handler.record_error("service1")

        # Should not affect other services
        assert error_handler.error_counts.get("service2", 0) == 0
        assert not error_handler.is_circuit_broken("service2")

        # Should affect the correct service
        assert error_handler.error_counts["service1"] == 1


class TestAdditionalBranchCoverage:
    """Additional tests to improve branch coverage."""

    def test_handle_http_error_non_status_error(self):
        """Test handling HTTP error that is not HTTPStatusError."""
        import httpx

        from src.mcp_server_anime.core.error_handler import ErrorHandler

        handler = ErrorHandler()

        # Test with a general HTTP error (not HTTPStatusError)
        http_error = httpx.ConnectError("Connection failed")

        result = handler.handle_http_error(http_error, "test_operation")

        assert "Network error during test_operation" in str(result)
        assert result.cause == http_error

    def test_circuit_breaker_time_window_reset(self):
        """Test circuit breaker error count reset after time window."""
        import time

        from src.mcp_server_anime.core.error_handler import ErrorHandler

        handler = ErrorHandler()
        service = "test_service"

        # Record some errors
        handler.record_error(service)
        handler.record_error(service)

        # Set last error time to past (simulate time window passing)
        handler.last_error_times[service] = time.time() - 400  # 400 seconds ago

        # Should reset error count and not trigger circuit breaker
        should_break = handler.should_circuit_break(
            service, error_threshold=2, time_window=300
        )
        assert not should_break
        assert handler.error_counts[service] == 0

    def test_with_error_handling_fallback_value_on_circuit_breaker(self):
        """Test error handling decorator returns fallback value when circuit breaker is active."""
        from src.mcp_server_anime.core.error_handler import (
            error_handler,
            with_error_handling,
        )

        # Activate circuit breaker for test service
        service = "test_service"
        error_handler.activate_circuit_breaker(service)

        @with_error_handling(
            operation="test_op",
            service=service,
            fallback_value="fallback_result",
            reraise=False,
        )
        def test_function():
            return "normal_result"

        result = test_function()
        assert result == "fallback_result"

        # Clean up
        error_handler.reset_circuit_breaker(service)

    def test_with_error_handling_service_error_on_circuit_breaker_no_fallback(self):
        """Test error handling decorator raises ServiceError when circuit breaker is active and no fallback."""
        from src.mcp_server_anime.core.error_handler import (
            error_handler,
            with_error_handling,
        )
        from src.mcp_server_anime.core.exceptions import ServiceError

        # Activate circuit breaker for test service
        service = "test_service"
        error_handler.activate_circuit_breaker(service)

        @with_error_handling(operation="test_op", service=service, reraise=True)
        def test_function():
            return "normal_result"

        with pytest.raises(
            ServiceError, match="Service test_service is currently unavailable"
        ):
            test_function()

        # Clean up
        error_handler.reset_circuit_breaker(service)

    def test_handle_exception_with_mcp_server_anime_error(self):
        """Test _handle_exception with MCPServerAnimeError."""
        from src.mcp_server_anime.core.error_handler import _handle_exception
        from src.mcp_server_anime.core.exceptions import DataValidationError

        # Create an MCPServerAnimeError
        original_error = DataValidationError("Test validation error")

        # Should return the same error
        result = _handle_exception(original_error, "test_operation")
        assert result is original_error

    def test_handle_exception_with_validation_like_error(self):
        """Test _handle_exception with ValueError containing 'validation'."""
        from src.mcp_server_anime.core.error_handler import _handle_exception
        from src.mcp_server_anime.core.exceptions import DataValidationError

        # Create a ValueError with 'validation' in the message
        original_error = ValueError("Validation failed for field")

        result = _handle_exception(original_error, "test_operation")
        assert isinstance(result, DataValidationError)
        assert "Validation error during test_operation" in str(result)
        assert result.cause == original_error

    def test_handle_exception_with_type_error_validation(self):
        """Test _handle_exception with TypeError containing 'validation'."""
        from src.mcp_server_anime.core.error_handler import _handle_exception
        from src.mcp_server_anime.core.exceptions import DataValidationError

        # Create a TypeError with 'validation' in the message
        original_error = TypeError("Type validation error occurred")

        result = _handle_exception(original_error, "test_operation")
        assert isinstance(result, DataValidationError)
        assert "Validation error during test_operation" in str(result)
        assert result.cause == original_error
