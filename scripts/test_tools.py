#!/usr/bin/env python3
"""Consolidated test utilities for mcp-server-anime.

This module provides comprehensive test execution, coverage analysis,
and integration test management tools.
"""

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


class TestRunner:
    """Unified test runner for all test scenarios."""

    def __init__(self, verbose: bool = False):
        """Initialize the test runner.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.poetry_cmd = ["poetry", "run"]

    def run_command(self, cmd: list[str], env: dict | None = None) -> int:
        """Run a command and return exit code.

        Args:
            cmd: Command to run
            env: Environment variables

        Returns:
            Exit code
        """
        full_cmd = self.poetry_cmd + cmd
        if self.verbose:
            print(f"Running: {' '.join(full_cmd)}")

        result = subprocess.run(full_cmd, env=env or os.environ.copy())
        return result.returncode

    def run_unit_tests(self, coverage: bool = True) -> int:
        """Run unit tests.

        Args:
            coverage: Enable coverage reporting

        Returns:
            Exit code
        """
        print("🧪 Running unit tests...")
        cmd = ["pytest", "-m", "not integration"]

        if coverage:
            cmd.extend(
                [
                    "--cov=src/mcp_server_anime",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov",
                    "--cov-report=xml:coverage.xml",
                    "--cov-branch",
                ]
            )

        if self.verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "-q"])

        return self.run_command(cmd)

    def run_integration_tests(self, check_network: bool = True) -> int:
        """Run integration tests.

        Args:
            check_network: Check network connectivity first

        Returns:
            Exit code
        """
        if check_network:
            print("🔍 Checking network connectivity...")
            if not self._check_network():
                print("⚠️  Warning: Cannot connect to AniDB API")
                response = input("Continue anyway? [y/N]: ")
                if response.lower() not in ("y", "yes"):
                    print("❌ Aborted by user")
                    return 1

        print("🧪 Running integration tests...")
        print("⚠️  Note: This will make real API calls to AniDB")

        cmd = ["pytest", "-m", "integration"]

        if self.verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "-q"])

        env = os.environ.copy()
        env["RUN_INTEGRATION_TESTS"] = "1"

        return self.run_command(cmd, env=env)

    def run_all_tests(self, coverage: bool = True) -> int:
        """Run all tests.

        Args:
            coverage: Enable coverage reporting

        Returns:
            Exit code
        """
        print("🧪 Running all tests...")
        cmd = ["pytest"]

        if coverage:
            cmd.extend(
                [
                    "--cov=src/mcp_server_anime",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov",
                    "--cov-report=xml:coverage.xml",
                    "--cov-branch",
                ]
            )

        if self.verbose:
            cmd.append("-v")
        else:
            cmd.extend(["--tb=short", "-q"])

        return self.run_command(cmd)

    def run_specific_test(self, test_path: str) -> int:
        """Run a specific test file or function.

        Args:
            test_path: Path to test file or function

        Returns:
            Exit code
        """
        print(f"🧪 Running specific test: {test_path}")
        cmd = ["pytest", test_path, "-v", "--tb=long"]
        return self.run_command(cmd)

    def run_failing_tests(self) -> int:
        """Run only tests that failed in the last run.

        Returns:
            Exit code
        """
        print("🧪 Running previously failed tests...")
        cmd = ["pytest", "--lf", "-v", "--tb=short"]
        return self.run_command(cmd)

    def _check_network(self) -> bool:
        """Check if network connectivity is available."""
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("api.anidb.net", 9001))
            sock.close()
            return result == 0
        except Exception:
            return False


class CoverageAnalyzer:
    """Analyze and report on test coverage."""

    def __init__(self, target: float = 90.0):
        """Initialize the coverage analyzer.

        Args:
            target: Target coverage percentage
        """
        self.target = target

    def analyze_coverage(self, detailed: bool = False) -> int:
        """Analyze coverage and provide recommendations.

        Args:
            detailed: Show detailed analysis

        Returns:
            Exit code (0 if target met, 1 otherwise)
        """
        print("📊 Analyzing test coverage...")
        print("=" * 60)

        # Run tests with coverage
        result = subprocess.run(
            [
                "poetry",
                "run",
                "pytest",
                "-m",
                "not integration",
                "--cov=src/mcp_server_anime",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
                "-q",
            ],
            capture_output=False,
        )

        if result.returncode != 0:
            print("❌ Tests failed. Please fix failing tests first.")
            return 1

        # Parse coverage XML
        coverage_data = self._parse_coverage_xml()
        if not coverage_data:
            print("❌ Could not parse coverage data")
            return 1

        overall_coverage = coverage_data.get("overall", 0.0)
        files = coverage_data.get("files", {})

        print(f"\n📊 Overall Coverage: {overall_coverage:.1f}%")

        if overall_coverage >= self.target:
            print(f"🎉 Coverage target of {self.target}% achieved!")
            status = 0
        else:
            gap = self.target - overall_coverage
            print(f"⚠️  Need {gap:.1f}% more coverage to reach {self.target}% target")
            status = 1

        if detailed and files:
            self._show_detailed_analysis(files)

        print("\n💡 Next Steps:")
        if overall_coverage < self.target:
            print("1. Run: make coverage")
            print("2. Open: htmlcov/index.html")
            print("3. Focus on red (uncovered) lines")
            print("4. Add tests for error conditions and edge cases")
        else:
            print("1. Maintain current coverage level")
            print("2. Add tests for new features")

        return status

    def _parse_coverage_xml(self) -> dict:
        """Parse coverage XML file."""
        xml_path = Path("coverage.xml")
        if not xml_path.exists():
            return {}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Get overall coverage
            overall = 0.0
            for elem in root.findall(".//coverage"):
                line_rate = float(elem.get("line-rate", 0))
                overall = line_rate * 100
                break

            # Get per-file coverage
            files = {}
            for class_elem in root.findall(".//class"):
                filename = class_elem.get("filename", "")
                if "src/mcp_server_anime" in filename:
                    line_rate = float(class_elem.get("line-rate", 0))
                    files[filename] = line_rate * 100

            return {"overall": overall, "files": files}
        except Exception as e:
            print(f"Warning: Could not parse coverage.xml: {e}")
            return {}

    def _show_detailed_analysis(self, files: dict) -> None:
        """Show detailed per-file coverage analysis."""
        print("\n📋 Per-File Coverage Analysis:")
        print("=" * 60)

        sorted_files = sorted(files.items(), key=lambda x: x[1])

        low_coverage = [(f, c) for f, c in sorted_files if c < self.target]
        good_coverage = [(f, c) for f, c in sorted_files if c >= self.target]

        if good_coverage:
            print(f"\n✅ Files with good coverage ({len(good_coverage)}):")
            for filename, coverage in good_coverage[-5:]:
                short_name = Path(filename).name
                print(f"  {short_name:<35} {coverage:6.1f}%")

        if low_coverage:
            print(f"\n⚠️  Files needing attention ({len(low_coverage)}):")
            for filename, coverage in low_coverage:
                short_name = Path(filename).name
                gap = self.target - coverage
                print(f"  {short_name:<35} {coverage:6.1f}% (need +{gap:.1f}%)")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test utilities for mcp-server-anime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run unit              # Run unit tests
  %(prog)s run integration       # Run integration tests
  %(prog)s run all               # Run all tests
  %(prog)s run specific PATH     # Run specific test
  %(prog)s run failing           # Run previously failed tests
  %(prog)s coverage              # Analyze coverage
  %(prog)s coverage --detailed   # Detailed coverage analysis
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "specific", "failing"],
        help="Type of tests to run",
    )
    run_parser.add_argument(
        "test_path", nargs="?", help="Path to specific test (for 'specific' type)"
    )
    run_parser.add_argument(
        "--no-coverage", action="store_true", help="Disable coverage reporting"
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    run_parser.add_argument(
        "--skip-network-check",
        action="store_true",
        help="Skip network connectivity check (integration tests)",
    )

    # Coverage command
    coverage_parser = subparsers.add_parser("coverage", help="Analyze coverage")
    coverage_parser.add_argument(
        "--target",
        type=float,
        default=90.0,
        help="Target coverage percentage (default: 90.0)",
    )
    coverage_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed per-file analysis"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run from project root.")
        return 1

    if args.command == "run":
        runner = TestRunner(verbose=args.verbose)

        if args.test_type == "unit":
            return runner.run_unit_tests(coverage=not args.no_coverage)
        elif args.test_type == "integration":
            return runner.run_integration_tests(
                check_network=not args.skip_network_check
            )
        elif args.test_type == "all":
            return runner.run_all_tests(coverage=not args.no_coverage)
        elif args.test_type == "specific":
            if not args.test_path:
                print("❌ Error: test_path required for 'specific' type")
                return 1
            return runner.run_specific_test(args.test_path)
        elif args.test_type == "failing":
            return runner.run_failing_tests()

    elif args.command == "coverage":
        analyzer = CoverageAnalyzer(target=args.target)
        return analyzer.analyze_coverage(detailed=args.detailed)

    return 1


if __name__ == "__main__":
    sys.exit(main())
