# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2025-10-18

### Removed
- Deprecated `anime_search` tool (use `anidb_search` instead)
- Deprecated `anime_details` tool (use `anidb_details` instead)

### Added
- Comprehensive Kiro setup documentation (`KIRO_SETUP.md`)
- Local development configuration examples for Kiro MCP
- Troubleshooting guide for common Kiro integration issues

### Changed
- Streamlined MCP tool interface to only expose current tools
- Improved API clarity by removing backward compatibility wrappers
- Enhanced README with local development setup instructions
- Updated CLI help text with Kiro configuration references

### Fixed
- Import error when using local development setup in Kiro
- Module resolution issues with direct Python executable paths
- Environment variable handling in Kiro MCP configuration

### Security
- Comprehensive security fixes for SQL injection vulnerabilities
- Enhanced table name validation and parameterized queries
- Improved exception handling and logging
- Replaced assert statements with runtime validation
- Updated hash function usage for non-cryptographic purposes

## [0.2.0] - 2025-10-18

### Added
- Initial release of mcp-server-anime
- Anime search functionality via AniDB HTTP API
- Detailed anime information retrieval
- Rate limiting and caching support
- MCP protocol compliance
- FastMCP integration
- Comprehensive error handling and logging
- Unit and integration test suite
- CI/CD pipeline with GitHub Actions

### Features
- **anime_search** tool: Search for anime by title with configurable result limits
- **anime_details** tool: Retrieve comprehensive anime information by AniDB ID
- Automatic rate limiting (2 seconds between requests) to respect AniDB API limits
- In-memory caching with TTL support to improve performance
- Structured error handling with custom exception types
- Async/await support for optimal performance
- Type-safe implementation with comprehensive type annotations
- Extensible architecture for future anime API integrations

### Technical Details
- Built with Python 3.12+ using modern async/await patterns
- Uses FastMCP for MCP protocol implementation
- HTTP client with retry logic and exponential backoff
- XML parsing with lxml for AniDB API responses
- Pydantic models for data validation and serialization
- Comprehensive logging with structured output
- 90%+ test coverage with pytest
- Code quality enforcement with ruff, mypy, and bandit

## [0.1.0] - 2024-12-XX

### Added
- Initial project setup and configuration
- Core MCP server implementation
- AniDB HTTP API integration
- Basic anime search and details functionality
- Package distribution configuration

### Dependencies
- mcp ^1.0.0 - Model Context Protocol implementation
- httpx ^0.28.0 - Async HTTP client
- pydantic ^2.11.0 - Data validation and serialization
- lxml ^5.0.0 - XML parsing for AniDB responses

### Development Dependencies
- pytest ^8.0.0 - Testing framework
- pytest-asyncio ^1.1.0 - Async test support
- pytest-cov ^6.0.0 - Coverage reporting
- pytest-mock ^3.12.0 - Mocking utilities
- respx ^0.20.0 - HTTP request mocking
- ruff ^0.12.0 - Code formatting and linting
- mypy ^1.8.0 - Static type checking
- bandit ^1.8.0 - Security vulnerability scanning
- pre-commit ^4.0.0 - Git hooks for code quality