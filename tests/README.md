# Testing Guide for mcp-server-anime

This directory contains comprehensive tests for the mcp-server-anime project, including unit tests, integration tests, and mock-based integration tests.

## Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and fixtures
├── test_integration.py          # Real API integration tests
├── test_integration_mock.py     # Mock-based integration tests
├── test_*.py                    # Unit tests for individual modules
└── fixtures/                    # Test data and fixtures
```

## Test Categories

### Unit Tests
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1 second per test)
- **Dependencies**: None (use mocks)
- **Run with**: `pytest -m "not integration"`

### Integration Tests (Real API)
- **Purpose**: Test complete functionality with real AniDB API
- **Speed**: Slow (2-5 seconds per test due to rate limiting)
- **Dependencies**: Network access, AniDB API availability
- **Run with**: `pytest -m integration`

### Mock Integration Tests
- **Purpose**: Test integration flow with mocked API responses
- **Speed**: Medium (< 1 second per test)
- **Dependencies**: None (use mocks)
- **Run with**: `pytest tests/test_integration_mock.py`

## Running Tests

### Quick Commands

```bash
# Run all tests except real integration tests
pytest -m "not integration"

# Run only unit tests (fastest)
pytest tests/test_*.py -k "not integration"

# Run mock integration tests
pytest tests/test_integration_mock.py

# Run real integration tests (requires network)
pytest -m integration

# Run all tests with coverage
pytest --cov=src --cov-report=html
```

### Environment Variables

| Variable | Effect |
|----------|--------|
| `SKIP_INTEGRATION_TESTS=1` | Skip all real integration tests |
| `RUN_INTEGRATION_TESTS=1` | Force run integration tests in CI |

### Helper Scripts

```bash
# Linux/macOS
python scripts/run_integration_tests.py --verbose

# Windows
scripts\run_integration_tests.bat --verbose
```

## Test Configuration

### CI/CD Environments

Integration tests are automatically skipped in CI environments unless explicitly enabled:

```yaml
# GitHub Actions example
- name: Run integration tests
  env:
    RUN_INTEGRATION_TESTS: "1"
  run: pytest -m integration
```

### Local Development

For local development, integration tests run by default but can be skipped:

```bash
# Skip integration tests locally
export SKIP_INTEGRATION_TESTS=1
pytest
```

## Test Data

### Real API Tests
- Use well-known anime that should always exist
- Respect API rate limits (2.5s between requests)
- Handle API errors gracefully

### Mock Tests
- Use realistic XML responses based on AniDB API format
- Test complete integration flow without network calls
- Verify error handling and edge cases

## Troubleshooting

### Common Issues

1. **Integration tests failing with network errors**
   - Check internet connectivity
   - Verify AniDB API is accessible
   - Consider using mock tests instead

2. **Rate limiting errors**
   - Increase `rate_limit_delay` in test configuration
   - Run fewer concurrent tests
   - Use mock tests for faster feedback

3. **Tests timing out**
   - Check network latency to AniDB API
   - Increase timeout values in test configuration
   - Use mock tests for consistent timing

### Debug Mode

```bash
# Run with debug logging
pytest -v -s --log-cli-level=DEBUG

# Run specific test with full output
pytest tests/test_integration.py::TestAniDBAPIIntegration::test_search_anime_real_api -v -s
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_<functionality>_<scenario>`
2. **Use appropriate markers**: `@pytest.mark.integration` for real API tests
3. **Include docstrings**: Explain what the test verifies
4. **Handle errors gracefully**: Use appropriate exception handling
5. **Clean up resources**: Use fixtures and context managers

### Test Template

```python
@pytest.mark.asyncio
async def test_new_functionality(service: AniDBService) -> None:
    """Test description explaining what is being verified.
    
    This test verifies that:
    - Specific behavior 1
    - Specific behavior 2
    - Error handling works correctly
    """
    # Arrange
    test_data = "test input"
    
    # Act
    result = await service.some_method(test_data)
    
    # Assert
    assert result is not None
    assert len(result) > 0
```

## Performance Guidelines

### Test Execution Time Targets

- Unit tests: < 0.1 seconds each
- Mock integration tests: < 1 second each
- Real integration tests: < 10 seconds each (including rate limiting)

### Optimization Tips

1. **Use fixtures** for expensive setup operations
2. **Mock external dependencies** in unit tests
3. **Cache test data** when possible
4. **Run tests in parallel** with `pytest-xdist` (for unit tests only)

```bash
# Run unit tests in parallel
pytest -m "not integration" -n auto
```

## Coverage Goals

- **Overall coverage**: > 90%
- **Critical paths**: 100% (error handling, data validation)
- **Integration coverage**: Verify all public APIs work end-to-end

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```