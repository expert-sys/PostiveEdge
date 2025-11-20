@echo off
REM PositiveEdge Launcher - Windows Batch Script
REM Quick launcher for the PositiveEdge platform

echo.
echo ===============================================
echo   PositiveEdge - Sports Value Analysis
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Run the launcher
python launcher.py %*

pause
