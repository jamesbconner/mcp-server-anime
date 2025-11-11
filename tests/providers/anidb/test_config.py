"""Unit tests for configuration management module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.mcp_server_anime.providers.anidb.config import AniDBConfig, load_config


class TestAniDBConfig:
    """Test cases for AniDBConfig class."""

    def test_default_configuration(self) -> None:
        """Test that default configuration values are set correctly."""
        config = AniDBConfig()

        assert config.client_name == "mcpservertcp"
        assert config.client_version == 1
        assert config.protocol_version == 1
        assert config.base_url == "http://api.anidb.net:9001/httpapi"
        assert config.rate_limit_delay == 2.0
        assert config.max_retries == 3
        assert config.cache_ttl == 3600
        assert config.timeout == 30.0
        assert (
            config.user_agent
            == "mcp-server-anime/0.2.1 (https://github.com/jamesbconner/mcp-server-anime)"
        )

    def test_custom_configuration(self) -> None:
        """Test creating configuration with custom values."""
        config = AniDBConfig(
            client_name="custom-client",
            client_version=2,
            protocol_version=2,
            base_url="https://custom.api.com/httpapi",
            rate_limit_delay=1.5,
            max_retries=5,
            cache_ttl=7200,
            timeout=60.0,
            user_agent="custom-client/2.0",
        )

        assert config.client_name == "custom-client"
        assert config.client_version == 2
        assert config.protocol_version == 2
        assert config.base_url == "https://custom.api.com/httpapi"
        assert config.rate_limit_delay == 1.5
        assert config.max_retries == 5
        assert config.cache_ttl == 7200
        assert config.timeout == 60.0
        assert config.user_agent == "custom-client/2.0"

    def test_client_version_validation(self) -> None:
        """Test validation of client_version field."""
        # Valid values
        AniDBConfig(client_version=1)
        AniDBConfig(client_version=10)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(client_version=0)

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(client_version=-1)

    def test_protocol_version_validation(self) -> None:
        """Test validation of protocol_version field."""
        # Valid values
        AniDBConfig(protocol_version=1)
        AniDBConfig(protocol_version=5)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(protocol_version=0)

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(protocol_version=-1)

    def test_rate_limit_delay_validation(self) -> None:
        """Test validation of rate_limit_delay field."""
        # Valid values
        AniDBConfig(rate_limit_delay=0.1)
        AniDBConfig(rate_limit_delay=2.0)
        AniDBConfig(rate_limit_delay=10.5)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 0.1"):
            AniDBConfig(rate_limit_delay=0.05)

        with pytest.raises(ValidationError, match="greater than or equal to 0.1"):
            AniDBConfig(rate_limit_delay=-1.0)

    def test_max_retries_validation(self) -> None:
        """Test validation of max_retries field."""
        # Valid values
        AniDBConfig(max_retries=0)
        AniDBConfig(max_retries=5)
        AniDBConfig(max_retries=10)

        # Invalid values
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            AniDBConfig(max_retries=11)

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            AniDBConfig(max_retries=-1)

    def test_cache_ttl_validation(self) -> None:
        """Test validation of cache_ttl field."""
        # Valid values
        AniDBConfig(cache_ttl=60)
        AniDBConfig(cache_ttl=3600)
        AniDBConfig(cache_ttl=86400)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 60"):
            AniDBConfig(cache_ttl=59)

        with pytest.raises(ValidationError, match="greater than or equal to 60"):
            AniDBConfig(cache_ttl=0)

    def test_timeout_validation(self) -> None:
        """Test validation of timeout field."""
        # Valid values
        AniDBConfig(timeout=1.0)
        AniDBConfig(timeout=30.0)
        AniDBConfig(timeout=120.0)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(timeout=0.5)

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AniDBConfig(timeout=0.0)

    def test_base_url_validation(self) -> None:
        """Test validation of base_url field."""
        # Valid URLs
        AniDBConfig(base_url="http://api.anidb.net:9001/httpapi")
        AniDBConfig(base_url="https://secure.api.com/v1")
        AniDBConfig(base_url="http://localhost:8080/api")

        # Invalid URLs
        with pytest.raises(
            ValidationError, match="must start with http:// or https://"
        ):
            AniDBConfig(base_url="ftp://invalid.com")

        with pytest.raises(
            ValidationError, match="must start with http:// or https://"
        ):
            AniDBConfig(base_url="invalid-url")

        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(base_url="")

        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(base_url="   ")

    def test_client_name_validation(self) -> None:
        """Test validation of client_name field."""
        # Valid client names
        AniDBConfig(client_name="mcp-server-anidb")
        AniDBConfig(client_name="my_client")
        AniDBConfig(client_name="client123")
        AniDBConfig(client_name="a")

        # Invalid client names
        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(client_name="")

        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(client_name="   ")

        with pytest.raises(ValidationError, match="must contain only alphanumeric"):
            AniDBConfig(client_name="client with spaces")

        with pytest.raises(ValidationError, match="must contain only alphanumeric"):
            AniDBConfig(client_name="client@domain.com")

        with pytest.raises(ValidationError, match="must contain only alphanumeric"):
            AniDBConfig(client_name="client/version")

    def test_user_agent_validation(self) -> None:
        """Test validation of user_agent field."""
        # Valid user agents
        AniDBConfig(user_agent="mcp-server-anidb/1.0")
        AniDBConfig(user_agent="Custom Client 2.0")
        AniDBConfig(user_agent="Mozilla/5.0 (compatible)")

        # Invalid user agents
        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(user_agent="")

        with pytest.raises(ValidationError, match="cannot be empty"):
            AniDBConfig(user_agent="   ")

    def test_to_client_params(self) -> None:
        """Test conversion to AniDB client parameters."""
        config = AniDBConfig(
            client_name="test-client", client_version=2, protocol_version=3
        )

        params = config.to_client_params()
        expected = {
            "client": "test-client",
            "clientver": 2,
            "protover": 3,
        }

        assert params == expected

    def test_get_http_headers(self) -> None:
        """Test HTTP headers generation."""
        config = AniDBConfig(user_agent="test-agent/1.0")

        headers = config.get_http_headers()
        expected = {
            "User-Agent": "test-agent/1.0",
            "Accept": "application/xml, text/xml",
            "Accept-Encoding": "gzip, deflate, identity",
            "Accept-Charset": "utf-8",
        }

        assert headers == expected


class TestAniDBConfigFromEnv:
    """Test cases for loading configuration from environment variables."""

    def test_from_env_with_no_env_vars(self) -> None:
        """Test loading configuration when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AniDBConfig.from_env()

            # Should use default values
            assert config.client_name == "mcpservertcp"
            assert config.client_version == 1
            assert config.protocol_version == 1
            assert config.rate_limit_delay == 2.0

    def test_from_env_with_all_env_vars(self) -> None:
        """Test loading configuration with all environment variables set."""
        env_vars = {
            "ANIDB_CLIENT_NAME": "env-client",
            "ANIDB_CLIENT_VERSION": "5",
            "ANIDB_PROTOCOL_VERSION": "2",
            "ANIDB_BASE_URL": "https://env.api.com/httpapi",
            "ANIDB_RATE_LIMIT_DELAY": "1.5",
            "ANIDB_MAX_RETRIES": "7",
            "ANIDB_CACHE_TTL": "7200",
            "ANIDB_TIMEOUT": "45.0",
            "ANIDB_USER_AGENT": "env-agent/2.0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AniDBConfig.from_env()

            assert config.client_name == "env-client"
            assert config.client_version == 5
            assert config.protocol_version == 2
            assert config.base_url == "https://env.api.com/httpapi"
            assert config.rate_limit_delay == 1.5
            assert config.max_retries == 7
            assert config.cache_ttl == 7200
            assert config.timeout == 45.0
            assert config.user_agent == "env-agent/2.0"

    def test_from_env_with_partial_env_vars(self) -> None:
        """Test loading configuration with only some environment variables set."""
        env_vars = {
            "ANIDB_CLIENT_NAME": "partial-client",
            "ANIDB_RATE_LIMIT_DELAY": "3.0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AniDBConfig.from_env()

            # Should use env vars where available
            assert config.client_name == "partial-client"
            assert config.rate_limit_delay == 3.0

            # Should use defaults for others
            assert config.client_version == 1
            assert config.protocol_version == 1
            assert config.base_url == "http://api.anidb.net:9001/httpapi"

    def test_from_env_with_custom_prefix(self) -> None:
        """Test loading configuration with custom environment variable prefix."""
        env_vars = {
            "CUSTOM_CLIENT_NAME": "custom-client",
            "CUSTOM_CLIENT_VERSION": "3",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AniDBConfig.from_env(env_prefix="CUSTOM_")

            assert config.client_name == "custom-client"
            assert config.client_version == 3
            # Others should use defaults
            assert config.protocol_version == 1

    def test_from_env_with_invalid_int_value(self) -> None:
        """Test error handling for invalid integer environment variables."""
        env_vars = {
            "ANIDB_CLIENT_VERSION": "not-a-number",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="Invalid value for ANIDB_CLIENT_VERSION"),
        ):
            AniDBConfig.from_env()

    def test_from_env_with_invalid_float_value(self) -> None:
        """Test error handling for invalid float environment variables."""
        env_vars = {
            "ANIDB_RATE_LIMIT_DELAY": "not-a-float",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="Invalid value for ANIDB_RATE_LIMIT_DELAY"),
        ):
            AniDBConfig.from_env()

    def test_from_env_with_validation_error(self) -> None:
        """Test that validation errors are still raised for invalid env values."""
        env_vars = {
            "ANIDB_CLIENT_VERSION": "0",  # Invalid: must be >= 1
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValidationError, match="greater than or equal to 1"),
        ):
            AniDBConfig.from_env()


