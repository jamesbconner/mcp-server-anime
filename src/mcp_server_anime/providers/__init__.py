"""Anime data provider framework.

This module provides the extensibility framework for integrating multiple anime data sources
into the MCP server. It defines abstract base classes and interfaces that allow for
consistent integration of different anime APIs while maintaining a unified tool interface.

Architecture:
    - base: Abstract provider interface and capability definitions
    - registry: Provider discovery, registration, and lifecycle management
    - config: Configuration system for provider settings and priorities
    - tools: Automatic MCP tool registration from provider capabilities
    - anidb/: AniDB provider implementation with local database support

The framework supports:
    - Dynamic provider discovery and registration
    - Priority-based provider selection and failover
    - Automatic MCP tool generation from provider capabilities
    - Configuration-driven provider enablement
    - Health monitoring and circuit breaker patterns

Example:
    >>> from mcp_server_anime.providers import get_provider_registry
    >>> registry = get_provider_registry()
    >>> providers = registry.get_enabled_providers()
    >>> results = await providers[0].search_anime("evangelion", limit=5)
"""

from .anidb import AniDBProvider, create_anidb_provider
from .base import AnimeDataProvider, ProviderCapabilities, ProviderInfo
from .config import ProviderConfig, ProvidersConfig, load_providers_config
from .registry import ProviderRegistry, get_provider_registry
from .tools import (
    ToolNamingConvention,
    register_all_provider_tools,
    register_provider_tools,
)

__all__ = [
    "AniDBProvider",
    "AnimeDataProvider",
    "ProviderCapabilities",
    "ProviderConfig",
    "ProviderInfo",
    "ProviderRegistry",
    "ProvidersConfig",
    "ToolNamingConvention",
    "create_anidb_provider",
    "get_provider_registry",
    "load_providers_config",
    "register_all_provider_tools",
    "register_provider_tools",
]
