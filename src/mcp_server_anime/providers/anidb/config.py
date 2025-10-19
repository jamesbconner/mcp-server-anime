"""Configuration management for the MCP Server Anime.

This module provides configuration classes for managing AniDB API client settings,
including environment variable handling, validation, and default values.
"""

import os
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AniDBConfig(BaseModel):
    """Configuration for AniDB HTTP API client.

    This class manages all configuration parameters required for connecting to and
    interacting with the AniDB HTTP API, including client registration parameters,
    rate limiting settings, and caching configuration.

    Attributes:
        client_name: Name of the client application for AniDB registration
        client_version: Version number of the client application
        protocol_version: AniDB HTTP API protocol version to use
        base_url: Base URL for the AniDB HTTP API
        rate_limit_delay: Minimum delay between API requests in seconds
        max_retries: Maximum number of retry attempts for failed requests
        cache_ttl: Time-to-live for cached responses in seconds
        timeout: HTTP request timeout in seconds
        user_agent: User agent string for HTTP requests
    """

    # Client registration parameters
    client_name: str = Field(
        default="mcpservertcp", description="Client name for AniDB API registration"
    )
    client_version: int = Field(
        default=1, ge=1, description="Client version number (must be >= 1)"
    )
    protocol_version: int = Field(
        default=1, ge=1, description="AniDB HTTP API protocol version (must be >= 1)"
    )

    # API connection settings
    base_url: str = Field(
        default="http://api.anidb.net:9001/httpapi",
        description="Base URL for AniDB HTTP API",
    )

    # Rate limiting and retry settings
    rate_limit_delay: float = Field(
        default=2.0,
        ge=0.1,
        description="Minimum delay between API requests in seconds (must be >= 0.1)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests (0-10)",
    )

    # Caching settings
    cache_ttl: int = Field(
        default=3600, ge=60, description="Cache time-to-live in seconds (must be >= 60)"
    )
    
    # Persistent cache settings
    persistent_cache_enabled: bool = Field(
        default=True, 
        description="Enable persistent SQLite cache"
    )
    persistent_cache_ttl: int = Field(
        default=172800,  # 48 hours
        ge=3600,  # Minimum 1 hour
        description="Persistent cache TTL in seconds (minimum 1 hour)"
    )
    cache_db_path: str | None = Field(
        default=None,
        description="Custom path for cache database file (uses default if None)"
    )
    memory_cache_size: int = Field(
        default=1000,
        ge=100,
        description="Maximum entries in memory cache (minimum 100)"
    )

    # HTTP client settings
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        description="HTTP request timeout in seconds (must be >= 1.0)",
    )
    user_agent: str = Field(
        default="mcp-server-anime/0.2.1 (https://github.com/jamesbconner/mcp-server-anime)",
        description="User agent string for HTTP requests",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url is a properly formatted URL.

        Args:
            v: The base URL string to validate

        Returns:
            The validated URL string

        Raises:
            ValueError: If the URL format is invalid
        """
        if not v.strip():
            raise ValueError("base_url cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.strip()

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Validate that client_name is not empty and contains valid characters.

        Args:
            v: The client name string to validate

        Returns:
            The validated client name string

        Raises:
            ValueError: If the client name is invalid
        """
        if not v.strip():
            raise ValueError("client_name cannot be empty")
        # AniDB client names should be alphanumeric with hyphens/underscores
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(
                "client_name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.strip()

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Validate that user_agent is not empty.

        Args:
            v: The user agent string to validate

        Returns:
            The validated user agent string

        Raises:
            ValueError: If the user agent is empty
        """
        if not v.strip():
            raise ValueError("user_agent cannot be empty")
        return v.strip()

    @classmethod
    def from_env(cls, env_prefix: str = "ANIDB_") -> "AniDBConfig":
        """Create configuration from environment variables.

        Loads configuration values from environment variables with the specified prefix.
        Environment variable names are constructed by uppercasing field names and
        prefixing them with the env_prefix.

        Args:
            env_prefix: Prefix for environment variable names (default: "ANIDB_")

        Returns:
            AniDBConfig instance with values loaded from environment variables

        Example:
            >>> # Set environment variables
            >>> os.environ["ANIDB_CLIENT_NAME"] = "my-anidb-client"
            >>> os.environ["ANIDB_RATE_LIMIT_DELAY"] = "1.5"
            >>>
            >>> # Load configuration
            >>> config = AniDBConfig.from_env()
            >>> print(config.client_name)  # "my-anidb-client"
            >>> print(config.rate_limit_delay)  # 1.5
        """
        env_values: dict[str, Any] = {}

        # Map of field names to their types for proper conversion
        field_types: dict[str, type[str] | type[int] | type[float] | type[bool]] = {
            "client_name": str,
            "client_version": int,
            "protocol_version": int,
            "base_url": str,
            "rate_limit_delay": float,
            "max_retries": int,
            "cache_ttl": int,
            "persistent_cache_enabled": bool,
            "persistent_cache_ttl": int,
            "cache_db_path": str,
            "memory_cache_size": int,
            "timeout": float,
            "user_agent": str,
        }

        for field_name, field_type in field_types.items():
            env_var_name = f"{env_prefix}{field_name.upper()}"
            env_value = os.getenv(env_var_name)

            if env_value is not None:
                try:
                    # Convert string environment variable to appropriate type
                    if field_type is str:
                        env_values[field_name] = env_value
                    elif field_type is int:
                        env_values[field_name] = int(env_value)
                    elif field_type is float:
                        env_values[field_name] = float(env_value)
                    elif field_type is bool:
                        # Handle boolean conversion from string
                        env_values[field_name] = env_value.lower() in ("true", "1", "yes", "on")
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid value for {env_var_name}: {env_value}. "
                        f"Expected {field_type.__name__}: {e}"
                    ) from e

        return cls(**env_values)

    def to_client_params(self) -> dict[str, str | int]:
        """Convert configuration to AniDB client parameters.

        Returns a dictionary of parameters that can be used for AniDB API requests,
        formatted according to the AniDB HTTP API specification.

        Returns:
            Dictionary containing client registration parameters for AniDB API

        Example:
            >>> config = AniDBConfig()
            >>> params = config.to_client_params()
            >>> print(params)
            {
                'client': 'mcp-server-anidb',
                'clientver': 1,
                'protover': 1
            }
        """
        return {
            "client": self.client_name,
            "clientver": self.client_version,
            "protover": self.protocol_version,
        }

    def get_http_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers to include in API requests

        Example:
            >>> config = AniDBConfig()
            >>> headers = config.get_http_headers()
            >>> print(headers)
            {'User-Agent': 'mcp-server-anime/0.2.1 (...)', 'Accept': '...'}
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/xml, text/xml",
            "Accept-Encoding": "gzip, deflate, identity",
            "Accept-Charset": "utf-8",
        }


def load_config(env_prefix: str = "ANIDB_") -> AniDBConfig:
    """Load configuration from environment variables with fallback to defaults.

    This is a convenience function that creates an AniDBConfig instance by first
    attempting to load values from environment variables, then falling back to
    default values for any missing configuration.

    Args:
        env_prefix: Prefix for environment variable names (default: "ANIDB_")

    Returns:
        AniDBConfig instance with configuration loaded from environment or defaults

    Example:
        >>> config = load_config()
        >>> print(config.client_name)  # "mcp-server-anidb" (default)
        >>>
        >>> # With environment variable set
        >>> os.environ["ANIDB_CLIENT_NAME"] = "custom-client"
        >>> config = load_config()
        >>> print(config.client_name)  # "custom-client"
    """
    return AniDBConfig.from_env(env_prefix)
