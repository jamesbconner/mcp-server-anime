@echo off
echo Checking current test coverage...
poetry run pytest -c pytest-unit.ini --cov-fail-under=90 --quiet
if %ERRORLEVEL% EQU 0 (
    echo [OK] Coverage target of 90%% achieved!
) else (
    echo [WARNING] Coverage below 90%%. Run test-coverage-analysis.bat for details.
)