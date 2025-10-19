# Kiro MCP Server Configuration Guide

This guide explains how to configure and use the mcp-server-anime with Kiro IDE.

## Prerequisites

1. **Kiro IDE**: Ensure you have Kiro IDE installed and running
2. **uvx**: Install `uv` and `uvx` for package management:
   ```bash
   # Install uv (Python package manager)
   pip install uv
   # uvx is included with uv
   ```

## Installation

### Method 1: Automatic Installation via Kiro

1. Open Kiro IDE
2. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Search for "MCP" and select "Configure MCP Servers"
4. Add a new server configuration (see Configuration section below)
5. Kiro will automatically install the package when first used

### Method 2: Pre-install with uvx

```bash
uvx install mcp-server-anime
```

## Configuration

### Basic Configuration

Add the following to your Kiro MCP configuration file:

**Location**: `.kiro/settings/mcp.json` (workspace-level) or `~/.kiro/settings/mcp.json` (user-level)

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

### Advanced Configuration with Environment Variables

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
| `env` | Environment variables | See environment variables section |
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

The server provides these tools to Kiro:

#### anime_search
- **Purpose**: Search for anime by title
- **Usage**: "Search for anime with 'dragon' in the title"
- **Parameters**: query (required), limit (optional, max 20)

#### anime_details  
- **Purpose**: Get detailed anime information
- **Usage**: "Get details for anime ID 9541"
- **Parameters**: aid (AniDB anime ID, required)

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

### Common Configuration Issues

**Issue**: Server shows as "Disconnected"
**Solution**: 
- Verify JSON syntax in mcp.json
- Check that uvx is in PATH
- Restart Kiro after configuration changes

**Issue**: Tools not appearing in chat
**Solution**:
- Verify server is connected
- Check autoApprove settings
- Try manually approving tools when prompted

**Issue**: API rate limit errors
**Solution**:
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

Configure Kiro to help with anime research:

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

For content creators needing anime information:

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