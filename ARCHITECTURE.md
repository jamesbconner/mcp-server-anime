# MCP Anime Server Architecture

## Overview

The MCP Anime Server is built using a modular, extensible architecture that separates concerns and allows for easy addition of new anime data providers. The architecture follows clean architecture principles with clear separation between core functionality, provider implementations, and external interfaces.

## Architectural Principles

### 1. Separation of Concerns
- **Core Layer**: Shared infrastructure and utilities
- **Provider Layer**: Data source implementations
- **Configuration Layer**: Settings and environment management
- **Server Layer**: MCP protocol implementation

### 2. Dependency Inversion
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- Providers implement abstract interfaces
- Core functionality is provider-agnostic

### 3. Open/Closed Principle
- Open for extension (new providers)
- Closed for modification (core functionality)
- New providers can be added without changing existing code

### 4. Single Responsibility
- Each module has a single, well-defined responsibility
- Clear boundaries between different concerns
- Minimal coupling between components

## Directory Structure

```
src/mcp_server_anime/
├── core/                    # Shared functionality
│   ├── __init__.py         # Core module exports
│   ├── cache.py            # TTL-based caching system
│   ├── http_client.py      # Rate-limited HTTP client
│   ├── error_handler.py    # Error handling and circuit breakers
│   ├── exceptions.py       # Custom exception hierarchy
│   ├── logging_config.py   # Structured logging setup
│   ├── models.py           # Pydantic data models
│   └── titles_db.py        # Local database utilities
├── providers/              # Data provider implementations
│   ├── __init__.py         # Provider module exports
│   ├── base.py            # Provider interface and base classes
│   ├── registry.py        # Provider discovery and management
│   ├── config.py          # Provider configuration system
│   ├── tools.py           # MCP tool registration
│   ├── anidb/             # AniDB provider implementation
│   │   ├── __init__.py    # AniDB provider exports
│   │   ├── provider.py    # Main provider class
│   │   ├── service.py     # API service layer
│   │   ├── config.py      # AniDB-specific configuration
│   │   ├── xml_parser.py  # XML response parsing
│   │   ├── search_service.py # Local database search
│   │   └── titles_downloader.py # Database synchronization
│   └── anidb.py           # Compatibility wrapper
├── config/                # Global configuration
│   ├── __init__.py        # Config module exports
│   └── settings.py        # Server-wide settings
├── __init__.py            # Main package exports
├── server.py              # Simple MCP server
├── extensible_server.py   # Multi-provider server
└── tools.py               # Legacy tool definitions
```

## Core Components

### Cache System (`core/cache.py`)

The caching system provides TTL-based caching with automatic cleanup and usage analytics:

```python
class TTLCache:
    """Thread-safe TTL cache with automatic cleanup."""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
```

**Features:**
- TTL-based expiration with automatic cleanup
- Size-based eviction with LRU behavior
- Thread-safe operations with async locks
- Cache statistics and monitoring with access_count tracking
- Configurable per-provider settings
- Persistent cache with database storage
- Usage analytics for cache optimization

### HTTP Client (`core/http_client.py`)

Rate-limited HTTP client with retry logic:

```python
class HTTPClient:
    """HTTP client with rate limiting and retry logic."""
    
    def __init__(self, rate_limiter: RateLimiter, retry_config: RetryConfig):
        self.rate_limiter = rate_limiter
        self.retry_config = retry_config
        self.client = httpx.AsyncClient()
```

**Features:**
- Rate limiting with configurable delays
- Exponential backoff retry logic
- Request/response logging
- Error classification and handling
- Connection pooling and reuse

### Error Handling (`core/error_handler.py`)

Comprehensive error handling with circuit breaker pattern:

```python
class ErrorHandler:
    """Centralized error handling with circuit breaker pattern."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
```

**Features:**
- Circuit breaker pattern implementation
- Automatic error classification
- Retry logic with backoff strategies
- Error context preservation
- Fallback value support

### Data Models (`core/models.py`)

Type-safe Pydantic models for all data structures:

```python
class AnimeSearchResult(BaseModel):
    """Anime search result model."""
    aid: int
    title: str
    type: str
    year: Optional[int] = None

class AnimeDetails(BaseModel):
    """Detailed anime information model."""
    aid: int
    title: str
    type: str
    episode_count: Optional[int] = None
    # ... additional fields
```

**Features:**
- Type-safe data structures
- Automatic validation and serialization
- Consistent data models across providers
- JSON schema generation
- Field validation and constraints
- Enhanced validation limits (e.g., AnimeTag descriptions up to 10,000 characters)

## Provider System

### Base Provider Interface (`providers/base.py`)

All providers must implement the `AnimeDataProvider` interface:

