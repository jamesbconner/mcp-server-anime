# MCP Anime Server Configuration Guide

This document provides comprehensive configuration options for the MCP Anime Server's local database integration features.

## Overview

The MCP Anime Server supports extensive configuration through environment variables, allowing you to customize database behavior, download protection, search performance, and transaction logging to meet your specific needs.

## Configuration Categories

### 1. Database Configuration

Controls SQLite database behavior, performance, and maintenance.

| Environment Variable | Default | Description | Valid Range |
|---------------------|---------|-------------|-------------|
| `MCP_ANIME_DB_PATH` | `~/.cache/mcp-server-anime/anime_multi_provider.db` | Path to SQLite database file | Any valid file path |
| `MCP_ANIME_DB_CONNECTION_TIMEOUT` | `30` | Database connection timeout (seconds) | 5-300 |
| `MCP_ANIME_DB_MAX_CONNECTIONS` | `10` | Maximum database connections | 1-100 |
| `MCP_ANIME_DB_CACHE_SIZE_MB` | `64` | SQLite cache size (MB) | 16-1024 |
| `MCP_ANIME_DB_ENABLE_WAL` | `true` | Enable WAL mode for better concurrency | true/false |
| `MCP_ANIME_DB_AUTO_VACUUM` | `true` | Enable automatic database vacuuming | true/false |
| `MCP_ANIME_DB_VACUUM_INTERVAL_HOURS` | `168` | Hours between vacuum operations | 1-8760 |
| `MCP_ANIME_DB_ANALYZE_INTERVAL_HOURS` | `24` | Hours between ANALYZE operations | 1-168 |

**Example:**
```bash
export MCP_ANIME_DB_PATH="/var/lib/mcp-anime/database.db"
export MCP_ANIME_DB_CACHE_SIZE_MB="128"
export MCP_ANIME_DB_ENABLE_WAL="true"
```

### 2. Download Protection Configuration

Controls download rate limiting and file validation to prevent AniDB bans.

| Environment Variable | Default | Description | Valid Range |
|---------------------|---------|-------------|-------------|
| `MCP_ANIME_DOWNLOAD_PROTECTION_HOURS` | `36` | Hours between allowed downloads | 1-168 |
| `MCP_ANIME_DOWNLOAD_MAX_RETRIES` | `3` | Maximum download retry attempts | 0-10 |
| `MCP_ANIME_DOWNLOAD_TIMEOUT_SECONDS` | `60` | Download timeout (seconds) | 10-300 |
| `MCP_ANIME_DOWNLOAD_MIN_FILE_SIZE` | `100000` | Minimum expected file size (bytes) | 1000+ |
| `MCP_ANIME_DOWNLOAD_MAX_FILE_SIZE` | `50000000` | Maximum allowed file size (bytes) | 1000000+ |
| `MCP_ANIME_DOWNLOAD_VERIFY_INTEGRITY` | `true` | Verify file integrity after download | true/false |
| `MCP_ANIME_DOWNLOAD_INTEGRITY_CHECK_LINES` | `1000` | Lines to check for integrity | 100-10000 |
| `MCP_ANIME_DOWNLOAD_ALLOW_EMERGENCY_OVERRIDE` | `false` | Allow emergency rate limit override | true/false |

**Example:**
```bash
export MCP_ANIME_DOWNLOAD_PROTECTION_HOURS="48"
export MCP_ANIME_DOWNLOAD_MAX_RETRIES="5"
export MCP_ANIME_DOWNLOAD_VERIFY_INTEGRITY="true"
```

### 3. Search Configuration

Controls search behavior, performance, and result formatting.

