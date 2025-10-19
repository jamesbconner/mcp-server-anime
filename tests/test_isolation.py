"""Test isolation utilities for managing circuit breaker and global state.

This module provides utilities to ensure proper test isolation by managing
circuit breaker states, global state cleanup, and test environment setup.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.mcp_server_anime.core.error_handler import error_handler
from src.mcp_server_anime.core.logging_config import get_logger

logger = get_logger(__name__)


class IsolationManagerClass:
    """Manages test isolation and cleanup between test runs.

    This class provides methods to reset circuit breakers, clean up global state,
    and set up clean test environments to prevent test interference.
    """

    def __init__(self) -> None:
        """Initialize the test isolation manager."""
        self._original_states: dict[str, Any] = {}
        self._managed_services: set[str] = set()
        self._cleanup_callbacks: list[callable] = []

    def reset_circuit_breakers(self, services: list[str] | None = None) -> None:
        """Reset circuit breaker states for specified services or all services.

        Args:
            services: List of service names to reset. If None, resets all services.
        """
        if services is None:
            # Reset all circuit breakers
            services_to_reset = list(error_handler.circuit_breaker_states.keys())
            error_handler.circuit_breaker_states.clear()
            error_handler.error_counts.clear()
            error_handler.last_error_times.clear()
            logger.debug("Reset all circuit breakers")
        else:
            # Reset specific services
            services_to_reset = services
            for service in services:
                error_handler.circuit_breaker_states.pop(service, None)
                error_handler.error_counts.pop(service, None)
                error_handler.last_error_times.pop(service, None)
            logger.debug(f"Reset circuit breakers for services: {services}")

        self._managed_services.update(services_to_reset)

    def cleanup_global_state(self) -> None:
        """Clean up any global state that might affect tests.

        This method resets various global state components to ensure
        tests start with a clean environment.
        """
        # Reset error handler completely
        error_handler.reset()

        # Clear any cached modules or singletons if needed
        # This can be extended as needed for other global state

        # Execute any registered cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")

        logger.debug("Global state cleaned up")

    def setup_test_environment(self) -> None:
        """Set up clean test environment.

        This method prepares a clean environment for test execution,
        ensuring no residual state from previous tests.
        """
        # Store original states before modification
        self._store_original_states()

        # Reset all managed components
        self.cleanup_global_state()
        self.reset_circuit_breakers()

        logger.debug("Test environment set up")

    def teardown_test_environment(self) -> None:
        """Tear down test environment and restore original states.

        This method should be called after test execution to clean up
        and optionally restore original states.
        """
        # Clean up test-specific state
        self.cleanup_global_state()

        # Restore original states if needed
        self._restore_original_states()

        logger.debug("Test environment torn down")

    def add_cleanup_callback(self, callback: callable) -> None:
        """Add a cleanup callback to be executed during cleanup.

        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)

    def remove_cleanup_callback(self, callback: callable) -> None:
        """Remove a cleanup callback.

        Args:
            callback: Function to remove from cleanup callbacks
        """
        if callback in self._cleanup_callbacks:
            self._cleanup_callbacks.remove(callback)

    def _store_original_states(self) -> None:
        """Store original states before modification."""
        self._original_states = {
            "circuit_breaker_states": error_handler.circuit_breaker_states.copy(),
            "error_counts": error_handler.error_counts.copy(),
            "last_error_times": error_handler.last_error_times.copy(),
        }

    def _restore_original_states(self) -> None:
        """Restore original states after test execution."""
        if "circuit_breaker_states" in self._original_states:
            error_handler.circuit_breaker_states = self._original_states[
                "circuit_breaker_states"
            ].copy()
        if "error_counts" in self._original_states:
            error_handler.error_counts = self._original_states["error_counts"].copy()
        if "last_error_times" in self._original_states:
            error_handler.last_error_times = self._original_states[
                "last_error_times"
            ].copy()

    def is_circuit_breaker_active(self, service: str) -> bool:
        """Check if circuit breaker is active for a service.

        Args:
            service: Service name to check

        Returns:
            True if circuit breaker is active, False otherwise
        """
        return error_handler.is_circuit_broken(service)

    def get_error_count(self, service: str) -> int:
        """Get error count for a service.

        Args:
            service: Service name

        Returns:
            Current error count for the service
        """
        return error_handler.error_counts.get(service, 0)

    def simulate_errors(self, service: str, error_count: int) -> None:
        """Simulate errors for testing circuit breaker behavior.

        Args:
            service: Service name
            error_count: Number of errors to simulate
        """
        # Simulate each error by calling record_error
        for _ in range(error_count):
            error_handler.record_error(service)

        logger.debug(f"Simulated {error_count} errors for service {service}")


# Global test isolation manager instance
test_isolation_manager = IsolationManagerClass()


def reset_test_state() -> None:
    """Convenience function to reset all test state.

    This function provides a simple way to reset all test-related state
    and is suitable for use in test fixtures.
    """
    test_isolation_manager.setup_test_environment()


def cleanup_test_state() -> None:
    """Convenience function to clean up all test state.

    This function provides a simple way to clean up all test-related state
    and is suitable for use in test fixtures.
    """
    test_isolation_manager.cleanup_global_state()


async def async_reset_test_state() -> None:
    """Async version of reset_test_state for async test fixtures."""
    reset_test_state()
    # Allow any pending async operations to complete
    await asyncio.sleep(0.01)


async def async_cleanup_test_state() -> None:
    """Async version of cleanup_test_state for async test fixtures."""
    cleanup_test_state()
    # Allow any pending async operations to complete
    await asyncio.sleep(0.01)
