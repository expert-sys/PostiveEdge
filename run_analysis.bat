@echo off
echo Starting Daily Sportsbet Analysis (Insight-Driven)...
echo.

REM Activate Virtual Environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found, using system python...
)

REM Run Script
python daily_sportsbet_analysis.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Analysis failed. Check logs.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Analysis Complete.
pause
