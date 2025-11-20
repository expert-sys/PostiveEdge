# PositiveEdge Launcher - PowerShell Script
# Quick launcher for the PositiveEdge platform

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   PositiveEdge - Sports Value Analysis" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Run the launcher
python launcher.py $args

Read-Host "`nPress Enter to exit"
