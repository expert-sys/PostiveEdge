@echo off
REM NBA Betting System Launcher (Windows)
REM =====================================

echo.
echo ========================================
echo NBA BETTING SYSTEM
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies (including new ones from refactoring)
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Warning: Some dependencies may have failed to install.
    echo Continuing with basic dependencies...
    pip install -q playwright beautifulsoup4 requests
)

REM Install Playwright browsers (first time only)
if not exist "venv\Lib\site-packages\playwright\driver\" (
    echo Installing Playwright browsers (one-time setup)...
    playwright install chromium
)

REM Run the betting system
echo.
echo Starting NBA Betting System...
echo.
echo Ensuring Python can find all modules...
set PYTHONPATH=%CD%;%PYTHONPATH%
python nba_betting_system.py %*

REM Keep window open if error
if errorlevel 1 (
    echo.
    echo ERROR: System encountered an error
    pause
)
