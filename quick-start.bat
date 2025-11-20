@echo off
REM Quick Start - Simplified 6 Options

echo.
echo ===============================================
echo   PositiveEdge - Quick Start
echo ===============================================
echo.
echo  1. Run Complete Analysis
echo  2. Scrape Data
echo  3. Value Analysis
echo  4. View Results
echo  5. Run Tests
echo  6. Exit
echo.
echo ===============================================

set /p choice="Select (1-6): "

if "%choice%"=="1" (
    python launcher.py --run 1
) else if "%choice%"=="2" (
    python launcher.py --run 2
) else if "%choice%"=="3" (
    python launcher.py --run 3
) else if "%choice%"=="4" (
    python launcher.py --run 4
) else if "%choice%"=="5" (
    python launcher.py --run 5
) else if "%choice%"=="6" (
    exit /b 0
) else (
    echo [ERROR] Invalid choice
    pause
)
