#!/usr/bin/env python3
"""Development environment setup and utilities for mcp-server-anime.

This module provides tools for setting up and managing the development environment.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str, check: bool = True) -> bool:
    """Run a command with error handling.

    Args:
        cmd: Command to run
        description: Description of the command
        check: Whether to check for errors

    Returns:
        True if successful, False otherwise
    """
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=not check)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            print(f"✗ {description} failed with exit code {result.returncode}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"✗ Command not found for: {description}")
        return False


def setup_dev_environment(skip_tests: bool = False) -> int:
    """Set up the development environment.

    Args:
        skip_tests: Whether to skip running tests

    Returns:
        Exit code (0 for success)
    """
    print("MCP Server Anime - Development Setup")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found. Please run from project root.")
        return 1

    setup_steps = [
        # Install dependencies
        (
            ["poetry", "install", "--extras", "dev"],
            "Installing dependencies with Poetry",
        ),
        # Install pre-commit hooks
        (["poetry", "run", "pre-commit", "install"], "Installing pre-commit hooks"),
        # Run initial code formatting
        (["poetry", "run", "ruff", "format", "."], "Formatting code with ruff"),
        # Run linting
        (["poetry", "run", "ruff", "check", "."], "Linting code with ruff", False),
        # Run type checking
        (["poetry", "run", "mypy", "src"], "Type checking with mypy", False),
    ]

    if not skip_tests:
        setup_steps.append(
            (
                [
                    "poetry",
                    "run",
                    "pytest",
                    "-m",
                    "not integration",
                    "--tb=short",
                    "-q",
                ],
                "Running unit tests",
                False,
            )
        )

    failed_steps = []

    for step in setup_steps:
        cmd, description = step[0], step[1]
        check = step[2] if len(step) > 2 else True
        success = run_command(cmd, description, check=check)
        if not success and check:
            failed_steps.append(description)
        print()

    # Summary
    print("Setup Summary:")
    print("-" * 30)

    if not failed_steps:
        print("✓ All setup steps completed successfully!")
        print("\nDevelopment environment is ready. You can now:")
        print("  - Run tests: make test-unit")
        print("  - Start server: poetry run mcp-server-anime")
        print("  - Format code: make format")
        print("  - Check code: make quality")
        return 0
    else:
        print("✗ Some setup steps failed:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nPlease resolve the issues and run the setup again.")
        return 1


def validate_environment() -> int:
    """Validate that the development environment is properly set up.

    Returns:
        Exit code (0 for success)
    """
    print("🔍 Validating development environment...")
    print("=" * 50)

    checks = [
        (["poetry", "--version"], "Poetry installation"),
        (["poetry", "run", "python", "--version"], "Python environment"),
        (["poetry", "run", "pytest", "--version"], "pytest installation"),
        (["poetry", "run", "ruff", "--version"], "ruff installation"),
        (["poetry", "run", "mypy", "--version"], "mypy installation"),
    ]

    failed_checks = []

    for cmd, description in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            version = result.stdout.strip().split("\n")[0]
            print(f"✅ {description}: {version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {description}: Failed")
            failed_checks.append(description)

    # Check test discovery
    print("\n🔍 Checking test discovery...")
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Count collected tests
        import re

        match = re.search(r"(\d+) tests? collected", result.stdout)
        if match:
            test_count = match.group(1)
            print(f"✅ Test discovery: {test_count} tests found")
        else:
            print("✅ Test discovery: Tests found")
    except subprocess.CalledProcessError:
        print("❌ Test discovery: Failed")
        failed_checks.append("Test discovery")

    print("\n" + "=" * 50)
    if not failed_checks:
        print("🎉 Environment validation successful!")
        return 0
    else:
        print("❌ Environment validation failed:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\nRun 'python scripts/dev_tools.py setup' to fix issues.")
        return 1


def clean_environment() -> int:
    """Clean up development environment artifacts.

    Returns:
        Exit code (0 for success)
    """
    print("🧹 Cleaning development environment...")
    print("=" * 50)

    # Directories to remove
    dirs_to_remove = [
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "build",
        "dist",
        ".coverage",
        "coverage.xml",
        "tests.log",
    ]

    removed_count = 0
    for dir_name in dirs_to_remove:
        path = Path(dir_name)
        if path.exists():
            if path.is_dir():
                import shutil

                shutil.rmtree(path)
                print(f"✓ Removed directory: {dir_name}")
            else:
                path.unlink()
                print(f"✓ Removed file: {dir_name}")
            removed_count += 1

    # Remove __pycache__ directories
    for pycache in Path(".").rglob("__pycache__"):
        import shutil

        shutil.rmtree(pycache)
        removed_count += 1

    # Remove .pyc files
    for pyc in Path(".").rglob("*.pyc"):
        pyc.unlink()
        removed_count += 1

    print(f"\n✅ Cleaned {removed_count} items")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Development environment tools for mcp-server-anime"
    )
    parser.add_argument(
        "command", choices=["setup", "validate", "clean"], help="Command to run"
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip running tests during setup"
    )

    args = parser.parse_args()

    if args.command == "setup":
        return setup_dev_environment(skip_tests=args.skip_tests)
    elif args.command == "validate":
        return validate_environment()
    elif args.command == "clean":
        return clean_environment()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
