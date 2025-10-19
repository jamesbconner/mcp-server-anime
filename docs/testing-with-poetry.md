# Testing with Poetry - MCP Server Anime

This document describes the Poetry-based testing framework for the MCP Server Anime project, including test execution commands, coverage collection, and test isolation strategies.

> **📖 For comprehensive test maintenance procedures, troubleshooting, and best practices, see [Test Maintenance Procedures](test-maintenance-procedures.md).**

## Overview

The project uses Poetry for dependency management and test execution, providing a consistent and isolated testing environment. All test commands should be run through Poetry to ensure proper dependency resolution and environment isolation.

## Quick Start

```bash
# Install dependencies
poetry install

# Run all tests with coverage
poetry run test-coverage

# Run only unit tests
poetry run test-unit

# Run only integration tests
poetry run test-integration

# Validate test environment
poetry run python scripts/test_runner.py validate
```

## Available Poetry Scripts

The following Poetry scripts are available for test execution:

### Basic Test Commands

- `poetry run test` - Run all tests
- `poetry run test-unit` - Run unit tests only (excludes integration tests)
- `poetry run test-integration` - Run integration tests only
- `poetry run test-fast` - Run tests with minimal output and early failure
- `poetry run test-verbose` - Run tests with verbose output
- `poetry run test-quiet` - Run tests with minimal output

### Coverage Commands

- `poetry run test-coverage` - Run tests with comprehensive coverage reporting
- `poetry run test-coverage-unit` - Run unit tests with coverage (recommended for coverage targets)

### Advanced Test Runner

For more advanced testing scenarios, use the test runner script:

```bash
# Validate test environment
poetry run python scripts/test_runner.py validate

# Run all tests with coverage
poetry run python scripts/test_runner.py all

# Run unit tests only
poetry run python scripts/test_runner.py unit

# Run integration tests
poetry run python scripts/test_runner.py integration

# Generate coverage report with custom threshold
poetry run python scripts/test_runner.py coverage --fail-under 90.0

# Run specific test file
poetry run python scripts/test_runner.py specific --test-path tests/test_http_client.py

# Run only failing tests from last run
poetry run python scripts/test_runner.py failing

# Run tests with isolation checking
poetry run python scripts/test_runner.py isolation
```

## Test Categories and Markers

The project uses pytest markers to categorize tests:

### Test Markers

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may require network access)
- `@pytest.mark.slow` - Tests that take significant time to run
- `@pytest.mark.circuit_breaker_isolation` - Tests requiring circuit breaker isolation
- `@pytest.mark.complete_isolation` - Tests requiring complete state isolation

### Running Specific Test Categories

```bash
# Run only unit tests
poetry run pytest -m "unit"

# Run only integration tests
poetry run pytest -m "integration"

# Run all tests except integration
poetry run pytest -m "not integration"

# Run only slow tests
poetry run pytest -m "slow"

# Run fast tests only
poetry run pytest -m "not slow"

# Combine markers
poetry run pytest -m "unit and not slow"
```

## Coverage Reporting

The project aims for 90%+ test coverage. Coverage is collected using pytest-cov and reported in multiple formats.

### Coverage Commands

```bash
# Basic coverage report
poetry run pytest --cov=src/mcp_server_anime --cov-report=term-missing

# Comprehensive coverage with all report formats
poetry run test-coverage

# Coverage with specific threshold
poetry run pytest --cov=src/mcp_server_anime --cov-fail-under=90

# Branch coverage
poetry run pytest --cov=src/mcp_server_anime --cov-branch --cov-report=term-missing
```

### Coverage Report Formats

1. **Terminal Report** - Displayed in console with missing lines
2. **HTML Report** - Generated in `htmlcov/index.html`
3. **XML Report** - Generated as `coverage.xml` (for CI/CD)

### Coverage Targets

- **Overall Coverage**: ≥ 90%
- **Branch Coverage**: ≥ 85%
- **providers/tools.py**: ≥ 90% (currently 58.10%)
- **xml_parser.py**: ≥ 90% (currently 77.26%)

## Test Isolation

The project implements comprehensive test isolation to prevent test interference:

### Automatic Isolation

All tests automatically benefit from:

- Circuit breaker state reset between tests
- Error handler state cleanup
- Global state isolation

### Manual Isolation

For tests requiring specific isolation:

```python
import pytest
from tests.fixtures.isolation_fixtures import *

@pytest.mark.circuit_breaker_isolation
def test_with_circuit_breaker_isolation():
    # Test with circuit breaker isolation
    pass

@pytest.mark.complete_isolation
def test_with_complete_isolation():
    # Test with complete state isolation
    pass

def test_with_isolation_manager(isolated_test_environment):
    # Use isolation manager fixture
    isolated_test_environment.simulate_errors("service", 5)
    assert isolated_test_environment.is_circuit_breaker_active("service")
```

### Available Isolation Fixtures

- `reset_circuit_breakers` - Reset circuit breaker states
- `isolate_error_handler` - Comprehensive error handler isolation
- `test_isolation` - Test isolation manager instance
- `clean_error_handler` - Clean error handler state
- `circuit_breaker_manager` - Circuit breaker management
- `isolated_test_environment` - Complete test isolation
- `async_isolated_test_environment` - Async test isolation
- `mock_circuit_breaker_state` - Mock circuit breaker state
- `simulate_circuit_breaker_errors` - Error simulation function
- `error_handler_spy` - Monitor error handler calls

