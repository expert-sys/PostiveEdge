@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM ENHANCED BET VIEWER
REM ============================================================================
REM This script displays your enhanced betting recommendations
REM The window will NOT close until you press a key
REM ============================================================================

title Enhanced Bet Viewer - Press any key when done

cls
echo.
echo ============================================================================
echo ENHANCED BETTING RECOMMENDATIONS VIEWER
echo ============================================================================
echo.
echo Checking requirements...
echo.

REM Step 1: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python not found
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    goto :cleanup
)
echo [OK] Python found

REM Step 2: Check for recommendations file
if not exist betting_recommendations.json (
    echo [FAIL] betting_recommendations.json not found
    echo.
    echo To generate recommendations, run:
    echo    python nba_betting_system.py
    echo.
    echo OR run the demo to see how it works:
    echo    python demo_enhanced_filtering.py
    echo.
    goto :cleanup
)
echo [OK] Recommendations file found

REM Step 3: Check for enhancement system
if not exist bet_enhancement_system.py (
    echo [FAIL] bet_enhancement_system.py not found
    echo.
    echo The enhancement system file is missing.
    echo Please ensure all files are in the same directory.
    echo.
    goto :cleanup
)
echo [OK] Enhancement system found

REM Step 4: Check for viewer script
if not exist view_enhanced_bets.py (
    echo [FAIL] view_enhanced_bets.py not found
    echo.
    echo The viewer script is missing.
    echo Please ensure all files are in the same directory.
    echo.
    goto :cleanup
)
echo [OK] Viewer script found

echo.
echo All requirements met! Loading enhanced bets...
echo.
echo ============================================================================
echo.

REM Run the viewer (unbuffered output, show all errors)
python -u view_enhanced_bets.py --no-filters 2>&1

REM Check if it succeeded
if errorlevel 1 (
    echo.
    echo ============================================================================
    echo ERROR OCCURRED
    echo ============================================================================
    echo.
    echo The script encountered an error. This might be due to:
    echo   - Corrupted betting_recommendations.json file
    echo   - Missing Python packages
    echo   - Syntax errors in the code
    echo.
    echo Try running: python demo_enhanced_filtering.py
    echo.
) else (
    echo.
    echo ============================================================================
    echo SUCCESS
    echo ============================================================================
    echo.
    echo Your enhanced recommendations are displayed above
    echo Output saved to: betting_recommendations_enhanced.json
    echo.
)

:cleanup
echo.
echo ============================================================================
echo.
echo This window will stay open so you can read the results.
echo Press any key to close this window...
echo.
pause >nul
exit /b
