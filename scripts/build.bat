@echo off
echo 🔨 Building MCP Server Anime package...
echo.

echo 1. Cleaning build artifacts...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
for /d %%i in (*.egg-info) do rmdir /s /q "%%i" 2>nul
if exist .pytest_cache rmdir /s /q .pytest_cache 2>nul
if exist .mypy_cache rmdir /s /q .mypy_cache 2>nul
if exist .ruff_cache rmdir /s /q .ruff_cache 2>nul
if exist .coverage del .coverage 2>nul
if exist htmlcov rmdir /s /q htmlcov 2>nul
if exist coverage.xml del coverage.xml 2>nul
if exist .tox rmdir /s /q .tox 2>nul

REM Clean Python cache files
for /r . %%i in (__pycache__) do if exist "%%i" rmdir /s /q "%%i" 2>nul
for /r . %%i in (*.pyc) do if exist "%%i" del "%%i" 2>nul

echo [OK] Cleanup complete

echo.
echo 2. Building package...
poetry build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    exit /b 1
)
echo [OK] Package built successfully

echo.
echo 3. Validating package...
poetry run twine check dist/*
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Package validation failed!
    exit /b 1
)
echo [OK] Package validation passed

echo.
echo ✅ Build complete! Package files created in dist/
dir dist\