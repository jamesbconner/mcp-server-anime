"""Structured logging configuration for the MCP server anime application.

This module provides comprehensive logging setup with structured logging,
contextual information, and appropriate log levels for different components.
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
import time
from contextvars import ContextVar
from typing import Any

from .exceptions import MCPServerAnimeError

# Context variables for request tracking
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
operation_var: ContextVar[str | None] = ContextVar("operation", default=None)
user_context_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "user_context", default=None
)


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs.

    This formatter creates structured log entries with consistent fields
    for better log analysis and monitoring.
    """

    def __init__(self, include_extra: bool = True) -> None:
        """Initialize the structured formatter.

        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Base log entry structure
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        operation = operation_var.get()
        if operation:
            log_entry["operation"] = operation

        user_context = user_context_var.get()
        if user_context:
            log_entry["user_context"] = user_context

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "message",
                }:
                    extra_fields[key] = value

            if extra_fields:
                log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ContextualFormatter(logging.Formatter):
    """Human-readable formatter with contextual information.

    This formatter creates readable log entries while still including
    contextual information for debugging.
    """

    def __init__(self) -> None:
        """Initialize the contextual formatter."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with contextual information.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Get base formatted message
        formatted = super().format(record)

        # Add context information
        context_parts = []

        request_id = request_id_var.get()
        if request_id:
            context_parts.append(f"req_id={request_id}")

        operation = operation_var.get()
        if operation:
            context_parts.append(f"op={operation}")

        # Add extra fields from record
        extra_fields = []
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                extra_fields.append(f"{key[4:]}={value}")

        if extra_fields:
            context_parts.extend(extra_fields)

        if context_parts:
            formatted += f" [{', '.join(context_parts)}]"

        return formatted


class MCPServerAnimeLogger:
    """Enhanced logger with contextual information and structured logging.

    This logger provides additional functionality for logging with context,
    error tracking, and performance monitoring.
    """

    def __init__(self, name: str) -> None:
        """Initialize the enhanced logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.name = name

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context.

        Args:
            message: Log message
            **kwargs: Additional context fields
        """
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context.

        Args:
            message: Log message
            **kwargs: Additional context fields
        """
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context.

        Args:
            message: Log message
            **kwargs: Additional context fields
        """
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context.

        Args:
            message: Log message
            **kwargs: Additional context fields
        """
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with context.

        Args:
            message: Log message
            **kwargs: Additional context fields
        """
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(
        self, message: str, exc: Exception | None = None, **kwargs: Any
    ) -> None:
        """Log exception with full context.

        Args:
            message: Log message
            exc: Exception to log (uses current exception if None)
            **kwargs: Additional context fields
        """
        if exc and isinstance(exc, MCPServerAnimeError):
            # Add exception context to kwargs
            kwargs.update(exc.context)
            kwargs["error_code"] = exc.code
            kwargs["error_details"] = exc.details

        self._log(logging.ERROR, message, exc_info=exc or True, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal logging method with context handling.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context fields
        """
        # Add context fields to log record
        extra = {}
        for key, value in kwargs.items():
            if key != "exc_info":
                extra[f"ctx_{key}"] = value

        self.logger.log(
            level,
            message,
            extra=extra,
            **{k: v for k, v in kwargs.items() if k == "exc_info"},
        )


def setup_logging(
    log_level: str = "INFO",
    structured: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure logging for the MCP server anime application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured JSON logging
        log_file: Optional log file path
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Choose formatter based on structured flag
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = ContextualFormatter()

    # Configure handlers
    handlers = []

    # Console handler (stderr to avoid interfering with MCP stdio)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Log configuration
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        log_level=log_level,
        structured=structured,
        log_file=log_file,
    )


def get_logger(name: str) -> MCPServerAnimeLogger:
    """Get an enhanced logger instance.

    Args:
        name: Logger name

    Returns:
        Enhanced logger instance
    """
    return MCPServerAnimeLogger(name)


def set_request_context(
    request_id: str | None = None,
    operation: str | None = None,
    user_context: dict[str, Any] | None = None,
) -> None:
    """Set request context for logging.

    Args:
        request_id: Unique request identifier
        operation: Current operation name
        user_context: Additional user context
    """
    if request_id:
        request_id_var.set(request_id)
    if operation:
        operation_var.set(operation)
    if user_context:
        user_context_var.set(user_context)


def clear_request_context() -> None:
    """Clear request context."""
    request_id_var.set(None)
    operation_var.set(None)
    user_context_var.set(None)


def log_performance(operation: str, duration: float, **kwargs: Any) -> None:
    """Log performance metrics.

    Args:
        operation: Operation name
        duration: Operation duration in seconds
        **kwargs: Additional performance metrics
    """
    logger = get_logger("performance")
    logger.info(
        f"Performance: {operation}",
        operation=operation,
        duration=duration,
        **kwargs,
    )


def log_api_request(
    method: str,
    url: str,
    status_code: int | None = None,
    duration: float | None = None,
    **kwargs: Any,
) -> None:
    """Log API request information.

    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional request context
    """
    logger = get_logger("api")
    logger.info(
        f"API {method} {url}",
        method=method,
        url=url,
        status_code=status_code,
        duration=duration,
        **kwargs,
    )


def log_cache_operation(
    operation: str,
    key: str,
    hit: bool | None = None,
    **kwargs: Any,
) -> None:
    """Log cache operation information.

    Args:
        operation: Cache operation (get, set, delete, etc.)
        key: Cache key
        hit: Whether it was a cache hit (for get operations)
        **kwargs: Additional cache context
    """
    logger = get_logger("cache")
    logger.debug(
        f"Cache {operation}: {key}",
        operation=operation,
        key=key,
        hit=hit,
        **kwargs,
    )


def log_error_with_context(
    error: Exception,
    operation: str | None = None,
    **kwargs: Any,
) -> None:
    """Log error with full context information.

    Args:
        error: Exception to log
        operation: Operation that failed
        **kwargs: Additional error context
    """
    logger = get_logger("error")

    if operation:
        set_request_context(operation=operation)

    logger.exception(
        f"Error in {operation or 'unknown operation'}: {error}",
        exc=error,
        **kwargs,
    )


# Logging configuration for different environments
LOGGING_CONFIGS = {
    "development": {
        "log_level": "DEBUG",
        "structured": False,
    },
    "production": {
        "log_level": "INFO",
        "structured": True,
    },
    "testing": {
        "log_level": "WARNING",
        "structured": False,
    },
}


def setup_logging_for_environment(environment: str = "development") -> None:
    """Setup logging for a specific environment.

    Args:
        environment: Environment name (development, production, testing)
    """
    config = LOGGING_CONFIGS.get(environment, LOGGING_CONFIGS["development"])
    setup_logging(**config)
