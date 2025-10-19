@echo off
REM Test coverage analysis script for Windows

echo 🎯 MCP Server Anime - Test Coverage Analysis
echo ============================================================

REM Run the Python coverage analysis script
poetry run python scripts/test_coverage.py %*

REM Check if coverage target was met
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Coverage target achieved!
) else (
    echo.
    echo ⚠️  Coverage target not met. See suggestions above.
)

pause