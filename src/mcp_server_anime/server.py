"""Main MCP server entry point for anime data access."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from .core.error_handler import with_error_handling
from .core.exceptions import ConfigurationError, ServiceError
from .core.logging_config import get_logger, setup_logging
from .providers.anidb.config import load_config
from .tools import register_anime_tools

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@with_error_handling("create_server", reraise=True)
def create_server() -> FastMCP:
    """Create and configure the MCP server instance.

    Returns:
        Configured FastMCP server instance with anime tools registered.

    Raises:
        ConfigurationError: If configuration loading fails
        ServiceError: If server creation fails

    Example:
        >>> server = create_server()
        >>> # Server is ready to handle MCP requests
    """
    logger = get_logger(__name__)

    try:
        # Load configuration
        config = load_config()
        logger.debug(
            "Configuration loaded",
            client_name=config.client_name,
            base_url=config.base_url,
            rate_limit_delay=config.rate_limit_delay,
        )

        # Create FastMCP server
        mcp = FastMCP("mcp-server-anime")

        # Register anime tools
        register_anime_tools(mcp)

        logger.info("MCP server created with anime tools registered")
        return mcp

    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        if "config" in str(e).lower():
            raise ConfigurationError(
                f"Server creation failed due to configuration error: {e}",
                cause=e,
            )
        else:
            raise ServiceError(
                f"Server creation failed: {e}",
                service_name="mcp_server",
                operation="create_server",
                cause=e,
            )


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    """Manage server startup and shutdown procedures.

    Args:
        server: FastMCP server instance

    Yields:
        None during server operation
    """
    logger = get_logger(__name__)

    try:
        logger.info("Starting MCP server...")
        # Server startup procedures can be added here if needed
        # For now, FastMCP handles most of the startup internally

        yield

    except Exception as e:
        logger.error(
            "Error during server operation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
    finally:
        logger.info("Shutting down MCP server...")
        # Server cleanup procedures can be added here if needed
        # FastMCP handles most cleanup internally


@with_error_handling("run_server", reraise=True)
async def run_server() -> None:
    """Run the MCP server with proper startup and shutdown handling.

    Raises:
        ServiceError: If server fails to start or run
    """
    logger = get_logger(__name__)

    try:
        # Create server instance
        server = create_server()

        # Set up signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(
                "Received shutdown signal",
                signal=signum,
            )
            shutdown_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run server with lifespan management
        async with server_lifespan(server):
            logger.info("MCP Server Anime is running...")

            # Run the server using stdio transport
            await server.run_stdio_async()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(
            "Server error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ServiceError(
            f"Server failed to run: {e}",
            service_name="mcp_server",
            operation="run_server",
            cause=e,
        )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="MCP Server for Anime data from AniDB API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run server with default settings
  %(prog)s --log-level DEBUG  # Run with debug logging
  %(prog)s --version          # Show version information

For Kiro MCP configuration, add this to your mcp.json:
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime"],
      "disabled": false
    }
  }
}

For local development in Kiro, see KIRO_SETUP.md for detailed configuration.
        """,
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument("--version", action="version", version="mcp-server-anime 0.2.1")

    return parser.parse_args()


def main() -> None:
    """Main entry point for the MCP server."""
    # Parse command line arguments
    args = parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = get_logger(__name__)

    try:
        logger.info(
            "Starting MCP Server Anime",
            log_level=args.log_level,
            version="0.2.1",
        )

        # Run the server
        asyncio.run(run_server())

    except KeyboardInterrupt:
        logger.info("Server shutdown completed")
        sys.exit(0)
    except Exception as e:
        logger.error(
            "Server failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
