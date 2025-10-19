@echo off
echo Running unit tests with coverage...
poetry run pytest -c pytest-unit.ini
echo.
echo Unit test coverage report generated in htmlcov-unit/