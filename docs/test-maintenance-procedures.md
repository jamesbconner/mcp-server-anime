# Test Maintenance Procedures

This document provides comprehensive guidelines for maintaining the test suite of the MCP Server Anime project, including running tests through Poetry, maintaining test coverage, and managing test isolation.

## Table of Contents

1. [Running Tests Through Poetry](#running-tests-through-poetry)
2. [Test Isolation Best Practices](#test-isolation-best-practices)
3. [Maintaining Test Coverage](#maintaining-test-coverage)
4. [Mock Management Strategies](#mock-management-strategies)
5. [Troubleshooting Common Issues](#troubleshooting-common-issues)
6. [Coverage Targets and Validation](#coverage-targets-and-validation)

## Running Tests Through Poetry

### Basic Test Execution

All tests should be run through Poetry to ensure consistent dependency management and virtual environment isolation:

```bash
# Run all tests
poetry run pytest

# Run tests with verbose output
poetry run pytest -v

# Run tests with short traceback format
poetry run pytest --tb=short

# Run specific test file
poetry run pytest tests/test_anidb_service.py

# Run specific test class
poetry run pytest tests/test_anidb_service.py::TestAniDBService

# Run specific test method
poetry run pytest tests/test_anidb_service.py::TestAniDBService::test_init_with_config
```

### Coverage Collection

Generate coverage reports using Poetry commands:

```bash
# Run tests with coverage and terminal report
poetry run pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
poetry run pytest --cov=src --cov-report=html

# Generate XML coverage report (for CI/CD)
poetry run pytest --cov=src --cov-report=xml

# Generate all report formats
poetry run pytest --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing
```

### Test Categories and Markers

Run specific categories of tests using markers:

```bash
# Run only unit tests (exclude integration tests)
poetry run pytest -m "not integration"

# Run only integration tests
poetry run pytest -m integration

# Run tests with specific markers
poetry run pytest -m "slow"
poetry run pytest -m "circuit_breaker"
```

### Performance and Debugging

```bash
# Run tests with performance timing
poetry run pytest --durations=10

# Run tests in parallel (if pytest-xdist is installed)
poetry run pytest -n auto

# Run tests with detailed output for debugging
poetry run pytest -vvv --tb=long

# Stop on first failure
poetry run pytest -x
```

## Test Isolation Best Practices

### Circuit Breaker Management

The project uses circuit breakers for error handling, which can interfere with tests if not properly isolated:

1. **Always use test isolation fixtures**: Tests should use the `isolated_test_environment` fixture to ensure clean state between tests.

2. **Reset circuit breakers between tests**: The test isolation system automatically resets circuit breaker states, but manual reset may be needed in some cases:

```python
from tests.fixtures.isolation_fixtures import reset_circuit_breakers

@pytest.fixture(autouse=True)
def reset_state():
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()
```

3. **Avoid shared global state**: Tests should not rely on or modify global state that could affect other tests.

### Test Environment Setup

Each test should have a clean environment:

```python
import pytest
from tests.fixtures.isolation_fixtures import isolated_test_environment

class TestMyFeature:
    @pytest.fixture(autouse=True)
    def setup(self, isolated_test_environment):
        # Test setup code here
        yield
        # Test cleanup code here
```

### Mock Isolation

Ensure mocks are properly isolated between tests:

```python
from unittest.mock import patch, MagicMock

class TestWithMocks:
    def test_with_mock(self):
        with patch('module.function') as mock_func:
            mock_func.return_value = "test_value"
            # Test code here
            # Mock is automatically cleaned up after the with block
```

## Maintaining Test Coverage

### Coverage Targets

The project maintains the following coverage targets:

- **Overall line coverage**: ≥ 90%
- **Branch coverage**: ≥ 85%
- **Individual module targets**:
  - `providers/tools.py`: ≥ 90%
  - `xml_parser.py`: ≥ 90%
  - All other modules: ≥ 85%

### Monitoring Coverage

1. **Regular coverage checks**: Run coverage analysis regularly during development:

```bash
poetry run pytest --cov=src --cov-report=term-missing --cov-fail-under=90
```

2. **Identify coverage gaps**: Use the HTML report to identify specific lines needing coverage:

```bash
poetry run pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

3. **Branch coverage analysis**: Focus on conditional logic and error handling paths:

```bash
poetry run pytest --cov=src --cov-branch --cov-report=term-missing
```

### Adding Tests for Uncovered Code

When adding tests for uncovered code:

1. **Identify the uncovered lines** using the coverage report
2. **Understand the code path** - what conditions trigger this code?
3. **Write focused tests** that specifically exercise the uncovered paths
4. **Test both success and failure scenarios**
5. **Verify the coverage improvement** after adding tests

Example of adding coverage for error handling:

```python
def test_error_handling_path(self):
    """Test the error handling path that was previously uncovered."""
    with pytest.raises(SpecificException):
        # Code that triggers the error condition
        function_under_test(invalid_input)
```

## Mock Management Strategies

### Integration Test Mocking

For integration tests, use comprehensive mocking to avoid external dependencies:

```python
from tests.fixtures.api_mocks import setup_common_mocks, mock_http_get
from unittest.mock import patch

class TestIntegration:
    async def test_with_api_mocks(self, service):
        # Set up comprehensive mocks
        setup_common_mocks()
        
        # Mock the HTTP client
        with patch('src.mcp_server_anime.http_client.HTTPClient.get') as mock_get:
            async def mock_get_response(url: str, params: dict = None, **kwargs):
                mock_response = await mock_http_get(url, params, **kwargs)
                
                response = AsyncMock()
                response.status_code = mock_response.status_code
                response.text = mock_response.content
                response.headers = mock_response.headers
                return response
            
            mock_get.side_effect = mock_get_response
            
            # Test code here
            result = await service.search_anime("test query")
            assert len(result) > 0
```

### Mock Data Management

1. **Centralized mock data**: Keep mock responses in `tests/fixtures/api_mocks.py`
2. **Realistic mock data**: Use realistic data structures that match actual API responses
3. **Reusable mocks**: Create reusable mock setups for common scenarios
4. **Mock validation**: Ensure mocks accurately represent real API behavior

### Mock Cleanup

Always ensure mocks are properly cleaned up:

```python
class TestWithMocks:
    def test_with_cleanup(self):
        with patch('module.function') as mock_func:
            # Test code
            pass
        # Mock is automatically cleaned up here
    
    @patch('module.function')
    def test_with_decorator(self, mock_func):
        # Test code
        pass
        # Mock is automatically cleaned up after method
```

## Troubleshooting Common Issues

### Circuit Breaker Interference

**Problem**: Tests fail with "Circuit breaker is active" errors.

**Solution**: 
1. Use the `isolated_test_environment` fixture
2. Reset circuit breakers manually if needed:

```python
from src.mcp_server_anime.core.error_handler import get_error_handler

def test_with_circuit_breaker_reset():
    error_handler = get_error_handler()
    error_handler.reset_circuit_breaker()  # Reset specific service
    # or
    error_handler.reset_all_circuit_breakers()  # Reset all
```

### Mock Configuration Issues

**Problem**: Tests fail because mocks aren't properly configured.

**Solution**:
1. Ensure mocks are set up before the code under test runs
2. Use the correct mock path (where the function is imported, not where it's defined)
3. Verify mock responses match expected data structures

### Test Isolation Failures

**Problem**: Tests pass individually but fail when run together.

**Solution**:
1. Use `isolated_test_environment` fixture
2. Avoid global state modifications
3. Clean up resources in test teardown
4. Use fresh instances for each test

### Coverage Reporting Issues

**Problem**: Coverage reports show incorrect or missing coverage.

**Solution**:
1. Ensure tests are run through Poetry: `poetry run pytest`
2. Use correct source path: `--cov=src`
3. Check for import issues that prevent code execution
4. Verify test discovery is working correctly

## Coverage Targets and Validation

### Automated Coverage Validation

Set up automated coverage validation in CI/CD:

```bash
# Fail if coverage is below threshold
poetry run pytest --cov=src --cov-fail-under=90

# Generate reports for CI
poetry run pytest --cov=src --cov-report=xml --cov-report=term
```

### Coverage Maintenance Workflow

1. **Before making changes**: Run coverage to establish baseline
2. **During development**: Monitor coverage impact of changes
3. **Before committing**: Ensure coverage targets are met
4. **In code review**: Review coverage changes and new tests

### Coverage Quality Guidelines

1. **Focus on meaningful coverage**: Don't just aim for high percentages
2. **Test edge cases**: Ensure error conditions and boundary cases are covered
3. **Branch coverage**: Pay attention to conditional logic coverage
4. **Integration coverage**: Ensure end-to-end scenarios are tested

### Regular Maintenance Tasks

1. **Weekly**: Review coverage reports and identify gaps
2. **Monthly**: Update mock data to reflect API changes
3. **Quarterly**: Review and update test isolation mechanisms
4. **Before releases**: Comprehensive test suite validation

## Best Practices Summary

1. **Always use Poetry** for test execution and dependency management
2. **Maintain test isolation** using provided fixtures and cleanup mechanisms
3. **Monitor coverage continuously** and address gaps promptly
4. **Use realistic mocks** that accurately represent external dependencies
5. **Document test scenarios** and maintain clear test organization
6. **Regular maintenance** of test infrastructure and mock data
7. **Validate coverage targets** before code changes are merged

## Additional Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Project Testing Configuration](../pytest.ini)
- [API Mock Fixtures](../tests/fixtures/api_mocks.py)
- [Test Isolation Utilities](../tests/fixtures/isolation_fixtures.py)