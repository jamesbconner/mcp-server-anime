# Integration Testing Guide

This document provides comprehensive guidance for running and configuring integration tests for the mcp-server-anime project.

## Overview

Integration tests verify that the mcp-server-anime package works correctly with the real AniDB HTTP API. These tests make actual network requests and validate the complete functionality chain from HTTP requests through XML parsing to data model validation.

## Test Categories

### 1. API Integration Tests
- **Real API calls**: Tests make actual HTTP requests to the AniDB API
- **Rate limiting verification**: Ensures rate limiting works correctly with multiple requests
- **XML parsing validation**: Verifies XML parsing works with real API responses
- **Caching behavior**: Tests caching functionality with real data

### 2. Error Handling Tests
- **Invalid input validation**: Tests error handling for invalid anime IDs and search queries
- **API error responses**: Verifies proper handling of API error conditions
- **Network error simulation**: Tests retry logic and error recovery

### 3. Service Integration Tests
- **Service factory functions**: Tests service creation and initialization
- **Context manager behavior**: Verifies proper resource management
- **Configuration loading**: Tests configuration from environment variables

## Running Integration Tests

### Prerequisites

1. **Network Access**: Integration tests require internet connectivity to reach the AniDB API
2. **Poetry**: The project uses Poetry for dependency management
3. **Python 3.12+**: Required Python version

### Local Development

#### Quick Start
```bash
# Run all integration tests
pytest -m integration

# Run with verbose output
pytest -m integration -v

# Run specific test
pytest -k "test_search_anime_real_api"

# Run with coverage
pytest -m integration --cov=src --cov-report=html
```

#### Using the Helper Script
```bash
# Linux/macOS
python scripts/run_integration_tests.py

# Windows
scripts\run_integration_tests.bat

# With options
python scripts/run_integration_tests.py --verbose --coverage
```

#### Manual Configuration
```bash
# Enable integration tests
export RUN_INTEGRATION_TESTS=1

# Run tests
poetry run pytest -m integration -v
```

### CI/CD Configuration

#### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SKIP_INTEGRATION_TESTS` | `1`, `true`, `yes` | Skip integration tests completely |
| `RUN_INTEGRATION_TESTS` | `1`, `true`, `yes` | Force run integration tests in CI |
| `CI` | Any value | Automatically detected CI environment |

#### GitHub Actions Example

```yaml
name: Integration Tests

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.12"
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    - name: Run integration tests
      env:
        RUN_INTEGRATION_TESTS: "1"
      run: poetry run pytest -m integration -v
```

#### GitLab CI Example

```yaml
integration_tests:
  stage: test
  script:
    - poetry install
    - poetry run pytest -m integration -v
  variables:
    RUN_INTEGRATION_TESTS: "1"
  only:
    - main
    - schedules
  allow_failure: true
```

## Test Configuration

### Rate Limiting

Integration tests use conservative rate limiting to be respectful to the AniDB API:

```python
integration_config = AniDBConfig(
    rate_limit_delay=2.5,  # 2.5 seconds between requests
    max_retries=2,         # Fewer retries for faster execution
    timeout=15.0,          # Longer timeout for API calls
)
```

### Test Data

Tests use well-known anime that should always exist in the AniDB database:

- **Neon Genesis Evangelion** (AID: 30) - For detailed information tests
- **Akira**, **Cowboy Bebop**, **Ghost in the Shell** - For search tests

### Caching Behavior

Integration tests verify that caching works correctly:
- First request hits the API
- Subsequent identical requests use cache
- Cache timing is validated (cached requests should be >10x faster)

## Best Practices

### For Developers

1. **Run integration tests before major releases**
2. **Use the helper scripts for consistent configuration**
3. **Monitor test execution time** - integration tests should complete in <60 seconds
4. **Check network connectivity** before running tests

### For CI/CD

1. **Run integration tests on main branch only** to reduce API load
2. **Use nightly schedules** for comprehensive integration testing
3. **Allow integration test failures** without failing the entire pipeline
4. **Cache dependencies** to speed up test execution

### API Etiquette

1. **Respect rate limits** - tests include 2.5s delays between requests
2. **Use realistic test data** - don't search for nonsensical terms
3. **Limit test scope** - use small result limits (≤10 results)
4. **Monitor API health** - be prepared to skip tests if API is down

## Troubleshooting

### Common Issues

#### Network Connectivity
```bash
# Test connectivity to AniDB API
curl -I http://api.anidb.net:9001/httpapi

# Check DNS resolution
nslookup api.anidb.net
```

#### Rate Limiting Errors
If you encounter rate limiting errors:
1. Increase `rate_limit_delay` in test configuration
2. Reduce the number of concurrent tests
3. Check if other processes are using the API

#### API Unavailability
If the AniDB API is temporarily unavailable:
1. Tests will fail with network errors
2. Check AniDB status page or forums
3. Consider skipping integration tests temporarily

#### Authentication Issues
If you encounter authentication errors:
1. Verify client name and version are valid
2. Check if your IP is banned (rare)
3. Review AniDB API documentation for changes

### Debugging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run specific test with debug output
pytest -k "test_search_anime_real_api" -v -s
```

#### Inspect HTTP Requests
```python
# Add to test code for debugging
import httpx

# Enable HTTP request logging
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
```

#### Analyze Test Timing
```bash
# Show test durations
pytest -m integration --durations=0

# Profile slow tests
pytest -m integration --durations=10 -v
```

## Test Maintenance

### Regular Tasks

1. **Update test data** if anime information changes
2. **Review API rate limits** and adjust test configuration
3. **Monitor test execution time** and optimize slow tests
4. **Update CI configuration** as needed

### API Changes

If the AniDB API changes:
1. Update XML parsing tests with new response formats
2. Adjust error handling for new error codes
3. Update configuration for new API parameters
4. Review and update test assertions

### Performance Monitoring

Track integration test performance over time:
- Test execution duration
- API response times
- Cache hit rates
- Error rates

## Security Considerations

### API Keys
- Currently, AniDB HTTP API doesn't require API keys
- If authentication is added, use environment variables
- Never commit credentials to version control

### Rate Limiting
- Respect AniDB's terms of service
- Implement exponential backoff for errors
- Monitor for ban warnings in API responses

### Data Privacy
- Integration tests use only public anime data
- No personal information is transmitted
- Test data is not stored permanently

## Contributing

When adding new integration tests:

1. **Follow existing patterns** for test structure and naming
2. **Use appropriate markers** (`@pytest.mark.integration`)
3. **Include proper error handling** and cleanup
4. **Document test purpose** and expected behavior
5. **Verify tests work in CI environment**

### Test Naming Convention

```python
# Good test names
def test_search_anime_real_api()
def test_rate_limiting_behavior()
def test_invalid_anime_id_error()

# Include test category in name
def test_caching_with_real_api()
def test_concurrent_requests_serialization()
```

### Error Handling

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_example_integration(service: AniDBService) -> None:
    """Test description with expected behavior."""
    try:
        # Test implementation
        result = await service.search_anime("test")
        assert len(result) > 0
    except APIError as e:
        # Handle expected API errors
        if e.code == "RATE_LIMITED":
            pytest.skip("API rate limited - try again later")
        raise
    finally:
        # Cleanup if needed
        pass
```

## Resources

- [AniDB HTTP API Documentation](http://wiki.anidb.net/w/HTTP_API_Definition)
- [pytest Documentation](https://docs.pytest.org/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
