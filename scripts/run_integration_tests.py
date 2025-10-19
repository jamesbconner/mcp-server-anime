#!/usr/bin/env python3
"""Script to run integration tests with proper configuration.

This script provides a convenient way to run integration tests locally
with appropriate warnings and configuration checks.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def check_network_connectivity() -> bool:
    """Check if network connectivity is available for API calls."""
    try:
        import socket
        
        # Try to connect to AniDB API host
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("api.anidb.net", 9001))
        sock.close()
        
        return result == 0
    except Exception:
        return False


def check_poetry_installation() -> bool:
    """Check if Poetry is installed and available."""
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_integration_tests(
    verbose: bool = False,
    fail_fast: bool = False,
    coverage: bool = False,
    specific_test: str | None = None,
) -> int:
    """Run integration tests with specified configuration.
    
    Args:
        verbose: Enable verbose output
        fail_fast: Stop on first failure
        coverage: Enable coverage reporting
        specific_test: Run only a specific test pattern
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Build pytest command
    cmd = ["poetry", "run", "pytest"]
    
    # Add integration test marker
    if specific_test:
        cmd.extend(["-k", specific_test])
    else:
        cmd.extend(["-m", "integration"])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add fail fast
    if fail_fast:
        cmd.append("--maxfail=1")
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov-integration",
        ])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--durations=10",  # Show 10 slowest tests
    ])
    
    # Set environment variables
    env = os.environ.copy()
    env["RUN_INTEGRATION_TESTS"] = "1"
    
    print("🚀 Running integration tests...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run the tests
    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run integration tests for mcp-server-anime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all integration tests
  %(prog)s --verbose                # Run with verbose output
  %(prog)s --fail-fast              # Stop on first failure
  %(prog)s --coverage               # Run with coverage reporting
  %(prog)s --test search            # Run only tests matching 'search'
  %(prog)s --dry-run                # Check configuration without running tests

Environment Variables:
  SKIP_INTEGRATION_TESTS=1          # Skip integration tests
  RUN_INTEGRATION_TESTS=1           # Force run integration tests
        """,
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true", 
        help="Stop on first failure"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "--test", "-k",
        help="Run only tests matching this pattern"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check configuration without running tests"
    )
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run from project root.")
        return 1
    
    # Check Poetry installation
    if not check_poetry_installation():
        print("❌ Error: Poetry not found. Please install Poetry first.")
        print("   Visit: https://python-poetry.org/docs/#installation")
        return 1
    
    # Check network connectivity
    print("🔍 Checking network connectivity...")
    if not check_network_connectivity():
        print("⚠️  Warning: Cannot connect to AniDB API (api.anidb.net:9001)")
        print("   Integration tests may fail due to network issues.")
        
        response = input("Continue anyway? [y/N]: ")
        if response.lower() not in ("y", "yes"):
            print("❌ Aborted by user")
            return 1
    else:
        print("✅ Network connectivity OK")
    
    # Check if integration tests are configured to be skipped
    skip_env = os.getenv("SKIP_INTEGRATION_TESTS", "").lower()
    if skip_env in ("1", "true", "yes"):
        print("⚠️  Warning: SKIP_INTEGRATION_TESTS is set to skip integration tests")
        print("   Unset this environment variable to run integration tests.")
        return 1
    
    # Show configuration
    print("\n📋 Configuration:")
    print(f"   Verbose: {args.verbose}")
    print(f"   Fail fast: {args.fail_fast}")
    print(f"   Coverage: {args.coverage}")
    print(f"   Specific test: {args.test or 'All integration tests'}")
    
    if args.dry_run:
        print("\n✅ Dry run completed - configuration looks good!")
        return 0
    
    # Warning about API usage
    print("\n⚠️  IMPORTANT:")
    print("   Integration tests will make real API calls to AniDB")
    print("   Please be respectful of their API rate limits")
    print("   Tests include built-in rate limiting (2.5s between requests)")
    
    # Countdown
    print("\nStarting in 3 seconds... (Ctrl+C to cancel)")
    try:
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return 130
    
    # Run the tests
    return run_integration_tests(
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        coverage=args.coverage,
        specific_test=args.test,
    )


if __name__ == "__main__":
    sys.exit(main())