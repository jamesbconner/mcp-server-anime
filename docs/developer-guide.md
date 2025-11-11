# Developer Guide

## Quick Start

### Prerequisites
- Python 3.12+
- Poetry (for dependency management)

### Setup

```bash
# Automated setup (recommended)
make setup
# or
poetry run python scripts/dev_tools.py setup

# Manual setup
poetry install --extras dev
poetry run pre-commit install

# Validate environment
make validate-env
# or
poetry run python scripts/dev_tools.py validate
```

## Development Workflow

### Running Tests

```bash
# Run unit tests only (fast)
make test-unit
# or
poetry run pytest -m "not integration"

# Run all tests including integration
make test-all
# or
poetry run pytest

# Run with coverage report
make coverage
# or
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/core/test_cache.py

# Run tests matching a pattern
poetry run pytest -k "test_cache"

# Run with verbose output
poetry run pytest -v

# Show slowest 10 tests
poetry run pytest --durations=10
```

### Code Quality

```bash
# Format code
make format
# or
poetry run ruff format .

# Lint code
make lint
# or
poetry run ruff check .

# Auto-fix linting issues
make lint-fix
# or
poetry run ruff check --fix .

# Type checking
make type-check
# or
poetry run mypy src

# Security scanning
make security
# or
poetry run bandit -r src

# Run all quality checks
make quality
```

### Pre-commit Hooks

```bash
# Run all pre-commit hooks manually
make pre-commit
# or
poetry run pre-commit run --all-files

# Update pre-commit hooks
poetry run pre-commit autoupdate
```

## Project Structure

```
mcp-server-anime/
├── src/mcp_server_anime/     # Main source code
│   ├── core/                 # Core functionality (cache, HTTP, errors)
│   ├── providers/            # Data provider implementations
│   │   └── anidb/           # AniDB provider
│   ├── config/              # Configuration management
│   ├── cli/                 # CLI tools
│   ├── server.py            # Simple MCP server
│   └── extensible_server.py # Multi-provider server
├── tests/                    # Test suite
│   ├── core/                # Core tests
│   ├── providers/           # Provider tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Pytest fixtures
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── pyproject.toml           # Project configuration (Poetry, tools)
├── Makefile                 # Development commands
└── README.md                # Project overview
```

## Configuration

All tool configuration is in `pyproject.toml`:
- `[tool.poetry]` - Dependencies and project metadata
- `[tool.pytest.ini_options]` - Test configuration
- `[tool.coverage]` - Coverage settings
- `[tool.ruff]` - Linting and formatting
- `[tool.mypy]` - Type checking
- `[tool.bandit]` - Security scanning

## Test Markers

Use markers to organize and run specific test categories:

```bash
# Unit tests (no external dependencies)
poetry run pytest -m unit

# Integration tests (may require network)
poetry run pytest -m integration

# Slow tests
poetry run pytest -m slow

# Smoke tests (basic functionality)
poetry run pytest -m smoke

# Cache-related tests
poetry run pytest -m cache

# Provider tests
poetry run pytest -m providers
```

Available markers:
- `unit` - Unit tests that don't require external dependencies
- `integration` - Integration tests that may require network access
- `slow` - Tests that take a long time to run
- `smoke` - Basic smoke tests for core functionality
- `api` - Tests that interact with external APIs
- `cache` - Tests related to caching functionality
- `error` - Tests focused on error handling
- `validation` - Tests for input validation
- `xml` - Tests for XML parsing functionality
- `http` - Tests for HTTP client functionality
- `tools` - Tests for MCP tools
- `service` - Tests for service layer functionality
- `config` - Tests for configuration management
- `models` - Tests for data models
- `server` - Tests for server functionality
- `providers` - Tests for provider system
- `database` - Tests for database integration
- `cli` - Tests for command-line interface
- `analytics` - Tests for analytics and logging

## Common Tasks

### Adding a New Dependency

```bash
# Add runtime dependency
poetry add package-name

# Add development dependency (to [project.optional-dependencies])
# Note: With PEP 621 format, manually edit pyproject.toml [project.optional-dependencies.dev]
# Then run: poetry lock

# Update dependencies
poetry update

# Show outdated packages
poetry show --outdated
```

### Building and Publishing

```bash
# Build package
make build
# or
poetry build

# Check package
poetry run twine check dist/*

# Publish to PyPI (requires authentication)
poetry publish
```

### Cleaning Up

```bash
# Clean build artifacts and cache (automated)
make clean

# Clean manually
make clean-manual

# Clean everything including virtual environment
make clean-all
```

### Advanced Test Tools

```bash
# Run specific test scenarios
poetry run python scripts/test_tools.py run unit
poetry run python scripts/test_tools.py run integration
poetry run python scripts/test_tools.py run specific tests/core/test_cache.py
poetry run python scripts/test_tools.py run failing

# Analyze coverage
poetry run python scripts/test_tools.py coverage
poetry run python scripts/test_tools.py coverage --detailed --target 95.0

# Development tools
poetry run python scripts/dev_tools.py setup
poetry run python scripts/dev_tools.py validate
poetry run python scripts/dev_tools.py clean
```

## Debugging

### Test Logs

Tests generate a log file at `tests.log` with DEBUG level output:

```bash
# View test logs
tail -f tests.log

# Search logs
grep "ERROR" tests.log
```

### Verbose Testing

```bash
# Show print statements and detailed output
poetry run pytest -v -s

# Show local variables on failure
poetry run pytest -l

# Drop into debugger on failure
poetry run pytest --pdb
```

### Coverage Reports

```bash
# Generate HTML coverage report
poetry run pytest --cov --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html
```

## Best Practices

### Code Style
- Follow PEP 8 (enforced by ruff)
- Use type hints (checked by mypy)
- Write docstrings for public APIs
- Keep functions focused and small

### Testing
- Write tests for new features
- Maintain 90%+ code coverage
- Use appropriate test markers
- Mock external dependencies in unit tests

### Git Workflow
1. Create feature branch from main
2. Make changes
3. Run quality checks: `make quality`
4. Run tests: `make test-all`
5. Commit with descriptive message
6. Push and create pull request

### Pre-commit Checks
Pre-commit hooks automatically run on `git commit`:
- Code formatting (ruff)
- Linting (ruff)
- Type checking (mypy)
- Trailing whitespace removal
- YAML/JSON validation

## Troubleshooting

### Poetry Issues

```bash
# Clear poetry cache
poetry cache clear pypi --all

# Recreate virtual environment
poetry env remove python
poetry install
```

### Test Issues

```bash
# Clear pytest cache
rm -rf .pytest_cache

# Run tests in isolation
poetry run pytest --forked

# Disable warnings
poetry run pytest --disable-warnings
```

### Import Errors

```bash
# Ensure you're using poetry run
poetry run python script.py

# Or activate virtual environment
poetry shell
python script.py
```

## Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [MCP Documentation](https://modelcontextprotocol.io/)

## Getting Help

- Check existing documentation in `docs/`
- Review EXAMPLE_ShokoBot for reference implementation
- Run `make help` to see available commands
- Check test files for usage examples
