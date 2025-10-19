"""Global configuration management for the MCP Server Anime.

This module handles server-wide configuration settings and coordinates
configuration routing to appropriate providers.
"""

import os
from typing import Any

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Global server configuration.

    This configuration manages server-wide settings that affect all providers
    and the overall operation of the MCP server.
    """

    log_level: str = Field(
        default="INFO", description="Global log level for the server"
    )

    cache_enabled: bool = Field(
        default=True, description="Whether caching is enabled globally"
    )

    default_providers: list[str] = Field(
        default=["anidb"], description="List of default providers to enable"
    )

    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of concurrent requests across all providers",
    )

    request_timeout: float = Field(
        default=30.0, ge=1.0, description="Default request timeout in seconds"
    )

    @classmethod
    def from_env(cls, env_prefix: str = "MCP_") -> "ServerConfig":
        """Load configuration from environment variables.

        Args:
            env_prefix: Prefix for environment variable names

        Returns:
            ServerConfig instance loaded from environment
        """
        env_values: dict[str, Any] = {}

        # Map environment variables to config fields
        env_mappings = {
            "log_level": str,
            "cache_enabled": lambda x: x.lower() in ("true", "1", "yes"),
            "default_providers": lambda x: x.split(","),
            "max_concurrent_requests": int,
            "request_timeout": float,
        }

        for field_name, converter in env_mappings.items():
            env_var_name = f"{env_prefix}{field_name.upper()}"
            env_value = os.getenv(env_var_name)

            if env_value is not None:
                try:
                    env_values[field_name] = converter(env_value)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid value for {env_var_name}: {env_value}. "
                        f"Expected {converter.__name__ if hasattr(converter, '__name__') else 'valid value'}: {e}"
                    ) from e

        return cls(**env_values)


def load_server_config() -> ServerConfig:
    """Load server configuration from environment variables.

    Returns:
        ServerConfig instance with values loaded from environment or defaults
    """
    return ServerConfig.from_env()
