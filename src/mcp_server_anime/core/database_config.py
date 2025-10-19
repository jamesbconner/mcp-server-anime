"""Database configuration management for local database integration.

This module provides comprehensive configuration classes for database behavior,
download protection, search performance, and transaction logging with environment
variable support and validation.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator, validator

from .logging_config import get_logger
from .security import SecurityLogger

logger = get_logger(__name__)


class DatabaseConfig(BaseModel):
    """Configuration for database operations and storage."""

    # Database file location
    database_path: str = Field(
        default_factory=lambda: str(
            Path.home() / ".cache" / "mcp-server-anime" / "anime_multi_provider.db"
        ),
        description="Path to SQLite database file",
    )

    # Connection and performance settings
    connection_timeout: int = Field(
        default=30, ge=5, le=300, description="Database connection timeout in seconds"
    )

    max_connections: int = Field(
        default=10, ge=1, le=100, description="Maximum number of database connections"
    )

    # Cache and performance
    cache_size_mb: int = Field(
        default=64, ge=16, le=1024, description="SQLite cache size in MB"
    )

    enable_wal_mode: bool = Field(
        default=True,
        description="Enable WAL (Write-Ahead Logging) mode for better concurrency",
    )

    # Maintenance settings
    auto_vacuum: bool = Field(
        default=True, description="Enable automatic database vacuuming"
    )

    vacuum_interval_hours: int = Field(
        default=168,  # 1 week
        ge=1,
        le=8760,  # 1 year
        description="Hours between automatic vacuum operations",
    )

    analyze_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours between automatic ANALYZE operations",
    )

    @validator("database_path")
    def validate_database_path(cls, v):
        """Validate database path and create directory if needed."""
        path = Path(v)

        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Check if parent directory is writable
        if not os.access(path.parent, os.W_OK):
            raise ValueError(f"Database directory is not writable: {path.parent}")

        return str(path)

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        return cls(
            database_path=os.getenv(
                "MCP_ANIME_DB_PATH", cls.__fields__["database_path"].default_factory()
            ),
            connection_timeout=int(os.getenv("MCP_ANIME_DB_CONNECTION_TIMEOUT", "30")),
            max_connections=int(os.getenv("MCP_ANIME_DB_MAX_CONNECTIONS", "10")),
            cache_size_mb=int(os.getenv("MCP_ANIME_DB_CACHE_SIZE_MB", "64")),
            enable_wal_mode=os.getenv("MCP_ANIME_DB_ENABLE_WAL", "true").lower()
            == "true",
            auto_vacuum=os.getenv("MCP_ANIME_DB_AUTO_VACUUM", "true").lower() == "true",
            vacuum_interval_hours=int(
                os.getenv("MCP_ANIME_DB_VACUUM_INTERVAL_HOURS", "168")
            ),
            analyze_interval_hours=int(
                os.getenv("MCP_ANIME_DB_ANALYZE_INTERVAL_HOURS", "24")
            ),
        )


class DownloadConfig(BaseModel):
    """Configuration for download protection and behavior."""

    # Rate limiting
    protection_hours: int = Field(
        default=36,
        ge=1,
        le=168,  # 1 week max
        description="Hours to wait between downloads",
    )

    # Download behavior
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum download retry attempts"
    )

    timeout_seconds: int = Field(
        default=30, ge=10, le=300, description="Download timeout in seconds"
    )

    # File validation
    min_file_size_bytes: int = Field(
        default=100000,  # 100KB
        ge=1000,
        description="Minimum expected file size in bytes",
    )

    max_file_size_bytes: int = Field(
        default=50000000,  # 50MB
        ge=1000000,
        description="Maximum allowed file size in bytes",
    )

    # Integrity checking
    verify_integrity: bool = Field(
        default=True, description="Verify file integrity after download"
    )

    integrity_check_lines: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Number of lines to check for integrity validation",
    )

    # Emergency override
    allow_emergency_override: bool = Field(
        default=False,
        description="Allow emergency override of rate limiting (use with caution)",
    )

    @classmethod
    def from_env(cls) -> "DownloadConfig":
        """Load configuration from environment variables."""
        return cls(
            protection_hours=int(
                os.getenv("MCP_ANIME_DOWNLOAD_PROTECTION_HOURS", "36")
            ),
            max_retries=int(os.getenv("MCP_ANIME_DOWNLOAD_MAX_RETRIES", "3")),
            timeout_seconds=int(os.getenv("MCP_ANIME_DOWNLOAD_TIMEOUT_SECONDS", "30")),
            min_file_size_bytes=int(
                os.getenv("MCP_ANIME_DOWNLOAD_MIN_FILE_SIZE", "100000")
            ),
            max_file_size_bytes=int(
                os.getenv("MCP_ANIME_DOWNLOAD_MAX_FILE_SIZE", "50000000")
            ),
            verify_integrity=os.getenv(
                "MCP_ANIME_DOWNLOAD_VERIFY_INTEGRITY", "true"
            ).lower()
            == "true",
            integrity_check_lines=int(
                os.getenv("MCP_ANIME_DOWNLOAD_INTEGRITY_CHECK_LINES", "1000")
            ),
            allow_emergency_override=os.getenv(
                "MCP_ANIME_DOWNLOAD_ALLOW_EMERGENCY_OVERRIDE", "false"
            ).lower()
            == "true",
        )


class SearchConfig(BaseModel):
    """Configuration for search behavior and performance."""

    # Search limits
    default_limit: int = Field(
        default=10, ge=1, le=100, description="Default number of search results"
    )

    max_limit: int = Field(
        default=20, ge=1, le=100, description="Maximum allowed search results"
    )

    min_query_length: int = Field(
        default=2, ge=1, le=10, description="Minimum search query length"
    )

    max_query_length: int = Field(
        default=100, ge=10, le=1000, description="Maximum search query length"
    )

    # Performance settings
    response_time_target_ms: float = Field(
        default=100.0,
        ge=10.0,
        le=5000.0,
        description="Target response time in milliseconds",
    )

    enable_fuzzy_matching: bool = Field(
        default=True, description="Enable fuzzy matching (exact, prefix, substring)"
    )

    # Caching
    enable_result_caching: bool = Field(
        default=True, description="Enable caching of search results"
    )

    cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=3600,
        description="Cache TTL for search results in seconds",
    )

    # Query normalization
    normalize_queries: bool = Field(
        default=True, description="Normalize queries (lowercase, trim whitespace)"
    )

    remove_special_chars: bool = Field(
        default=False, description="Remove special characters from queries"
    )

    @validator("max_limit")
    def validate_max_limit(cls, v, values):
        """Ensure max_limit is greater than or equal to default_limit."""
        if "default_limit" in values and v < values["default_limit"]:
            raise ValueError("max_limit must be >= default_limit")
        return v

    @classmethod
    def from_env(cls) -> "SearchConfig":
        """Load configuration from environment variables."""
        return cls(
            default_limit=int(os.getenv("MCP_ANIME_SEARCH_DEFAULT_LIMIT", "10")),
            max_limit=int(os.getenv("MCP_ANIME_SEARCH_MAX_LIMIT", "20")),
            min_query_length=int(os.getenv("MCP_ANIME_SEARCH_MIN_QUERY_LENGTH", "2")),
            max_query_length=int(os.getenv("MCP_ANIME_SEARCH_MAX_QUERY_LENGTH", "100")),
            response_time_target_ms=float(
                os.getenv("MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS", "100.0")
            ),
            enable_fuzzy_matching=os.getenv(
                "MCP_ANIME_SEARCH_ENABLE_FUZZY_MATCHING", "true"
            ).lower()
            == "true",
            enable_result_caching=os.getenv(
                "MCP_ANIME_SEARCH_ENABLE_RESULT_CACHING", "true"
            ).lower()
            == "true",
            cache_ttl_seconds=int(
                os.getenv("MCP_ANIME_SEARCH_CACHE_TTL_SECONDS", "300")
            ),
            normalize_queries=os.getenv(
                "MCP_ANIME_SEARCH_NORMALIZE_QUERIES", "true"
            ).lower()
            == "true",
            remove_special_chars=os.getenv(
                "MCP_ANIME_SEARCH_REMOVE_SPECIAL_CHARS", "false"
            ).lower()
            == "true",
        )


class TransactionConfig(BaseModel):
    """Configuration for transaction logging and analytics."""

    # Logging settings
    enable_logging: bool = Field(default=True, description="Enable transaction logging")

    log_client_ids: bool = Field(
        default=True, description="Log client identifiers for tracking"
    )

    log_query_details: bool = Field(
        default=True, description="Log detailed query information"
    )

    # Retention and cleanup
    retention_days: int = Field(
        default=30, ge=1, le=365, description="Days to retain transaction logs"
    )

    cleanup_interval_hours: int = Field(
        default=24, ge=1, le=168, description="Hours between automatic cleanup runs"
    )

    # Analytics
    enable_analytics: bool = Field(
        default=True, description="Enable analytics generation"
    )

    analytics_batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Batch size for analytics processing",
    )

    # Performance monitoring
    track_response_times: bool = Field(
        default=True, description="Track and analyze response times"
    )

    response_time_percentiles: list[float] = Field(
        default=[50.0, 90.0, 95.0, 99.0],
        description="Response time percentiles to calculate",
    )

    # Privacy settings
    anonymize_queries: bool = Field(
        default=False, description="Anonymize queries in logs for privacy"
    )

    max_query_log_length: int = Field(
        default=100, ge=10, le=1000, description="Maximum query length to log"
    )

    @validator("response_time_percentiles")
    def validate_percentiles(cls, v):
        """Validate response time percentiles."""
        for p in v:
            if not 0 <= p <= 100:
                raise ValueError("Percentiles must be between 0 and 100")
        return sorted(v)

    @classmethod
    def from_env(cls) -> "TransactionConfig":
        """Load configuration from environment variables."""
        percentiles_str = os.getenv(
            "MCP_ANIME_TRANSACTION_RESPONSE_TIME_PERCENTILES", "50.0,90.0,95.0,99.0"
        )
        percentiles = [float(p.strip()) for p in percentiles_str.split(",")]

        return cls(
            enable_logging=os.getenv(
                "MCP_ANIME_TRANSACTION_ENABLE_LOGGING", "true"
            ).lower()
            == "true",
            log_client_ids=os.getenv(
                "MCP_ANIME_TRANSACTION_LOG_CLIENT_IDS", "true"
            ).lower()
            == "true",
            log_query_details=os.getenv(
                "MCP_ANIME_TRANSACTION_LOG_QUERY_DETAILS", "true"
            ).lower()
            == "true",
            retention_days=int(os.getenv("MCP_ANIME_TRANSACTION_RETENTION_DAYS", "30")),
            cleanup_interval_hours=int(
                os.getenv("MCP_ANIME_TRANSACTION_CLEANUP_INTERVAL_HOURS", "24")
            ),
            enable_analytics=os.getenv(
                "MCP_ANIME_TRANSACTION_ENABLE_ANALYTICS", "true"
            ).lower()
            == "true",
            analytics_batch_size=int(
                os.getenv("MCP_ANIME_TRANSACTION_ANALYTICS_BATCH_SIZE", "1000")
            ),
            track_response_times=os.getenv(
                "MCP_ANIME_TRANSACTION_TRACK_RESPONSE_TIMES", "true"
            ).lower()
            == "true",
            response_time_percentiles=percentiles,
            anonymize_queries=os.getenv(
                "MCP_ANIME_TRANSACTION_ANONYMIZE_QUERIES", "false"
            ).lower()
            == "true",
            max_query_log_length=int(
                os.getenv("MCP_ANIME_TRANSACTION_MAX_QUERY_LOG_LENGTH", "100")
            ),
        )


class LocalDatabaseIntegrationConfig(BaseModel):
    """Master configuration class for local database integration."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    transaction: TransactionConfig = Field(default_factory=TransactionConfig)

    # Global settings
    debug_mode: bool = Field(
        default=False, description="Enable debug mode with verbose logging"
    )

    environment: str = Field(
        default="production",
        description="Environment name (development, staging, production)",
    )

    @model_validator(mode="after")
    def validate_configuration_consistency(self):
        """Validate configuration consistency across components."""
        # Validate search limits consistency
        if self.search.default_limit > self.search.max_limit:
            raise ValueError("search.default_limit cannot exceed search.max_limit")

        # Validate transaction retention vs cleanup interval
        if (
            self.transaction.retention_days * 24
            < self.transaction.cleanup_interval_hours
        ):
            raise ValueError(
                "transaction.retention_days should be longer than cleanup_interval_hours"
            )

        # Validate download timeout vs database timeout
        if self.download.timeout_seconds > self.database.connection_timeout:
            logger.warning(
                "download.timeout_seconds exceeds database.connection_timeout"
            )

        return self

    @classmethod
    def from_env(cls) -> "LocalDatabaseIntegrationConfig":
        """Load complete configuration from environment variables."""
        return cls(
            database=DatabaseConfig.from_env(),
            download=DownloadConfig.from_env(),
            search=SearchConfig.from_env(),
            transaction=TransactionConfig.from_env(),
            debug_mode=os.getenv("MCP_ANIME_DEBUG_MODE", "false").lower() == "true",
            environment=os.getenv("MCP_ANIME_ENVIRONMENT", "production"),
        )

    def validate_runtime_requirements(self) -> list[str]:
        """Validate runtime requirements and return any issues.

        Returns:
            List of validation issues (empty if all valid)
        """
        issues = []

        # Check database path accessibility
        db_path = Path(self.database.database_path)
        if not db_path.parent.exists():
            issues.append(f"Database directory does not exist: {db_path.parent}")
        elif not os.access(db_path.parent, os.W_OK):
            issues.append(f"Database directory is not writable: {db_path.parent}")

        # Check disk space (warn if less than 1GB available)
        try:
            import shutil

            free_space = shutil.disk_usage(db_path.parent).free
            if free_space < 1024 * 1024 * 1024:  # 1GB
                issues.append(
                    f"Low disk space: {free_space / (1024**3):.1f}GB available"
                )
        except Exception as e:
            # Log disk space check errors but continue validation
            SecurityLogger.log_exception_with_context(
                e, {"operation": "disk_space_check", "db_path": str(self.database.database_path)}
            )
            logger.debug(f"Could not check disk space for {self.database.database_path}: {e}")

        # Validate memory requirements
        cache_memory_mb = self.database.cache_size_mb
        if cache_memory_mb > 512:
            issues.append(
                f"High cache size may impact memory usage: {cache_memory_mb}MB"
            )

        return issues

    def get_summary(self) -> dict[str, Any]:
        """Get configuration summary for logging and debugging.

        Returns:
            Dictionary with configuration summary
        """
        return {
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "database": {
                "path": self.database.database_path,
                "cache_size_mb": self.database.cache_size_mb,
                "wal_mode": self.database.enable_wal_mode,
            },
            "download": {
                "protection_hours": self.download.protection_hours,
                "max_retries": self.download.max_retries,
                "verify_integrity": self.download.verify_integrity,
            },
            "search": {
                "default_limit": self.search.default_limit,
                "max_limit": self.search.max_limit,
                "target_response_ms": self.search.response_time_target_ms,
                "fuzzy_matching": self.search.enable_fuzzy_matching,
            },
            "transaction": {
                "logging_enabled": self.transaction.enable_logging,
                "retention_days": self.transaction.retention_days,
                "analytics_enabled": self.transaction.enable_analytics,
            },
        }


# Global configuration instance
_config_instance: LocalDatabaseIntegrationConfig | None = None


def get_local_db_config() -> LocalDatabaseIntegrationConfig:
    """Get the global configuration instance.

    Returns:
        LocalDatabaseIntegrationConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = LocalDatabaseIntegrationConfig.from_env()
    return _config_instance


def reload_config() -> LocalDatabaseIntegrationConfig:
    """Reload configuration from environment variables.

    Returns:
        New LocalDatabaseIntegrationConfig instance
    """
    global _config_instance
    _config_instance = LocalDatabaseIntegrationConfig.from_env()
    return _config_instance


def validate_config() -> list[str]:
    """Validate current configuration and return any issues.

    Returns:
        List of validation issues
    """
    config = get_local_db_config()
    return config.validate_runtime_requirements()