| Environment Variable | Default | Description | Valid Range |
|---------------------|---------|-------------|-------------|
| `MCP_ANIME_SEARCH_DEFAULT_LIMIT` | `10` | Default number of search results | 1-100 |
| `MCP_ANIME_SEARCH_MAX_LIMIT` | `20` | Maximum allowed search results | 1-100 |
| `MCP_ANIME_SEARCH_MIN_QUERY_LENGTH` | `2` | Minimum search query length | 1-10 |
| `MCP_ANIME_SEARCH_MAX_QUERY_LENGTH` | `100` | Maximum search query length | 10-1000 |
| `MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS` | `100.0` | Target response time (milliseconds) | 10.0-5000.0 |
| `MCP_ANIME_SEARCH_ENABLE_FUZZY_MATCHING` | `true` | Enable fuzzy matching | true/false |
| `MCP_ANIME_SEARCH_ENABLE_RESULT_CACHING` | `true` | Enable result caching | true/false |
| `MCP_ANIME_SEARCH_CACHE_TTL_SECONDS` | `300` | Cache TTL (seconds) | 60-3600 |
| `MCP_ANIME_SEARCH_NORMALIZE_QUERIES` | `true` | Normalize queries (lowercase, trim) | true/false |
| `MCP_ANIME_SEARCH_REMOVE_SPECIAL_CHARS` | `false` | Remove special characters | true/false |

**Example:**
```bash
export MCP_ANIME_SEARCH_DEFAULT_LIMIT="15"
export MCP_ANIME_SEARCH_MAX_LIMIT="25"
export MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS="50.0"
```

### 4. Transaction Logging Configuration

Controls search transaction logging, analytics, and data retention.

| Environment Variable | Default | Description | Valid Range |
|---------------------|---------|-------------|-------------|
| `MCP_ANIME_TRANSACTION_ENABLE_LOGGING` | `true` | Enable transaction logging | true/false |
| `MCP_ANIME_TRANSACTION_LOG_CLIENT_IDS` | `true` | Log client identifiers | true/false |
| `MCP_ANIME_TRANSACTION_LOG_QUERY_DETAILS` | `true` | Log detailed query information | true/false |
| `MCP_ANIME_TRANSACTION_RETENTION_DAYS` | `30` | Days to retain transaction logs | 1-365 |
| `MCP_ANIME_TRANSACTION_CLEANUP_INTERVAL_HOURS` | `24` | Hours between cleanup runs | 1-168 |
| `MCP_ANIME_TRANSACTION_ENABLE_ANALYTICS` | `true` | Enable analytics generation | true/false |
| `MCP_ANIME_TRANSACTION_ANALYTICS_BATCH_SIZE` | `1000` | Analytics processing batch size | 100-10000 |
| `MCP_ANIME_TRANSACTION_TRACK_RESPONSE_TIMES` | `true` | Track response times | true/false |
| `MCP_ANIME_TRANSACTION_RESPONSE_TIME_PERCENTILES` | `50.0,90.0,95.0,99.0` | Response time percentiles | 0-100 (comma-separated) |
| `MCP_ANIME_TRANSACTION_ANONYMIZE_QUERIES` | `false` | Anonymize queries for privacy | true/false |
| `MCP_ANIME_TRANSACTION_MAX_QUERY_LOG_LENGTH` | `100` | Maximum query length to log | 10-1000 |

**Example:**
```bash
export MCP_ANIME_TRANSACTION_RETENTION_DAYS="60"
export MCP_ANIME_TRANSACTION_ANONYMIZE_QUERIES="true"
export MCP_ANIME_TRANSACTION_RESPONSE_TIME_PERCENTILES="50.0,90.0,95.0,99.0,99.9"
```

### 5. Global Settings

General server configuration options.

| Environment Variable | Default | Description | Valid Range |
|---------------------|---------|-------------|-------------|
| `MCP_ANIME_DEBUG_MODE` | `false` | Enable debug mode with verbose logging | true/false |
| `MCP_ANIME_ENVIRONMENT` | `production` | Environment name | Any string |

**Example:**
```bash
export MCP_ANIME_DEBUG_MODE="true"
export MCP_ANIME_ENVIRONMENT="development"
```

