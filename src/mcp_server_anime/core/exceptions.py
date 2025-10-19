"""Custom exception classes for the MCP server anime application.

This module defines a hierarchy of custom exceptions that provide structured
error handling with context information and appropriate error codes.
"""

from __future__ import annotations

import traceback
from typing import Any


class MCPServerAnimeError(Exception):
    """Base exception class for all MCP server anime errors.

    This is the root exception class that all other custom exceptions inherit from.
    It provides common functionality for error handling, logging, and context management.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the base exception.

        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            details: Additional error details
            context: Dictionary of contextual information
            cause: The underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details
        self.context = context or {}
        self.cause = cause

        # Capture stack trace for debugging
        self.stack_trace = traceback.format_stack()

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [f"{self.code}: {self.message}"]
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"code='{self.code}', "
            f"details={self.details!r}, "
            f"context={self.context!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }

    def add_context(self, key: str, value: Any) -> MCPServerAnimeError:
        """Add contextual information to the exception.

        Args:
            key: Context key
            value: Context value

        Returns:
            Self for method chaining
        """
        self.context[key] = value
        return self


class ConfigurationError(MCPServerAnimeError):
    """Exception raised for configuration-related errors.

    This includes missing environment variables, invalid configuration values,
    and configuration validation failures.
    """

    def __init__(
        self,
        message: str,
        *,
        config_key: str | None = None,
        expected_type: str | None = None,
        actual_value: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            expected_type: Expected type for the configuration value
            actual_value: The actual value that was provided
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if config_key:
            context["config_key"] = config_key
        if expected_type:
            context["expected_type"] = expected_type
        if actual_value is not None:
            context["actual_value"] = actual_value

        super().__init__(message, context=context, **kwargs)


class APIError(MCPServerAnimeError):
    """Exception raised for API-related errors.

    This includes HTTP errors, rate limiting, authentication failures,
    and API response parsing errors.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        request_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_body: Response body content
            request_url: The URL that was requested
            request_params: Parameters sent with the request
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if status_code:
            context["status_code"] = status_code
        if response_body:
            context["response_body"] = response_body[:1000]  # Truncate long responses
        if request_url:
            context["request_url"] = request_url
        if request_params:
            context["request_params"] = request_params

        super().__init__(message, context=context, **kwargs)


