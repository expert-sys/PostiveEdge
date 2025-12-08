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

REM Run the comprehensive launcher
python launcher_comprehensive.py --auto

pause

