@echo off
REM View Last Analysis Recommendations
REM ====================================

echo.
echo ================================================================================
echo   Viewing Last Analysis Recommendations
echo ================================================================================
echo.

REM Ensure Python can find all modules
set PYTHONPATH=%CD%;%PYTHONPATH%

REM Run the script
python view_last_recommendations.py

REM Keep window open
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo   ERROR: Script failed with exit code %errorlevel%
    echo ================================================================================
    echo.
    pause
) else (
    echo.
)