## Configuration Profiles

### Development Profile

Optimized for development with verbose logging and relaxed limits:

```bash
# Development configuration
export MCP_ANIME_DEBUG_MODE="true"
export MCP_ANIME_ENVIRONMENT="development"
export MCP_ANIME_DB_CACHE_SIZE_MB="32"
export MCP_ANIME_DOWNLOAD_PROTECTION_HOURS="1"  # Reduced for testing
export MCP_ANIME_SEARCH_MAX_LIMIT="50"
export MCP_ANIME_TRANSACTION_RETENTION_DAYS="7"
```

### Production Profile

Optimized for production with security and performance:

```bash
# Production configuration
export MCP_ANIME_DEBUG_MODE="false"
export MCP_ANIME_ENVIRONMENT="production"
export MCP_ANIME_DB_CACHE_SIZE_MB="128"
export MCP_ANIME_DB_PATH="/var/lib/mcp-anime/database.db"
export MCP_ANIME_DOWNLOAD_PROTECTION_HOURS="36"
export MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS="50.0"
export MCP_ANIME_TRANSACTION_ANONYMIZE_QUERIES="true"
export MCP_ANIME_TRANSACTION_RETENTION_DAYS="90"
```

### High-Performance Profile

Optimized for high-traffic scenarios:

```bash
# High-performance configuration
export MCP_ANIME_DB_CACHE_SIZE_MB="256"
export MCP_ANIME_DB_MAX_CONNECTIONS="20"
export MCP_ANIME_DB_ENABLE_WAL="true"
export MCP_ANIME_SEARCH_ENABLE_RESULT_CACHING="true"
export MCP_ANIME_SEARCH_CACHE_TTL_SECONDS="600"
export MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS="25.0"
export MCP_ANIME_TRANSACTION_ANALYTICS_BATCH_SIZE="2000"
```

## Configuration Validation

The server automatically validates configuration on startup and provides detailed error messages for invalid settings.

### Common Validation Rules

1. **Path Validation**: Database paths must be writable
2. **Range Validation**: Numeric values must be within specified ranges
3. **Consistency Validation**: Related settings must be consistent (e.g., max_limit >= default_limit)
4. **Resource Validation**: Settings are checked against available system resources

### Validation Examples

```bash
# Invalid: max_limit < default_limit
export MCP_ANIME_SEARCH_DEFAULT_LIMIT="20"
export MCP_ANIME_SEARCH_MAX_LIMIT="10"  # Error: max_limit must be >= default_limit

# Invalid: retention shorter than cleanup interval
export MCP_ANIME_TRANSACTION_RETENTION_DAYS="1"
export MCP_ANIME_TRANSACTION_CLEANUP_INTERVAL_HOURS="48"  # Error: retention too short

# Invalid: cache size too large
export MCP_ANIME_DB_CACHE_SIZE_MB="2048"  # Warning: may impact memory usage
```

## Configuration Testing

### Validate Current Configuration

```python
from mcp_server_anime.core.database_config import validate_config

# Check for configuration issues
issues = validate_config()
if issues:
    for issue in issues:
        print(f"Configuration issue: {issue}")
else:
    print("Configuration is valid")
```

### Load and Inspect Configuration

```python
from mcp_server_anime.core.database_config import get_local_db_config

# Load configuration
config = get_local_db_config()

# Get configuration summary
summary = config.get_summary()
print(f"Database path: {summary['database']['path']}")
print(f"Protection hours: {summary['download']['protection_hours']}")
print(f"Search target: {summary['search']['target_response_ms']}ms")
```

## Performance Tuning

### Database Performance

- **Cache Size**: Increase `MCP_ANIME_DB_CACHE_SIZE_MB` for better performance (monitor memory usage)
- **WAL Mode**: Keep `MCP_ANIME_DB_ENABLE_WAL="true"` for better concurrency
- **Maintenance**: Adjust vacuum/analyze intervals based on usage patterns

