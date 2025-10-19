"""Core functionality for the MCP Server Anime.

This module contains shared functionality that can be used by any anime data provider,
providing a foundation for building robust, scalable anime data services.

Components:
    - cache: TTL-based caching system with automatic cleanup and statistics
    - exceptions: Comprehensive error hierarchy for different failure modes
    - http_client: Rate-limited HTTP client with retry logic and circuit breakers
    - error_handler: Centralized error handling with context preservation
    - logging_config: Structured logging with performance tracking and context
    - models: Type-safe Pydantic models for anime data structures

The core module is designed to be provider-agnostic, allowing different anime
data sources to share common infrastructure while maintaining consistency.
"""

from .cache import CacheEntry, CacheStats, TTLCache, create_cache, generate_cache_key
from .error_handler import ErrorHandler, error_handler, with_error_handling, with_retry
from .exceptions import (
    APIError,
    AuthenticationError,
    CacheError,
    ConfigurationError,
    DataValidationError,
    MCPServerAnimeError,
    MCPToolError,
    NetworkError,
    ProviderError,
    RateLimitError,
    ServiceError,
    XMLParsingError,
    create_api_error,
    create_network_error,
    create_validation_error,
)
from .http_client import HTTPClient, RateLimiter, RetryConfig, create_http_client
from .logging_config import (
    clear_request_context,
    get_logger,
    log_api_request,
    log_cache_operation,
    log_error_with_context,
    log_performance,
    set_request_context,
    setup_logging,
)
from .models import (
    AnimeCreator,
    AnimeDetails,
    AnimeSearchResult,
    AnimeTitle,
    RelatedAnime,
)
from .security import (
    SecurityConfig,
    SecurityLogger,
    SecurityValidationError,
    SecureQueryHelper,
    TableNameValidator,
    ValidationError,
    ensure_condition,
    ensure_not_none,
)

# Core functionality exports
__all__ = [
    # Cache
    "TTLCache",
    "CacheStats",
    "CacheEntry",
    "generate_cache_key",
    "create_cache",
    # Exceptions
    "MCPServerAnimeError",
    "ConfigurationError",
    "APIError",
    "NetworkError",
    "RateLimitError",
    "AuthenticationError",
    "DataValidationError",
    "XMLParsingError",
    "CacheError",
    "ServiceError",
    "MCPToolError",
    "ProviderError",
    "create_api_error",
    "create_validation_error",
    "create_network_error",
    # HTTP Client
    "HTTPClient",
    "RateLimiter",
    "RetryConfig",
    "create_http_client",
    # Error Handler
    "ErrorHandler",
    "error_handler",
    "with_error_handling",
    "with_retry",
    # Logging
    "get_logger",
    "setup_logging",
    "log_api_request",
    "log_performance",
    "log_error_with_context",
    "set_request_context",
    "clear_request_context",
    "log_cache_operation",
    # Models
    "AnimeSearchResult",
    "AnimeDetails",
    "AnimeTitle",
    "AnimeCreator",
    "RelatedAnime",
    # Security
    "SecurityConfig",
    "SecurityLogger",
    "SecurityValidationError",
    "SecureQueryHelper",
    "TableNameValidator",
    "ValidationError",
    "ensure_condition",
    "ensure_not_none",
]
