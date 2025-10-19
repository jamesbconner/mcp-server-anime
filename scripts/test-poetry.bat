@echo off
REM Test execution script for MCP Server Anime using Poetry
REM This script provides easy access to Poetry-based test commands

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: test-poetry.bat [command] [options]
    echo.
    echo Available commands:
    echo   all          - Run all tests
    echo   unit         - Run unit tests only
    echo   integration  - Run integration tests only
    echo   coverage     - Run tests with coverage reporting
    echo   validate     - Validate test environment
    echo   specific     - Run specific test file ^(requires test path^)
    echo   failing      - Run only failing tests from last run
    echo   isolation    - Run tests with isolation checking
    echo.
    echo Examples:
    echo   test-poetry.bat all
    echo   test-poetry.bat unit
    echo   test-poetry.bat coverage
    echo   test-poetry.bat specific tests/test_http_client.py
    echo   test-poetry.bat validate
    goto :eof
)

set COMMAND=%1
shift

REM Check if Poetry is available
poetry --version >nul 2>&1
if errorlevel 1 (
    echo Error: Poetry not found. Please install Poetry first.
    echo Visit: https://python-poetry.org/docs/#installation
    exit /b 1
)

REM Execute based on command
if "%COMMAND%"=="all" (
    echo Running all tests...
    poetry run pytest
) else if "%COMMAND%"=="unit" (
    echo Running unit tests...
    poetry run pytest -m "not integration"
) else if "%COMMAND%"=="integration" (
    echo Running integration tests...
    set RUN_INTEGRATION_TESTS=1
    poetry run pytest -m integration
) else if "%COMMAND%"=="coverage" (
    echo Running tests with coverage...
    poetry run pytest --cov=src/mcp_server_anime --cov-report=term-missing --cov-report=html --cov-report=xml --cov-branch
) else if "%COMMAND%"=="validate" (
    echo Validating test environment...
    poetry run python scripts/test_runner.py validate
) else if "%COMMAND%"=="specific" (
    if "%1"=="" (
        echo Error: Test path required for specific command
        echo Usage: test-poetry.bat specific tests/test_file.py
        exit /b 1
    )
    echo Running specific test: %1
    poetry run pytest %1 -v
) else if "%COMMAND%"=="failing" (
    echo Running only failing tests...
    poetry run pytest --lf -v
) else if "%COMMAND%"=="isolation" (
    echo Running tests with isolation checking...
    poetry run pytest -v --tb=short --maxfail=1
) else (
    echo Error: Unknown command "%COMMAND%"
    echo Run "test-poetry.bat" without arguments to see available commands.
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo Test execution failed with exit code %errorlevel%
    exit /b %errorlevel%
) else (
    echo.
    echo Test execution completed successfully!
)