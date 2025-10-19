"""Tests for the extensible MCP server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_server_anime.core.exceptions import (
    ConfigurationError,
    ProviderError,
    ServiceError,
)
from src.mcp_server_anime.extensible_server import (
    ExtensibleMCPServer,
    create_extensible_server,
)
from src.mcp_server_anime.providers.config import ProvidersConfig


class TestExtensibleMCPServer:
    """Test ExtensibleMCPServer functionality."""

    @pytest.fixture
    def server(self):
        """Create an extensible server for testing."""
        return ExtensibleMCPServer("test-server")

    def test_initialization(self, server):
        """Test server initialization."""
        assert server.server_name == "test-server"
        assert server._mcp is None
        assert server._providers_config is None
        assert server._registered_tools == {}
        assert not server._initialized
        assert not server.is_initialized

    def test_create_server(self, server):
        """Test MCP server creation."""
        with patch("src.mcp_server_anime.extensible_server.FastMCP") as mock_fastmcp:
            mock_mcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_mcp_instance

            mcp_server = server.create_server()

            assert mcp_server == mock_mcp_instance
            assert server._mcp == mock_mcp_instance
            mock_fastmcp.assert_called_once_with("test-server")

    def test_create_server_failure(self, server):
        """Test MCP server creation failure."""
        with patch("src.mcp_server_anime.extensible_server.FastMCP") as mock_fastmcp:
            mock_fastmcp.side_effect = Exception("FastMCP creation failed")

            with pytest.raises(ServiceError) as exc_info:
                server.create_server()

            assert "Extensible server creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_configuration(self, server):
        """Test configuration loading."""
        with patch(
            "src.mcp_server_anime.extensible_server.load_providers_config"
        ) as mock_load:
            mock_config = MagicMock(spec=ProvidersConfig)
            mock_config.auto_initialize = True
            mock_config.health_check_interval = 300
            mock_config.get_enabled_providers.return_value = ["anidb"]
            mock_load.return_value = mock_config

            await server.load_configuration()

            assert server._providers_config == mock_config
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_configuration_failure(self, server):
        """Test configuration loading failure."""
        with patch(
            "src.mcp_server_anime.extensible_server.load_providers_config"
        ) as mock_load:
            mock_load.side_effect = Exception("Config loading failed")

            with pytest.raises(ConfigurationError) as exc_info:
                await server.load_configuration()

            assert "Provider configuration loading failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_default_providers(self, server):
        """Test default provider registration."""
        # Setup mock configuration
        mock_config = MagicMock(spec=ProvidersConfig)
        mock_provider_config = MagicMock()
        mock_provider_config.config = {}
        mock_provider_config.enabled = True
        mock_config.get_provider_config.return_value = mock_provider_config
        server._providers_config = mock_config

        with patch(
            "src.mcp_server_anime.extensible_server.create_anidb_provider"
        ) as mock_create:
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            # Mock registry
            mock_registry = MagicMock()
            server._registry = mock_registry

            await server.register_default_providers()

            mock_create.assert_called_once()
            mock_registry.register_provider.assert_called_once_with(
                mock_provider, config={}, enabled=True
            )

    @pytest.mark.asyncio
    async def test_register_default_providers_failure(self, server):
        """Test default provider registration failure."""
        server._providers_config = MagicMock()

        with patch(
            "src.mcp_server_anime.extensible_server.create_anidb_provider"
        ) as mock_create:
            mock_create.side_effect = Exception("Provider creation failed")

            with pytest.raises(ProviderError) as exc_info:
                await server.register_default_providers()

            assert "Default provider registration failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_providers(self, server):
        """Test provider initialization."""
        mock_registry = MagicMock()
        mock_registry.initialize_all_providers = AsyncMock()
        mock_registry.initialize_all_providers.return_value = {
            "provider1": True,
            "provider2": True,
        }
        server._registry = mock_registry

        results = await server.initialize_providers()

        assert results == {"provider1": True, "provider2": True}
        mock_registry.initialize_all_providers.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_providers_all_failed(self, server):
        """Test provider initialization when all providers fail."""
        mock_registry = MagicMock()
        mock_registry.initialize_all_providers = AsyncMock()
        mock_registry.initialize_all_providers.return_value = {
            "provider1": False,
            "provider2": False,
        }
        server._registry = mock_registry

        with pytest.raises(ProviderError) as exc_info:
            await server.initialize_providers()

        assert "No providers initialized successfully" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_providers_failure(self, server):
        """Test provider initialization failure."""
        mock_registry = MagicMock()
        mock_registry.initialize_all_providers = AsyncMock()
        mock_registry.initialize_all_providers.side_effect = Exception("Init failed")
        server._registry = mock_registry

        with pytest.raises(ProviderError) as exc_info:
            await server.initialize_providers()

        assert "Provider initialization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_tools(self, server):
        """Test MCP tool registration."""
        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        mock_registry = MagicMock()
        server._registry = mock_registry

        expected_tools = {
            "provider1": ["anime_search_provider1", "anime_details_provider1"],
            "provider2": ["anime_search_provider2"],
        }

        with patch(
            "src.mcp_server_anime.extensible_server.register_all_provider_tools"
        ) as mock_register:
            mock_register.return_value = expected_tools

            registered_tools = await server.register_tools()

            assert registered_tools == expected_tools
            assert server._registered_tools == expected_tools
            mock_register.assert_called_once_with(mock_mcp, mock_registry)

    @pytest.mark.asyncio
    async def test_register_tools_no_mcp_server(self, server):
        """Test tool registration when MCP server not created."""
        with pytest.raises(ServiceError) as exc_info:
            await server.register_tools()

        assert "MCP server not created" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_tools_failure(self, server):
        """Test tool registration failure."""
        server._mcp = MagicMock()

        with patch(
            "src.mcp_server_anime.extensible_server.register_all_provider_tools"
        ) as mock_register:
            mock_register.side_effect = Exception("Tool registration failed")

            with pytest.raises(ServiceError) as exc_info:
                await server.register_tools()

            assert "Tool registration failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_full_flow(self, server):
        """Test full server initialization flow."""
        # Mock all dependencies
        mock_config = MagicMock(spec=ProvidersConfig)
        mock_config.auto_initialize = True
        mock_config.health_check_interval = 300
        mock_config.get_enabled_providers.return_value = ["anidb"]
        mock_config.get_provider_config.return_value = MagicMock(
            config={}, enabled=True
        )

        with patch.multiple(
            "src.mcp_server_anime.extensible_server",
            load_providers_config=MagicMock(return_value=mock_config),
            FastMCP=MagicMock(return_value=MagicMock()),
            create_anidb_provider=MagicMock(return_value=MagicMock()),
            register_all_provider_tools=MagicMock(return_value={}),
        ):
            # Mock registry methods
            server._registry.initialize_all_providers = AsyncMock(
                return_value={"anidb": True}
            )

            await server.initialize()

            assert server.is_initialized
            assert server._mcp is not None
            assert server._providers_config == mock_config

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, server):
        """Test initialization when already initialized."""
        server._initialized = True

        # Should not raise exception, just log warning
        await server.initialize()

        assert server.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_failure(self, server):
        """Test initialization failure."""
        with patch(
            "src.mcp_server_anime.extensible_server.load_providers_config"
        ) as mock_load:
            mock_load.side_effect = Exception("Config failed")

            with pytest.raises(ServiceError) as exc_info:
                await server.initialize()

            assert "Extensible server initialization failed" in str(exc_info.value)
            assert not server.is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, server):
        """Test server cleanup."""
        # Setup initialized server
        server._initialized = True
        server._registered_tools = {"provider1": ["tool1"]}

        mock_registry = MagicMock()
        mock_registry.cleanup_all_providers = AsyncMock()
        server._registry = mock_registry

        await server.cleanup()

        assert not server.is_initialized
        assert server._registered_tools == {}
        mock_registry.cleanup_all_providers.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self, server):
        """Test cleanup with exception."""
        server._initialized = True

        mock_registry = MagicMock()
        mock_registry.cleanup_all_providers = AsyncMock()
        mock_registry.cleanup_all_providers.side_effect = Exception("Cleanup failed")
        server._registry = mock_registry

        # Should not raise exception
        await server.cleanup()

        # Should still reset state
        assert not server.is_initialized

    @pytest.mark.asyncio
    async def test_health_check(self, server):
        """Test server health check."""
        # Setup server state
        server._initialized = True
        server._mcp = MagicMock()
        server._registered_tools = {"provider1": ["tool1", "tool2"]}

        mock_registry = MagicMock()
        mock_registry.health_check_all_providers = AsyncMock()
        mock_registry.health_check_all_providers.return_value = {
            "provider1": {"status": "healthy"},
            "provider2": {"status": "error"},
        }
        server._registry = mock_registry

        health = await server.health_check()

        assert health["server"]["name"] == "test-server"
        assert health["server"]["initialized"] is True
        assert health["server"]["mcp_server_created"] is True
        assert health["providers"]["total"] == 2
        assert health["providers"]["healthy"] == 1
        assert health["tools"]["total_registered"] == 2
        assert health["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, server):
        """Test health check when no providers are healthy."""
        server._initialized = True

        mock_registry = MagicMock()
        mock_registry.health_check_all_providers = AsyncMock()
        mock_registry.health_check_all_providers.return_value = {
            "provider1": {"status": "error"},
        }
        server._registry = mock_registry

        health = await server.health_check()

        assert health["providers"]["healthy"] == 0
        assert health["overall_status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_with_exception(self, server):
        """Test health check when exception occurs."""
        mock_registry = MagicMock()
        mock_registry.health_check_all_providers = AsyncMock()
        mock_registry.health_check_all_providers.side_effect = Exception(
            "Health check failed"
        )
        server._registry = mock_registry

        health = await server.health_check()

        assert health["overall_status"] == "error"
        assert "error" in health

    def test_get_mcp_server(self, server):
        """Test getting MCP server instance."""
        assert server.get_mcp_server() is None

        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        assert server.get_mcp_server() == mock_mcp

    def test_get_provider_registry(self, server):
        """Test getting provider registry."""
        registry = server.get_provider_registry()
        assert registry == server._registry

    def test_get_registered_tools(self, server):
        """Test getting registered tools."""
        tools = {"provider1": ["tool1"]}
        server._registered_tools = tools

        registered_tools = server.get_registered_tools()

        assert registered_tools == tools
        # Should return a copy, not the original
        assert registered_tools is not server._registered_tools


class TestExtensibleServerFactory:
    """Test extensible server factory function."""

    @pytest.mark.asyncio
    async def test_create_extensible_server(self):
        """Test creating and initializing extensible server."""
        with patch.object(
            ExtensibleMCPServer, "initialize", new_callable=AsyncMock
        ) as mock_init:
            server = await create_extensible_server("test-server")

            assert isinstance(server, ExtensibleMCPServer)
            assert server.server_name == "test-server"
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_extensible_server_default_name(self):
        """Test creating extensible server with default name."""
        with patch.object(ExtensibleMCPServer, "initialize", new_callable=AsyncMock):
            server = await create_extensible_server()

            assert server.server_name == "mcp-server-anime-extensible"
