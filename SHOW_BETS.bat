@echo off
REM ============================================================================
REM ENHANCED BET VIEWER - Double-click to view your betting recommendations
REM ============================================================================

title Enhanced Bet Viewer

echo.
echo ================================================================================
echo ENHANCED BETTING RECOMMENDATIONS
echo ================================================================================
echo.

REM Check for betting recommendations file
if not exist betting_recommendations.json (
    echo ERROR: betting_recommendations.json not found
    echo.
    echo You need to generate recommendations first by running:
    echo    python nba_betting_system.py
    echo.
    echo Or run the demo to see how it works:
    echo    python demo_enhanced_filtering.py
    echo.
    goto :end
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not found in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo.
    goto :end
)

REM Run the viewer with output buffering disabled
echo Loading enhancement system...
echo.
python -u view_enhanced_bets.py --no-filters 2>&1

REM Check result
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo AN ERROR OCCURRED
    echo ================================================================================
    echo.
    echo The script encountered an error. Common issues:
    echo   - Missing bet_enhancement_system.py file
    echo   - Corrupted betting_recommendations.json
    echo   - Missing Python dependencies
    echo.
    echo Try running the demo instead:
    echo   python demo_enhanced_filtering.py
    echo.
) else (
    echo.
    echo ================================================================================
    echo COMPLETE
    echo ================================================================================
    echo.
    echo Enhanced recommendations saved to: betting_recommendations_enhanced.json
    echo.
)

:end
echo.
echo Press any key to close this window...
pause >nul
