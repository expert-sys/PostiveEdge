@echo off
title Universal Sports Scraper

echo Starting Universal Sports Scraper...
echo.

python universal_scraper.py

if errorlevel 1 (
    echo.
    echo Error: Python or required packages not found
    echo Please run: pip install -r scraper_requirements.txt
    echo Then run: playwright install chromium
    echo.
    pause
)
