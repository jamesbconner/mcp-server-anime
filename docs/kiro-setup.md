# Kiro MCP Setup Guide

Complete guide for setting up and using the MCP Server Anime with Kiro IDE.

## Table of Contents

- [Quick Setup](#quick-setup)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Local Development Setup](#local-development-setup)
- [Usage in Kiro](#usage-in-kiro)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Integration Examples](#integration-examples)

## Quick Setup

For most users, the standard `uvx` setup is recommended:

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

**Location**: `.kiro/settings/mcp.json` (workspace) or `~/.kiro/settings/mcp.json` (global)

## Prerequisites

1. **Kiro IDE**: Ensure you have Kiro IDE installed and running
2. **Python 3.12+**: Required for the MCP server
3. **uvx**: Install `uv` and `uvx` for package management:
   ```bash
   pip install uv
   # uvx is included with uv
   ```

## Installation Methods

### Method 1: Automatic Installation (Recommended)

1. Open Kiro IDE
2. Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Search for "MCP" → "Configure MCP Servers"
4. Add the configuration (see Quick Setup above)
5. Kiro will automatically install the package when first used

### Method 2: Pre-install with uvx

```bash
uvx install mcp-server-anime
```

### Method 3: Local Development

See [Local Development Setup](#local-development-setup) section below.

## Configuration

### Basic Configuration

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime", "--log-level", "INFO"],
      "disabled": false,
      "env": {
        "ANIDB_CLIENT_NAME": "my-kiro-app",
        "ANIDB_CLIENT_VERSION": "1",
        "ANIDB_RATE_LIMIT_DELAY": "2.0",
        "ANIDB_CACHE_TTL": "3600"
      },
      "autoApprove": [
        "anime_search",
        "anime_details"
      ]
    }
  }
}
```

### Configuration Options

| Option | Description | Example |
|--------|-------------|---------|
| `command` | Command to run the server | `"uvx"` |
| `args` | Arguments for the command | `["mcp-server-anime"]` |
| `disabled` | Whether the server is disabled | `false` |
| `env` | Environment variables | See below |
| `autoApprove` | Tools to auto-approve | `["anime_search"]` |

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ANIDB_CLIENT_NAME` | Your app name for AniDB | `mcp-server-anidb` | `my-kiro-app` |
| `ANIDB_CLIENT_VERSION` | Your app version | `1` | `1` |
| `ANIDB_PROTOCOL_VERSION` | AniDB protocol version | `1` | `1` |
| `ANIDB_BASE_URL` | AniDB API endpoint | `http://api.anidb.net:9001/httpapi` | Custom URL |
| `ANIDB_RATE_LIMIT_DELAY` | Seconds between requests | `2.0` | `3.0` |
| `ANIDB_MAX_RETRIES` | Max retry attempts | `3` | `5` |
| `ANIDB_CACHE_TTL` | Cache duration (seconds) | `3600` | `7200` |

## Local Development Setup

When developing the MCP server locally or when `uvx` caching causes issues, use the direct Python executable approach.

### Prerequisites for Development

1. **Python Environment**: Python 3.12+ installed
2. **Package Installation**: Install the package in your environment
3. **Source Code**: Have the source code available locally

### Configuration Steps

#### 1. Find Your Python Executable Path

**For Anaconda/Miniconda:**
```bash
conda info --envs
# Look for your environment path
```

**For Virtual Environments:**
```bash
# Activate your environment first
which python  # Linux/Mac
where python  # Windows
```

#### 2. Locate Your Source Code Directory

Note the full path to your cloned repository:
- Windows: `D:/Documents/Code/mcp-server-anime`
- Linux/Mac: `/home/user/projects/mcp-server-anime`

#### 3. Update Kiro MCP Configuration

**Windows Example:**
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

**Linux/Mac Example:**
```json
{
  "mcpServers": {
    "anime": {
      "command": "/home/user/.conda/envs/mcp-server-anime/bin/python",
      "args": ["-m", "mcp_server_anime.server"],
      "cwd": "/home/user/projects/mcp-server-anime",
      "env": {
        "PYTHONPATH": "/home/user/projects/mcp-server-anime/src"
      },
      "disabled": false
    }
  }
}
```

### Development Configuration Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `command` | Direct path to Python executable | `D:/Languages/Anaconda/envs/mcp-server-anime/python.exe` |
| `args` | Arguments to run the server module | `["-m", "mcp_server_anime.server"]` |
| `cwd` | Working directory for the process | `D:/Documents/Code/mcp-server-anime` |
| `env.PYTHONPATH` | Path to source code | `D:/Documents/Code/mcp-server-anime/src` |

### Switching Back to Production

Once you're ready to use the published version:

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

## Usage in Kiro

### 1. Verify Server Connection

1. Open Kiro IDE
2. Look for the MCP server panel (usually in the sidebar)
3. Verify that "anime" server shows as "Connected"
4. If not connected, check the server logs for errors

### 2. Using Anime Tools in Chat

