@echo off
REM CI script for comprehensive testing and quality checks

echo 🚀 Running CI pipeline...
echo.

echo Step 1: Install dependencies
poetry install --no-interaction
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo Step 2: Run quality checks
call scripts\quality-check.bat
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