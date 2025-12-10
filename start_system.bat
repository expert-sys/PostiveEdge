@echo off
REM PositiveEdge System Launcher
REM ==========================================

echo.
echo ==========================================
echo    PositiveEdge - Sports Betting System
echo ==========================================
echo.

REM 1. Check Python Installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from python.org and ensure it is added to PATH.
    pause
    exit /b 1
)

REM 2. Setup Virtual Environment
if not exist "venv\" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

REM 3. Activate Virtual Environment
call venv\Scripts\activate.bat

REM 4. Check/Install Dependencies
echo [CHECK] Verifying dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [WARN] Some dependencies failed to install. attempting selective install...
    pip install -q playwright beautifulsoup4 requests pandas
)

REM 5. Install Playwright Browsers (if needed)
if not exist "venv\Lib\site-packages\playwright\driver\" (
    echo [SETUP] Installing Playwright browsers...
    playwright install chromium
)

REM 6. Launch System
echo.
echo [LAUNCH] Starting PositiveEdge...
echo.
python launcher.py

if errorlevel 1 (
    echo.
    echo [EXIT] System exited with error code %errorlevel%
    pause
)
