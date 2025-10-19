@echo off
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