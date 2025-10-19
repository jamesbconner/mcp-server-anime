"""Command-line interface tools for MCP Anime Server database management.

This package provides CLI tools for database initialization, maintenance,
monitoring, and troubleshooting of the local anime database.
"""

from .analytics_cli import main as analytics_main
from .database_cli import main as database_main

__all__ = ["analytics_main", "database_main"]
