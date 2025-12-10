@echo off
REM Generate Fresh Betting Recommendations (Unified Pipeline)
REM ============================================================

echo.
echo ================================================================================
echo GENERATING FRESH BETTING RECOMMENDATIONS (Unified Pipeline)
echo ================================================================================
echo.
echo This will:
echo   1. Scrape latest NBA games from Sportsbet
echo   2. Apply Unified Analysis (Team Bets + Player Props)
echo   3. Display top quality bets only
echo.

REM Activate venv
if not exist "venv\" (
    echo [ERROR] Virtual environment not found. Please run start_system.bat first.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM Set Python path
set PYTHONPATH=%CD%;%PYTHONPATH%

echo Running unified analysis pipeline...
echo.

REM Run the pipeline
python scrapers/unified_analysis_pipeline.py

if errorlevel 1 (
    echo.
    echo [ERROR] Analysis failed.
    pause
) else (
    echo.
    echo ================================================================================
    echo SUCCESS - Fresh recommendations generated!
    echo ================================================================================
    echo.
    echo Launching results viewer...
    echo.
    
    REM View the results in LEGACY FORMAT (Diamonds/Tiers) using ORIGINAL SCRIPT
    python view_enhanced_bets.py --input latest --no-filters
)

pause
