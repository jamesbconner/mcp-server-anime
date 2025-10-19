# Contributing to MCP Anime Server

Thank you for your interest in contributing to the MCP Anime Server! This guide will help you understand the project structure and how to contribute effectively.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Adding New Providers](#adding-new-providers)
- [Code Style and Standards](#code-style-and-standards)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Changes](#submitting-changes)

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Git for version control
- Basic understanding of async/await patterns
- Familiarity with Pydantic models

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/mcp-server-anime.git
   cd mcp-server-anime
   ```

2. **Install Dependencies**:
   ```bash
   poetry install
   poetry run pre-commit install
   ```

3. **Run Tests**:
   ```bash
   poetry run pytest
   ```

4. **Start Development Server**:
   ```bash
   poetry run python -m mcp_server_anime.server
   ```

## Architecture Overview

The project follows a modular architecture with clear separation of concerns:

```
src/mcp_server_anime/
├── core/           # Shared infrastructure
├── providers/      # Data source implementations
├── config/         # Configuration management
└── *.py           # Server implementations
```

### Key Principles

1. **Provider Pattern**: All anime data sources implement the same interface
2. **Dependency Injection**: Core functionality is injected into providers
3. **Type Safety**: Full type annotations with Pydantic models
4. **Error Resilience**: Comprehensive error handling with circuit breakers
5. **Testability**: Each component can be tested independently

## Adding New Providers

Adding a new anime data provider is the most common contribution. Here's how to do it:

### 1. Create Provider Structure

Create a new directory for your provider:

```bash
mkdir -p src/mcp_server_anime/providers/your_provider
touch src/mcp_server_anime/providers/your_provider/__init__.py
```

### 2. Implement Provider Interface

Create `src/mcp_server_anime/providers/your_provider/provider.py`:

```python
"""Your Provider implementation for anime data."""

from typing import Optional
from ...core.models import AnimeSearchResult, AnimeDetails
from ...core.logging_config import get_logger
from ..base import AnimeDataProvider, ProviderCapabilities, ProviderInfo
from .config import YourProviderConfig
from .service import YourProviderService

logger = get_logger(__name__)

class YourProvider(AnimeDataProvider):
    """Your Provider implementation."""
    
    def __init__(self, config: YourProviderConfig):
        self.config = config
        self.service = YourProviderService(config)
        self._initialized = False
    
    @property
    def info(self) -> ProviderInfo:
        """Get provider information."""
        return ProviderInfo(
            name="your_provider",
            display_name="Your Provider",
            description="Description of your provider",
            version="1.0.0",
            capabilities=ProviderCapabilities(
                search=True,
                details=True,
                # Add other capabilities as needed
            )
        )
    
    async def initialize(self) -> None:
        """Initialize the provider."""
        if self._initialized:
            return
        
        await self.service.initialize()
        self._initialized = True
        logger.info("Your Provider initialized successfully")
    
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        if not self._initialized:
            return
        
        await self.service.cleanup()
        self._initialized = False
        logger.info("Your Provider cleaned up")
    
    async def health_check(self) -> bool:
        """Check provider health."""
        if not self._initialized:
            return False
        
        return await self.service.health_check()
    
    async def search_anime(self, query: str, limit: int = 10) -> list[AnimeSearchResult]:
        """Search for anime by title."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        return await self.service.search_anime(query, limit)
    
    async def get_anime_details(self, anime_id: int) -> AnimeDetails:
        """Get detailed anime information."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        return await self.service.get_anime_details(anime_id)

def create_your_provider(config: Optional[YourProviderConfig] = None) -> YourProvider:
    """Create a Your Provider instance."""
    if config is None:
        config = YourProviderConfig()
    return YourProvider(config)
```

### 3. Create Configuration

Create `src/mcp_server_anime/providers/your_provider/config.py`:

```python
"""Configuration for Your Provider."""

import os
from typing import Optional
from pydantic import BaseModel, Field

class YourProviderConfig(BaseModel):
    """Configuration for Your Provider."""
    
    # API configuration
    api_key: Optional[str] = Field(
        default=None,
        description="API key for Your Provider"
    )
    base_url: str = Field(
        default="https://api.yourprovider.com",
        description="Base URL for Your Provider API"
    )
    
    # Rate limiting
    rate_limit_delay: float = Field(
        default=1.0,
        description="Delay between requests in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts"
    )
    
    # Caching
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    
    @classmethod
    def from_env(cls) -> "YourProviderConfig":
        """Load configuration from environment variables."""
        return cls(
            api_key=os.getenv("YOUR_PROVIDER_API_KEY"),
            base_url=os.getenv("YOUR_PROVIDER_BASE_URL", "https://api.yourprovider.com"),
            rate_limit_delay=float(os.getenv("YOUR_PROVIDER_RATE_LIMIT_DELAY", "1.0")),
            max_retries=int(os.getenv("YOUR_PROVIDER_MAX_RETRIES", "3")),
            cache_ttl=int(os.getenv("YOUR_PROVIDER_CACHE_TTL", "3600")),
        )

def load_config() -> YourProviderConfig:
    """Load Your Provider configuration."""
    return YourProviderConfig.from_env()
```

### 4. Implement Service Layer

Create `src/mcp_server_anime/providers/your_provider/service.py`:

```python
"""Service layer for Your Provider API."""

from typing import Any, Dict, List
import httpx
from ...core.http_client import HTTPClient, RateLimiter, RetryConfig
from ...core.cache import TTLCache, generate_cache_key
from ...core.error_handler import with_error_handling
from ...core.exceptions import APIError, NetworkError
from ...core.logging_config import get_logger
from ...core.models import AnimeSearchResult, AnimeDetails
from .config import YourProviderConfig

logger = get_logger(__name__)

class YourProviderService:
    """Service for interacting with Your Provider API."""
    
    def __init__(self, config: YourProviderConfig):
        self.config = config
        self.cache = TTLCache(default_ttl=config.cache_ttl)
        
        # Set up HTTP client with rate limiting
        rate_limiter = RateLimiter(delay=config.rate_limit_delay)
        retry_config = RetryConfig(max_retries=config.max_retries)
        self.http_client = HTTPClient(rate_limiter, retry_config)
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # Perform any initialization tasks
        logger.info("Your Provider service initialized")
    
    async def cleanup(self) -> None:
        """Clean up service resources."""
        await self.http_client.close()
        logger.info("Your Provider service cleaned up")
    
    async def health_check(self) -> bool:
        """Check service health."""
        try:
            # Perform a simple API call to check health
            response = await self.http_client.get(f"{self.config.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    @with_error_handling(fallback_value=[])
    async def search_anime(self, query: str, limit: int = 10) -> List[AnimeSearchResult]:
        """Search for anime by title."""
        cache_key = generate_cache_key("search", query=query, limit=limit)
        
        # Check cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Make API request
        params = {
            "q": query,
            "limit": limit,
        }
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        
        response = await self.http_client.get(
            f"{self.config.base_url}/search",
            params=params
        )
        
        if response.status_code != 200:
            raise APIError(f"Search failed: {response.status_code}")
        
        data = response.json()
        results = [self._parse_search_result(item) for item in data.get("results", [])]
        
        # Cache results
        await self.cache.set(cache_key, results)
        
        return results
    
    @with_error_handling(fallback_value=None)
    async def get_anime_details(self, anime_id: int) -> AnimeDetails:
        """Get detailed anime information."""
        cache_key = generate_cache_key("details", anime_id=anime_id)
        
        # Check cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Make API request
        params = {}
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        
        response = await self.http_client.get(
            f"{self.config.base_url}/anime/{anime_id}",
            params=params
        )
        
        if response.status_code != 200:
            raise APIError(f"Details request failed: {response.status_code}")
        
        data = response.json()
        result = self._parse_anime_details(data)
        
        # Cache result
        await self.cache.set(cache_key, result)
        
        return result
    
    def _parse_search_result(self, data: Dict[str, Any]) -> AnimeSearchResult:
        """Parse search result from API response."""
        return AnimeSearchResult(
            aid=data["id"],
            title=data["title"],
            type=data.get("type", "Unknown"),
            year=data.get("year"),
        )
    
    def _parse_anime_details(self, data: Dict[str, Any]) -> AnimeDetails:
        """Parse anime details from API response."""
        return AnimeDetails(
            aid=data["id"],
            title=data["title"],
            type=data.get("type", "Unknown"),
            episode_count=data.get("episode_count"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            synopsis=data.get("synopsis"),
            # Add other fields as needed
        )
```

### 5. Update Provider Exports

Update `src/mcp_server_anime/providers/your_provider/__init__.py`:

```python
"""Your Provider for anime data."""

from .provider import YourProvider, create_your_provider
from .service import YourProviderService
from .config import YourProviderConfig, load_config

__all__ = [
    "YourProvider",
    "create_your_provider",
    "YourProviderService", 
    "YourProviderConfig",
    "load_config",
]
```

### 6. Register Provider

Update `src/mcp_server_anime/providers/__init__.py` to include your provider:

```python
# Add import
from .your_provider import YourProvider, create_your_provider

# Add to __all__
__all__ = [
    # ... existing exports
    "YourProvider",
    "create_your_provider",
]
```

### 7. Add Tests

Create comprehensive tests in `tests/providers/your_provider/`:

```bash
mkdir -p tests/providers/your_provider
touch tests/providers/your_provider/__init__.py
```

Create `tests/providers/your_provider/test_provider.py`:

```python
"""Tests for Your Provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.mcp_server_anime.providers.your_provider import YourProvider, YourProviderConfig
from src.mcp_server_anime.core.models import AnimeSearchResult, AnimeDetails

class TestYourProvider:
    """Test Your Provider implementation."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return YourProviderConfig(
            api_key="test_key",
            base_url="https://test.api.com",
        )
    
    @pytest.fixture
    def provider(self, config):
        """Create test provider."""
        return YourProvider(config)
    
    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        """Test provider initialization."""
        await provider.initialize()
        assert provider._initialized is True
    
    @pytest.mark.asyncio
    async def test_search_anime(self, provider):
        """Test anime search."""
        # Mock the service
        provider.service.search_anime = AsyncMock(return_value=[
            AnimeSearchResult(aid=1, title="Test Anime", type="TV", year=2023)
        ])
        
        await provider.initialize()
        results = await provider.search_anime("test", limit=5)
        
        assert len(results) == 1
        assert results[0].title == "Test Anime"
    
    # Add more tests as needed
```

### 8. Update Configuration

If your provider needs global configuration, update the providers config system to include it.

## Code Style and Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for all functions and methods
- Use Pydantic models for data structures
- Follow async/await patterns for I/O operations

### Documentation

- Add comprehensive docstrings to all classes and methods
- Use Google-style docstrings
- Include usage examples where helpful
- Document any configuration options

### Error Handling

- Use the core error handling system
- Create provider-specific exceptions if needed
- Always provide meaningful error messages
- Use the `@with_error_handling` decorator for API calls

### Logging

- Use the core logging system
- Log important events and errors
- Include context in log messages
- Use appropriate log levels

## Testing Guidelines

### Test Structure

- Unit tests for individual components
- Integration tests for API interactions
- Mock external dependencies
- Test both success and failure cases

### Test Coverage

- Aim for 90%+ test coverage
- Test all public methods
- Test error conditions
- Test configuration loading

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific provider tests
poetry run pytest tests/providers/your_provider/

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

## Submitting Changes

### Before Submitting

1. **Run Quality Checks**:
   ```bash
   poetry run pre-commit run --all-files
   ```

2. **Run Tests**:
   ```bash
   poetry run pytest
   ```

3. **Update Documentation**:
   - Update README.md if needed
   - Add provider documentation
   - Update CHANGELOG.md

### Pull Request Process

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/add-your-provider
   ```

2. **Make Changes**:
   - Follow the guidelines above
   - Keep commits focused and atomic
   - Write clear commit messages

3. **Push and Create PR**:
   ```bash
   git push origin feature/add-your-provider
   ```

4. **PR Requirements**:
   - Clear description of changes
   - Link to any related issues
   - Include test results
   - Update documentation

### Review Process

- All PRs require review from maintainers
- Address any feedback promptly
- Ensure CI checks pass
- Squash commits if requested

## Getting Help

- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check existing documentation first
- **Code Examples**: Look at the AniDB provider for reference

## Common Patterns

### Configuration Loading

```python
@classmethod
def from_env(cls) -> "YourConfig":
    """Load from environment variables."""
    return cls(
        api_key=os.getenv("YOUR_API_KEY"),
        # ... other fields
    )
```

### Error Handling

```python
@with_error_handling(fallback_value=[])
async def api_method(self) -> List[Result]:
    """Method with error handling."""
    # Implementation
```

### Caching

```python
cache_key = generate_cache_key("operation", param1=value1)
cached = await self.cache.get(cache_key)
if cached is not None:
    return cached

# Perform operation
result = await self.do_operation()
await self.cache.set(cache_key, result)
return result
```

### HTTP Requests

```python
response = await self.http_client.get(url, params=params)
if response.status_code != 200:
    raise APIError(f"Request failed: {response.status_code}")
return response.json()
```

Thank you for contributing to the MCP Anime Server! Your contributions help make anime data more accessible to AI assistants and developers worldwide.