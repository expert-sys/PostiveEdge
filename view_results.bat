@echo off
REM ============================================================================
REM PositiveEdge - View Analysis Results
REM ============================================================================
REM Displays the most recent analysis results in a formatted view
REM ============================================================================

echo.
echo ============================================================================
echo PositiveEdge - View Analysis Results
echo ============================================================================
echo.

REM Change to the script's directory (project root)
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher and try again.
    echo.
    pause
    exit /b 1
)

REM Check if the viewer script exists
if not exist "view_results.py" (
    echo [ERROR] Viewer script not found: view_results.py
    echo Please ensure you're running this from the project root directory.
    echo.
    pause
    exit /b 1
)

REM Run the viewer script
python view_results.py

REM Keep window open so user can read results
echo.
echo Press Enter to exit...
pause >nul
