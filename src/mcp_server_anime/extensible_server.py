"""Extensible MCP server with provider framework integration.

This module provides an enhanced MCP server that integrates with the provider
framework to support multiple anime data sources through a unified interface.
The server automatically discovers and initializes providers based on
configuration, making it easy to add new anime data sources.

Features:
    - Dynamic provider registration and management
    - Automatic tool registration from provider capabilities
    - Health checking and monitoring for all providers
    - Configuration-driven provider selection and priorities
    - Graceful error handling and fallback mechanisms
    - Lifecycle management for provider resources

The server supports both single-provider and multi-provider configurations,
with automatic failover and load balancing capabilities.

Example:
    >>> from mcp_server_anime.extensible_server import create_extensible_server
    >>> server = create_extensible_server()
    >>> # Server automatically discovers and initializes configured providers
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .core.error_handler import with_error_handling
from .core.exceptions import ConfigurationError, ProviderError, ServiceError
from .core.logging_config import get_logger
from .providers import get_provider_registry
from .providers.anidb import create_anidb_provider
from .providers.config import load_providers_config
from .providers.tools import register_all_provider_tools

logger = get_logger(__name__)


class ExtensibleMCPServer:
    """Extensible MCP server with provider framework support.

    This server automatically discovers and registers anime data providers,
    creating appropriate MCP tools for each enabled provider while maintaining
    consistent naming conventions and error handling.
    """

    def __init__(self, server_name: str = "mcp-server-anime-extensible") -> None:
        """Initialize the extensible MCP server.

        Args:
            server_name: Name for the MCP server instance
        """
        self.server_name = server_name
        self._mcp: FastMCP | None = None
        self._registry = get_provider_registry()
        self._providers_config = None
        self._registered_tools: dict[str, list[str]] = {}
        self._initialized = False

    @with_error_handling("create_server", reraise=True)
    def create_server(self) -> FastMCP:
        """Create and configure the MCP server instance.

        Returns:
            Configured FastMCP server instance

        Raises:
            ConfigurationError: If configuration loading fails
            ServiceError: If server creation fails
        """
        if self._mcp is not None:
            return self._mcp

        try:
            logger.info("Creating extensible MCP server", server_name=self.server_name)

            # Create FastMCP server
            self._mcp = FastMCP(self.server_name)

            logger.info("Extensible MCP server created successfully")
            return self._mcp

        except Exception as e:
            logger.error(f"Failed to create extensible MCP server: {e}")
            raise ServiceError(
                f"Extensible server creation failed: {e}",
                service_name="extensible_mcp_server",
                operation="create_server",
                cause=e,
            )

    @with_error_handling("load_configuration", reraise=True)
    async def load_configuration(self) -> None:
        """Load provider configuration from environment variables.

        Raises:
            ConfigurationError: If configuration loading fails
        """
        try:
            logger.info("Loading provider configuration")

            # Load providers configuration
            self._providers_config = load_providers_config()

            logger.info(
                "Provider configuration loaded",
                auto_initialize=self._providers_config.auto_initialize,
                health_check_interval=self._providers_config.health_check_interval,
                enabled_providers=self._providers_config.get_enabled_providers(),
            )

        except Exception as e:
            logger.error(f"Failed to load provider configuration: {e}")
            raise ConfigurationError(
                f"Provider configuration loading failed: {e}",
                cause=e,
            )

    @with_error_handling("register_default_providers", reraise=True)
    async def register_default_providers(self) -> None:
        """Register default anime data providers.

        Raises:
            ProviderError: If provider registration fails
        """
        try:
            logger.info("Registering default anime data providers")

            # Register AniDB provider
            anidb_provider = create_anidb_provider()
            anidb_config = self._providers_config.get_provider_config("anidb")

            self._registry.register_provider(
                anidb_provider, config=anidb_config.config, enabled=anidb_config.enabled
            )

            logger.info("Default providers registered successfully")

        except Exception as e:
            logger.error(f"Failed to register default providers: {e}")
            raise ProviderError(
                f"Default provider registration failed: {e}",
                operation="register_default_providers",
                cause=e,
            )

    @with_error_handling("initialize_providers", reraise=True)
    async def initialize_providers(self) -> dict[str, bool]:
        """Initialize all enabled providers.

        Returns:
            Dictionary mapping provider names to initialization success status

        Raises:
            ProviderError: If provider initialization fails critically
        """
        try:
            logger.info("Initializing anime data providers")

            # Initialize all enabled providers
            initialization_results = await self._registry.initialize_all_providers()

            successful_count = sum(initialization_results.values())
            total_count = len(initialization_results)

            if successful_count == 0 and total_count > 0:
                raise ProviderError(
                    "No providers initialized successfully",
                    operation="initialize_providers",
                )

            logger.info(
                "Provider initialization completed",
                successful=successful_count,
                total=total_count,
                results=initialization_results,
            )

            return initialization_results

        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            if isinstance(e, ProviderError):
                raise
            else:
                raise ProviderError(
                    f"Provider initialization failed: {e}",
                    operation="initialize_providers",
                    cause=e,
                )

    @with_error_handling("register_tools", reraise=True)
    async def register_tools(self) -> dict[str, list[str]]:
        """Register MCP tools for all enabled providers.

        Returns:
            Dictionary mapping provider names to their registered tool names

        Raises:
            ServiceError: If tool registration fails
        """
        if self._mcp is None:
            raise ServiceError(
                "MCP server not created",
                service_name="extensible_mcp_server",
                operation="register_tools",
            )

        try:
            logger.info("Registering MCP tools for enabled providers")

            # Register tools for all enabled providers
            self._registered_tools = register_all_provider_tools(
                self._mcp, self._registry
            )

            total_tools = sum(len(tools) for tools in self._registered_tools.values())

            logger.info(
                "MCP tools registered successfully",
                total_providers=len(self._registered_tools),
                total_tools=total_tools,
                registered_tools=self._registered_tools,
            )

            return self._registered_tools

        except Exception as e:
            logger.error(f"Failed to register MCP tools: {e}")
            raise ServiceError(
                f"Tool registration failed: {e}",
                service_name="extensible_mcp_server",
                operation="register_tools",
                cause=e,
            )

    @with_error_handling("initialize", reraise=True)
    async def initialize(self) -> None:
        """Initialize the extensible MCP server and all components.

        Raises:
            ServiceError: If initialization fails
        """
        if self._initialized:
            logger.warning("Extensible MCP server already initialized")
            return

        try:
            logger.info("Initializing extensible MCP server")

            # Load configuration
            await self.load_configuration()

            # Create MCP server
            self.create_server()

            # Register default providers
            await self.register_default_providers()

            # Initialize providers if auto-initialization is enabled
            if self._providers_config.auto_initialize:
                await self.initialize_providers()

            # Register MCP tools
            await self.register_tools()

            self._initialized = True

            logger.info(
                "Extensible MCP server initialized successfully",
                registered_providers=list(
                    self._registry.get_enabled_providers().keys()
                ),
                registered_tools=self._registered_tools,
            )

        except Exception as e:
            logger.error(f"Failed to initialize extensible MCP server: {e}")
            raise ServiceError(
                f"Extensible server initialization failed: {e}",
                service_name="extensible_mcp_server",
                operation="initialize",
                cause=e,
            )

    async def cleanup(self) -> None:
        """Clean up server resources and provider connections."""
        try:
            logger.info("Cleaning up extensible MCP server")

            # Clean up all providers
            await self._registry.cleanup_all_providers()

            logger.info("Extensible MCP server cleanup completed")

        except Exception as e:
            logger.error(
                "Error during extensible MCP server cleanup",
                error=str(e),
                error_type=type(e).__name__,
            )
        finally:
            # Always reset state, even if cleanup fails
            self._registered_tools.clear()
            self._initialized = False

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the server and all providers.

        Returns:
            Dictionary containing health status information
        """
        try:
            # Get provider health status
            provider_health = await self._registry.health_check_all_providers()

            # Calculate overall health
            healthy_providers = sum(
                1
                for status in provider_health.values()
                if status.get("status") == "healthy"
            )
            total_providers = len(provider_health)

            return {
                "server": {
                    "name": self.server_name,
                    "initialized": self._initialized,
                    "mcp_server_created": self._mcp is not None,
                },
                "providers": {
                    "total": total_providers,
                    "healthy": healthy_providers,
                    "details": provider_health,
                },
                "tools": {
                    "total_registered": sum(
                        len(tools) for tools in self._registered_tools.values()
                    ),
                    "by_provider": self._registered_tools,
                },
                "overall_status": "healthy" if healthy_providers > 0 else "unhealthy",
            }

        except Exception as e:
            return {
                "server": {
                    "name": self.server_name,
                    "initialized": self._initialized,
                    "mcp_server_created": self._mcp is not None,
                },
                "overall_status": "error",
                "error": str(e),
            }

    def get_mcp_server(self) -> FastMCP | None:
        """Get the underlying FastMCP server instance.

        Returns:
            FastMCP server instance if created, None otherwise
        """
        return self._mcp

    def get_provider_registry(self) -> Any:
        """Get the provider registry instance.

        Returns:
            ProviderRegistry instance
        """
        return self._registry

    def get_registered_tools(self) -> dict[str, list[str]]:
        """Get information about registered tools.

        Returns:
            Dictionary mapping provider names to their registered tool names
        """
        return self._registered_tools.copy()

    @property
    def is_initialized(self) -> bool:
        """Check if the server is initialized.

        Returns:
            True if the server is initialized and ready to use
        """
        return self._initialized


async def create_extensible_server(
    server_name: str = "mcp-server-anime-extensible",
) -> ExtensibleMCPServer:
    """Create and initialize an extensible MCP server.

    Args:
        server_name: Name for the MCP server instance

    Returns:
        Initialized ExtensibleMCPServer instance
    """
    server = ExtensibleMCPServer(server_name)
    await server.initialize()
    return server
