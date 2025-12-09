@echo off
REM Generate Fresh Betting Recommendations with V2 Enhancements
REM ============================================================

echo.
echo ================================================================================
echo GENERATING FRESH BETTING RECOMMENDATIONS (V2 Enhanced)
echo ================================================================================
echo.
echo This will:
echo   1. Scrape latest NBA games from Sportsbet
echo   2. Validate with DataBallr player stats
echo   3. Run model projections
echo   4. Apply V2 enhancement filters
echo   5. Display top quality bets only
echo.
echo ================================================================================
echo.

REM Activate venv if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Set Python path
set PYTHONPATH=%CD%;%PYTHONPATH%

echo Running betting system with V2 enhancements...
echo.
echo Configuration:
echo   - Games to analyze: ALL available games
echo   - Min confidence: 55%%
echo   - Enhanced filtering: ON
echo   - Min tier: B (playable or better)
echo.

REM Run the betting system with enhancements (all games)
python nba_betting_system.py --enhanced --min-tier B --min-confidence 55

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Betting system failed
    echo ================================================================================
    echo.
    echo Possible issues:
    echo   - Network connection problems
    echo   - Sportsbet website changes
    echo   - Missing dependencies
    echo.
    echo Try running: verify_modules.bat
    echo.
) else (
    echo.
    echo ================================================================================
    echo SUCCESS - Fresh recommendations generated!
    echo ================================================================================
    echo.
    echo Files created:
    echo   - betting_recommendations.json (base)
    echo   - betting_recommendations_enhanced.json (V2 filtered)
    echo.
    echo View enhanced bets:
    echo   - Double-click: show-bets.bat
    echo   - Or run: python view_enhanced_bets.py
    echo.
)

pause
