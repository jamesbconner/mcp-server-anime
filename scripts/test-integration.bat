@echo off
echo Running integration tests...
set RUN_INTEGRATION_TESTS=1
poetry run pytest -c pytest-integration.ini
echo.
echo Integration test coverage report generated in htmlcov-integration/