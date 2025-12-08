#!/bin/bash
# NBA Betting System Launcher (Linux/Mac)
# ========================================

echo ""
echo "========================================"
echo "NBA BETTING SYSTEM"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.8+ from python.org"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q playwright beautifulsoup4 requests

# Install Playwright browsers (first time only)
if [ ! -d "venv/lib/python*/site-packages/playwright/driver" ]; then
    echo "Installing Playwright browsers (one-time setup)..."
    playwright install chromium
fi

# Run the betting system
echo ""
echo "Starting NBA Betting System..."
echo ""
python3 nba_betting_system.py "$@"

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: System encountered an error"
    exit 1
fi
