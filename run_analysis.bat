@echo off
REM ============================================================================
REM PositiveEdge - NBA Betting Analysis System
REM ============================================================================
REM Run the unified analysis pipeline with all updates and enhancements
REM ============================================================================

echo.
echo ============================================================================
echo PositiveEdge - NBA Betting Analysis System
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

REM Display Python version
echo Python version:
python --version
echo.

REM Check if the main script exists
if not exist "scrapers\unified_analysis_pipeline.py" (
    echo [ERROR] Main script not found: scrapers\unified_analysis_pipeline.py
    echo Please ensure you're running this from the project root directory.
    echo.
    pause
    exit /b 1
)

REM Run the unified analysis pipeline
echo Starting unified analysis pipeline...
echo.

python scrapers\unified_analysis_pipeline.py %*

REM Check if the script ran successfully
if errorlevel 1 (
    echo.
    echo ============================================================================
    echo [ERROR] Analysis pipeline encountered an error
    echo ============================================================================
    echo Check the output above for details.
    echo Error log may also be saved to: error_log.txt
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ============================================================================
    echo [SUCCESS] Analysis completed successfully
    echo ============================================================================
    echo.
)

REM Keep window open so user can read results
echo Press Enter to exit...
pause >nul
