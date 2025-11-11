"""Error handling and graceful degradation for the MCP server anime application.

This module provides comprehensive error handling strategies, graceful degradation
mechanisms, and error recovery patterns for robust operation.
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from pydantic import ValidationError

from .exceptions import (
    AuthenticationError,
    CacheError,
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
from .logging_config import get_logger, log_error_with_context, set_request_context

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handler with graceful degradation strategies.

    This class provides methods for handling different types of errors
    and implementing graceful degradation when services are unavailable.
    """

    def __init__(self) -> None:
        """Initialize the error handler."""
        self.error_counts: dict[str, int] = {}
        self.last_error_times: dict[str, float] = {}
        self.circuit_breaker_states: dict[str, bool] = {}

    def handle_http_error(
        self,
        error: httpx.HTTPError,
        operation: str,
        url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> MCPServerAnimeError:
        """Handle HTTP errors and convert to appropriate exception types.

        Args:
            error: The HTTP error that occurred
            operation: Operation that failed
            url: Request URL
            params: Request parameters

        Returns:
            Appropriate MCPServerAnimeError subclass
        """
        log_error_with_context(
            error,
            operation=operation,
            url=url,
            params=params,
        )

        if isinstance(error, httpx.TimeoutException):
            return (
                create_network_error(
                    f"Request timeout during {operation}",
                    timeout_duration=getattr(error, "timeout", None),
                    cause=error,
                )
                .add_context("url", url)
                .add_context("params", params)
            )

        elif isinstance(error, httpx.NetworkError):
            return (
                create_network_error(
                    f"Network error during {operation}: {error}",
                    cause=error,
                )
                .add_context("url", url)
                .add_context("params", params)
            )

        elif isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            response_body = (
                error.response.text if hasattr(error.response, "text") else None
            )

            if status_code == 401:
                return AuthenticationError(
                    f"Authentication failed during {operation}",
                    status_code=status_code,
                    response_body=response_body,
                    cause=error,
                )
            elif status_code == 403:
                return AuthenticationError(
                    f"Access forbidden during {operation}",
                    status_code=status_code,
                    response_body=response_body,
                    cause=error,
                )
            elif status_code == 429:
                retry_after = error.response.headers.get("Retry-After")
                return RateLimitError(
                    f"Rate limit exceeded during {operation}",
                    status_code=status_code,
                    response_body=response_body,
                    retry_after=float(retry_after) if retry_after else None,
                    cause=error,
                )
            else:
                return create_api_error(
                    f"HTTP {status_code} error during {operation}",
                    status_code=status_code,
                    response_body=response_body,
                    cause=error,
                )

        else:
            return (
                create_api_error(
                    f"HTTP error during {operation}: {error}",
                    cause=error,
                )
                .add_context("url", url)
                .add_context("params", params)
            )

    def handle_validation_error(
        self,
        error: ValidationError,
        operation: str,
        data: Any | None = None,
    ) -> DataValidationError:
        """Handle Pydantic validation errors.

        Args:
            error: The validation error
            operation: Operation that failed
            data: Data that failed validation

        Returns:
            DataValidationError with context
        """
        log_error_with_context(error, operation=operation, data=data)

        # Extract validation error details
        validation_errors = []
        for err in error.errors():
            field_path = ".".join(str(loc) for loc in err["loc"])
            validation_errors.append(f"{field_path}: {err['msg']}")

        return DataValidationError(
            f"Data validation failed during {operation}",
            validation_errors=validation_errors,
            cause=error,
        ).add_context("data", data)

    def handle_xml_parsing_error(
        self,
        error: Exception,
        operation: str,
        xml_content: str | None = None,
    ) -> XMLParsingError:
        """Handle XML parsing errors.

        Args:
            error: The parsing error
            operation: Operation that failed
            xml_content: XML content that failed to parse

        Returns:
            XMLParsingError with context
        """
        log_error_with_context(error, operation=operation)

        return XMLParsingError(
            f"XML parsing failed during {operation}: {error}",
            xml_content=xml_content,
            cause=error,
        )

    def handle_cache_error(
        self,
        error: Exception,
        operation: str,
        cache_key: str | None = None,
    ) -> CacheError:
        """Handle cache-related errors.

        Args:
            error: The cache error
            operation: Cache operation that failed
            cache_key: Cache key involved

        Returns:
            CacheError with context
        """
        log_error_with_context(error, operation=operation, cache_key=cache_key)

        return CacheError(
            f"Cache error during {operation}: {error}",
            cache_key=cache_key,
            operation=operation,
            cause=error,
        )

    def should_circuit_break(
        self, service: str, error_threshold: int = 5, time_window: int = 300
    ) -> bool:
        """Check if circuit breaker should be activated for a service.

        Args:
            service: Service name
            error_threshold: Number of errors to trigger circuit breaker
            time_window: Time window in seconds to count errors

        Returns:
            True if circuit breaker should be activated
        """
        current_time = time.time()

        # Reset error count if time window has passed
        if service in self.last_error_times:
            if current_time - self.last_error_times[service] > time_window:
                self.error_counts[service] = 0

        # Check if error threshold is exceeded
        error_count = self.error_counts.get(service, 0)
        return error_count >= error_threshold

    def record_error(self, service: str) -> None:
        """Record an error for circuit breaker tracking.

        Args:
            service: Service name
        """
        current_time = time.time()
        self.error_counts[service] = self.error_counts.get(service, 0) + 1
        self.last_error_times[service] = current_time

        logger.warning(
            f"Error recorded for service {service}",
            service=service,
            error_count=self.error_counts[service],
        )

        # Check if circuit breaker should be activated
        if self.should_circuit_break(service):
            self.activate_circuit_breaker(service)

    def activate_circuit_breaker(self, service: str) -> None:
        """Activate circuit breaker for a service.

        Args:
            service: Service name
        """
        self.circuit_breaker_states[service] = True
        logger.error(
            f"Circuit breaker activated for service {service}",
            service=service,
            error_count=self.error_counts.get(service, 0),
        )

    def is_circuit_broken(self, service: str) -> bool:
        """Check if circuit breaker is active for a service.

        Args:
            service: Service name

        Returns:
            True if circuit breaker is active
        """
        return self.circuit_breaker_states.get(service, False)

    def reset_circuit_breaker(self, service: str) -> None:
        """Reset circuit breaker for a service.

        Args:
            service: Service name
        """
        self.circuit_breaker_states[service] = False
        self.error_counts[service] = 0
        logger.info(f"Circuit breaker reset for service {service}", service=service)

    def reset(self) -> None:
        """Reset all error handler state.

        This clears all error counts and circuit breaker states.
        Useful for testing to ensure clean state between tests.
        """
        self.error_counts.clear()
        self.circuit_breaker_states.clear()
        logger.debug("Error handler state reset")


# Global error handler instance
error_handler = ErrorHandler()


def with_error_handling(
    operation: str,
    service: str | None = None,
    fallback_value: Any | None = None,
    reraise: bool = True,
) -> Callable[[F], F]:
    """Decorator for adding comprehensive error handling to functions.

    Args:
        operation: Operation name for logging
        service: Service name for circuit breaker
        fallback_value: Value to return on error (if reraise=False)
        reraise: Whether to reraise exceptions after handling

    Returns:
        Decorated function with error handling
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                set_request_context(operation=operation)

                # Check circuit breaker
                if service and error_handler.is_circuit_broken(service):
                    logger.warning(
                        f"Circuit breaker active for {service}, skipping operation"
                    )
                    if fallback_value is not None:
                        return fallback_value
                    raise ServiceError(
                        f"Service {service} is currently unavailable",
                        service_name=service,
                        operation=operation,
                    )

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    handled_error = _handle_exception(e, operation, service)

                    if service:
                        error_handler.record_error(service)
                        if error_handler.should_circuit_break(service):
                            error_handler.activate_circuit_breaker(service)

                    if reraise:
                        raise handled_error
                    return fallback_value

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                set_request_context(operation=operation)

                # Check circuit breaker
                if service and error_handler.is_circuit_broken(service):
                    logger.warning(
                        f"Circuit breaker active for {service}, skipping operation"
                    )
                    if fallback_value is not None:
                        return fallback_value
                    raise ServiceError(
                        f"Service {service} is currently unavailable",
                        service_name=service,
                        operation=operation,
                    )

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    handled_error = _handle_exception(e, operation, service)

                    if service:
                        error_handler.record_error(service)
                        if error_handler.should_circuit_break(service):
                            error_handler.activate_circuit_breaker(service)

                    if reraise:
                        raise handled_error
                    return fallback_value

            return sync_wrapper  # type: ignore

    return decorator


def _handle_exception(
    error: Exception, operation: str, service: str | None = None
) -> MCPServerAnimeError:
    """Handle and convert exceptions to appropriate types.

    Args:
        error: Exception to handle
        operation: Operation that failed
        service: Service name

    Returns:
        Appropriate MCPServerAnimeError subclass
    """
    if isinstance(error, MCPServerAnimeError):
        # Already a handled error, just log and return
        log_error_with_context(error, operation=operation, service=service)
        return error

    elif isinstance(error, httpx.HTTPError):
        return error_handler.handle_http_error(error, operation)

    elif isinstance(error, ValidationError):
        return error_handler.handle_validation_error(error, operation)

    elif (
        isinstance(error, ValueError | TypeError) and "validation" in str(error).lower()
    ):
        return create_validation_error(
            f"Validation error during {operation}: {error}",
            cause=error,
        )

    else:
        # Generic error handling
        log_error_with_context(error, operation=operation, service=service)
        return MCPServerAnimeError(
            f"Unexpected error during {operation}: {error}",
            code="UNEXPECTED_ERROR",
            cause=error,
        ).add_context("service", service)


async def with_retry[T](
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (NetworkError, RateLimitError),
) -> T:
    """Execute function with retry logic.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Exponential backoff base
        retryable_exceptions: Exception types that should trigger retries

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            # Check if exception is retryable
            if not isinstance(e, retryable_exceptions):
                raise

            # Don't retry on last attempt
            if attempt == max_retries:
                raise

            # Calculate delay
            delay = min(base_delay * (exponential_base**attempt), max_delay)

            # Special handling for rate limit errors
            if isinstance(e, RateLimitError) and e.context.get("retry_after"):
                delay = max(delay, e.context["retry_after"])

            logger.info(
                f"Retrying after error (attempt {attempt + 1}/{max_retries + 1})",
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=delay,
                error=str(e),
            )

            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic failed unexpectedly")


def create_fallback_response(
    operation: str,
    error: Exception,
    default_data: Any | None = None,
) -> dict[str, Any]:
    """Create a fallback response for failed operations.

    Args:
        operation: Operation that failed
        error: Error that occurred
        default_data: Default data to include

    Returns:
        Fallback response dictionary
    """
    return {
        "success": False,
        "error": {
            "operation": operation,
            "message": str(error),
            "type": type(error).__name__,
            "fallback": True,
        },
        "data": default_data,
        "timestamp": time.time(),
    }


def handle_mcp_tool_error(
    error: Exception, tool_name: str, parameters: dict[str, Any]
) -> MCPToolError:
    """Handle errors in MCP tools and convert to appropriate exceptions.

    Args:
        error: Exception that occurred
        tool_name: Name of the MCP tool
        parameters: Parameters passed to the tool

    Returns:
        MCPToolError with context
    """
    log_error_with_context(
        error,
        operation=f"mcp_tool_{tool_name}",
        tool_name=tool_name,
        parameters=parameters,
    )

    if isinstance(error, MCPServerAnimeError):
        # Convert to MCP tool error while preserving context
        return MCPToolError(
            f"Tool {tool_name} failed: {error.message}",
            tool_name=tool_name,
            parameters=parameters,
            code=error.code,
            details=error.details,
            context=error.context,
            cause=error,
        )
    else:
        return MCPToolError(
            f"Tool {tool_name} failed: {error}",
            tool_name=tool_name,
            parameters=parameters,
            cause=error,
        )
