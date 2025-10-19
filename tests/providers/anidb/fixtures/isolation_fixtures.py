"""Pytest fixtures for test isolation and circuit breaker management.

This module provides pytest fixtures that ensure proper test isolation
by managing circuit breaker states and global state cleanup.
"""

from __future__ import annotations

from collections.abc import Generator

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


@pytest.fixture(autouse=True)
def reset_circuit_breakers() -> Generator[None, None, None]:
    """Automatically reset circuit breakers before and after each test.

    This fixture ensures that circuit breaker states don't interfere
    between tests by resetting them before and after each test execution.
    """
    # Reset before test
    error_handler.reset()

    yield

    # Reset after test
    error_handler.reset()


@pytest.fixture(autouse=True)
def isolate_error_handler() -> Generator[None, None, None]:
    """Isolate error handler state between tests.

    This fixture provides comprehensive error handler state isolation,
    ensuring that error counts, circuit breaker states, and timing
    information don't leak between tests.
    """
    # Store original state
    original_circuit_breaker_states = error_handler.circuit_breaker_states.copy()
    original_error_counts = error_handler.error_counts.copy()
    original_last_error_times = error_handler.last_error_times.copy()

    # Reset to clean state
    error_handler.reset()

    yield

    # Restore original state (optional - usually we want clean state)
    # For most tests, we want to end with clean state, but this can be
    # uncommented if specific tests need state restoration
    # error_handler.circuit_breaker_states = original_circuit_breaker_states
    # error_handler.error_counts = original_error_counts
    # error_handler.last_error_times = original_last_error_times

    # Ensure clean state after test
    error_handler.reset()


@pytest.fixture
def test_isolation() -> IsolationManagerClass:
    """Provide a test isolation manager instance for tests.

    Returns:
        TestIsolationManager instance for managing test isolation
    """
    manager = IsolationManagerClass()
    manager.setup_test_environment()

    yield manager

    manager.teardown_test_environment()


@pytest.fixture
def clean_error_handler() -> Generator[None, None, None]:
    """Provide a completely clean error handler for tests.

    This fixture ensures the error handler starts in a completely
    clean state and is reset after the test completes.
    """
    # Ensure clean state before test
    error_handler.reset()

    yield

    # Ensure clean state after test
    error_handler.reset()


@pytest.fixture
def circuit_breaker_manager() -> Generator[IsolationManagerClass, None, None]:
    """Provide a circuit breaker manager for tests that need to manipulate circuit breaker state.

    This fixture provides a TestIsolationManager instance specifically
    configured for circuit breaker testing scenarios.

    Returns:
        TestIsolationManager instance for circuit breaker management
    """
    manager = IsolationManagerClass()

    # Ensure clean state before test
    manager.reset_circuit_breakers()

    yield manager

    # Clean up after test
    manager.reset_circuit_breakers()


@pytest.fixture(scope="function")
def isolated_test_environment() -> Generator[IsolationManagerClass, None, None]:
    """Provide a completely isolated test environment.

    This fixture sets up a completely isolated test environment,
    including circuit breaker reset, global state cleanup, and
    proper teardown after test completion.

    Returns:
        TestIsolationManager instance for the isolated environment
    """
    manager = IsolationManagerClass()

    # Set up isolated environment
    manager.setup_test_environment()

    yield manager

    # Tear down isolated environment
    manager.teardown_test_environment()


@pytest.fixture
async def async_isolated_test_environment() -> Generator[
    IsolationManagerClass, None, None
]:
    """Provide an async isolated test environment.

    This fixture is similar to isolated_test_environment but designed
    for async tests, ensuring proper async cleanup.

    Returns:
        TestIsolationManager instance for the isolated async environment
    """
    manager = IsolationManagerClass()

    # Set up isolated environment asynchronously
    await async_reset_test_state()

    yield manager

    # Tear down isolated environment asynchronously
    await async_cleanup_test_state()


@pytest.fixture
def mock_circuit_breaker_state() -> Generator[dict[str, bool], None, None]:
    """Provide a mock circuit breaker state for testing.

    This fixture allows tests to set up specific circuit breaker
    states for testing scenarios.

    Returns:
        Dictionary representing circuit breaker states
    """
    # Store original state
    original_states = error_handler.circuit_breaker_states.copy()

    # Provide empty state for test to populate
    mock_states: dict[str, bool] = {}
    error_handler.circuit_breaker_states = mock_states

    yield mock_states

    # Restore original state
    error_handler.circuit_breaker_states = original_states


