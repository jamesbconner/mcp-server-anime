"""Global configuration management for the MCP Server Anime.

This module handles server-wide configuration settings and coordinates
configuration routing to appropriate providers. It provides a centralized
configuration system that supports environment variables, file-based
configuration, and runtime configuration updates.

Features:
    - Environment variable loading with validation
    - Provider configuration routing and management
    - Server settings and operational parameters
    - Configuration inheritance and defaults
    - Runtime configuration updates with validation

The configuration system supports both file-based and environment-based
configuration with proper validation and type safety using Pydantic models.

Example:
    >>> from mcp_server_anime.config import load_server_config
    >>> config = load_server_config()
    >>> print(f"Server running on port {config.port}")
"""

from .settings import ServerConfig, load_server_config

# Global configuration exports
__all__ = [
    "ServerConfig",
    "load_server_config",
]
