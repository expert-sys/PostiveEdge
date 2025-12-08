@echo off
REM Quick View of Enhanced Betting Recommendations
REM Double-click to view your bets with all enhancements applied

echo.
echo ================================================================================
echo LOADING ENHANCED BETTING RECOMMENDATIONS...
echo ================================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Check if recommendations file exists
if not exist betting_recommendations.json (
    echo ERROR: betting_recommendations.json not found
    echo.
    echo Please run nba_betting_system.py first to generate recommendations:
    echo   python nba_betting_system.py
    echo.
    pause
    exit /b 1
)

REM Run the enhancement viewer
python view_enhanced_bets.py --no-filters

REM Check if script ran successfully
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Script encountered an error
    echo ================================================================================
    echo.
) else (
    echo.
    echo ================================================================================
    echo SUCCESS: Enhanced recommendations displayed above
    echo ================================================================================
    echo.
)

echo Press any key to exit...
pause >nul