class NetworkError(APIError):
    """Exception raised for network-related errors.

    This includes connection timeouts, DNS resolution failures,
    and other network connectivity issues.
    """

    def __init__(
        self,
        message: str,
        *,
        timeout_duration: float | None = None,
        retry_count: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize network error.

        Args:
            message: Error message
            timeout_duration: Timeout duration if applicable
            retry_count: Number of retries attempted
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if timeout_duration:
            context["timeout_duration"] = timeout_duration
        if retry_count is not None:
            context["retry_count"] = retry_count

        super().__init__(message, context=context, **kwargs)


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded.

    This includes both client-side rate limiting and server-side rate limit responses.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        rate_limit: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            rate_limit: Description of the rate limit
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if retry_after:
            context["retry_after"] = retry_after
        if rate_limit:
            context["rate_limit"] = rate_limit

        super().__init__(message, context=context, **kwargs)


class AuthenticationError(APIError):
    """Exception raised for authentication and authorization errors.

    This includes invalid API keys, banned clients, and permission denied errors.
    """

    def __init__(
        self,
        message: str,
        *,
        auth_method: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize authentication error.

        Args:
            message: Error message
            auth_method: Authentication method that failed
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if auth_method:
            context["auth_method"] = auth_method

        super().__init__(message, context=context, **kwargs)


class DataValidationError(MCPServerAnimeError):
    """Exception raised for data validation errors.

    This includes Pydantic validation failures, invalid input parameters,
    and data format errors.
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        field_value: Any | None = None,
        validation_errors: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize data validation error.

        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_errors: List of validation error messages
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = field_value
        if validation_errors:
            context["validation_errors"] = validation_errors

        super().__init__(message, context=context, **kwargs)


class XMLParsingError(MCPServerAnimeError):
    """Exception raised for XML parsing errors.

    This includes malformed XML, missing required elements,
    and XML structure validation failures.
    """

    def __init__(
        self,
        message: str,
        *,
        xml_content: str | None = None,
        xpath: str | None = None,
        line_number: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize XML parsing error.

        Args:
            message: Error message
            xml_content: The XML content that failed to parse (truncated)
            xpath: XPath expression that failed
            line_number: Line number where parsing failed
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if xml_content:
            # Truncate XML content for logging
            context["xml_content"] = (
                xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
            )
        if xpath:
            context["xpath"] = xpath
        if line_number:
            context["line_number"] = line_number

        super().__init__(message, context=context, **kwargs)


class CacheError(MCPServerAnimeError):
    """Exception raised for cache-related errors.

    This includes cache initialization failures, cache corruption,
    and cache operation errors.
    """

    def __init__(
        self,
        message: str,
        *,
        cache_key: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize cache error.

        Args:
            message: Error message
            cache_key: Cache key involved in the error
            operation: Cache operation that failed (get, set, delete, etc.)
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if cache_key:
            context["cache_key"] = cache_key
        if operation:
            context["operation"] = operation

        super().__init__(message, context=context, **kwargs)


class ServiceError(MCPServerAnimeError):
    """Exception raised for service layer errors.

    This includes service initialization failures, service state errors,
    and service operation errors.
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize service error.

        Args:
            message: Error message
            service_name: Name of the service that encountered the error
            operation: Service operation that failed
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if service_name:
            context["service_name"] = service_name
        if operation:
            context["operation"] = operation

        super().__init__(message, context=context, **kwargs)


class MCPToolError(MCPServerAnimeError):
    """Exception raised for MCP tool-related errors.

    This includes tool parameter validation, tool execution failures,
    and tool response formatting errors.
    """

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MCP tool error.

        Args:
            message: Error message
            tool_name: Name of the MCP tool that failed
            parameters: Parameters passed to the tool
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        if parameters:
            context["parameters"] = parameters

        super().__init__(message, context=context, **kwargs)


class ProviderError(MCPServerAnimeError):
    """Exception raised for anime data provider errors.

    This includes provider initialization failures, provider operation errors,
    and provider configuration issues.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_name: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize provider error.

        Args:
            message: Error message
            provider_name: Name of the provider that encountered the error
            operation: Provider operation that failed
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if provider_name:
            context["provider_name"] = provider_name
        if operation:
            context["operation"] = operation

        super().__init__(message, context=context, **kwargs)


class DatabaseError(MCPServerAnimeError):
    """Exception raised for database operation errors.

    This includes database connection failures, query errors,
    and database schema issues.
    """

    def __init__(
        self,
        message: str,
        *,
        database_path: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize database error.

        Args:
            message: Error message
            database_path: Path to the database file
            operation: Database operation that failed
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.pop("context", {})
        if database_path:
            context["database_path"] = database_path
        if operation:
            context["operation"] = operation

        super().__init__(message, context=context, **kwargs)


# Convenience functions for creating common exceptions


def create_api_error(
    message: str,
    status_code: int | None = None,
    response_body: str | None = None,
    cause: Exception | None = None,
) -> APIError:
    """Create an API error with common parameters.

    Args:
        message: Error message
        status_code: HTTP status code
        response_body: Response body content
        cause: Underlying exception

    Returns:
        Configured APIError instance
    """
    return APIError(
        message,
        status_code=status_code,
        response_body=response_body,
        cause=cause,
    )


def create_validation_error(
    message: str,
    field_name: str | None = None,
    field_value: Any | None = None,
    cause: Exception | None = None,
) -> DataValidationError:
    """Create a validation error with common parameters.

    Args:
        message: Error message
        field_name: Field that failed validation
        field_value: Value that failed validation
        cause: Underlying exception

    Returns:
        Configured DataValidationError instance
    """
    return DataValidationError(
        message,
        field_name=field_name,
        field_value=field_value,
        cause=cause,
    )


def create_network_error(
    message: str,
    timeout_duration: float | None = None,
    retry_count: int | None = None,
    cause: Exception | None = None,
) -> NetworkError:
    """Create a network error with common parameters.

    Args:
        message: Error message
        timeout_duration: Timeout duration
        retry_count: Number of retries attempted
        cause: Underlying exception

    Returns:
        Configured NetworkError instance
    """
    return NetworkError(
        message,
        timeout_duration=timeout_duration,
        retry_count=retry_count,
        cause=cause,
    )


# Enhanced exception classes for local database integration


class DatabaseNotInitializedError(DatabaseError):
    """Exception raised when database is not initialized or ready for use.

    This error indicates that the local anime database needs to be set up
    or initialized before search operations can be performed.
    """

    def __init__(
        self,
        message: str = "AniDB titles database is not initialized",
        *,
        provider: str = "anidb",
        setup_instructions: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize database not initialized error.

        Args:
            message: Error message
            provider: Provider name that needs initialization
            setup_instructions: Instructions for setting up the database
            cause: Underlying exception
        """
        super().__init__(
            message,
            code="DB_NOT_INITIALIZED",
            details=setup_instructions
            or "Please contact administrator to initialize the database",
            context={"provider": provider},
            cause=cause,
        )
        self.provider = provider
        self.setup_instructions = setup_instructions


class DownloadRateLimitedError(APIError):
    """Exception raised when download is blocked due to rate limiting.

    This error indicates that the download protection system has blocked
    a download attempt due to the 36-hour rate limiting policy.
    """

    def __init__(
        self,
        message: str,
        *,
        last_download_time: str | None = None,
        next_allowed_time: str | None = None,
        hours_remaining: float | None = None,
        protection_hours: int = 36,
        cause: Exception | None = None,
    ) -> None:
        """Initialize download rate limited error.

        Args:
            message: Error message
            last_download_time: ISO timestamp of last download
            next_allowed_time: ISO timestamp when next download is allowed
            hours_remaining: Hours remaining until next download allowed
            protection_hours: Protection period in hours
            cause: Underlying exception
        """
        super().__init__(
            message,
            code="DOWNLOAD_RATE_LIMITED",
            details=f"Downloads are limited to once every {protection_hours} hours to prevent bans",
            context={
                "last_download_time": last_download_time,
                "next_allowed_time": next_allowed_time,
                "hours_remaining": hours_remaining,
                "protection_hours": protection_hours,
            },
            cause=cause,
        )
        self.last_download_time = last_download_time
        self.next_allowed_time = next_allowed_time
        self.hours_remaining = hours_remaining
        self.protection_hours = protection_hours


class SearchValidationError(DataValidationError):
    """Exception raised when search parameters fail validation.

    This error provides detailed information about search parameter
    validation failures with helpful guidance for correction.
    """

    def __init__(
        self,
        message: str,
        *,
        query: str | None = None,
        limit: int | None = None,
        validation_requirements: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize search validation error.

        Args:
            message: Error message
            query: The query that failed validation
            limit: The limit that failed validation
            validation_requirements: Dictionary of validation requirements
            cause: Underlying exception
        """
        requirements = validation_requirements or {
            "query_min_length": 2,
            "query_max_length": 100,
            "limit_min": 1,
            "limit_max": 20,
        }

        super().__init__(
            message,
            code="SEARCH_VALIDATION_ERROR",
            details=f"Search requirements: {requirements}",
            context={
                "query": query,
                "limit": limit,
                "requirements": requirements,
            },
            cause=cause,
        )
        self.query = query
        self.limit = limit
        self.validation_requirements = requirements


class DatabaseCorruptionError(DatabaseError):
    """Exception raised when database corruption is detected.

    This error indicates that the local database has become corrupted
    and needs to be reinitialized or repaired.
    """

    def __init__(
        self,
        message: str = "Database corruption detected",
        *,
        corruption_type: str | None = None,
        recovery_suggestions: list[str] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize database corruption error.

        Args:
            message: Error message
            corruption_type: Type of corruption detected
            recovery_suggestions: List of recovery suggestions
            cause: Underlying exception
        """
        suggestions = recovery_suggestions or [
            "Reinitialize the database",
            "Download fresh titles data",
            "Contact administrator if problem persists",
        ]

        super().__init__(
            message,
            code="DATABASE_CORRUPTED",
            details=f"Recovery suggestions: {'; '.join(suggestions)}",
            context={
                "corruption_type": corruption_type,
                "recovery_suggestions": suggestions,
            },
            cause=cause,
        )
        self.corruption_type = corruption_type
        self.recovery_suggestions = suggestions


class TransactionLoggingError(MCPServerAnimeError):
    """Exception raised when transaction logging fails.

    This is a non-critical error that should not prevent search operations
    from completing successfully.
    """

    def __init__(
        self,
        message: str = "Failed to log search transaction",
        *,
        provider: str | None = None,
        query: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize transaction logging error.

        Args:
            message: Error message
            provider: Provider name
            query: Search query that failed to log
            cause: Underlying exception
        """
        super().__init__(
            message,
            code="TRANSACTION_LOGGING_ERROR",
            details="This error does not affect search functionality",
            context={
                "provider": provider,
                "query": query,
                "non_critical": True,
            },
            cause=cause,
        )
        self.provider = provider
        self.query = query


# Enhanced error creation functions


def create_database_not_initialized_error(
    provider: str = "anidb",
    setup_instructions: str | None = None,
    cause: Exception | None = None,
) -> DatabaseNotInitializedError:
    """Create a database not initialized error.

    Args:
        provider: Provider name
        setup_instructions: Setup instructions
        cause: Underlying exception

    Returns:
        Configured DatabaseNotInitializedError instance
    """
    return DatabaseNotInitializedError(
        f"{provider.upper()} titles database is not initialized",
        provider=provider,
        setup_instructions=setup_instructions,
        cause=cause,
    )


def create_download_rate_limited_error(
    last_download_time: str | None = None,
    next_allowed_time: str | None = None,
    hours_remaining: float | None = None,
    protection_hours: int = 36,
    cause: Exception | None = None,
) -> DownloadRateLimitedError:
    """Create a download rate limited error.

    Args:
        last_download_time: ISO timestamp of last download
        next_allowed_time: ISO timestamp when next download is allowed
        hours_remaining: Hours remaining until next download allowed
        protection_hours: Protection period in hours
        cause: Underlying exception

    Returns:
        Configured DownloadRateLimitedError instance
    """
    message = f"Download blocked by {protection_hours}-hour rate limit"
    if hours_remaining:
        message += f". {hours_remaining:.1f} hours remaining"

    return DownloadRateLimitedError(
        message,
        last_download_time=last_download_time,
        next_allowed_time=next_allowed_time,
        hours_remaining=hours_remaining,
        protection_hours=protection_hours,
        cause=cause,
    )


def create_search_validation_error(
    message: str,
    query: str | None = None,
    limit: int | None = None,
    cause: Exception | None = None,
) -> SearchValidationError:
    """Create a search validation error.

    Args:
        message: Error message
        query: Query that failed validation
        limit: Limit that failed validation
        cause: Underlying exception

    Returns:
        Configured SearchValidationError instance
    """
    return SearchValidationError(
        message,
        query=query,
        limit=limit,
        cause=cause,
    )


def create_database_corruption_error(
    corruption_type: str | None = None,
    cause: Exception | None = None,
) -> DatabaseCorruptionError:
    """Create a database corruption error.

    Args:
        corruption_type: Type of corruption detected
        cause: Underlying exception

    Returns:
        Configured DatabaseCorruptionError instance
    """
    return DatabaseCorruptionError(
        corruption_type=corruption_type,
        cause=cause,
    )
