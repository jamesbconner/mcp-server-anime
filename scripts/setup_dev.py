#!/usr/bin/env python3
"""
Development setup script for mcp-server-anime.

This script sets up the development environment with all necessary tools.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str, check: bool = True) -> bool:
    """Run a command with error handling."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=check)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"✗ Command not found for: {description}")
        return False


def main():
    """Main setup function."""
    print("MCP Server Anime - Development Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found. Please run from project root.")
        return 1
    
    setup_steps = [
        # Install dependencies
        (["poetry", "install"], "Installing dependencies with Poetry"),
        
        # Install pre-commit hooks
        (["poetry", "run", "pre-commit", "install"], "Installing pre-commit hooks"),
        
        # Run initial code formatting
        (["poetry", "run", "ruff", "format", "."], "Formatting code with ruff"),
        
        # Run linting
        (["poetry", "run", "ruff", "check", "."], "Linting code with ruff"),
        
        # Run type checking
        (["poetry", "run", "mypy", "."], "Type checking with mypy"),
        
        # Run security scan
        (["poetry", "run", "bandit", "-r", "src/"], "Security scanning with bandit"),
        
        # Run tests
        (["poetry", "run", "pytest", "--tb=short"], "Running test suite"),
    ]
    
    failed_steps = []
    
    for cmd, description in setup_steps:
        success = run_command(cmd, description, check=False)
        if not success:
            failed_steps.append(description)
        print()
    
    # Summary
    print("Setup Summary:")
    print("-" * 20)
    
    if not failed_steps:
        print("✓ All setup steps completed successfully!")
        print("\nDevelopment environment is ready. You can now:")
        print("  - Run tests: poetry run pytest")
        print("  - Start server: poetry run mcp-server-anime")
        print("  - Format code: poetry run ruff format .")
        print("  - Check code: poetry run ruff check .")
        return 0
    else:
        print("✗ Some setup steps failed:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nPlease resolve the issues and run the setup again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())