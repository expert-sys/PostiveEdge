@echo off
title Sports Data Consolidator

echo Starting Sports Data Consolidator...
echo.

python data_consolidator.py

if errorlevel 1 (
    echo.
    echo Error: Python or required packages not found
    echo.
    pause
)
