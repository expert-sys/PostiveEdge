@echo off
REM PositiveEdge - Comprehensive Launcher (Windows)
REM Automatically runs full pipeline: Scrapers -> Analysis -> Top Bets

echo ================================================================================
echo   PositiveEdge - Comprehensive Betting Analysis
echo ================================================================================
echo.
echo This will run the complete pipeline:
echo   1. Sportsbet Scraper (Markets + Insights)
echo   2. DataballR Scraper (Player Stats)
echo   3. Unified Analysis (Model Projections)
echo   4. Display Top Bets (High Confidence)
echo.
echo ================================================================================
echo.

REM Check if venv exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found. Using system Python...
)

REM Install/upgrade dependencies (including new ones from refactoring)
echo.
echo Installing/updating dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Warning: Some dependencies may have failed to install.
)

REM Ensure Python can find all modules (for refactored structure)
set PYTHONPATH=%CD%;%PYTHONPATH%

REM Verify module structure
echo.
echo Verifying module structure...
python -c "from nba_betting.collectors import SportsbetCollector, DataBallrValidator; from nba_betting.engines import ValueProjector; from models import BettingRecommendation; print('✓ All modules found')" 2>nul
if errorlevel 1 (
    echo Warning: Some modules may not be found. Continuing anyway...
)

REM Run the comprehensive launcher (with V2 enhancements)
echo.
echo Running NBA Betting System with V2 Enhancements...
echo Analyzing ALL available games today...
echo.

REM Run the main betting system with enhancements (all games)
python nba_betting_system.py --enhanced --min-tier B

echo.
echo ================================================================================
echo PIPELINE COMPLETE
echo ================================================================================
echo.
echo Results saved to:
echo   - betting_recommendations.json (base recommendations)
echo   - betting_recommendations_enhanced.json (V2 enhanced with all filters)
echo.
echo V2 Enhancements Applied:
echo   ✓ Scaled correlation penalty
echo   ✓ A-tier probability gate (≥75%)
echo   ✓ Minutes stability score
echo   ✓ Line shading detection
echo   ✓ C-tier as "Do Not Bet"
echo.

pause

