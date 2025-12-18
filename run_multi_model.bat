@echo off
echo Starting Multi-Model Engine Demo...
echo.

REM Set PYTHONPATH to include the multi-model-engine directory
set PYTHONPATH=%PYTHONPATH%;%~dp0\multi-model-engine

REM Run the demo script
python multi-model-engine/demo_run.py

echo.
pause
