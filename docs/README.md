# MCP Anime Server Documentation

This directory contains comprehensive documentation for the MCP Anime Server project.

## Documentation Index

### Core Documentation
- **[Main README](../README.md)** - Project overview, installation, and quick start guide
- **[Architecture](../ARCHITECTURE.md)** - Detailed system architecture and design patterns
- **[Configuration](../CONFIGURATION.md)** - Comprehensive configuration options and examples
- **[Changelog](../CHANGELOG.md)** - Version history and release notes

### Setup and Configuration
- **[Kiro Configuration](kiro-configuration.md)** - Detailed Kiro MCP setup instructions
- **[Distribution](distribution.md)** - Package distribution and deployment guide

### Development and Testing
- **[Testing with Poetry](testing-with-poetry.md)** - Development environment setup and testing
- **[Test Maintenance Procedures](test-maintenance-procedures.md)** - Test suite maintenance guidelines
- **[Integration Testing](integration_testing.md)** - Integration test setup and execution

### Features and Enhancements
- **[Enhanced Parsing Examples](enhanced_parsing_examples.md)** - Advanced XML parsing capabilities
- **[Recent Fixes and Enhancements](recent-fixes-and-enhancements.md)** - Latest bug fixes and improvements

## Quick Navigation

### For Users
1. Start with the [Main README](../README.md) for installation and basic usage
2. Follow the [Kiro Configuration](kiro-configuration.md) guide for MCP setup
3. Check [Recent Fixes and Enhancements](recent-fixes-and-enhancements.md) for latest updates

### For Developers
1. Review the [Architecture](../ARCHITECTURE.md) document for system design
2. Set up development environment with [Testing with Poetry](testing-with-poetry.md)
3. Follow [Test Maintenance Procedures](test-maintenance-procedures.md) for testing guidelines

### For Troubleshooting
1. Check the [Configuration](../CONFIGURATION.md) guide for setup issues
2. Review [Recent Fixes and Enhancements](recent-fixes-and-enhancements.md) for known issues
3. Use debug tools described in the configuration documentation

## Recent Updates

### v0.2.2 (October 19, 2025)
- **Cache Persistence Fix**: Fixed persistent cache being cleared after MCP tool execution
- **Validation Enhancement**: Increased AnimeTag description limit to 10,000 characters
- **Debug Tools**: Enhanced debug script with command-line argument support
- **Analytics**: Improved access_count tracking for cache usage analytics

### v0.2.1 (October 18, 2025)
- **Documentation**: Comprehensive Kiro setup guide and troubleshooting
- **Security**: Enhanced SQL injection protection and input validation
- **Development**: Improved local development configuration examples

## Contributing

When adding new documentation:

1. **Follow Markdown Standards**: Use consistent formatting and structure
2. **Update This Index**: Add new documents to the appropriate section
3. **Cross-Reference**: Link related documents for easy navigation
4. **Keep Current**: Update documentation with code changes
5. **Test Examples**: Verify all code examples and commands work

## Support

For additional help:
- Check the troubleshooting sections in relevant documents
- Review the [Changelog](../CHANGELOG.md) for recent changes
- Use the debug tools described in [Configuration](../CONFIGURATION.md)
- Refer to inline help and error messages in the application