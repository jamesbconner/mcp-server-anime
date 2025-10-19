"""AniDB provider for anime data.

This module contains all AniDB-specific functionality including the provider
implementation, service layer, configuration, and XML parsing. It provides
comprehensive access to AniDB's anime database through their HTTP API.

Components:
    - provider: Main AniDBProvider class implementing the provider interface
    - service: AniDBService for direct API access and business logic
    - config: Configuration management with environment variable support
    - xml_parser: Robust XML parsing for AniDB's response format
    - search_service: Local database search capabilities for offline access
    - titles_downloader: Database synchronization and maintenance

Features:
    - HTTP API integration with rate limiting and error handling
    - Local database support for offline search capabilities
    - Comprehensive XML parsing with error recovery
    - Caching system for improved performance
    - Configuration-driven behavior with sensible defaults

Example:
    >>> from mcp_server_anime.providers.anidb import AniDBProvider, AniDBConfig
    >>> config = AniDBConfig()
    >>> provider = AniDBProvider(config)
    >>> await provider.initialize()
    >>> results = await provider.search_anime("evangelion", limit=5)
"""

from .config import AniDBConfig, load_config
from .provider import AniDBProvider, create_anidb_provider
from .service import AniDBService, create_anidb_service
from .xml_parser import parse_anime_details, parse_anime_search_results

# AniDB provider functionality exports
__all__ = [
    "AniDBConfig",
    "AniDBProvider",
    "AniDBService",
    "create_anidb_provider",
    "create_anidb_service",
    "load_config",
    "parse_anime_details",
    "parse_anime_search_results",
]