### Search Performance

- **Response Time Target**: Set `MCP_ANIME_SEARCH_RESPONSE_TIME_TARGET_MS` based on your SLA requirements
- **Result Caching**: Enable caching for frequently searched terms
- **Query Limits**: Balance user experience with resource usage

### Transaction Logging

- **Retention**: Longer retention provides better analytics but uses more storage
- **Batch Size**: Larger batches improve analytics performance but use more memory
- **Anonymization**: Enable for privacy compliance (may impact debugging)

## Troubleshooting

### Common Issues

1. **Database Permission Errors**
   ```bash
   # Ensure database directory is writable
   mkdir -p ~/.cache/mcp-server-anime
   chmod 755 ~/.cache/mcp-server-anime
   ```

2. **High Memory Usage**
   ```bash
   # Reduce cache size
   export MCP_ANIME_DB_CACHE_SIZE_MB="32"
   ```

3. **Slow Search Performance**
   ```bash
   # Enable caching and increase cache size
   export MCP_ANIME_SEARCH_ENABLE_RESULT_CACHING="true"
   export MCP_ANIME_DB_CACHE_SIZE_MB="128"
   ```

4. **Download Rate Limiting Issues**
   ```bash
   # Check protection status (development only)
   export MCP_ANIME_DOWNLOAD_PROTECTION_HOURS="1"
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export MCP_ANIME_DEBUG_MODE="true"
```

This provides:
- Detailed configuration validation messages
- Performance timing information
- Database operation logging
- Transaction logging details

### Debug Tools

Use the enhanced debug script to test cache workflows:

```bash
# Test with default XML file (22.xml)
python debug_cache_workflow.py

# Test with specific XML file
python debug_cache_workflow.py 17550.xml

# Test with custom XML file
python debug_cache_workflow.py your_anime.xml
```

The debug script provides comprehensive cache testing including:
- Cache persistence verification
- Database storage validation
- Performance metrics analysis
- Access count tracking

### Cache Statistics Tool

Monitor cache performance and health with the analytics CLI:

```bash
# Show comprehensive cache statistics
python -m mcp_server_anime.cli.analytics_cli cache-stats --provider anidb

# Get JSON output for programmatic use
python -m mcp_server_anime.cli.analytics_cli cache-stats --provider anidb --json
```

The cache statistics tool provides:
- Service and database cache status
- Storage metrics (entries, sizes, distribution)
- Performance metrics (hit rates, access times)
- Provider and method breakdowns
- Real-time cache health monitoring

## Security Considerations

### Data Privacy

- Enable query anonymization in production: `MCP_ANIME_TRANSACTION_ANONYMIZE_QUERIES="true"`
- Limit query log length: `MCP_ANIME_TRANSACTION_MAX_QUERY_LOG_LENGTH="50"`
- Set appropriate retention periods: `MCP_ANIME_TRANSACTION_RETENTION_DAYS="30"`

### File System Security

- Use restrictive permissions on database files (600)
- Store database in secure location with limited access
- Regular backup of configuration and database files

### Rate Limiting

- Never disable download protection in production
- Use emergency override only in critical situations
- Monitor download attempts and failures

## Migration and Upgrades

### Configuration Migration

When upgrading, check for:
1. New configuration options
2. Changed default values
3. Deprecated settings
4. Validation rule changes

### Backup Configuration

```bash
# Save current environment configuration
env | grep MCP_ANIME_ > mcp-anime-config.env

# Restore configuration
source mcp-anime-config.env
```

## Support and Resources

- **Configuration Validation**: Use built-in validation functions
- **Performance Monitoring**: Enable transaction logging and analytics
- **Debug Information**: Use debug mode for troubleshooting
- **Documentation**: Refer to inline help and error messages

For additional support, check the server logs and use the built-in diagnostic tools.
