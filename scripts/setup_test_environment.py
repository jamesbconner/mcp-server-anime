#!/usr/bin/env python3
"""
Setup comprehensive test environment for achieving 90%+ coverage.

This script configures the test environment and provides tools to systematically
improve test coverage for the MCP Server Anime project.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"Error: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if not check:
            return e
        sys.exit(1)


def setup_pytest_config() -> None:
    """Set up comprehensive pytest configuration."""
    print("🔧 Setting up pytest configuration...")
    
    # Create pytest configuration for different test scenarios
    configs = {
        "pytest-unit.ini": """
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=src/mcp_server_anime
    --cov-report=term-missing
    --cov-report=html:htmlcov-unit
    --cov-report=xml:coverage-unit.xml
    --cov-branch
    -m "not integration"
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
""",
        "pytest-integration.ini": """
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=src/mcp_server_anime
    --cov-report=term-missing
    --cov-report=html:htmlcov-integration
    --cov-report=xml:coverage-integration.xml
    --cov-branch
    -m integration
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
""",
        "pytest-all.ini": """
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=src/mcp_server_anime
    --cov-report=term-missing
    --cov-report=html:htmlcov-all
    --cov-report=xml:coverage-all.xml
    --cov-branch
    --maxfail=10
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""
    }
    
    for filename, content in configs.items():
        with open(filename, 'w') as f:
            f.write(content.strip())
        print(f"✅ Created {filename}")


def create_test_scripts() -> None:
    """Create test execution scripts."""
    print("📝 Creating test execution scripts...")
    
    scripts = {
        "test-unit.bat": """@echo off
echo Running unit tests with coverage...
poetry run pytest -c pytest-unit.ini
echo.
echo Unit test coverage report generated in htmlcov-unit/
""",
        "test-integration.bat": """@echo off
echo Running integration tests...
set RUN_INTEGRATION_TESTS=1
poetry run pytest -c pytest-integration.ini
echo.
echo Integration test coverage report generated in htmlcov-integration/
""",
        "test-all.bat": """@echo off
echo Running all tests with comprehensive coverage...
poetry run pytest -c pytest-all.ini
echo.
echo Complete coverage report generated in htmlcov-all/
""",
        "test-coverage-check.bat": """@echo off
echo Checking current test coverage...
poetry run pytest -c pytest-unit.ini --cov-fail-under=90 --quiet
if %ERRORLEVEL% EQU 0 (
    echo [OK] Coverage target of 90%% achieved!
) else (
    echo [WARNING] Coverage below 90%%. Run test-coverage-analysis.bat for details.
)
""",
        "test-coverage-analysis.bat": """@echo off
echo Analyzing test coverage...
poetry run python scripts/test_coverage.py --detailed --suggestions
"""
    }
    
    scripts_dir = Path("scripts")
    for filename, content in scripts.items():
        script_path = scripts_dir / filename
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"✅ Created {script_path}")


def setup_coverage_config() -> None:
    """Set up coverage configuration."""
    print("📊 Setting up coverage configuration...")
    
    # Create .coveragerc for more detailed coverage control
    coveragerc_content = """
[run]
source = src/mcp_server_anime
branch = True
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */site-packages/*
    */venv/*
    */.venv/*

[report]
precision = 2
show_missing = True
skip_covered = False
skip_empty = False
sort = Cover
fail_under = 90.0
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if False:
    if __name__ == .__main__.:
    class .*\\bProtocol\\):
    @(abc\\.)?abstractmethod
    @overload
    \\.\\.\\.
    pass
    except ImportError:
    except ModuleNotFoundError:
    TYPE_CHECKING

[html]
directory = htmlcov
title = MCP Server Anime Coverage Report

[xml]
output = coverage.xml
"""
    
    with open('.coveragerc', 'w', encoding='utf-8') as f:
        f.write(coveragerc_content.strip())
    print("✅ Created .coveragerc")


def create_test_markers_config() -> None:
    """Create test markers configuration."""
    print("🏷️  Setting up test markers...")
    
    # Update pytest.ini with comprehensive markers
    pytest_ini_content = """
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts = 
    --verbose
    --tb=short
    --strict-markers
    --strict-config
    --cov=src/mcp_server_anime
    --cov-report=term-missing:skip-covered
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-branch
    --durations=10
    --maxfail=5

asyncio_mode = auto

markers =
    unit: Unit tests that don't require external dependencies
    integration: Integration tests that may require network access
    slow: Tests that take a long time to run
    smoke: Basic smoke tests for core functionality
    api: Tests that interact with external APIs
    cache: Tests related to caching functionality
    error: Tests focused on error handling
    validation: Tests for input validation
    xml: Tests for XML parsing functionality
    http: Tests for HTTP client functionality
    tools: Tests for MCP tools
    service: Tests for service layer functionality
    config: Tests for configuration management
    models: Tests for data models
    server: Tests for server functionality
    providers: Tests for provider system
    extensible: Tests for extensibility features

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
    ignore::pytest.PytestUnraisableExceptionWarning
    ignore::UserWarning:httpx.*
    ignore::UserWarning:asyncio.*
    ignore:ast.Str is deprecated:DeprecationWarning
    ignore:ast.Constant is deprecated:DeprecationWarning
    error::UserWarning:mcp_server_anime.*

minversion = 8.0

log_cli = false
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s: %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

log_file = tests.log
log_file_level = DEBUG
log_file_format = %(asctime)s [%(levelname)8s] %(filename)s:%(lineno)d %(funcName)s(): %(message)s
log_file_date_format = %Y-%m-%d %H:%M:%S

cache_dir = .pytest_cache

junit_family = xunit2
junit_logging = system-out
junit_log_passing_tests = false
"""
    
    with open('pytest.ini', 'w', encoding='utf-8') as f:
        f.write(pytest_ini_content.strip())
    print("✅ Updated pytest.ini with comprehensive configuration")


