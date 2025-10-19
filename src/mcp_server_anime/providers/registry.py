"""Provider registry for managing anime data providers.

This module implements the plugin system for registering, discovering, and managing
multiple anime data providers within the MCP server framework.
"""

import asyncio
from typing import Any

from ..core.exceptions import ProviderError
from ..core.logging_config import get_logger
from .base import AnimeDataProvider, ProviderInfo

logger = get_logger(__name__)


class ProviderRegistry:
    """Registry for managing anime data providers.

    This class provides a centralized system for registering, discovering, and
    managing multiple anime data providers. It handles provider lifecycle,
    configuration, and provides a unified interface for accessing provider functionality.
    """

    def __init__(self) -> None:
        """Initialize the provider registry."""
        self._providers: dict[str, AnimeDataProvider] = {}
        self._provider_configs: dict[str, dict[str, Any]] = {}
        self._enabled_providers: set[str] = set()
        self._initialized = False
        self._cleanup_tasks: set[asyncio.Task] = set()

    def register_provider(
        self,
        provider: AnimeDataProvider,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> None:
        """Register a new anime data provider.

        Args:
            provider: The provider instance to register
            config: Optional configuration dictionary for the provider
            enabled: Whether the provider should be enabled by default

        Raises:
            ProviderError: If a provider with the same name is already registered
        """
        provider_name = provider.info.name

        if provider_name in self._providers:
            raise ProviderError(
                f"Provider '{provider_name}' is already registered",
                provider_name=provider_name,
                operation="register_provider",
            )

        logger.info(
            "Registering anime data provider",
            provider_name=provider_name,
            display_name=provider.info.display_name,
            version=provider.info.version,
            enabled=enabled,
        )

        self._providers[provider_name] = provider
        self._provider_configs[provider_name] = config or {}

        if enabled:
            self._enabled_providers.add(provider_name)

        logger.debug(
            "Provider registered successfully",
            provider_name=provider_name,
            capabilities=provider.info.capabilities.model_dump(),
        )

    def unregister_provider(self, provider_name: str) -> None:
        """Unregister a provider.

        Args:
            provider_name: Name of the provider to unregister

        Raises:
            ProviderError: If the provider is not registered
        """
        if provider_name not in self._providers:
            raise ProviderError(
                f"Provider '{provider_name}' is not registered",
                provider_name=provider_name,
                operation="unregister_provider",
            )

        logger.info("Unregistering provider", provider_name=provider_name)

        # Clean up the provider if it's initialized
        provider = self._providers[provider_name]
        if provider.is_initialized:
            # Create cleanup task and store reference to prevent garbage collection
            cleanup_task = asyncio.create_task(provider.cleanup())
            
            # Add error handling callback
            def cleanup_done_callback(task: asyncio.Task) -> None:
                try:
                    task.result()  # This will raise any exception that occurred
                    logger.debug(
                        "Provider cleanup completed successfully",
                        provider_name=provider_name,
                    )
                except Exception as e:
                    logger.warning(
                        "Provider cleanup failed during unregistration",
                        provider_name=provider_name,
                        error=str(e),
                    )
            
            cleanup_task.add_done_callback(cleanup_done_callback)
            
            # Store task reference to prevent garbage collection
            self._cleanup_tasks.add(cleanup_task)
            
            # Remove task from set when done to prevent memory leaks
            def remove_task_callback(task: asyncio.Task) -> None:
                self._cleanup_tasks.discard(task)
            
            cleanup_task.add_done_callback(remove_task_callback)

        # Remove from all tracking structures
        del self._providers[provider_name]
        self._provider_configs.pop(provider_name, None)
        self._enabled_providers.discard(provider_name)

        logger.debug("Provider unregistered successfully", provider_name=provider_name)

    def enable_provider(self, provider_name: str) -> None:
        """Enable a registered provider.

        Args:
            provider_name: Name of the provider to enable

        Raises:
            ProviderError: If the provider is not registered
        """
        if provider_name not in self._providers:
            raise ProviderError(
                f"Provider '{provider_name}' is not registered",
                provider_name=provider_name,
                operation="enable_provider",
            )

        self._enabled_providers.add(provider_name)
        logger.info("Provider enabled", provider_name=provider_name)

    def disable_provider(self, provider_name: str) -> None:
        """Disable a registered provider.

        Args:
            provider_name: Name of the provider to disable

        Raises:
            ProviderError: If the provider is not registered
        """
        if provider_name not in self._providers:
            raise ProviderError(
                f"Provider '{provider_name}' is not registered",
                provider_name=provider_name,
                operation="disable_provider",
            )

        self._enabled_providers.discard(provider_name)
        logger.info("Provider disabled", provider_name=provider_name)

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled.

        Args:
            provider_name: Name of the provider to check

        Returns:
            True if the provider is registered and enabled
        """
        return provider_name in self._enabled_providers

    def get_provider(self, provider_name: str) -> AnimeDataProvider | None:
        """Get a registered provider by name.

        Args:
            provider_name: Name of the provider to retrieve

        Returns:
            The provider instance if registered and enabled, None otherwise
        """
        if (
            provider_name not in self._providers
            or provider_name not in self._enabled_providers
        ):
            return None

        return self._providers[provider_name]

    def get_enabled_providers(self) -> dict[str, AnimeDataProvider]:
        """Get all enabled providers.

        Returns:
            Dictionary mapping provider names to provider instances
        """
        return {
            name: provider
            for name, provider in self._providers.items()
            if name in self._enabled_providers
        }

    def get_all_providers(self) -> dict[str, AnimeDataProvider]:
        """Get all registered providers (enabled and disabled).

        Returns:
            Dictionary mapping provider names to provider instances
        """
        return self._providers.copy()

    def get_provider_info(self, provider_name: str) -> ProviderInfo | None:
        """Get information about a registered provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderInfo object if the provider is registered, None otherwise
        """
        provider = self._providers.get(provider_name)
        return provider.info if provider else None

    def list_providers(self) -> list[dict[str, Any]]:
        """List all registered providers with their status.

        Returns:
            List of dictionaries containing provider information and status
        """
        providers_list = []

        for name, provider in self._providers.items():
            providers_list.append(
                {
                    "name": name,
                    "display_name": provider.info.display_name,
                    "version": provider.info.version,
                    "description": provider.info.description,
                    "enabled": name in self._enabled_providers,
                    "initialized": provider.is_initialized,
                    "capabilities": provider.info.capabilities.model_dump(),
                }
            )

        return providers_list

    def get_providers_by_capability(
        self, capability: str
    ) -> dict[str, AnimeDataProvider]:
        """Get enabled providers that support a specific capability.

        Args:
            capability: Name of the capability to filter by

        Returns:
            Dictionary of providers that support the specified capability
        """
        matching_providers = {}

        for name, provider in self.get_enabled_providers().items():
            capabilities = provider.info.capabilities

            # Check if the provider supports the requested capability
            if hasattr(capabilities, f"supports_{capability}"):
                if getattr(capabilities, f"supports_{capability}"):
                    matching_providers[name] = provider

        return matching_providers

    async def initialize_all_providers(self) -> dict[str, bool]:
        """Initialize all enabled providers.

        Returns:
            Dictionary mapping provider names to initialization success status
        """
        if self._initialized:
            logger.warning("Providers already initialized")
            return {}

        logger.info("Initializing all enabled providers")
        initialization_results = {}

        # Create a copy of enabled providers to avoid modification during iteration
        enabled_providers_list = list(self._enabled_providers)

        for provider_name in enabled_providers_list:
            provider = self._providers[provider_name]
            config = self._provider_configs.get(provider_name, {})

            try:
                logger.debug("Initializing provider", provider_name=provider_name)

                # Pass configuration to provider if it accepts it
                if hasattr(provider, "_config"):
                    provider._config.update(config)

                await provider.initialize()
                provider._initialized = True
                initialization_results[provider_name] = True

                logger.info(
                    "Provider initialized successfully",
                    provider_name=provider_name,
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize provider",
                    provider_name=provider_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                initialization_results[provider_name] = False

                # Disable the provider if initialization fails
                self._enabled_providers.discard(provider_name)

        self._initialized = True

        successful_count = sum(initialization_results.values())
        total_count = len(initialization_results)

        logger.info(
            "Provider initialization completed",
            successful=successful_count,
            total=total_count,
            enabled_providers=list(self._enabled_providers),
        )

        return initialization_results

    async def cleanup_all_providers(self) -> None:
        """Clean up all providers and close their resources."""
        logger.info("Cleaning up all providers")

        # Wait for any pending cleanup tasks from unregister_provider
        if self._cleanup_tasks:
            logger.debug(f"Waiting for {len(self._cleanup_tasks)} pending cleanup tasks")
            await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)
            self._cleanup_tasks.clear()

        # Clean up remaining initialized providers
        cleanup_tasks = []
        for provider in self._providers.values():
            if provider.is_initialized:
                cleanup_tasks.append(provider.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # Reset initialization state
        for provider in self._providers.values():
            provider._initialized = False

        self._initialized = False
        logger.info("All providers cleaned up")

    async def health_check_all_providers(self) -> dict[str, dict[str, Any]]:
        """Perform health checks on all enabled providers.

        Returns:
            Dictionary mapping provider names to their health status
        """
        health_results = {}

        for provider_name in self._enabled_providers:
            provider = self._providers[provider_name]

            try:
                health_status = await provider.health_check()
                health_results[provider_name] = health_status
            except Exception as e:
                health_results[provider_name] = {
                    "provider": provider_name,
                    "status": "error",
                    "error": str(e),
                }

        return health_results


# Global registry instance
_global_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry instance.

    Returns:
        The global ProviderRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ProviderRegistry()

    return _global_registry


def reset_provider_registry() -> None:
    """Reset the global provider registry.

    This function is primarily intended for testing purposes.
    """
    global _global_registry
    _global_registry = None
