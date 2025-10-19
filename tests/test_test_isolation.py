"""Unit tests for test isolation manager.

This module tests the TestIsolationManager class to ensure it properly
manages circuit breaker states and global state cleanup.
"""

import time
from unittest.mock import Mock

import pytest

from src.mcp_server_anime.core.error_handler import error_handler
from tests.test_isolation import (
    IsolationManagerClass,
    async_cleanup_test_state,
    async_reset_test_state,
    cleanup_test_state,
    reset_test_state,
    test_isolation_manager,
)


class TestTestIsolationManager:
    """Test cases for TestIsolationManager class."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Ensure clean state before each test
        error_handler.reset()
        self.manager = IsolationManagerClass()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        error_handler.reset()

    def test_init(self) -> None:
        """Test TestIsolationManager initialization."""
        manager = IsolationManagerClass()
        assert manager._original_states == {}
        assert manager._managed_services == set()
        assert manager._cleanup_callbacks == []

    def test_reset_circuit_breakers_all(self) -> None:
        """Test resetting all circuit breakers."""
        # Set up some circuit breaker state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.circuit_breaker_states["service2"] = True
        error_handler.error_counts["service1"] = 5
        error_handler.error_counts["service2"] = 3
        error_handler.last_error_times["service1"] = time.time()
        error_handler.last_error_times["service2"] = time.time()

        # Reset all circuit breakers
        self.manager.reset_circuit_breakers()

        # Verify all states are cleared
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}
        assert error_handler.last_error_times == {}
        assert "service1" in self.manager._managed_services
        assert "service2" in self.manager._managed_services

    def test_reset_circuit_breakers_specific_services(self) -> None:
        """Test resetting circuit breakers for specific services."""
        # Set up circuit breaker state for multiple services
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.circuit_breaker_states["service2"] = True
        error_handler.circuit_breaker_states["service3"] = True
        error_handler.error_counts["service1"] = 5
        error_handler.error_counts["service2"] = 3
        error_handler.error_counts["service3"] = 2

        # Reset only specific services
        self.manager.reset_circuit_breakers(["service1", "service2"])

        # Verify only specified services are reset
        assert "service1" not in error_handler.circuit_breaker_states
        assert "service2" not in error_handler.circuit_breaker_states
        assert "service3" in error_handler.circuit_breaker_states
        assert "service1" not in error_handler.error_counts
        assert "service2" not in error_handler.error_counts
        assert "service3" in error_handler.error_counts
        assert "service1" in self.manager._managed_services
        assert "service2" in self.manager._managed_services

    def test_cleanup_global_state(self) -> None:
        """Test global state cleanup."""
        # Set up some global state
        error_handler.circuit_breaker_states["test_service"] = True
        error_handler.error_counts["test_service"] = 3

        # Add a cleanup callback
        callback_called = False

        def test_callback():
            nonlocal callback_called
            callback_called = True

        self.manager.add_cleanup_callback(test_callback)

        # Clean up global state
        self.manager.cleanup_global_state()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}
        assert callback_called

    def test_cleanup_callback_exception_handling(self) -> None:
        """Test that cleanup callback exceptions are handled gracefully."""

        def failing_callback():
            raise ValueError("Test exception")

        def working_callback():
            working_callback.called = True

        working_callback.called = False

        self.manager.add_cleanup_callback(failing_callback)
        self.manager.add_cleanup_callback(working_callback)

        # Should not raise exception
        self.manager.cleanup_global_state()

        # Working callback should still be called
        assert working_callback.called

    def test_setup_test_environment(self) -> None:
        """Test test environment setup."""
        # Set up some initial state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Set up test environment
        self.manager.setup_test_environment()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}

        # Verify original states are stored
        assert "circuit_breaker_states" in self.manager._original_states
        assert "error_counts" in self.manager._original_states
        assert "last_error_times" in self.manager._original_states

    def test_teardown_test_environment(self) -> None:
        """Test test environment teardown."""
        # Set up initial state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Set up and then tear down
        self.manager.setup_test_environment()

        # Add some test state
        error_handler.circuit_breaker_states["test_service"] = True

        # Tear down
        self.manager.teardown_test_environment()

        # Verify test state is cleaned
        assert "test_service" not in error_handler.circuit_breaker_states

    def test_add_remove_cleanup_callback(self) -> None:
        """Test adding and removing cleanup callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        # Add callbacks
        self.manager.add_cleanup_callback(callback1)
        self.manager.add_cleanup_callback(callback2)
        assert len(self.manager._cleanup_callbacks) == 2

        # Remove one callback
        self.manager.remove_cleanup_callback(callback1)
        assert len(self.manager._cleanup_callbacks) == 1
        assert callback2 in self.manager._cleanup_callbacks

        # Try to remove non-existent callback (should not raise)
        self.manager.remove_cleanup_callback(callback1)
        assert len(self.manager._cleanup_callbacks) == 1

    def test_is_circuit_breaker_active(self) -> None:
        """Test circuit breaker status checking."""
        service = "test_service"

        # Initially not active
        assert not self.manager.is_circuit_breaker_active(service)

        # Activate circuit breaker
        error_handler.circuit_breaker_states[service] = True
        assert self.manager.is_circuit_breaker_active(service)

        # Deactivate circuit breaker
        error_handler.circuit_breaker_states[service] = False
        assert not self.manager.is_circuit_breaker_active(service)

    def test_get_error_count(self) -> None:
        """Test error count retrieval."""
        service = "test_service"

        # Initially zero
        assert self.manager.get_error_count(service) == 0

        # Set error count
        error_handler.error_counts[service] = 5
        assert self.manager.get_error_count(service) == 5

    def test_simulate_errors(self) -> None:
        """Test error simulation for testing."""
        service = "test_service"
        error_count = 6  # Above default threshold of 5

        # Simulate errors
        self.manager.simulate_errors(service, error_count)

        # Verify error count is set
        assert error_handler.error_counts[service] == error_count
        assert service in error_handler.last_error_times

        # Verify circuit breaker is activated (threshold exceeded)
        assert error_handler.circuit_breaker_states[service] is True

    def test_simulate_errors_below_threshold(self) -> None:
        """Test error simulation below circuit breaker threshold."""
        service = "test_service"
        error_count = 3  # Below default threshold of 5

        # Simulate errors
        self.manager.simulate_errors(service, error_count)

        # Verify error count is set but circuit breaker is not activated
        assert error_handler.error_counts[service] == error_count
        assert (
            service not in error_handler.circuit_breaker_states
            or not error_handler.circuit_breaker_states[service]
        )