class TestLoadConfig:
    """Test cases for the load_config convenience function."""

    def test_load_config_default(self) -> None:
        """Test load_config function with default parameters."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

            assert isinstance(config, AniDBConfig)
            assert config.client_name == "mcpservertcp"

    def test_load_config_with_env_vars(self) -> None:
        """Test load_config function with environment variables."""
        env_vars = {
            "ANIDB_CLIENT_NAME": "loaded-client",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()

            assert config.client_name == "loaded-client"

    def test_load_config_with_custom_prefix(self) -> None:
        """Test load_config function with custom prefix."""
        env_vars = {
            "TEST_CLIENT_NAME": "test-client",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config(env_prefix="TEST_")

            assert config.client_name == "test-client"


class TestConfigIntegration:
    """Integration tests for configuration functionality."""

    def test_config_roundtrip(self) -> None:
        """Test that configuration can be created, converted, and used."""
        # Create config with custom values
        config = AniDBConfig(
            client_name="integration-test",
            client_version=2,
            protocol_version=1,
            rate_limit_delay=1.0,
        )

        # Convert to client parameters
        client_params = config.to_client_params()
        assert client_params["client"] == "integration-test"
        assert client_params["clientver"] == 2
        assert client_params["protover"] == 1

        # Get HTTP headers
        headers = config.get_http_headers()
        assert "User-Agent" in headers
        assert (
            headers["User-Agent"]
            == "mcp-server-anime/0.2.1 (https://github.com/jamesbconner/mcp-server-anime)"
        )

    def test_env_to_config_to_params(self) -> None:
        """Test full workflow from environment variables to API parameters."""
        env_vars = {
            "ANIDB_CLIENT_NAME": "workflow-test",
            "ANIDB_CLIENT_VERSION": "3",
            "ANIDB_PROTOCOL_VERSION": "1",
            "ANIDB_USER_AGENT": "workflow-test/3.0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Load from environment
            config = load_config()

            # Verify configuration
            assert config.client_name == "workflow-test"
            assert config.client_version == 3
            assert config.user_agent == "workflow-test/3.0"

            # Convert to API parameters
            params = config.to_client_params()
            headers = config.get_http_headers()

            # Verify API parameters
            assert params["client"] == "workflow-test"
            assert params["clientver"] == 3
            assert headers["User-Agent"] == "workflow-test/3.0"
