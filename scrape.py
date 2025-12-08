#!/usr/bin/env python3
"""
DataballR Robust Scraper - CLI Entry Point
===========================================
Main CLI script for running the scraper.

Usage:
    python scrape.py --date 2025-01-05
    python scrape.py --player "LeBron James"
    python scrape.py --players "LeBron James" "Stephen Curry"
"""

import sys
from pathlib import Path

# Add scrapers to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.databallr_robust.main import main

if __name__ == '__main__':
    main()

