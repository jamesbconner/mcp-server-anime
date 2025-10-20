# MCP Server Anime

[![PyPI version](https://badge.fury.io/py/mcp-server-anime.svg)](https://badge.fury.io/py/mcp-server-anime)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Model Context Protocol (MCP) server that provides AI assistants with access to anime data through the AniDB HTTP API. Built with FastMCP for seamless integration with Kiro and other MCP-compatible AI assistants.

## Quick Start

1. **Install with uvx** (recommended for Kiro):

   ```bash
   uvx mcp-server-anime --version
   ```

2. **Configure in Kiro** - Add to `.kiro/settings/mcp.json`:

   ```json
   {
     "mcpServers": {
       "anime": {
         "command": "uvx",
         "args": ["mcp-server-anime"],
         "disabled": false
       }
     }
   }
   ```

3. **Start using** - Ask Kiro: _"Search for anime about pirates"_

## Features

- 🔍 **Anime Search**: Search for anime by title with configurable result limits
- 📊 **Detailed Information**: Retrieve comprehensive anime data including synopsis, ratings, episodes, and metadata
- ⚡ **Fast & Reliable**: Built with FastMCP and async/await for optimal performance
- 🛡️ **Rate Limited**: Automatic rate limiting to respect AniDB API guidelines (2 seconds between requests)
- 💾 **Caching**: In-memory caching with TTL support to improve response times
- 🔧 **Extensible**: Clean provider architecture supporting multiple anime data sources
  - **AniDB Provider**: Full-featured anime database access (currently implemented)
  - **Future Providers**: AniList and MyAnimeList support planned
- 🧪 **Well Tested**: Comprehensive test suite with 90%+ coverage
- 📝 **Type Safe**: Full type annotations with mypy validation
- 🏗️ **Modular Design**: Separated core functionality from provider-specific implementations

## Installation

### Using uvx (Recommended for Kiro)

The easiest way to use this MCP server with Kiro is via `uvx`:

```bash
uvx mcp-server-anime
```

### Using pip

```bash
pip install mcp-server-anime
```

### From Source

```bash
git clone https://github.com/example/mcp-server-anime.git
cd mcp-server-anime
poetry install
poetry run mcp-server-anime
```

## Configuration

> 📖 **Detailed Setup Guide**: For comprehensive Kiro setup instructions, including local development configuration, see [KIRO_SETUP.md](KIRO_SETUP.md)

### Kiro MCP Configuration

#### Production Setup (Recommended)

Add the following to your Kiro MCP configuration file (`.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime"],
      "disabled": false,
      "env": {
        "ANIDB_CLIENT_NAME": "your-app-name",
        "ANIDB_CLIENT_VERSION": "1"
      }
    }
  }
}
```

#### Local Development Setup

For local development or when not using `uvx`, use the direct Python executable path:

```json
{
  "mcpServers": {
    "anime": {
      "command": "/path/to/your/python/env/python.exe",
      "args": ["-m", "mcp_server_anime.server"],
      "cwd": "/path/to/mcp-server-anime",
      "env": {
        "PYTHONPATH": "/path/to/mcp-server-anime/src",
        "ANIDB_CLIENT_NAME": "your-app-name",
        "ANIDB_CLIENT_VERSION": "1"
      },
      "disabled": false
    }
  }
}
```

**Example for Windows with Anaconda:**
```json
{
  "mcpServers": {
    "anime": {
      "command": "D:/Languages/Anaconda/envs/mcp-server-anime/python.exe",
      "args": ["-m", "mcp_server_anime.server"],
      "cwd": "D:/Documents/Code/mcp-server-anime",
      "env": {
        "PYTHONPATH": "D:/Documents/Code/mcp-server-anime/src"
      },
      "disabled": false
    }
  }
}
```

**Why Local Development Setup is Needed:**
- `uvx` caches packages and may use outdated versions during development
- Direct Python path ensures you're using your local development version
- `PYTHONPATH` ensures the source code is found correctly
- `cwd` sets the working directory for the server process

> **Note**: The server uses a clean provider architecture. The AniDB provider is the primary data source, with additional providers (AniList, MyAnimeList) planned for future releases.

### Environment Variables

The server supports the following environment variables for configuration:

| Variable                 | Description                         | Default                             | Required |
| ------------------------ | ----------------------------------- | ----------------------------------- | -------- |
| `ANIDB_CLIENT_NAME`      | Your application name for AniDB API | `mcp-server-anidb`                  | No       |
| `ANIDB_CLIENT_VERSION`   | Your application version            | `1`                                 | No       |
| `ANIDB_PROTOCOL_VERSION` | AniDB protocol version              | `1`                                 | No       |
| `ANIDB_BASE_URL`         | AniDB API base URL                  | `http://api.anidb.net:9001/httpapi` | No       |
| `ANIDB_RATE_LIMIT_DELAY` | Delay between requests (seconds)    | `2.0`                               | No       |
| `ANIDB_MAX_RETRIES`      | Maximum retry attempts              | `3`                                 | No       |
| `ANIDB_CACHE_TTL`        | Cache TTL in seconds                | `3600`                              | No       |

### Alternative MCP Clients

For other MCP clients, you can run the server directly:

```bash
mcp-server-anime
```

Or with custom log level:

```bash
mcp-server-anime --log-level DEBUG
```

## Available Tools

### anime_search

Search for anime by title.

**Parameters:**

- `query` (string, required): Search term for anime title
- `limit` (integer, optional): Maximum number of results (default: 10, max: 20)

**Example:**

```json
{
  "name": "anime_search",
  "arguments": {
    "query": "Attack on Titan",
    "limit": 5
  }
}
```

**Response:**

```json
{
  "results": [
    {
      "aid": 9541,
      "title": "Shingeki no Kyojin",
      "type": "TV Series",
      "year": 2013
    }
  ]
}
```

### anime_details

Get detailed information about a specific anime.

**Parameters:**

- `aid` (integer, required): AniDB anime ID

**Example:**

```json
{
  "name": "anime_details",
  "arguments": {
    "aid": 9541
  }
}
```

**Response:**

```json
{
  "aid": 9541,
  "title": "Shingeki no Kyojin",
  "type": "TV Series",
  "episode_count": 25,
  "start_date": "2013-04-07T00:00:00Z",
  "end_date": "2013-09-29T00:00:00Z",
  "synopsis": "Several hundred years ago, humans were nearly exterminated by titans...",
  "titles": [
    {
      "title": "Attack on Titan",
      "language": "en",
      "type": "official"
    }
  ],
  "creators": [
    {
      "name": "Tetsuro Araki",
      "id": 5088,
      "type": "Direction"
    }
  ],
  "related_anime": [],
  "restricted": false
}
```

## Error Handling

The server provides comprehensive error handling with informative messages:

- **Invalid Parameters**: Clear validation error messages for incorrect input
- **API Errors**: Graceful handling of AniDB API errors with retry logic
- **Rate Limiting**: Automatic backoff when rate limits are exceeded
- **Network Issues**: Retry with exponential backoff for transient failures

## Performance

- **Caching**: Responses are cached for 1 hour by default to reduce API calls
- **Rate Limiting**: Respects AniDB's 2-second rate limit between requests
- **Async Operations**: Non-blocking I/O for optimal performance
- **Connection Pooling**: Efficient HTTP connection management

## Architecture

The MCP Server Anime uses a clean, modular architecture designed for extensibility and maintainability:

```
src/mcp_server_anime/
├── core/                    # Shared functionality
│   ├── cache.py            # TTL-based caching with automatic cleanup
│   ├── http_client.py      # Rate-limited HTTP client with retry logic
│   ├── error_handler.py    # Circuit breaker and error recovery patterns
│   ├── exceptions.py       # Comprehensive exception hierarchy
│   ├── logging_config.py   # Structured logging with context tracking
│   ├── models.py           # Type-safe Pydantic data models
│   └── titles_db.py        # Local database utilities (future use)
├── providers/              # Pluggable data provider system
│   ├── base.py            # Abstract provider interface and capabilities
│   ├── registry.py        # Provider discovery and lifecycle management
│   ├── config.py          # Provider configuration and validation
│   ├── tools.py           # Automatic MCP tool registration
│   └── anidb/             # AniDB provider implementation
│       ├── provider.py    # Provider interface implementation
│       ├── service.py     # AniDB API service layer
│       ├── config.py      # AniDB-specific configuration
│       ├── xml_parser.py  # Robust XML response parsing
│       ├── search_service.py  # Local database search (future)
│       └── titles_downloader.py  # Database sync (future)
├── config/                # Global configuration management
│   └── settings.py        # Server-wide settings and environment loading
├── server.py              # Simple MCP server (single provider)
├── extensible_server.py   # Multi-provider MCP server
└── tools.py               # Legacy tool definitions (compatibility)
```

### Architectural Principles

The server follows clean architecture principles with clear separation of concerns:

#### Core Layer
- **Shared Infrastructure**: Reusable components for all providers
- **Type Safety**: Full Pydantic model validation and type checking
- **Error Resilience**: Circuit breakers, retry logic, and graceful degradation
- **Performance**: Multi-level caching and connection pooling
- **Observability**: Structured logging with performance metrics

#### Provider Layer
- **Plugin Architecture**: Dynamic provider discovery and registration
- **Consistent Interface**: All providers implement the same contract
- **Independent Configuration**: Provider-specific settings and validation
- **Health Monitoring**: Automatic health checks and failover
- **Tool Generation**: Automatic MCP tool creation from provider capabilities

#### Configuration Layer
- **Environment-Driven**: Configuration via environment variables
- **Validation**: Type-safe configuration with Pydantic models
- **Hierarchical**: Global settings with provider-specific overrides
- **Runtime Updates**: Support for configuration changes without restart

### Provider Architecture

The extensible provider system supports multiple anime data sources:

- **Base Provider Interface**: Defines the contract all providers must implement
- **Provider Registry**: Manages provider lifecycle and health monitoring
- **Automatic Tool Registration**: MCP tools are generated from provider capabilities
- **Priority-Based Selection**: Configurable provider priorities and failover
- **Configuration Management**: Provider-specific settings with validation

**Current Providers:**
- **AniDB Provider**: Full-featured anime database with local search capabilities

**Planned Providers:**
- **AniList Provider**: Modern GraphQL-based anime database
- **MyAnimeList Provider**: Popular community-driven anime database

### Benefits of This Architecture

1. **Extensibility**: Easy to add new anime data providers
2. **Maintainability**: Clear separation of concerns and modular design
3. **Reliability**: Comprehensive error handling and circuit breaker patterns
4. **Performance**: Multi-level caching and efficient resource management
5. **Type Safety**: Full type annotations and runtime validation
6. **Testability**: Independent testing of core functionality and providers
7. **Observability**: Structured logging and performance monitoring

For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Recent Fixes and Enhancements

For detailed information about recent bug fixes and enhancements, see [Recent Fixes and Enhancements](docs/recent-fixes-and-enhancements.md).

### Backward Compatibility

All existing imports and APIs remain unchanged:

```python
# These imports continue to work
from mcp_server_anime import AniDBService, AniDBConfig
from mcp_server_anime import create_server
```

## Development

### Prerequisites

- Python 3.12+
- Poetry
- Git

### Setup

```bash
git clone https://github.com/example/mcp-server-anime.git
cd mcp-server-anime
poetry install
poetry run pre-commit install
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run only unit tests
poetry run pytest tests/ -m "not integration"

# Run integration tests (requires internet)
poetry run pytest tests/ -m integration
```

### Code Quality

```bash
# Format and lint code
poetry run ruff format .
poetry run ruff check .

# Type checking
poetry run mypy .

# Security scanning
poetry run bandit -r src/

# Run all quality checks
poetry run pre-commit run --all-files
```

### Adding New Providers

The modular architecture makes it straightforward to add new anime data providers. See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions.

**Quick Overview:**

1. **Create Provider Directory**: `src/mcp_server_anime/providers/your_provider/`
2. **Implement Provider Interface**: Extend `AnimeDataProvider` abstract base class
3. **Add Configuration**: Create provider-specific configuration with Pydantic models
4. **Implement Service Layer**: Handle API interactions with error handling and caching
5. **Register Provider**: Add to the provider registry for automatic discovery
6. **Add Tests**: Create comprehensive tests with mocks and integration tests

**Key Benefits:**
- **Shared Infrastructure**: Automatic access to caching, HTTP client, error handling
- **Type Safety**: Full Pydantic model validation and type checking
- **Configuration Management**: Environment-based configuration with validation
- **Tool Registration**: Automatic MCP tool generation from provider capabilities
- **Health Monitoring**: Built-in health checks and circuit breaker patterns

For complete examples and detailed instructions, see:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Step-by-step provider development guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- `src/mcp_server_anime/providers/anidb/` - Reference implementation

### Building and Publishing

```bash
# Validate package configuration
python scripts/validate_package.py

# Build package
poetry build

# Verify installation locally
python scripts/verify_installation.py

# Publish to PyPI (requires authentication)
poetry publish

# Publish to test PyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish -r testpypi
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks (`poetry run pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Troubleshooting

### Common Issues

**Server won't start:**

- Check that Python 3.12+ is installed
- Verify all dependencies are installed (`poetry install`)
- Check for port conflicts if running multiple MCP servers

**API errors:**

- Verify internet connection
- Check if AniDB API is accessible
- Review rate limiting settings if getting 429 errors
- Ensure AniDB client name is properly configured (defaults to `mcp-server-anidb`)

**Kiro integration issues:**

- Ensure `uvx` is installed and available in PATH
- Check MCP configuration syntax in `.kiro/settings/mcp.json`
- Verify server is listed in Kiro's MCP server panel

**Cache persistence issues:**

- Cache entries should persist across MCP tool calls (fixed in v0.2.2)
- Use `debug_cache_workflow.py` script to test cache behavior
- Check cache statistics with built-in analytics tools:
  ```bash
  python -m mcp_server_anime.cli.analytics_cli cache-stats --provider anidb
  ```

### Debug Mode

Run with debug logging for troubleshooting:

```bash
mcp-server-anime --log-level DEBUG
```

Debug logs will show:

- Provider initialization and configuration
- Cache operations and hit/miss ratios
- HTTP requests and rate limiting
- Error handling and retry attempts
- AniDB API interactions and XML parsing

### Analytics and Monitoring

The server includes comprehensive analytics tools for monitoring performance:

```bash
# Show cache statistics
python -m mcp_server_anime.cli.analytics_cli cache-stats --provider anidb

# Show search performance metrics
python -m mcp_server_anime.cli.analytics_cli performance --provider anidb

# Show search statistics
python -m mcp_server_anime.cli.analytics_cli stats --provider anidb

# Generate comprehensive report
python -m mcp_server_anime.cli.analytics_cli report --provider anidb
```

Available analytics commands:
- `cache-stats` - Cache performance and storage metrics
- `stats` - Search statistics and popular queries
- `performance` - Response time metrics and SLA compliance
- `queries` - Query analytics and patterns
- `benchmark` - Performance benchmarking
- `scheduler-status` - Analytics scheduler status
- `cleanup` - Clean up old transaction data

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Recent Updates

### v0.2.2 - Cache Persistence & Validation Fixes

- **🐛 Cache Persistence Fix**: Fixed persistent cache being cleared after MCP tool execution
- **📏 Validation Enhancement**: Increased AnimeTag description limit from 1000 to 10000 characters
- **🔧 Debug Tools**: Enhanced debug script with command-line argument support
- **📊 Analytics Improvement**: Better access_count tracking for cache usage analytics

### v0.2.1 - Documentation & Security Enhancements

- **📚 Comprehensive Documentation**: Added detailed Kiro setup guide and troubleshooting
- **🔒 Security Fixes**: Enhanced SQL injection protection and input validation
- **🛠️ Development Tools**: Improved local development configuration examples

### v0.2.0 - Provider Architecture & Client Name Correction

- **🏗️ Restructured Architecture**: Implemented clean provider architecture for better extensibility
- **🔧 Client Name Fix**: Corrected default AniDB client name to `mcp-server-anidb` (officially registered)
- **📦 Modular Design**: Separated core functionality from provider-specific implementations
- **🔄 Backward Compatibility**: All existing imports and APIs continue to work unchanged
- **🚀 Future Ready**: Architecture prepared for AniList and MyAnimeList providers

### Migration Notes

- **No Breaking Changes**: Existing configurations and imports continue to work
- **Environment Variables**: All existing environment variables work as before
- **Default Client Name**: Now uses the officially registered `mcp-server-anidb` name
- **Import Paths**: Both old and new import paths are supported

## Acknowledgments

- [AniDB](https://anidb.net/) for providing the anime database API
- [Model Context Protocol](https://modelcontextprotocol.io/) for the MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) for the Python MCP SDK
