"""Tests for provider configuration management."""

import os
from unittest.mock import patch

import pytest

from src.mcp_server_anime.providers.config import (
    ProviderConfig,
    ProvidersConfig,
    create_default_providers_config,
    load_providers_config,
)


class TestProviderConfig:
    """Test ProviderConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProviderConfig()

        assert config.enabled is True
        assert config.config == {}
        assert config.priority == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            enabled=False,
            config={"api_key": "test", "timeout": 30},
            priority=50,
        )

        assert config.enabled is False
        assert config.config == {"api_key": "test", "timeout": 30}
        assert config.priority == 50

    def test_priority_validation(self):
        """Test priority field validation."""
        # Valid priorities
        ProviderConfig(priority=1)
        ProviderConfig(priority=1000)

        # Invalid priorities
        with pytest.raises(ValueError):
            ProviderConfig(priority=0)

        with pytest.raises(ValueError):
            ProviderConfig(priority=1001)

    def test_config_validation(self):
        """Test config field validation."""
        # Valid config
        ProviderConfig(config={"key": "value"})

        # Invalid config (not a dict)
        with pytest.raises(ValueError):
            ProviderConfig(config="not a dict")


class TestProvidersConfig:
    """Test ProvidersConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProvidersConfig()

        assert config.auto_initialize is True
        assert config.health_check_interval == 300
        assert config.max_concurrent_requests == 10
        assert config.providers == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        provider_configs = {
            "anidb": ProviderConfig(enabled=True, priority=1),
            "myanimelist": ProviderConfig(enabled=False, priority=2),
        }

        config = ProvidersConfig(
            auto_initialize=False,
            health_check_interval=600,
            max_concurrent_requests=20,
            providers=provider_configs,
        )

        assert config.auto_initialize is False
        assert config.health_check_interval == 600
        assert config.max_concurrent_requests == 20
        assert len(config.providers) == 2
        assert "anidb" in config.providers
        assert "myanimelist" in config.providers

    def test_health_check_interval_validation(self):
        """Test health check interval validation."""
        # Valid intervals
        ProvidersConfig(health_check_interval=60)
        ProvidersConfig(health_check_interval=3600)

        # Invalid interval (too low)
        with pytest.raises(ValueError):
            ProvidersConfig(health_check_interval=59)

    def test_max_concurrent_requests_validation(self):
        """Test max concurrent requests validation."""
        # Valid values
        ProvidersConfig(max_concurrent_requests=1)
        ProvidersConfig(max_concurrent_requests=100)

        # Invalid values
        with pytest.raises(ValueError):
            ProvidersConfig(max_concurrent_requests=0)

        with pytest.raises(ValueError):
            ProvidersConfig(max_concurrent_requests=101)

    def test_providers_validation(self):
        """Test providers field validation."""
        # Valid providers
        ProvidersConfig(providers={"anidb": ProviderConfig()})

        # Invalid providers (not a dict)
        with pytest.raises(ValueError):
            ProvidersConfig(providers="not a dict")

        # Invalid provider name (empty)
        with pytest.raises(ValueError):
            ProvidersConfig(providers={"": ProviderConfig()})

        # Invalid provider name (special characters)
        with pytest.raises(ValueError):
            ProvidersConfig(providers={"invalid@name": ProviderConfig()})

    def test_get_provider_config(self):
        """Test getting provider configuration."""
        provider_config = ProviderConfig(enabled=False, priority=50)
        config = ProvidersConfig(providers={"test": provider_config})

        # Existing provider
        retrieved = config.get_provider_config("test")
        assert retrieved == provider_config

        # Non-existing provider (should return default)
        default = config.get_provider_config("nonexistent")
        assert isinstance(default, ProviderConfig)
        assert default.enabled is True  # Default value

    def test_set_provider_config(self):
        """Test setting provider configuration."""
        config = ProvidersConfig()
        provider_config = ProviderConfig(enabled=False, priority=25)

        config.set_provider_config("test", provider_config)

        assert "test" in config.providers
        assert config.providers["test"] == provider_config

    def test_is_provider_enabled(self):
        """Test checking if provider is enabled."""
        config = ProvidersConfig(
            providers={
                "enabled": ProviderConfig(enabled=True),
                "disabled": ProviderConfig(enabled=False),
            }
        )

        assert config.is_provider_enabled("enabled") is True
        assert config.is_provider_enabled("disabled") is False
        assert config.is_provider_enabled("nonexistent") is True  # Default

    def test_enable_disable_provider(self):
        """Test enabling and disabling providers."""
        config = ProvidersConfig()

        # Enable a provider
        config.enable_provider("test")
        assert config.is_provider_enabled("test") is True

        # Disable the provider
        config.disable_provider("test")
        assert config.is_provider_enabled("test") is False

    def test_get_enabled_providers(self):
        """Test getting list of enabled providers."""
        config = ProvidersConfig(
            providers={
                "provider1": ProviderConfig(enabled=True),
                "provider2": ProviderConfig(enabled=False),
                "provider3": ProviderConfig(enabled=True),
            }
        )

        enabled = config.get_enabled_providers()

        assert len(enabled) == 2
        assert "provider1" in enabled
        assert "provider3" in enabled
        assert "provider2" not in enabled

    def test_get_providers_by_priority(self):
        """Test getting providers sorted by priority."""
        config = ProvidersConfig(
            providers={
                "high": ProviderConfig(priority=10),
                "medium": ProviderConfig(priority=50),
                "low": ProviderConfig(priority=100),
            }
        )

        sorted_providers = config.get_providers_by_priority()

        assert len(sorted_providers) == 3
        assert (
            sorted_providers[0][0] == "high"
        )  # Lowest priority number = highest priority
        assert sorted_providers[1][0] == "medium"
        assert sorted_providers[2][0] == "low"

    @patch.dict(
        os.environ,
        {
            "MCP_ANIME_AUTO_INITIALIZE": "false",
            "MCP_ANIME_HEALTH_CHECK_INTERVAL": "600",
            "MCP_ANIME_MAX_CONCURRENT_REQUESTS": "20",
            "MCP_ANIME_PROVIDER_ANIDB_ENABLED": "true",
            "MCP_ANIME_PROVIDER_MYANIMELIST_ENABLED": "false",
        },
    )
    def test_from_env(self):
        """Test loading configuration from environment variables."""
        config = ProvidersConfig.from_env()

        assert config.auto_initialize is False
        assert config.health_check_interval == 600
        assert config.max_concurrent_requests == 20

        assert "anidb" in config.providers
        assert config.providers["anidb"].enabled is True

        assert "myanimelist" in config.providers
        assert config.providers["myanimelist"].enabled is False

    @patch.dict(
        os.environ,
        {
            "CUSTOM_AUTO_INITIALIZE": "false",
            "CUSTOM_PROVIDER_TEST_ENABLED": "true",
        },
    )
    def test_from_env_custom_prefix(self):
        """Test loading configuration with custom prefix."""
        config = ProvidersConfig.from_env("CUSTOM_")

        assert config.auto_initialize is False
        assert "test" in config.providers
        assert config.providers["test"].enabled is True

    @patch.dict(
        os.environ,
        {
            "MCP_ANIME_HEALTH_CHECK_INTERVAL": "invalid",
            "MCP_ANIME_PROVIDER_TEST_ENABLED": "invalid_bool",
        },
    )
    def test_from_env_invalid_values(self):
        """Test handling of invalid environment variable values."""
        # Should not raise an exception, but log warnings
        config = ProvidersConfig.from_env()

        # Should use default values for invalid settings
        assert config.health_check_interval == 300  # Default value

        # Invalid boolean should be handled gracefully
        if "test" in config.providers:
            # The invalid boolean should default to False
            assert config.providers["test"].enabled is False

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        provider_config = ProviderConfig(
            enabled=False, priority=25, config={"key": "value"}
        )
        config = ProvidersConfig(
            auto_initialize=False,
            health_check_interval=600,
            providers={"test": provider_config},
        )

        result = config.to_dict()

        assert result["auto_initialize"] is False
        assert result["health_check_interval"] == 600
        assert "providers" in result
        assert "test" in result["providers"]
        assert result["providers"]["test"]["enabled"] is False
        assert result["providers"]["test"]["priority"] == 25
        assert result["providers"]["test"]["config"] == {"key": "value"}


class TestConfigurationFunctions:
    """Test configuration utility functions."""

    @patch.dict(
        os.environ,
        {
            "MCP_ANIME_AUTO_INITIALIZE": "false",
        },
    )
    def test_load_providers_config(self):
        """Test load_providers_config function."""
        config = load_providers_config()

        assert isinstance(config, ProvidersConfig)
        assert config.auto_initialize is False

    def test_create_default_providers_config(self):
        """Test create_default_providers_config function."""
        config = create_default_providers_config()

        assert isinstance(config, ProvidersConfig)
        assert config.auto_initialize is True
        assert "anidb" in config.providers
        assert config.providers["anidb"].enabled is True
        assert config.providers["anidb"].priority == 1
