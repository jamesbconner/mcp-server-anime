# MCP Server Anime Documentation

Welcome to the MCP Server Anime documentation. This guide will help you understand, configure, and develop with the MCP Server Anime project.

## Quick Links

- [Main README](../README.md) - Project overview and quick start
- [Developer Guide](developer-guide.md) - Complete development workflow
- [Architecture](architecture.md) - System design and architecture
- [Configuration](configuration.md) - Configuration options and settings

## Getting Started

### For Users

1. **Installation**: See the [main README](../README.md#installation)
2. **Kiro Setup**: Follow the [Kiro Setup Guide](kiro-setup.md)
3. **Configuration**: Review [Configuration Guide](configuration.md)

### For Developers

1. **Setup**: Follow the [Developer Guide](developer-guide.md#setup)
2. **Testing**: See [Testing with Poetry](testing-with-poetry.md)
3. **Contributing**: Read [CONTRIBUTING.md](../CONTRIBUTING.md)

## Documentation Structure

### Core Documentation

- **[Architecture](architecture.md)** - System architecture, design patterns, and component overview
- **[Configuration](configuration.md)** - Configuration options, environment variables, and settings
- **[Developer Guide](developer-guide.md)** - Development workflow, testing, and best practices

### Integration Guides

- **[Kiro Setup](kiro-setup.md)** - Complete guide for Kiro IDE integration
- **[Distribution](distribution.md)** - Package distribution and publishing

### Testing Documentation

- **[Testing with Poetry](testing-with-poetry.md)** - Poetry-based testing workflow
- **[Integration Testing](integration-testing.md)** - Integration test guidelines
- **[Test Maintenance](test-maintenance.md)** - Test maintenance procedures

### Reference Documentation

- **[Parsing Examples](parsing-examples.md)** - XML parsing examples and patterns
- **[Recent Changes](recent-changes.md)** - Recent fixes and enhancements

### Historical Documentation

- **[Refactoring Documentation](refactoring/)** - Historical record of project refactoring

## Key Features

### Anime Data Access
- Search anime by title
- Get detailed anime information
- Access comprehensive metadata

### Provider System
- Pluggable provider architecture
- Currently supports AniDB
- Planned: AniList, MyAnimeList

### Performance
- In-memory caching with TTL
- Rate limiting for API compliance
- Retry logic with exponential backoff

### Developer Experience
- Modern Python packaging (PEP 621)
- Comprehensive test suite (90%+ coverage)
- Type-safe with mypy
- Well-documented APIs

## Common Tasks

### Running Tests

```bash
# Unit tests
make test-unit

# All tests
make test-all

# With coverage
make coverage
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make type-check

# All quality checks
make quality
```

### Development Setup

```bash
# Automated setup
make setup

# Validate environment
make validate-env

# Clean artifacts
make clean
```

## Project Structure

```
mcp-server-anime/
├── src/mcp_server_anime/     # Main source code
│   ├── core/                 # Core functionality
│   ├── providers/            # Data provider implementations
│   ├── config/              # Configuration management
│   └── cli/                 # CLI tools
├── tests/                    # Test suite
├── docs/                     # Documentation (you are here)
├── scripts/                  # Development utilities
├── pyproject.toml           # Project configuration
└── Makefile                 # Development commands
```

## Getting Help

### Documentation

- Browse this documentation site
- Check the [main README](../README.md)
- Review [CONTRIBUTING.md](../CONTRIBUTING.md)

### Issues and Support

- [GitHub Issues](https://github.com/example/mcp-server-anime/issues)
- [Changelog](../CHANGELOG.md)
- [Security Policy](../SECURITY.md)

### Development

- [Developer Guide](developer-guide.md)
- [Architecture Documentation](architecture.md)
- [Test Documentation](testing-with-poetry.md)

## Contributing

We welcome contributions! Please see:

1. [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
2. [Developer Guide](developer-guide.md) - Development workflow
3. [Test Maintenance](test-maintenance.md) - Testing guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for version history and release notes.

---

**Last Updated**: 2025-11-10
**Version**: 0.2.1
**Status**: Active Development
