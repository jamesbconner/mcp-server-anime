"""Command-line interface tools for MCP Anime Server database management.

This package provides CLI tools for database initialization, maintenance,
monitoring, and troubleshooting of the local anime database.
"""

# Lazy imports to avoid module loading issues with python -m
def get_analytics_main():
    """Get the analytics CLI main function."""
    from .analytics_cli import main as analytics_main
    return analytics_main

def get_database_main():
    """Get the database CLI main function."""
    from .database_cli import main as database_main
    return database_main

# Backward compatibility: direct imports for existing code
# These are lazy-loaded to avoid import issues
def __getattr__(name):
    """Provide backward compatibility for direct imports."""
    if name == 'analytics_main':
        from .analytics_cli import main
        return main
    elif name == 'database_main':
        from .database_cli import main
        return main
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["get_analytics_main", "get_database_main", "analytics_main", "database_main"]
