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

__all__ = ["get_analytics_main", "get_database_main"]