```python
class AnimeDataProvider(ABC):
    """Abstract base class for anime data providers."""
    
    @abstractmethod
    async def search_anime(self, query: str, limit: int) -> list[AnimeSearchResult]:
        """Search for anime by title."""
        pass
    
    @abstractmethod
    async def get_anime_details(self, anime_id: int) -> AnimeDetails:
        """Get detailed anime information."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health."""
        pass
```

### Provider Registry (`providers/registry.py`)

Manages provider lifecycle and discovery:

```python
class ProviderRegistry:
    """Registry for managing anime data providers."""
    
    def __init__(self):
        self._providers: dict[str, AnimeDataProvider] = {}
        self._provider_configs: dict[str, ProviderConfig] = {}
        self._health_status: dict[str, bool] = {}
    
    def register_provider(self, name: str, provider: AnimeDataProvider) -> None:
        """Register a new provider."""
        pass
    
    def get_enabled_providers(self) -> list[AnimeDataProvider]:
        """Get all enabled and healthy providers."""
        pass
```

**Features:**
- Dynamic provider discovery
- Priority-based provider selection
- Health monitoring and failover
- Configuration-driven enablement
- Lifecycle management

### AniDB Provider (`providers/anidb/`)

Full-featured AniDB implementation:

```python
class AniDBProvider(AnimeDataProvider):
    """AniDB provider implementation."""
    
    def __init__(self, config: AniDBConfig):
        self.config = config
        self.service = AniDBService(config)
    
    async def search_anime(self, query: str, limit: int) -> list[AnimeSearchResult]:
        """Search anime using AniDB API."""
        return await self.service.search_anime(query, limit)
```

**Components:**
- **Provider** (`provider.py`): Main provider implementation
- **Service** (`service.py`): API service layer with business logic
- **Config** (`config.py`): AniDB-specific configuration
- **XML Parser** (`xml_parser.py`): Robust XML response parsing
- **Search Service** (`search_service.py`): Local database search
- **Titles Downloader** (`titles_downloader.py`): Database synchronization

## Configuration System

### Global Configuration (`config/settings.py`)

Server-wide settings and environment management:

```python
class ServerConfig(BaseModel):
    """Global server configuration."""
    
    log_level: str = "INFO"
    port: int = 8000
    host: str = "localhost"
    
    @classmethod
    def load_from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        pass
```

### Provider Configuration (`providers/config.py`)

Provider-specific settings with validation:

```python
class ProviderConfig(BaseModel):
    """Base provider configuration."""
    
    enabled: bool = True
    priority: int = 100
    timeout: int = 30
    max_retries: int = 3

class ProvidersConfig(BaseModel):
    """Configuration for all providers."""
    
    anidb: AniDBConfig = Field(default_factory=AniDBConfig)
    # Future: anilist, mal, etc.
```

## MCP Integration

### Tool Registration (`providers/tools.py`)

Automatic tool generation from provider capabilities:

```python
def register_provider_tools(server: FastMCP, provider: AnimeDataProvider) -> None:
    """Register MCP tools for a provider."""
    
    @server.tool()
    async def anime_search(query: str, limit: int = 10) -> dict[str, Any]:
        """Search for anime by title."""
        results = await provider.search_anime(query, limit)
        return {"results": [result.model_dump() for result in results]}
```

### Server Implementations

Two server implementations are provided:

1. **Simple Server** (`server.py`): Single-provider server for basic use cases
2. **Extensible Server** (`extensible_server.py`): Multi-provider server with full features

## Data Flow

### Request Processing Flow

1. **Request Reception**: MCP client sends tool request
2. **Tool Routing**: Server identifies target provider and method
3. **Parameter Validation**: Request parameters are validated using Pydantic
4. **Cache Check**: Cache is checked for existing results
5. **Provider Selection**: Registry selects appropriate provider based on health and priority
6. **Provider Execution**: Provider performs the requested operation
7. **Error Handling**: Any errors are caught and processed by error handler
8. **Response Formatting**: Results are formatted for MCP response
9. **Cache Storage**: Results are cached for future requests

### Error Handling Flow

1. **Error Detection**: Exception caught by error handler
2. **Error Classification**: Error type determined (network, API, validation, etc.)
3. **Circuit Breaker Check**: Circuit breaker state evaluated
4. **Retry Logic**: Retry attempted if appropriate
5. **Fallback**: Fallback value returned if available
6. **Error Response**: Formatted error response sent to client

## Extension Points

### Adding New Providers

To add a new anime data provider:

1. **Create Provider Directory**: `src/mcp_server_anime/providers/your_provider/`

2. **Implement Provider Interface**:
   ```python
   class YourProvider(AnimeDataProvider):
       async def search_anime(self, query: str, limit: int) -> list[AnimeSearchResult]:
           # Implementation
           pass
   ```

