"""MCP Server for Anime data with extensible provider architecture.

This package provides a Model Context Protocol (MCP) server for accessing anime data
through multiple providers. The architecture separates core functionality from
provider-specific implementations, making it easy to add new anime data sources.

Core Components:
    - core/: Shared functionality (caching, HTTP client, error handling, models)
    - providers/: Provider implementations (currently supports AniDB)
    - config/: Global server configuration

Example Usage:
    >>> from mcp_server_anime import create_server, AniDBService, AniDBConfig
    >>> server = create_server()  # Creates MCP server with anime tools
    >>> config = AniDBConfig()    # Load AniDB configuration
    >>> service = AniDBService(config)  # Create AniDB service
"""

# Backward compatibility imports
from .core.exceptions import APIError, XMLParsingError
from .core.models import AnimeDetails, AnimeSearchResult
from .providers.anidb.config import AniDBConfig, load_config
from .providers.anidb.service import AniDBService, create_anidb_service
from .providers.anidb.xml_parser import (
    parse_anime_details,
    parse_anime_search_results,
)
from .server import create_server

__version__ = "0.2.1"
__author__ = "MCP Server Anime"
__description__ = (
    "Model Context Protocol server for accessing anime data through AniDB HTTP API"
)

# Maintain existing public API for backward compatibility
__all__ = [
    "APIError",
    "AniDBConfig",
    "AniDBService",
    "AnimeDetails",
    "AnimeSearchResult",
    "XMLParsingError",
    "create_anidb_service",
    "create_server",
    "load_config",
    "parse_anime_details",
    "parse_anime_search_results",
]
