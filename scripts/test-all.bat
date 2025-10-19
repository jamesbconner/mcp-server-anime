@echo off
echo Running all tests with comprehensive coverage...
poetry run pytest -c pytest-all.ini
echo.
echo Complete coverage report generated in htmlcov-all/