"""Error response formatting for consistent error handling across the application.

This module provides standardized error response formatting with contextual information,
user-friendly messages, and actionable guidance for different error scenarios.
"""

from datetime import datetime
from typing import Any

from .exceptions import (
    DatabaseCorruptionError,
    DatabaseNotInitializedError,
    DownloadRateLimitedError,
    MCPServerAnimeError,
    SearchValidationError,
    TransactionLoggingError,
)
from .logging_config import get_logger

logger = get_logger(__name__)


class ErrorResponseFormatter:
    """Formats error responses with consistent structure and helpful information."""

    @staticmethod
    def format_error_response(
        error: Exception,
        operation: str | None = None,
        request_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Format an error into a standardized response structure.

        Args:
            error: The exception to format
            operation: The operation that failed
            request_context: Additional context about the request

        Returns:
            Dictionary with standardized error response
        """
        # Base error response structure
        response = {
            "error": True,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": request_context or {},
        }

        # Add specific formatting based on error type
        if isinstance(error, DatabaseNotInitializedError):
            response.update(
                ErrorResponseFormatter._format_database_not_initialized(error)
            )
        elif isinstance(error, DownloadRateLimitedError):
            response.update(ErrorResponseFormatter._format_download_rate_limited(error))
        elif isinstance(error, SearchValidationError):
            response.update(ErrorResponseFormatter._format_search_validation(error))
        elif isinstance(error, DatabaseCorruptionError):
            response.update(ErrorResponseFormatter._format_database_corruption(error))
        elif isinstance(error, TransactionLoggingError):
            response.update(ErrorResponseFormatter._format_transaction_logging(error))
        elif isinstance(error, MCPServerAnimeError):
            response.update(ErrorResponseFormatter._format_mcp_server_error(error))
        else:
            response.update(ErrorResponseFormatter._format_generic_error(error))

        return response

    @staticmethod
    def _format_database_not_initialized(
        error: DatabaseNotInitializedError,
    ) -> dict[str, Any]:
        """Format database not initialized error."""
        return {
            "error_code": "DATABASE_NOT_INITIALIZED",
            "severity": "error",
            "user_message": "The anime search database needs to be set up before searches can be performed.",
            "technical_message": error.message,
            "provider": error.provider,
            "suggested_actions": [
                "Contact your system administrator to initialize the database",
                "Ensure the titles database has been downloaded and loaded",
                "Check database configuration and permissions",
            ],
            "setup_instructions": error.setup_instructions,
            "retry_possible": False,
            "documentation_link": "https://github.com/example/mcp-server-anime#database-setup",
        }

    @staticmethod
    def _format_download_rate_limited(
        error: DownloadRateLimitedError,
    ) -> dict[str, Any]:
        """Format download rate limited error."""
        return {
            "error_code": "DOWNLOAD_RATE_LIMITED",
            "severity": "warning",
            "user_message": f"Download blocked by {error.protection_hours}-hour rate limit to prevent service bans.",
            "technical_message": error.message,
            "rate_limit_info": {
                "protection_hours": error.protection_hours,
                "last_download": error.last_download_time,
                "next_allowed": error.next_allowed_time,
                "hours_remaining": error.hours_remaining,
            },
            "suggested_actions": [
                f"Wait {error.hours_remaining:.1f} hours before attempting download"
                if error.hours_remaining
                else "Wait for the protection period to expire",
                "Use existing database if available",
                "Contact administrator for emergency override if critical",
            ],
            "retry_possible": True,
            "retry_after": error.next_allowed_time,
        }

    @staticmethod
    def _format_search_validation(error: SearchValidationError) -> dict[str, Any]:
        """Format search validation error."""
        return {
            "error_code": "SEARCH_VALIDATION_ERROR",
            "severity": "warning",
            "user_message": "Search parameters are invalid. Please check your query and try again.",
            "technical_message": error.message,
            "validation_details": {
                "provided_query": error.query,
                "provided_limit": error.limit,
                "requirements": error.validation_requirements,
            },
            "suggested_actions": [
                "Ensure search query is at least 2 characters long",
                "Use a limit between 1 and 20 results",
                "Remove any special characters that might cause issues",
            ],
            "examples": {
                "valid_query": "evangelion",
                "valid_limit": 10,
            },
            "retry_possible": True,
        }

    @staticmethod
    def _format_database_corruption(error: DatabaseCorruptionError) -> dict[str, Any]:
        """Format database corruption error."""
        return {
            "error_code": "DATABASE_CORRUPTED",
            "severity": "error",
            "user_message": "The anime database appears to be corrupted and needs to be repaired.",
            "technical_message": error.message,
            "corruption_info": {
                "type": error.corruption_type,
                "recovery_suggestions": error.recovery_suggestions,
            },
            "suggested_actions": error.recovery_suggestions
            or [
                "Contact system administrator for database repair",
                "Reinitialize the database with fresh data",
                "Check disk space and file permissions",
            ],
            "retry_possible": False,
            "requires_admin": True,
        }

    @staticmethod
    def _format_transaction_logging(error: TransactionLoggingError) -> dict[str, Any]:
        """Format transaction logging error."""
        return {
            "error_code": "TRANSACTION_LOGGING_ERROR",
            "severity": "info",
            "user_message": "Search completed successfully, but usage tracking failed.",
            "technical_message": error.message,
            "impact": "This error does not affect search functionality",
            "logging_details": {
                "provider": error.provider,
                "query": error.query,
            },
            "suggested_actions": [
                "No action required - search functionality is unaffected",
                "Report to administrator if this occurs frequently",
            ],
            "retry_possible": True,
            "non_critical": True,
        }

    @staticmethod
    def _format_mcp_server_error(error: MCPServerAnimeError) -> dict[str, Any]:
        """Format general MCP server error."""
        return {
            "error_code": error.code,
            "severity": "error",
            "user_message": error.message,
            "technical_message": error.message,
            "details": error.details,
            "context": error.context,
            "suggested_actions": [
                "Check the error details for specific guidance",
                "Retry the operation if appropriate",
                "Contact support if the problem persists",
            ],
            "retry_possible": True,
        }

    @staticmethod
    def _format_generic_error(error: Exception) -> dict[str, Any]:
        """Format generic error."""
        return {
            "error_code": "UNEXPECTED_ERROR",
            "severity": "error",
            "user_message": "An unexpected error occurred. Please try again or contact support.",
            "technical_message": str(error),
            "suggested_actions": [
                "Retry the operation",
                "Check your input parameters",
                "Contact support if the problem persists",
            ],
            "retry_possible": True,
        }

    @staticmethod
    def format_validation_errors(errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors into a single response.

        Args:
            errors: List of validation error dictionaries

        Returns:
            Formatted response with all validation errors
        """
        return {
            "error": True,
            "error_code": "MULTIPLE_VALIDATION_ERRORS",
            "severity": "warning",
            "timestamp": datetime.now().isoformat(),
            "user_message": f"Found {len(errors)} validation errors. Please correct them and try again.",
            "validation_errors": errors,
            "suggested_actions": [
                "Review each validation error below",
                "Correct the invalid parameters",
                "Retry the operation with valid parameters",
            ],
            "retry_possible": True,
        }

    @staticmethod
    def create_success_response(
        data: Any,
        operation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a standardized success response.

        Args:
            data: The successful response data
            operation: The operation that succeeded
            metadata: Additional metadata about the response

        Returns:
            Standardized success response
        """
        return {
            "error": False,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "data": data,
            "metadata": metadata or {},
        }


class MCPErrorFormatter:
    """Specialized formatter for MCP tool errors."""

    @staticmethod
    def format_mcp_tool_error(
        error: Exception,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Format error for MCP tool response.

        Args:
            error: The exception that occurred
            tool_name: Name of the MCP tool
            parameters: Parameters passed to the tool

        Returns:
            MCP-compatible error response
        """
        base_response = ErrorResponseFormatter.format_error_response(
            error,
            operation=f"mcp_tool_{tool_name}",
            request_context={"tool": tool_name, "parameters": parameters},
        )

        # Convert to MCP-specific format
        mcp_response = {
            "error": {
                "code": base_response.get("error_code", "UNKNOWN_ERROR"),
                "message": base_response.get("user_message", str(error)),
                "data": {
                    "tool": tool_name,
                    "parameters": parameters,
                    "timestamp": base_response["timestamp"],
                    "severity": base_response.get("severity", "error"),
                    "suggested_actions": base_response.get("suggested_actions", []),
                    "retry_possible": base_response.get("retry_possible", True),
                },
            }
        }

        # Add specific fields for certain error types
        if isinstance(error, DatabaseNotInitializedError):
            mcp_response["error"]["data"]["setup_required"] = True
            mcp_response["error"]["data"]["provider"] = error.provider
        elif isinstance(error, DownloadRateLimitedError):
            mcp_response["error"]["data"]["rate_limited"] = True
            mcp_response["error"]["data"]["retry_after"] = error.next_allowed_time
        elif isinstance(error, SearchValidationError):
            mcp_response["error"]["data"]["validation_error"] = True
            mcp_response["error"]["data"]["requirements"] = (
                error.validation_requirements
            )

        return mcp_response


def format_error_for_user(error: Exception, operation: str | None = None) -> str:
    """Format error into a user-friendly message.

    Args:
        error: The exception to format
        operation: The operation that failed

    Returns:
        User-friendly error message
    """
    formatter = ErrorResponseFormatter()
    response = formatter.format_error_response(error, operation)

    user_message = response.get("user_message", str(error))
    suggested_actions = response.get("suggested_actions", [])

    if suggested_actions:
        actions_text = "\n".join(f"• {action}" for action in suggested_actions[:3])
        return f"{user_message}\n\nSuggested actions:\n{actions_text}"

    return user_message


def format_error_for_logging(
    error: Exception, operation: str | None = None
) -> dict[str, Any]:
    """Format error for structured logging.

    Args:
        error: The exception to format
        operation: The operation that failed

    Returns:
        Dictionary suitable for structured logging
    """
    formatter = ErrorResponseFormatter()
    response = formatter.format_error_response(error, operation)

    return {
        "error_type": response["error_type"],
        "error_code": response.get("error_code", "UNKNOWN"),
        "message": response["message"],
        "operation": operation,
        "severity": response.get("severity", "error"),
        "timestamp": response["timestamp"],
        "context": response.get("context", {}),
    }
