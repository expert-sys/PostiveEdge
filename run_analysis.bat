@echo off
REM ============================================================================
REM PositiveEdge - NBA Betting Analysis System
REM ============================================================================
REM Run the unified analysis pipeline with all updates and enhancements
REM
REM Features Enabled:
REM   - Market-Specific Confidence Tiers (Player Props C=35, Sides C=40, Totals C=45)
REM   - Role Modifier (Usage/Minutes/Teammate Impact, max +5% probability boost)
REM   - Insight Decay Penalties (Age-based and multi-season)
REM   - Prop Volatility Index (PVI) for bench/low-minutes players
REM   - Correlation Awareness (De-tier instead of blocking)
REM   - CLV Tracking (Opening vs Closing Line Value)
REM   - Explanation Consistency Validation
REM   - SQLite Persistent Cache (Minutes/Usage/Injuries/Role data)
REM ============================================================================

echo.
echo PositiveEdge - NBA Betting Analysis
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

REM Display Python version (quiet)
python --version >nul 2>&1

REM Check if the main script exists
if not exist "scrapers\unified_analysis_pipeline.py" (
    echo [ERROR] Main script not found: scrapers\unified_analysis_pipeline.py
    echo Please ensure you're running this from the project root directory.
    echo.
    pause
    exit /b 1
)

REM Check if required directories exist (quiet)
if not exist "data" mkdir data >nul 2>&1
if not exist "data\cache" mkdir data\cache >nul 2>&1
if not exist "data\outputs" mkdir data\outputs >nul 2>&1

echo Starting analysis...
echo.

REM Run the unified analysis pipeline
python scrapers\unified_analysis_pipeline.py %*

REM Check if the script ran successfully
if errorlevel 1 (
    echo.
    echo [ERROR] Analysis failed - check output above
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo [SUCCESS] Analysis complete - results in data\outputs\
    echo.
)

REM Keep window open so user can read results
echo Press Enter to exit...
pause >nul
