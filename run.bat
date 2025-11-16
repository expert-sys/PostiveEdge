@echo off
REM ============================================
REM VALUE ENGINE - WINDOWS BATCH LAUNCHER
REM ============================================
REM
REM This batch file launches the Value Engine interactive application
REM Run from Command Prompt or PowerShell
REM

setlocal enabledelayedexpansion

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo ERROR: Python is not installed or not in PATH
    echo ============================================
    echo.
    echo Please install Python 3.7+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements if they exist
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -q -r requirements.txt
)

REM Run the main application
echo.
echo ============================================
echo VALUE ENGINE - SPORTS ANALYSIS
echo ============================================
echo.

python main.py

REM Cleanup
call venv\Scripts\deactivate.bat
endlocal