@pytest.fixture
def simulate_circuit_breaker_errors():
    """Provide a function to simulate circuit breaker errors for testing.

    Returns:
        Function that can simulate errors for circuit breaker testing
    """

    def simulate_errors(service: str, error_count: int) -> None:
        """Simulate errors for a service to trigger circuit breaker.

        Args:
            service: Service name
            error_count: Number of errors to simulate
        """
        test_isolation_manager.simulate_errors(service, error_count)

    return simulate_errors


@pytest.fixture(autouse=True, scope="function")
def ensure_test_isolation() -> Generator[None, None, None]:
    """Ensure comprehensive test isolation for all tests.

    This autouse fixture provides the highest level of test isolation,
    ensuring that no test state leaks between test functions.
    """
    # Reset all state before test
    reset_test_state()

    yield

    # Clean up all state after test
    cleanup_test_state()


@pytest.fixture
def database_isolation() -> Generator[None, None, None]:
    """Provide database component isolation for tests.

    This fixture ensures that database components are properly
    isolated between tests, preventing state leakage.
    """
    # Store original state (if any global database state exists)
    # For now, we'll just ensure clean state

    yield

    # Clean up any database-related global state
    # This would reset any global database connections, caches, etc.
    pass


@pytest.fixture
def enhanced_isolation(
    reset_circuit_breakers: Generator[None, None, None],
    database_isolation: Generator[None, None, None],
) -> Generator[None, None, None]:
    """Provide enhanced isolation including database components.

    This fixture combines circuit breaker isolation with database
    component isolation for comprehensive test isolation.
    """
    yield


@pytest.fixture
def error_handler_spy():
    """Provide a spy for monitoring error handler calls.

    This fixture allows tests to monitor calls to the error handler
    without affecting its functionality.

    Returns:
        Mock object that can be used to verify error handler calls
    """
    from unittest.mock import Mock, patch

    spy = Mock()

    # Patch error handler methods to add spying
    original_record_error = error_handler.record_error
    original_activate_circuit_breaker = error_handler.activate_circuit_breaker
    original_reset_circuit_breaker = error_handler.reset_circuit_breaker

    def spy_record_error(service: str) -> None:
        spy.record_error(service)
        return original_record_error(service)

    def spy_activate_circuit_breaker(service: str) -> None:
        spy.activate_circuit_breaker(service)
        return original_activate_circuit_breaker(service)

    def spy_reset_circuit_breaker(service: str) -> None:
        spy.reset_circuit_breaker(service)
        return original_reset_circuit_breaker(service)

    with (
        patch.object(error_handler, "record_error", side_effect=spy_record_error),
        patch.object(
            error_handler,
            "activate_circuit_breaker",
            side_effect=spy_activate_circuit_breaker,
        ),
        patch.object(
            error_handler,
            "reset_circuit_breaker",
            side_effect=spy_reset_circuit_breaker,
        ),
    ):
        yield spy


# Marker for tests that require circuit breaker isolation
pytest_circuit_breaker_isolation = pytest.mark.circuit_breaker_isolation


# Marker for tests that require complete isolation
pytest_complete_isolation = pytest.mark.complete_isolation


def pytest_configure(config):
    """Configure pytest with custom markers for isolation."""
    config.addinivalue_line(
        "markers",
        "circuit_breaker_isolation: mark test as requiring circuit breaker isolation",
    )
    config.addinivalue_line(
        "markers", "complete_isolation: mark test as requiring complete test isolation"
    )


def pytest_runtest_setup(item):
    """Set up test isolation based on markers."""
    if item.get_closest_marker("circuit_breaker_isolation"):
        # Ensure circuit breaker isolation for marked tests
        error_handler.reset()

    if item.get_closest_marker("complete_isolation"):
        # Ensure complete isolation for marked tests
        reset_test_state()


def pytest_runtest_teardown(item):
    """Clean up test isolation after test completion."""
    if item.get_closest_marker("circuit_breaker_isolation"):
        # Clean up circuit breaker state after marked tests
        error_handler.reset()

    if item.get_closest_marker("complete_isolation"):
        # Clean up complete state after marked tests
        cleanup_test_state()
