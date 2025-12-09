@echo off
REM Install all dependencies for NBA Betting System
REM ===============================================

echo.
echo ================================================================================
echo   Installing NBA Betting System Dependencies
echo ================================================================================
echo.

REM Check if venv exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found. Installing to system Python...
    echo.
    echo To create a virtual environment, run:
    echo   python -m venv venv
    echo.
)

REM Upgrade pip first
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install all dependencies from requirements.txt
echo.
echo Installing dependencies from requirements.txt...
echo.
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo   ERROR: Some dependencies failed to install
    echo ================================================================================
    echo.
    echo Please check the error messages above and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo   Dependencies installed successfully!
echo ================================================================================
echo.
echo Key dependencies installed:
echo   - playwright (web scraping)
echo   - beautifulsoup4 (HTML parsing)
echo   - requests (HTTP requests)
echo   - tenacity (retry logic)
echo   - python-dotenv (configuration)
echo   - numpy, pandas (data processing)
echo   - scipy (statistical analysis)
echo.
pause