Once configured, you can use anime-related queries in Kiro's AI chat:

**Example Queries:**
- "Search for anime about pirates"
- "Find information about Attack on Titan"
- "What's the episode count for Demon Slayer?"
- "Show me details for anime ID 9541"

### 3. Available Tools

#### anime_search
- **Purpose**: Search for anime by title
- **Usage**: "Search for anime with 'dragon' in the title"
- **Parameters**:
  - `query` (required): Search term
  - `limit` (optional): Max results (default: 10, max: 20)

#### anime_details
- **Purpose**: Get detailed anime information
- **Usage**: "Get details for anime ID 9541"
- **Parameters**:
  - `aid` (required): AniDB anime ID

## Troubleshooting

### Server Not Connecting

1. **Check uvx installation**:
   ```bash
   uvx --version
   ```

2. **Verify package installation**:
   ```bash
   uvx run mcp-server-anime --version
   ```

3. **Check Kiro MCP logs**:
   - Open Kiro's developer tools
   - Look for MCP-related error messages
   - Check the Output panel for server logs

### Common Issues

#### Issue: `ModuleNotFoundError: No module named 'mcp_server_anime'`

**Cause**: Python can't find the module.

**Solutions**:
1. Check PYTHONPATH points to the `src` directory
2. Run `poetry install` or `pip install -e .` in the project directory
3. Verify the `command` points to the correct Python executable

#### Issue: `ImportError: cannot import name 'APIError'`

**Cause**: Using an outdated cached version from `uvx`.

**Solution**: Switch to the local development setup.

#### Issue: Server shows as "Disconnected"

**Solutions**:
- Verify JSON syntax in mcp.json
- Check that uvx is in PATH
- Restart Kiro after configuration changes

#### Issue: Tools not appearing in chat

**Solutions**:
- Verify server is connected
- Check autoApprove settings
- Try manually approving tools when prompted

#### Issue: API rate limit errors

**Solutions**:
- Increase `ANIDB_RATE_LIMIT_DELAY` to 3.0 or higher
- Reduce concurrent requests

### Debug Mode

Enable debug logging for troubleshooting:

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime", "--log-level", "DEBUG"],
      "disabled": false
    }
  }
}
```

### Verification Steps

After updating the configuration:

1. **Restart Kiro** or reconnect the MCP server
2. **Check MCP Logs** for successful connection messages
3. **Verify Tools**: You should see these tools available:
   - `anime_search` - Search for anime by title
   - `anime_details` - Get detailed anime information

## Best Practices

### 1. Rate Limiting
- Keep default rate limit (2 seconds) or increase it
- Avoid making rapid successive requests
- Use caching effectively by not repeating identical queries

### 2. Error Handling
- Enable auto-approval for trusted tools
- Monitor server logs for API issues
- Have fallback queries ready for when API is unavailable

### 3. Performance
- Use specific search terms for better results
- Cache frequently accessed anime details
- Consider increasing cache TTL for stable data

### 4. Security
- Use workspace-level configuration for project-specific settings
- Avoid exposing sensitive information in environment variables
- Regularly update the package for security fixes

## Integration Examples

### Example 1: Anime Research Assistant

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime"],
      "disabled": false,
      "env": {
        "ANIDB_CLIENT_NAME": "anime-research-assistant",
        "ANIDB_CACHE_TTL": "7200"
      },
      "autoApprove": ["anime_search", "anime_details"]
    }
  }
}
```

**Usage**: "Help me research anime from the 1990s with mecha themes"

### Example 2: Content Creator Setup

```json
{
  "mcpServers": {
    "anime": {
      "command": "uvx",
      "args": ["mcp-server-anime", "--log-level", "WARNING"],
      "disabled": false,
      "env": {
        "ANIDB_CLIENT_NAME": "content-creator-tools",
        "ANIDB_RATE_LIMIT_DELAY": "1.5",
        "ANIDB_CACHE_TTL": "10800"
      },
      "autoApprove": ["anime_search"]
    }
  }
}
```

**Usage**: "Find popular anime from 2023 for my video script"

## Updates and Maintenance

### Updating the Server

```bash
# Update to latest version
uvx install --force mcp-server-anime

# Or reinstall
uvx uninstall mcp-server-anime
uvx install mcp-server-anime
```

### Monitoring

- Check Kiro's MCP server panel regularly
- Monitor API usage to avoid rate limits
- Review server logs for performance issues
- Update configuration as needed for new features

## Support

If you encounter issues:

1. Check this documentation first
2. Review the main [README.md](../README.md) for general troubleshooting
3. Check the [GitHub Issues](https://github.com/example/mcp-server-anime/issues)
4. Create a new issue with:
   - Kiro version
   - Server configuration (sanitized)
   - Error messages
   - Steps to reproduce

## See Also

- [Configuration Guide](configuration.md) - General configuration options
- [Developer Guide](developer-guide.md) - Development workflow
- [Architecture](architecture.md) - System architecture