class TestGlobalTestIsolationManager:
    """Test cases for global test isolation manager instance."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        error_handler.reset()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        error_handler.reset()

    def test_global_instance_exists(self) -> None:
        """Test that global test isolation manager instance exists."""
        assert test_isolation_manager is not None
        assert isinstance(test_isolation_manager, IsolationManagerClass)

    def test_reset_test_state(self) -> None:
        """Test reset_test_state convenience function."""
        # Set up some state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Reset test state
        reset_test_state()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}

    def test_cleanup_test_state(self) -> None:
        """Test cleanup_test_state convenience function."""
        # Set up some state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Clean up test state
        cleanup_test_state()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}

    @pytest.mark.asyncio
    async def test_async_reset_test_state(self) -> None:
        """Test async_reset_test_state convenience function."""
        # Set up some state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Reset test state asynchronously
        await async_reset_test_state()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}

    @pytest.mark.asyncio
    async def test_async_cleanup_test_state(self) -> None:
        """Test async_cleanup_test_state convenience function."""
        # Set up some state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Clean up test state asynchronously
        await async_cleanup_test_state()

        # Verify state is cleaned
        assert error_handler.circuit_breaker_states == {}
        assert error_handler.error_counts == {}


class TestStateRestoration:
    """Test cases for state restoration functionality."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        error_handler.reset()
        self.manager = IsolationManagerClass()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        error_handler.reset()

    def test_store_and_restore_original_states(self) -> None:
        """Test storing and restoring original states."""
        # Set up initial state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5
        error_handler.last_error_times["service1"] = 123.456

        # Store original states
        self.manager._store_original_states()

        # Modify state
        error_handler.circuit_breaker_states["service1"] = False
        error_handler.error_counts["service1"] = 10
        error_handler.last_error_times["service1"] = 789.012

        # Restore original states
        self.manager._restore_original_states()

        # Verify original states are restored
        assert error_handler.circuit_breaker_states["service1"] is True
        assert error_handler.error_counts["service1"] == 5
        assert error_handler.last_error_times["service1"] == 123.456

    def test_restore_with_empty_original_states(self) -> None:
        """Test restoring when no original states were stored."""
        # Don't store any original states

        # Set up current state
        error_handler.circuit_breaker_states["service1"] = True
        error_handler.error_counts["service1"] = 5

        # Restore (should not crash)
        self.manager._restore_original_states()

        # State should remain unchanged
        assert error_handler.circuit_breaker_states["service1"] is True
        assert error_handler.error_counts["service1"] == 5