3. **Create Configuration**:
   ```python
   class YourProviderConfig(BaseModel):
       api_key: str
       base_url: str = "https://api.yourprovider.com"
   ```

4. **Register Provider**:
   ```python
   registry = get_provider_registry()
   provider = YourProvider(config)
   registry.register_provider("your_provider", provider)
   ```

5. **Add Tests**: Create comprehensive tests in `tests/providers/your_provider/`

### Adding New Capabilities

To extend provider capabilities:

1. **Extend Base Interface**:
   ```python
   class AnimeDataProvider(ABC):
       @abstractmethod
       async def get_recommendations(self, anime_id: int) -> list[AnimeSearchResult]:
           pass
   ```

2. **Update Existing Providers**: Implement new capability in all providers

3. **Add MCP Tools**: Create corresponding MCP tools for new capability

4. **Update Configuration**: Add any new configuration options

## Testing Architecture

### Test Organization

```
tests/
├── core/                  # Core functionality tests
│   ├── test_cache.py     # Cache system tests
│   ├── test_http_client.py # HTTP client tests
│   └── ...
├── providers/             # Provider-specific tests
│   ├── test_base.py      # Base provider tests
│   ├── test_registry.py  # Registry tests
│   └── anidb/            # AniDB provider tests
│       ├── test_provider.py
│       ├── test_service.py
│       └── ...
├── integration/          # Integration tests
│   ├── test_integration.py
│   └── test_integration_mock.py
└── fixtures/             # Test data and mocks
    ├── anidb_responses/
    └── mock_data.py
```

### Test Categories

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: Provider API testing with real services
- **End-to-End Tests**: Full server workflow testing
- **Performance Tests**: Load and stress testing

## Performance Considerations

### Caching Strategy

- **Multi-level Caching**: Memory cache with optional disk cache
- **TTL-based Expiration**: Configurable time-to-live for different data types
- **Size-based Eviction**: LRU eviction when cache size limits are reached
- **Cache Warming**: Proactive caching of popular queries

### Rate Limiting

- **Provider-specific Limits**: Each provider has its own rate limiting
- **Adaptive Rate Limiting**: Adjust rates based on response times
- **Request Queuing**: Queue requests when rate limits are exceeded
- **Circuit Breaker Integration**: Prevent cascading failures

### Resource Management

- **Connection Pooling**: Reuse HTTP connections across requests
- **Memory Usage Monitoring**: Track and limit memory usage
- **Graceful Degradation**: Reduce functionality under load
- **Resource Cleanup**: Proper cleanup of resources on shutdown

## Security Considerations

### API Key Management

- **Environment Variables**: Store sensitive data in environment variables
- **Key Rotation**: Support for rotating API keys without restart
- **Rate Limit Compliance**: Respect provider rate limits to avoid bans
- **Error Message Sanitization**: Avoid exposing sensitive data in errors

### Data Validation

- **Input Sanitization**: Validate and sanitize all user inputs
- **Output Validation**: Validate provider responses before processing
- **Type Safety**: Use Pydantic models for type safety
- **Injection Prevention**: Prevent various injection attacks

## Monitoring and Observability

### Logging

- **Structured Logging**: JSON-formatted logs with context
- **Performance Metrics**: Track response times and cache hit rates
- **Error Tracking**: Comprehensive error logging with stack traces
- **Request Tracing**: Track requests through the entire system

### Health Checks

- **Provider Health**: Monitor individual provider health
- **Dependency Checking**: Check external service availability
- **Performance Metrics**: Track system performance metrics
- **Alerting Integration**: Support for external alerting systems

## Future Enhancements

### Planned Features

- **Additional Providers**: AniList, MyAnimeList, Kitsu
- **Local Database**: Offline search capabilities
- **Real-time Updates**: WebSocket support for real-time data
- **Advanced Search**: Fuzzy search, filters, sorting
- **Recommendation Engine**: AI-powered anime recommendations

### Scalability Improvements

- **Horizontal Scaling**: Support for multiple server instances
- **Load Balancing**: Distribute requests across providers
- **Distributed Caching**: Redis or similar for shared caching
- **Database Sharding**: Scale local database storage

### Performance Optimizations

- **GraphQL Support**: More efficient data fetching
- **Streaming Responses**: Stream large result sets
- **Compression**: Compress responses to reduce bandwidth
- **CDN Integration**: Cache static data in CDN

## Conclusion

The MCP Anime Server architecture provides a solid foundation for building a scalable, maintainable anime data service. The modular design allows for easy extension while maintaining clean separation of concerns. The comprehensive error handling and monitoring capabilities ensure reliable operation in production environments.

The provider pattern makes it straightforward to add new anime data sources, while the core infrastructure provides consistent behavior across all providers. This architecture supports both current needs and future growth, making it an excellent choice for anime data integration projects.