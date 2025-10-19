"""Configuration management for anime data providers.

This module provides configuration classes and utilities for managing provider-specific
settings, including enabling/disabling providers and provider-specific configuration.
"""

import os
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ProviderConfig(BaseModel):
    """Configuration for a single anime data provider.

    This model defines the configuration structure for individual providers,
    including enablement status and provider-specific settings.
    """

    enabled: bool = Field(default=True, description="Whether this provider is enabled")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific configuration parameters"
    )
    priority: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Provider priority for tool registration (lower = higher priority)",
    )

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate provider configuration dictionary.

        Args:
            v: Configuration dictionary to validate

        Returns:
            Validated configuration dictionary
        """
        # Ensure config is a dictionary
        if not isinstance(v, dict):
            raise ValueError("Provider config must be a dictionary")

        return v


class ProvidersConfig(BaseModel):
    """Configuration for all anime data providers.

    This model manages the configuration for all registered providers,
    including global settings and per-provider configurations.
    """

    # Global provider settings
    auto_initialize: bool = Field(
        default=True,
        description="Whether to automatically initialize providers on startup",
    )
    health_check_interval: int = Field(
        default=300, ge=60, description="Interval in seconds for provider health checks"
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent requests across all providers",
    )

    # Per-provider configurations
    providers: dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Configuration for individual providers"
    )

    @field_validator("providers")
    @classmethod
    def validate_providers(
        cls, v: dict[str, ProviderConfig]
    ) -> dict[str, ProviderConfig]:
        """Validate providers configuration dictionary.

        Args:
            v: Providers configuration dictionary to validate

        Returns:
            Validated providers configuration dictionary
        """
        if not isinstance(v, dict):
            raise ValueError("Providers config must be a dictionary")

        # Validate provider names
        for provider_name in v:
            if not provider_name or not isinstance(provider_name, str):
                raise ValueError(f"Invalid provider name: {provider_name}")

            # Provider names should be alphanumeric with hyphens/underscores
            if not all(c.isalnum() or c in "-_" for c in provider_name):
                raise ValueError(
                    f"Provider name '{provider_name}' must contain only "
                    "alphanumeric characters, hyphens, and underscores"
                )

        return v

    def get_provider_config(self, provider_name: str) -> ProviderConfig:
        """Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderConfig for the specified provider (default if not configured)
        """
        return self.providers.get(provider_name, ProviderConfig())

    def set_provider_config(self, provider_name: str, config: ProviderConfig) -> None:
        """Set configuration for a specific provider.

        Args:
            provider_name: Name of the provider
            config: ProviderConfig to set for the provider
        """
        self.providers[provider_name] = config

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled.

        Args:
            provider_name: Name of the provider to check

        Returns:
            True if the provider is enabled, False otherwise
        """
        provider_config = self.get_provider_config(provider_name)
        return provider_config.enabled

    def enable_provider(self, provider_name: str) -> None:
        """Enable a provider.

        Args:
            provider_name: Name of the provider to enable
        """
        provider_config = self.get_provider_config(provider_name)
        provider_config.enabled = True
        self.providers[provider_name] = provider_config

    def disable_provider(self, provider_name: str) -> None:
        """Disable a provider.

        Args:
            provider_name: Name of the provider to disable
        """
        provider_config = self.get_provider_config(provider_name)
        provider_config.enabled = False
        self.providers[provider_name] = provider_config

    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled provider names.

        Returns:
            List of provider names that are enabled
        """
        return [name for name, config in self.providers.items() if config.enabled]

    def get_providers_by_priority(self) -> list[tuple[str, ProviderConfig]]:
        """Get providers sorted by priority.

        Returns:
            List of (provider_name, config) tuples sorted by priority (ascending)
        """
        return sorted(self.providers.items(), key=lambda x: x[1].priority)

    @classmethod
    def from_env(cls, env_prefix: str = "MCP_ANIME_") -> "ProvidersConfig":
        """Create configuration from environment variables.

        Args:
            env_prefix: Prefix for environment variable names

        Returns:
            ProvidersConfig instance with values loaded from environment variables
        """
        env_values: dict[str, Any] = {}

        # Load global settings
        global_settings = {
            "auto_initialize": bool,
            "health_check_interval": int,
            "max_concurrent_requests": int,
        }

        for setting_name, setting_type in global_settings.items():
            env_var_name = f"{env_prefix}{setting_name.upper()}"
            env_value = os.getenv(env_var_name)

            if env_value is not None:
                try:
                    if setting_type is bool:
                        env_values[setting_name] = env_value.lower() in (
                            "true",
                            "1",
                            "yes",
                            "on",
                        )
                    elif setting_type is int:
                        env_values[setting_name] = int(env_value)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid value for {env_var_name}: {env_value}. "
                        f"Expected {setting_type.__name__}: {e}"
                    )

        # Load provider-specific settings
        providers_config: dict[str, ProviderConfig] = {}

        # Look for provider enable/disable settings
        # Format: MCP_ANIME_PROVIDER_<PROVIDER_NAME>_ENABLED=true/false
        for env_var, env_value in os.environ.items():
            if env_var.startswith(f"{env_prefix}PROVIDER_") and env_var.endswith(
                "_ENABLED"
            ):
                # Extract provider name from environment variable
                provider_part = env_var[
                    len(f"{env_prefix}PROVIDER_") : -len("_ENABLED")
                ]
                provider_name = provider_part.lower().replace("_", "-")

                try:
                    enabled = env_value.lower() in ("true", "1", "yes", "on")

                    if provider_name not in providers_config:
                        providers_config[provider_name] = ProviderConfig()

                    providers_config[provider_name].enabled = enabled

                    logger.debug(
                        "Loaded provider config from environment",
                        provider_name=provider_name,
                        enabled=enabled,
                    )

                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid value for {env_var}: {env_value}. "
                        f"Expected boolean: {e}"
                    )

        env_values["providers"] = providers_config

        return cls(**env_values)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary format.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "auto_initialize": self.auto_initialize,
            "health_check_interval": self.health_check_interval,
            "max_concurrent_requests": self.max_concurrent_requests,
            "providers": {
                name: {
                    "enabled": config.enabled,
                    "config": config.config,
                    "priority": config.priority,
                }
                for name, config in self.providers.items()
            },
        }


def load_providers_config(env_prefix: str = "MCP_ANIME_") -> ProvidersConfig:
    """Load providers configuration from environment variables with fallback to defaults.

    Args:
        env_prefix: Prefix for environment variable names

    Returns:
        ProvidersConfig instance with configuration loaded from environment or defaults
    """
    return ProvidersConfig.from_env(env_prefix)


def create_default_providers_config() -> ProvidersConfig:
    """Create a default providers configuration.

    Returns:
        ProvidersConfig with default settings and AniDB provider enabled
    """
    config = ProvidersConfig()

    # Enable AniDB provider by default
    config.providers["anidb"] = ProviderConfig(
        enabled=True,
        priority=1,  # Highest priority as the primary provider
        config={},
    )

    return config
