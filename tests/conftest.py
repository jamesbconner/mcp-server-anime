"""Pytest configuration for mcp-server-anime tests.

This module provides shared fixtures and configuration for all tests,
including special handling for integration tests and CI environments.
"""

import os
from collections.abc import Generator
from typing import Any

import pytest

from src.mcp_server_anime.providers.anidb.config import AniDBConfig

# Import database mock fixtures to make them available to all tests
from tests.fixtures.database_mocks import *

# Import isolation fixtures to make them available to all tests
from tests.providers.anidb.fixtures.isolation_fixtures import *


@pytest.fixture
def enhanced_test_config() -> AniDBConfig:
    """Provide an enhanced test configuration with database integration support.

    This configuration includes settings optimized for testing the new
    database integration components.
    """
    return AniDBConfig(
        client_name="mcp-server-anidb-enhanced-test",
        client_version=1,
        protocol_version=1,
        base_url="http://test.api.com/httpapi",
        rate_limit_delay=0.05,  # Very fast for unit tests
        max_retries=1,  # Minimal retries for faster tests
        cache_ttl=60,  # Short cache for testing
        timeout=2.0,  # Short timeout for faster tests
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires network access and real API calls)",
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (may take several seconds to complete)"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Modify test collection to add markers and handle CI configuration."""
    for item in items:
        # Add slow marker to all integration tests
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)

        # Skip integration tests if configured to do so
        if "integration" in item.keywords and should_skip_integration_tests():
            skip_reason = (
                "Integration tests skipped (SKIP_INTEGRATION_TESTS=1 or CI environment)"
            )
            item.add_marker(pytest.mark.skip(reason=skip_reason))


def should_skip_integration_tests() -> bool:
    """Determine if integration tests should be skipped.

    Integration tests are skipped if:
    1. SKIP_INTEGRATION_TESTS environment variable is set to 1/true/yes
    2. Running in a CI environment without explicit integration test enablement

    Returns:
        True if integration tests should be skipped, False otherwise.
    """
    # Explicit skip configuration
    skip_env = os.getenv("SKIP_INTEGRATION_TESTS", "").lower()
    if skip_env in ("1", "true", "yes"):
        return True

    # Check if explicitly enabled in CI
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "").lower()
    if run_integration in ("1", "true", "yes"):
        return False

    # Check for CI environment indicators
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "TRAVIS",
        "CIRCLECI",
        "BUILDKITE",
    ]

    is_ci = any(os.getenv(var) for var in ci_indicators)

    # Skip integration tests in CI by default (unless explicitly enabled)
    return is_ci


@pytest.fixture(autouse=True)
def reset_error_handler() -> Generator[None, None, None]:
    """Reset the error handler state between tests.

    This fixture ensures that circuit breakers and error counts
    are reset between tests to prevent test interference.

    Note: This fixture is being enhanced by the isolation fixtures
    in tests/fixtures/isolation_fixtures.py for more comprehensive
    test isolation.
    """
    from src.mcp_server_anime.core.error_handler import error_handler

    # Reset before test
    error_handler.reset()

    yield

    # Reset after test
    error_handler.reset()


@pytest.fixture
def test_config() -> AniDBConfig:
    """Provide a test configuration for unit tests.

    This configuration uses faster settings suitable for unit tests
    with mocked HTTP calls.
    """
    return AniDBConfig(
        client_name="mcp-server-anidb-test",
        client_version=1,
        protocol_version=1,
        base_url="http://test.api.com/httpapi",
        rate_limit_delay=0.1,  # Fast for unit tests
        max_retries=2,
        cache_ttl=300,
        timeout=5.0,
    )


@pytest.fixture
def integration_config() -> AniDBConfig:
    """Provide a configuration optimized for integration tests.

    This configuration uses more conservative settings to be respectful
    to the real AniDB API during integration testing.
    """
    return AniDBConfig(
        client_name="mcp-server-anidb-integration-test",
        client_version=1,
        protocol_version=1,
        rate_limit_delay=2.5,  # Be extra respectful during testing
        max_retries=2,
        cache_ttl=300,
        timeout=15.0,  # Longer timeout for potentially slow API
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[Any, None, None]:
    """Create an event loop for the test session.

    This fixture ensures that async tests have access to an event loop
    and that the loop is properly cleaned up after tests complete.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        # Clean up any remaining tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Set up individual test runs with appropriate configuration."""
    # Log test information for integration tests
    if "integration" in item.keywords:
        print(f"\n🔗 Running integration test: {item.name}")

        # Warn about network requirements
        if not should_skip_integration_tests():
            print("⚠️  This test requires network access and will make real API calls")


def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Clean up after individual test runs."""
    if "integration" in item.keywords and not should_skip_integration_tests():
        print(f"✅ Integration test completed: {item.name}")


# Custom pytest command line options
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options for test configuration."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires network access)",
    )
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow tests (including integration tests)",
    )


# Note: pytest_configure_node is only available with pytest-xdist
# def pytest_configure_node(node: Any) -> None:
#     """Configure test nodes for distributed testing."""
#     # This can be used for pytest-xdist configuration if needed
#     pass


# Environment variable documentation for CI/CD
"""
Environment Variables for CI/CD Configuration:

SKIP_INTEGRATION_TESTS: Set to "1", "true", or "yes" to skip integration tests
RUN_INTEGRATION_TESTS: Set to "1", "true", or "yes" to force run integration tests in CI
CI: Automatically detected CI environment indicator
GITHUB_ACTIONS: GitHub Actions environment indicator
GITLAB_CI: GitLab CI environment indicator

Example CI configurations:

GitHub Actions:
  - name: Run unit tests
    run: pytest -m "not integration"

  - name: Run integration tests
    run: pytest -m integration
    env:
      RUN_INTEGRATION_TESTS: "1"

GitLab CI:
  unit_tests:
    script:
      - pytest -m "not integration"

  integration_tests:
    script:
      - pytest -m integration
    variables:
      RUN_INTEGRATION_TESTS: "1"
    only:
      - main
      - develop

Local development:
  # Run all tests including integration
  pytest

  # Run only unit tests
  pytest -m "not integration"

  # Run only integration tests
  pytest -m integration

  # Skip slow tests
  pytest --skip-slow
"""
