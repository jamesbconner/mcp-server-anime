#!/usr/bin/env python3
"""Test command entry points for Poetry scripts.

This module provides entry points for various test commands that can be
executed through Poetry scripts.
"""

import subprocess
import sys


def run_pytest_command(args: list[str]) -> int:
    """Run pytest with the given arguments.

    Args:
        args: Arguments to pass to pytest

    Returns:
        Exit code from pytest
    """
    cmd = ["pytest", *args]
    result = subprocess.run(cmd)
    return result.returncode


def test_all() -> int:
    """Run all tests."""
    return run_pytest_command([])


def test_unit() -> int:
    """Run unit tests only."""
    return run_pytest_command(["-m", "not integration"])


def test_integration() -> int:
    """Run integration tests only."""
    import os

    # Set environment variable to enable integration tests
    os.environ["RUN_INTEGRATION_TESTS"] = "1"
    return run_pytest_command(["-m", "integration"])


def test_coverage() -> int:
    """Run tests with coverage reporting."""
    return run_pytest_command(
        [
            "--cov=src/mcp_server_anime",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-branch",
        ]
    )


def test_coverage_unit() -> int:
    """Run unit tests with coverage reporting."""
    return run_pytest_command(
        [
            "-m",
            "not integration",
            "--cov=src/mcp_server_anime",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-branch",
        ]
    )


def test_fast() -> int:
    """Run tests with minimal output and early failure."""
    return run_pytest_command(["--tb=short", "--maxfail=5"])


def test_verbose() -> int:
    """Run tests with verbose output."""
    return run_pytest_command(["-v", "--tb=long"])


def test_quiet() -> int:
    """Run tests with minimal output."""
    return run_pytest_command(["-q", "--tb=no"])


def test_failing() -> int:
    """Run only tests that failed in the last run."""
    return run_pytest_command(["--lf", "-v"])


def test_isolation() -> int:
    """Run tests with isolation checking."""
    return run_pytest_command(["-v", "--tb=short", "--maxfail=1", "--random-order"])


if __name__ == "__main__":
    # Allow running specific test commands from command line
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "all":
            sys.exit(test_all())
        elif command == "unit":
            sys.exit(test_unit())
        elif command == "integration":
            sys.exit(test_integration())
        elif command == "coverage":
            sys.exit(test_coverage())
        elif command == "coverage-unit":
            sys.exit(test_coverage_unit())
        elif command == "fast":
            sys.exit(test_fast())
        elif command == "verbose":
            sys.exit(test_verbose())
        elif command == "quiet":
            sys.exit(test_quiet())
        elif command == "failing":
            sys.exit(test_failing())
        elif command == "isolation":
            sys.exit(test_isolation())
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    else:
        # Default to running all tests
        sys.exit(test_all())
