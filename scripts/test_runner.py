#!/usr/bin/env python3
"""Test runner script for MCP Server Anime project.

This script provides a comprehensive test execution framework using Poetry,
with support for different test categories, coverage reporting, and
test isolation management.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Test runner for executing tests with Poetry."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the test runner.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.poetry_cmd = ["poetry", "run"]
    
    def run_command(self, cmd: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a command using Poetry.
        
        Args:
            cmd: Command to run
            capture_output: Whether to capture output
            
        Returns:
            CompletedProcess result
        """
        full_cmd = self.poetry_cmd + cmd
        print(f"Running: {' '.join(full_cmd)}")
        
        return subprocess.run(
            full_cmd,
            cwd=self.project_root,
            capture_output=capture_output,
            text=True
        )
    
    def run_all_tests(self, coverage: bool = True, verbose: bool = False) -> int:
        """Run all tests.
        
        Args:
            coverage: Whether to collect coverage
            verbose: Whether to use verbose output
            
        Returns:
            Exit code
        """
        cmd = ["pytest"]
        
        if coverage:
            cmd.extend([
                "--cov=src/mcp_server_anime",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-branch"
            ])
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "--maxfail=10"])
        
        result = self.run_command(cmd)
        return result.returncode
    
    def run_unit_tests(self, coverage: bool = True, verbose: bool = False) -> int:
        """Run unit tests only.
        
        Args:
            coverage: Whether to collect coverage
            verbose: Whether to use verbose output
            
        Returns:
            Exit code
        """
        cmd = ["pytest", "-m", "not integration"]
        
        if coverage:
            cmd.extend([
                "--cov=src/mcp_server_anime",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-branch"
            ])
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "--maxfail=10"])
        
        result = self.run_command(cmd)
        return result.returncode
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """Run integration tests only.
        
        Args:
            verbose: Whether to use verbose output
            
        Returns:
            Exit code
        """
        cmd = ["pytest", "-m", "integration"]
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "--maxfail=5"])
        
        # Set environment variable to enable integration tests
        import os
        env = os.environ.copy()
        env["RUN_INTEGRATION_TESTS"] = "1"
        
        full_cmd = self.poetry_cmd + cmd
        print(f"Running: {' '.join(full_cmd)}")
        
        result = subprocess.run(
            full_cmd,
            cwd=self.project_root,
            env=env
        )
        return result.returncode
    
    def run_coverage_report(self, fail_under: float = 90.0) -> int:
        """Run tests with comprehensive coverage reporting.
        
        Args:
            fail_under: Minimum coverage percentage required
            
        Returns:
            Exit code
        """
        cmd = [
            "pytest",
            "-m", "not integration",  # Focus on unit tests for coverage
            "--cov=src/mcp_server_anime",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-branch",
            f"--cov-fail-under={fail_under}",
            "--tb=short"
        ]
        
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print(f"\n✅ Coverage target of {fail_under}% met!")
            print("📊 Coverage reports generated:")
            print("  - Terminal: displayed above")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")
        else:
            print(f"\n❌ Coverage target of {fail_under}% not met!")
        
        return result.returncode
    
    def run_specific_test(self, test_path: str, verbose: bool = True) -> int:
        """Run a specific test file or test function.
        
        Args:
            test_path: Path to test file or test function
            verbose: Whether to use verbose output
            
        Returns:
            Exit code
        """
        cmd = ["pytest", test_path]
        
        if verbose:
            cmd.extend(["-v", "--tb=long"])
        else:
            cmd.extend(["--tb=short"])
        
        result = self.run_command(cmd)
        return result.returncode
    
    def run_failing_tests_only(self) -> int:
        """Run only tests that failed in the last run.
        
        Returns:
            Exit code
        """
        cmd = ["pytest", "--lf", "-v", "--tb=short"]
        result = self.run_command(cmd)
        return result.returncode
    
    def run_tests_with_isolation_check(self) -> int:
        """Run tests with extra isolation checking.
        
        Returns:
            Exit code
        """
        cmd = [
            "pytest",
            "-v",
            "--tb=short",
            "--maxfail=1",  # Stop on first failure to identify isolation issues
            "--random-order",  # Run tests in random order to catch isolation issues
        ]
        
        result = self.run_command(cmd)
        return result.returncode
    
    def validate_test_environment(self) -> int:
        """Validate that the test environment is properly set up.
        
        Returns:
            Exit code
        """
        print("🔍 Validating test environment...")
        
        # Check Poetry installation
        try:
            result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Poetry not found or not working")
                return 1
            print(f"✅ Poetry: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Poetry not found in PATH")
            return 1
        
        # Check Python version
        result = self.run_command(["python", "--version"], capture_output=True)
        if result.returncode != 0:
            print("❌ Python not accessible through Poetry")
            return 1
        print(f"✅ Python: {result.stdout.strip()}")
        
        # Check pytest installation
        result = self.run_command(["pytest", "--version"], capture_output=True)
        if result.returncode != 0:
            print("❌ pytest not accessible through Poetry")
            return 1
        print(f"✅ pytest: {result.stdout.strip()}")
        
        # Check test discovery
        result = self.run_command(["pytest", "--collect-only", "-q"], capture_output=True)
        if result.returncode != 0:
            print("❌ Test discovery failed")
            print(result.stderr)
            return 1
        
        # Parse test count from output
        lines = result.stdout.split('\n')
        test_count = 0
        for line in lines:
            if 'collected' in line and 'items' in line:
                # Extract number from "collected X items"
                import re
                match = re.search(r'collected (\d+) items', line)
                if match:
                    test_count = int(match.group(1))
                    break
        
        if test_count == 0:
            # Fallback: count lines with test indicators
            test_count = len([line for line in lines if '::' in line])
        
        print(f"✅ Test discovery: {test_count} tests found")
        
        print("\n🎉 Test environment validation successful!")
        return 0


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Test runner for MCP Server Anime")
    parser.add_argument(
        "command",
        choices=[
            "all", "unit", "integration", "coverage", "specific", 
            "failing", "isolation", "validate"
        ],
        help="Test command to run"
    )
    parser.add_argument(
        "--test-path",
        help="Specific test path (for 'specific' command)"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage collection"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=90.0,
        help="Minimum coverage percentage (default: 90.0)"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.command == "validate":
        return runner.validate_test_environment()
    elif args.command == "all":
        return runner.run_all_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        )
    elif args.command == "unit":
        return runner.run_unit_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        )
    elif args.command == "integration":
        return runner.run_integration_tests(verbose=args.verbose)
    elif args.command == "coverage":
        return runner.run_coverage_report(fail_under=args.fail_under)
    elif args.command == "specific":
        if not args.test_path:
            print("❌ --test-path required for 'specific' command")
            return 1
        return runner.run_specific_test(args.test_path, verbose=args.verbose)
    elif args.command == "failing":
        return runner.run_failing_tests_only()
    elif args.command == "isolation":
        return runner.run_tests_with_isolation_check()
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())