def setup_quality_checks() -> None:
    """Set up quality check configurations."""
    print("🔍 Setting up quality check configurations...")
    
    # Create script for running all quality checks
    quality_script = """@echo off
echo 🔍 Running comprehensive quality checks...
echo.

echo 1. Code formatting check...
poetry run ruff format --check src tests
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Code formatting issues found. Run 'make format' to fix.
    set QUALITY_FAILED=1
) else (
    echo [OK] Code formatting OK
)

echo.
echo 2. Linting check...
poetry run ruff check src tests
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Linting issues found. Run 'make lint-fix' to fix.
    set QUALITY_FAILED=1
) else (
    echo [OK] Linting OK
)

echo.
echo 3. Type checking...
poetry run mypy src
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Type checking issues found.
    set QUALITY_FAILED=1
) else (
    echo [OK] Type checking OK
)

echo.
echo 4. Security scan...
poetry run bandit -r src -q
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Security issues found.
    set QUALITY_FAILED=1
) else (
    echo [OK] Security scan OK
)

echo.
echo 5. Test coverage check...
poetry run pytest -c pytest-unit.ini --cov-fail-under=90 --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Coverage below 90%%
    set QUALITY_FAILED=1
) else (
    echo [OK] Coverage target met
)

echo.
if defined QUALITY_FAILED (
    echo [ERROR] Quality checks failed. Please fix issues above.
    exit /b 1
) else (
    echo [OK] All quality checks passed!
    exit /b 0
)
"""
    
    with open('scripts/quality-check.bat', 'w', encoding='utf-8') as f:
        f.write(quality_script.strip())
    print("✅ Created scripts/quality-check.bat")


def create_ci_scripts() -> None:
    """Create CI-specific scripts."""
    print("🚀 Creating CI scripts...")
    
    ci_script = """@echo off
REM CI script for comprehensive testing and quality checks

echo 🚀 Running CI pipeline...
echo.

echo Step 1: Install dependencies
poetry install --no-interaction
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo Step 2: Run quality checks
call scripts\\quality-check.bat
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo Step 3: Run unit tests with coverage
poetry run pytest -c pytest-unit.ini --cov-fail-under=85
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo Step 4: Generate coverage reports
poetry run coverage html
poetry run coverage xml

echo.
echo [OK] CI pipeline completed successfully!
"""
    
    with open('scripts/ci-pipeline.bat', 'w', encoding='utf-8') as f:
        f.write(ci_script.strip())
    print("✅ Created scripts/ci-pipeline.bat")


def main():
    """Main setup function."""
    print("🎯 Setting up comprehensive test environment for MCP Server Anime")
    print("=" * 70)
    
    # Ensure scripts directory exists
    Path("scripts").mkdir(exist_ok=True)
    
    # Run setup functions
    setup_pytest_config()
    create_test_scripts()
    setup_coverage_config()
    create_test_markers_config()
    setup_quality_checks()
    create_ci_scripts()
    
    print("\n🎉 Test environment setup complete!")
    print("\n📋 Available commands:")
    print("  scripts/test-unit.bat              - Run unit tests with coverage")
    print("  scripts/test-integration.bat       - Run integration tests")
    print("  scripts/test-all.bat              - Run all tests")
    print("  scripts/test-coverage-check.bat   - Quick coverage check")
    print("  scripts/test-coverage-analysis.bat - Detailed coverage analysis")
    print("  scripts/quality-check.bat         - Run all quality checks")
    print("  scripts/ci-pipeline.bat           - Full CI pipeline")
    
    print("\n🎯 Next steps to achieve 90%+ coverage:")
    print("1. Run: scripts/test-coverage-analysis.bat")
    print("2. Focus on files with lowest coverage")
    print("3. Add tests for uncovered lines")
    print("4. Run: scripts/test-coverage-check.bat to verify progress")
    
    print("\n💡 Tips:")
    print("- Use 'make coverage-html' to generate visual coverage report")
    print("- Focus on error handling and edge cases")
    print("- Test async code paths thoroughly")
    print("- Add validation tests for all input parameters")


if __name__ == "__main__":
    main()