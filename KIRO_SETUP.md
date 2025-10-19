# Kiro MCP Setup Guide

This guide provides detailed instructions for setting up the MCP Server Anime with Kiro IDE.

## Quick Setup (Production)

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

## Local Development Setup

When developing the MCP server locally or when `uvx` caching causes issues, use the direct Python executable approach.

### Prerequisites

1. **Python Environment**: Ensure you have Python 3.12+ installed
2. **Package Installation**: Install the package in your environment
3. **Source Code**: Have the source code available locally

### Configuration Steps

#### 1. Find Your Python Executable Path

**For Anaconda/Miniconda:**
```bash
conda info --envs
# Look for your environment path, e.g.:
# mcp-server-anime    D:\Languages\Anaconda\envs\mcp-server-anime
```

**For Virtual Environments:**
```bash
# Activate your environment first
which python  # Linux/Mac
where python  # Windows
```

#### 2. Locate Your Source Code Directory

Note the full path to your cloned repository, e.g.:
- Windows: `D:/Documents/Code/mcp-server-anime`
- Linux/Mac: `/home/user/projects/mcp-server-anime`

#### 3. Update Kiro MCP Configuration

Edit your Kiro MCP configuration file:
- **Workspace level**: `.kiro/settings/mcp.json` (in your project)
- **User level**: `~/.kiro/settings/mcp.json` (global)

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

### Configuration Parameters Explained

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `command` | Direct path to Python executable | `D:/Languages/Anaconda/envs/mcp-server-anime/python.exe` |
| `args` | Arguments to run the server module | `["-m", "mcp_server_anime.server"]` |
| `cwd` | Working directory for the process | `D:/Documents/Code/mcp-server-anime` |
| `env.PYTHONPATH` | Path to source code | `D:/Documents/Code/mcp-server-anime/src` |

### Troubleshooting

#### Issue: `ModuleNotFoundError: No module named 'mcp_server_anime'`

**Cause**: Python can't find the module in the current environment.

**Solutions**:
1. **Check PYTHONPATH**: Ensure it points to the `src` directory
2. **Install Package**: Run `poetry install` or `pip install -e .` in the project directory
3. **Verify Python Path**: Ensure the `command` points to the correct Python executable

#### Issue: `ImportError: cannot import name 'APIError'`

**Cause**: Using an outdated cached version from `uvx`.

**Solution**: Switch to the local development setup as described above.

#### Issue: Server starts but tools don't appear

**Cause**: Kiro might not be connecting to the server properly.

**Solutions**:
1. **Check Logs**: Look at Kiro's MCP logs for error messages
2. **Test Locally**: Run the server directly to verify it works:
   ```bash
   python -m mcp_server_anime.server --version
   ```
3. **Restart Kiro**: Sometimes a restart is needed to pick up configuration changes

### Verification

After updating the configuration:

1. **Restart Kiro** or reconnect the MCP server
2. **Check MCP Logs** for successful connection messages
3. **Verify Tools**: You should see these tools available:
   - `anidb_search` - Search for anime by title
   - `anidb_details` - Get detailed anime information

### Environment Variables (Optional)

You can add additional environment variables to customize the server behavior:

```json
{
  "mcpServers": {
    "anime": {
      "command": "...",
      "args": [...],
      "cwd": "...",
      "env": {
        "PYTHONPATH": "...",
        "ANIDB_CLIENT_NAME": "my-kiro-setup",
        "ANIDB_CLIENT_VERSION": "1",
        "ANIDB_RATE_LIMIT_DELAY": "2.0",
        "ANIDB_CACHE_TTL": "3600"
      },
      "disabled": false
    }
  }
}
```

## Switching Back to Production

Once you're ready to use the published version, simply change back to the `uvx` configuration:

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

This will use the latest published version from PyPI instead of your local development version.

## Support

If you encounter issues:

1. **Check the logs** in Kiro's MCP panel
2. **Verify the paths** in your configuration match your system
3. **Test the server** independently using the command line
4. **Review the main README** for additional troubleshooting steps

For development-specific issues, ensure you have the latest source code and all dependencies installed correctly.