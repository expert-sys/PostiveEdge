@echo off
REM Quick Start - PositiveEdge with Player Cache System

:menu
cls
echo.
echo ===============================================
echo   PositiveEdge - Quick Start
echo ===============================================
echo.
echo  1. Run Unified Analysis (Team Bets + Props)
echo  2. Scrape Data
echo  3. Player Cache Management
echo  4. Value Analysis
echo  5. View Results
echo  6. Run Tests
echo  7. Exit
echo.
echo ===============================================
echo.
set /p choice="Select (1-7): "

if "%choice%"=="1" (
    call python launcher.py --run 1
    echo.
    pause
    goto menu
) else if "%choice%"=="2" (
    call python launcher.py --run 2
    echo.
    pause
    goto menu
) else if "%choice%"=="3" (
    call python launcher.py --run 3
    echo.
    pause
    goto menu
) else if "%choice%"=="4" (
    call python launcher.py --run 4
    echo.
    pause
    goto menu
) else if "%choice%"=="5" (
    call python launcher.py --run 5
    echo.
    pause
    goto menu
) else if "%choice%"=="6" (
    call python launcher.py --run 6
    echo.
    pause
    goto menu
) else if "%choice%"=="7" (
    exit /b 0
) else (
    echo [ERROR] Invalid choice
    pause
    goto menu
)
