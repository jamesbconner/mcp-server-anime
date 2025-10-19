"""Test basic project structure and imports."""

from importlib import import_module

import pytest


def test_package_imports() -> None:
    """Test that the main package can be imported."""
    import mcp_server_anime

    assert mcp_server_anime.__version__ == "0.2.0"
    assert mcp_server_anime.__author__ == "MCP Server Anime"
    assert "anime data" in mcp_server_anime.__description__.lower()


def test_server_module_imports() -> None:
    """Test that the server module can be imported."""
    from mcp_server_anime import server

    assert hasattr(server, "main")
    assert hasattr(server, "setup_logging")
    assert hasattr(server, "create_server")


def test_required_dependencies_available() -> None:
    """Test that all required dependencies are available."""
    required_packages = [
        "mcp",
        "httpx",
        "pydantic",
        "lxml",
    ]

    for package in required_packages:
        try:
            import_module(package)
        except ImportError:
            pytest.fail(f"Required package '{package}' is not available")


def test_dev_dependencies_available() -> None:
    """Test that development dependencies are available."""
    dev_packages = [
        "pytest",
        "ruff",
        "mypy",
        "bandit",
    ]

    for package in dev_packages:
        try:
            import_module(package)
        except ImportError:
            pytest.fail(f"Development package '{package}' is not available")
