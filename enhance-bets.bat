@echo off
REM Enhance Existing Betting Recommendations
REM Usage: enhance-bets.bat

echo ================================================================================
echo BET ENHANCEMENT SYSTEM
echo ================================================================================
echo.

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

REM Run enhancement with all bets visible
python view_enhanced_bets.py --no-filters

echo.
echo ================================================================================
echo.
echo Output saved to: betting_recommendations_enhanced.json
echo.
echo Press any key to exit...
pause > nul
