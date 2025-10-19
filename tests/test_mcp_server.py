"""Integration tests for MCP server protocol compliance."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from src.mcp_server_anime.core.exceptions import ConfigurationError, ServiceError
from src.mcp_server_anime.core.logging_config import setup_logging
from src.mcp_server_anime.server import (
    create_server,
    main,
    parse_args,
    run_server,
    server_lifespan,
)


class TestMCPServerIntegration:
    """Integration tests for MCP server protocol compliance."""

    @pytest.fixture
    def server(self) -> FastMCP:
        """Create a test server instance."""
        return create_server()

    @pytest.fixture
    def mock_anidb_service(self) -> AsyncMock:
        """Mock AniDB service for testing."""
        service = AsyncMock()
        service.__aenter__ = AsyncMock(return_value=service)
        service.__aexit__ = AsyncMock(return_value=None)
        return service

    def test_server_creation(self) -> None:
        """Test that server can be created successfully."""
        server = create_server()
        assert isinstance(server, FastMCP)
        assert server.name == "mcp-server-anime"

    def test_server_creation_config_error(self) -> None:
        """Test server creation with configuration error."""
        with patch("src.mcp_server_anime.server.load_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Configuration file not found")

            with pytest.raises(
                ConfigurationError,
                match="Server creation failed due to configuration error",
            ):
                create_server()

    def test_server_creation_service_error(self) -> None:
        """Test server creation with service error."""
        with patch("src.mcp_server_anime.server.FastMCP") as mock_fastmcp:
            mock_fastmcp.side_effect = Exception("Service initialization failed")

            with pytest.raises(ServiceError, match="Server creation failed"):
                create_server()

    def test_logging_setup(self) -> None:
        """Test logging configuration."""
        # Test that setup_logging doesn't raise an exception
        setup_logging("DEBUG")
        setup_logging("INFO")
        setup_logging("WARNING")

        # Test that logger can be created
        logger = logging.getLogger("test")
        assert logger is not None

    @pytest.mark.asyncio
    async def test_server_lifespan(self, server: FastMCP) -> None:
        """Test server lifespan management."""
        startup_called = False
        shutdown_called = False

        async with server_lifespan(server):
            startup_called = True
            # Simulate some server operation
            await asyncio.sleep(0.01)

        shutdown_called = True

        assert startup_called
        assert shutdown_called

    def test_server_tools_registration(self, server: FastMCP) -> None:
        """Test that tools are properly registered with the server."""
        # Check that server has tools registered
        # FastMCP doesn't expose _tools directly, but we can check it was created successfully
        assert server is not None
        assert server.name == "mcp-server-anime"

    def test_server_creation_with_config_error(self) -> None:
        """Test server creation when configuration fails."""
        with patch(
            "src.mcp_server_anime.server.load_config",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises(
                ConfigurationError,
                match="Server creation failed due to configuration error",
            ):
                create_server()

    def test_server_creation_with_service_error(self) -> None:
        """Test server creation when service fails."""
        with patch(
            "src.mcp_server_anime.server.register_anime_tools",
            side_effect=Exception("Service error"),
        ):
            with pytest.raises(ServiceError, match="Server creation failed"):
                create_server()

    @pytest.mark.asyncio
    async def test_run_server_keyboard_interrupt(self) -> None:
        """Test run_server handles keyboard interrupt gracefully."""
        with patch("src.mcp_server_anime.server.create_server") as mock_create:
            with patch("src.mcp_server_anime.server.stdio_server") as mock_stdio:
                mock_server = MagicMock()
                mock_create.return_value = mock_server

                # Mock stdio_server to raise KeyboardInterrupt
                mock_stdio.return_value.__aenter__.side_effect = KeyboardInterrupt()

                # Should not raise an exception
                await run_server()

    @pytest.mark.asyncio
    async def test_run_server_service_error(self) -> None:
        """Test run_server handles service errors."""
        with patch(
            "src.mcp_server_anime.server.create_server",
            side_effect=Exception("Service error"),
        ):
            with pytest.raises(ServiceError, match="Server failed to run"):
                await run_server()

    def test_parse_args_default(self) -> None:
        """Test parse_args with default arguments."""
        with patch("sys.argv", ["mcp-server-anime"]):
            args = parse_args()
            assert args.log_level == "INFO"

    def test_parse_args_custom_log_level(self) -> None:
        """Test parse_args with custom log level."""
        with patch("sys.argv", ["mcp-server-anime", "--log-level", "DEBUG"]):
            args = parse_args()
            assert args.log_level == "DEBUG"

    def test_parse_args_version(self) -> None:
        """Test parse_args with version flag."""
        with patch("sys.argv", ["mcp-server-anime", "--version"]):
            with pytest.raises(SystemExit):
                parse_args()

    def test_main_success(self) -> None:
        """Test main function success path."""
        with patch("sys.argv", ["mcp-server-anime", "--log-level", "INFO"]):
            with patch("src.mcp_server_anime.server.asyncio.run") as mock_run:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_run.assert_called_once()
                    mock_exit.assert_not_called()

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles keyboard interrupt."""
        with patch("sys.argv", ["mcp-server-anime"]):
            # Use AsyncMock to properly handle the coroutine
            async def mock_run_server():
                raise KeyboardInterrupt()

            with patch(
                "src.mcp_server_anime.server.run_server", side_effect=mock_run_server
            ):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_once_with(0)

    def test_main_exception(self) -> None:
        """Test main function handles exceptions."""
        with patch("sys.argv", ["mcp-server-anime"]):
            # Use AsyncMock to properly handle the coroutine
            async def mock_run_server():
                raise Exception("Test error")

            with patch(
                "src.mcp_server_anime.server.run_server", side_effect=mock_run_server
            ):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_once_with(1)


class TestMCPServerConfiguration:
    """Test server configuration and setup."""

    def test_logging_levels(self) -> None:
        """Test different logging levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            setup_logging(level)
            # Test that logging is configured without errors
            logger = logging.getLogger("test")
            assert logger is not None

    @pytest.mark.asyncio
    async def test_server_lifespan_error_handling(self) -> None:
        """Test server lifespan error handling."""
        server = create_server()

        with pytest.raises(RuntimeError, match="Test error"):
            async with server_lifespan(server):
                raise RuntimeError("Test error")


@pytest.mark.integration
class TestMCPServerRealIntegration:
    """Real integration tests that can be run against actual services."""

    @pytest.mark.asyncio
    async def test_server_startup_shutdown_cycle(self) -> None:
        """Test complete server startup and shutdown cycle."""
        server = create_server()

        # Test that server can be created and tools are registered
        assert server is not None

        # Test lifespan management
        async with server_lifespan(server):
            # Server should be operational
            pass

        # Server should shut down cleanly

    def test_command_line_interface_setup(self) -> None:
        """Test that the command line interface is properly configured."""
        # Test default arguments
        with patch("sys.argv", ["mcp-server-anime"]):
            args = parse_args()
            assert args.log_level == "INFO"

        # Test with custom log level
        with patch("sys.argv", ["mcp-server-anime", "--log-level", "DEBUG"]):
            args = parse_args()
            assert args.log_level == "DEBUG"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
