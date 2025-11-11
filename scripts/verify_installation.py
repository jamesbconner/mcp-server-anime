#!/usr/bin/env python3
"""
Installation verification script for mcp-server-anime.

This script verifies that the package is properly installed and can be run.
"""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"Testing: {description}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✓ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ {description} - FAILED")
            if result.stderr.strip():
                print(f"  Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - TIMEOUT")
        return False
    except FileNotFoundError:
        print(f"✗ {description} - COMMAND NOT FOUND")
        return False
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False


def main():
    """Main verification function."""
    print("MCP Server Anime - Installation Verification")
    print("=" * 50)

    tests = [
        # Test Python version
        ([sys.executable, "--version"], "Python version check"),
        # Test package import
        (
            [
                sys.executable,
                "-c",
                "import mcp_server_anime; print('Import successful')",
            ],
            "Package import",
        ),
        # Test entry point
        (["mcp-server-anime", "--version"], "Entry point version check"),
        # Test help command
        (["mcp-server-anime", "--help"], "Help command"),
        # Test uvx compatibility (if uvx is available)
        (["uvx", "--version"], "uvx availability (optional)"),
    ]

    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
        print()

    # Summary
    print("Verification Summary:")
    print("-" * 30)

    passed = 0
    total = len(results)

    for description, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status:4} | {description}")
        if success:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed! Installation is working correctly.")
        return 0
    elif passed >= total - 1:  # Allow uvx to fail
        print("⚠ Most tests passed. Installation should work.")
        return 0
    else:
        print("✗ Some tests failed. Please check the installation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
