@echo off
REM Batch script to run integration tests on Windows

echo 🚀 Running integration tests for mcp-server-anime...
echo.

REM Check if Poetry is installed
poetry --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Poetry not found. Please install Poetry first.
    echo    Visit: https://python-poetry.org/docs/#installation
    exit /b 1
)

REM Check if we're in the right directory
if not exist pyproject.toml (
    echo ❌ Error: pyproject.toml not found. Please run from project root.
    exit /b 1
)

REM Set environment variable to enable integration tests
set RUN_INTEGRATION_TESTS=1

REM Show warning about API usage
echo ⚠️  IMPORTANT:
echo    Integration tests will make real API calls to AniDB
echo    Please be respectful of their API rate limits
echo    Tests include built-in rate limiting (2.5s between requests)
echo.

REM Parse command line arguments
set VERBOSE=
set FAIL_FAST=
set COVERAGE=
set SPECIFIC_TEST=

:parse_args
if "%1"=="--verbose" set VERBOSE=-v
if "%1"=="-v" set VERBOSE=-v
if "%1"=="--fail-fast" set FAIL_FAST=--maxfail=1
if "%1"=="-x" set FAIL_FAST=--maxfail=1
if "%1"=="--coverage" set COVERAGE=--cov=src --cov-report=term-missing --cov-report=html:htmlcov-integration
if "%1"=="-c" set COVERAGE=--cov=src --cov-report=term-missing --cov-report=html:htmlcov-integration
if "%1"=="--test" (
    shift
    set SPECIFIC_TEST=-k %1
)
shift
if not "%1"=="" goto parse_args

REM Build pytest command
set PYTEST_CMD=poetry run pytest -m integration %VERBOSE% %FAIL_FAST% %COVERAGE% %SPECIFIC_TEST% --tb=short --durations=10

echo Command: %PYTEST_CMD%
echo.

REM Run the tests
%PYTEST_CMD%

if errorlevel 1 (
    echo.
    echo ❌ Integration tests failed
    exit /b 1
) else (
    echo.
    echo ✅ Integration tests completed successfully
    exit /b 0
)