## Integration Tests

Integration tests require special handling as they may interact with external services.

### Running Integration Tests

```bash
# Run integration tests (requires network)
poetry run test-integration

# Run integration tests with explicit enablement
RUN_INTEGRATION_TESTS=1 poetry run pytest -m integration

# Skip integration tests
SKIP_INTEGRATION_TESTS=1 poetry run pytest
```

### Integration Test Environment Variables

- `RUN_INTEGRATION_TESTS=1` - Force run integration tests
- `SKIP_INTEGRATION_TESTS=1` - Force skip integration tests
- `CI=1` - Detected CI environment (skips integration by default)

### CI/CD Integration Test Handling

In CI/CD environments, integration tests are skipped by default unless explicitly enabled:

```yaml
# GitHub Actions example
- name: Run unit tests
  run: poetry run test-coverage-unit

- name: Run integration tests
  run: poetry run test-integration
  env:
    RUN_INTEGRATION_TESTS: "1"
```

## Debugging and Troubleshooting

### Common Issues

1. **Circuit Breaker Interference**
   ```bash
   # Run with isolation checking
   poetry run python scripts/test_runner.py isolation
   ```

2. **Test Discovery Issues**
   ```bash
   # Validate test environment
   poetry run python scripts/test_runner.py validate
   
   # Check test discovery
   poetry run pytest --collect-only
   ```

3. **Coverage Issues**
   ```bash
   # Generate detailed coverage report
   poetry run test-coverage
   
   # Check specific file coverage
   poetry run pytest --cov=src/mcp_server_anime/http_client.py --cov-report=term-missing
   ```

### Debugging Test Failures

```bash
# Run with verbose output and full tracebacks
poetry run pytest -v --tb=long

# Run specific failing test
poetry run pytest tests/test_http_client.py::test_rate_limiting_applied -v

# Run only failing tests from last run
poetry run python scripts/test_runner.py failing

# Stop on first failure
poetry run pytest --maxfail=1 -v
```

### Performance Analysis

```bash
# Show slowest tests
poetry run pytest --durations=10

# Show all test durations
poetry run pytest --durations=0

# Profile test execution
poetry run pytest --profile
```

## Best Practices

### Test Execution

1. **Always use Poetry** - Run tests through Poetry for consistent environment
2. **Use appropriate markers** - Mark tests with appropriate categories
3. **Isolate tests** - Use isolation fixtures for tests that modify global state
4. **Check coverage** - Regularly run coverage reports to identify gaps

### Test Development

1. **Write isolated tests** - Tests should not depend on execution order
2. **Use fixtures** - Leverage isolation fixtures for clean test environments
3. **Mock external dependencies** - Use mocks for external API calls
4. **Test error conditions** - Include tests for error handling and edge cases

### CI/CD Integration

1. **Separate test stages** - Run unit and integration tests separately
2. **Use coverage thresholds** - Fail builds if coverage drops below targets
3. **Cache dependencies** - Cache Poetry dependencies for faster builds
4. **Parallel execution** - Use pytest-xdist for parallel test execution

## Configuration Files

### pytest.ini

The main pytest configuration is in `pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=src/mcp_server_anime
    --cov-report=term-missing:skip-covered
    --cov-branch
    --maxfail=5

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    circuit_breaker_isolation: Tests requiring circuit breaker isolation
    complete_isolation: Tests requiring complete isolation
```

### pyproject.toml

Poetry configuration and tool settings are in `pyproject.toml`:

```toml
[tool.poetry.scripts]
test = "pytest"
test-unit = "pytest -m 'not integration'"
test-integration = "pytest -m integration"
test-coverage = "pytest --cov=src/mcp_server_anime --cov-report=term-missing --cov-report=html --cov-report=xml"

[tool.coverage.run]
source = ["src/mcp_server_anime"]
branch = true

[tool.coverage.report]
fail_under = 90.0
show_missing = true
```

## Examples

### Basic Test Execution

```bash
# Development workflow
poetry install                    # Install dependencies
poetry run test-coverage-unit    # Run unit tests with coverage
poetry run test-integration      # Run integration tests

# Check specific coverage
poetry run pytest tests/test_http_client.py --cov=src/mcp_server_anime/http_client.py --cov-report=term-missing
```

### Advanced Test Scenarios

```bash
# Test isolation debugging
poetry run python scripts/test_runner.py isolation

# Coverage improvement workflow
poetry run test-coverage --fail-under 90
poetry run pytest tests/test_providers_tools.py --cov=src/mcp_server_anime/providers/tools.py --cov-report=term-missing

# Integration test development
RUN_INTEGRATION_TESTS=1 poetry run pytest tests/test_integration.py -v
```

### CI/CD Pipeline Example

```bash
# Validation stage
poetry run python scripts/test_runner.py validate

# Unit test stage
poetry run test-coverage-unit --fail-under 90

# Integration test stage (if enabled)
poetry run test-integration

# Coverage reporting
poetry run coverage xml  # Generate XML report for CI
```

This testing framework provides comprehensive test execution capabilities while maintaining proper isolation and coverage reporting through Poetry's dependency management system.