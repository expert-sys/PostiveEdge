"""
Test script to demonstrate the rate limiting improvements
"""
import sys
import logging
from scrapers.unified_analysis_pipeline import scrape_games

# Set up logging to see the rate limiting messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("TESTING RATE LIMITING IMPROVEMENTS")
print("=" * 80)
print("\nThis script will demonstrate the new rate limiting features:")
print("  1. Initial delay (5-8s) after fetching games list")
print("  2. Longer page load delays (8s instead of 5s)")
print("  3. Longer scroll delays (3s instead of 2s)")
print("  4. Between-game delays (10-15s randomized)")
print("\n" + "=" * 80)
print()

# Run scraping with just 2 games to demonstrate the delays
logger.info("Starting game scraping with max_games=2...")
results = scrape_games(
    max_games=2,  # Just 2 games to show the delays
    headless=False  # Show browser so you can see what's happening
)

print("\n" + "=" * 80)
print("RATE LIMITING TEST COMPLETE")
print("=" * 80)
print(f"\nSuccessfully scraped {len(results)} games with rate limiting")
print("\nKey observations:")
print("  - Initial delay before scraping games")
print("  - Longer waits for page content to load")
print("  - Randomized delays between games (10-15 seconds)")
print("\nThese delays help avoid detection and rate limiting by Sportsbet")
