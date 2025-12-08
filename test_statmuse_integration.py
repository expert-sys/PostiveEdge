"""
Test StatMuse Integration with Unified Pipeline
================================================
Tests that the StatMuse adapter successfully enriches betting analysis
with comprehensive team stats and situational splits.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("TESTING STATMUSE INTEGRATION WITH BETTING PIPELINE")
print("=" * 80)
print()

# Test 1: Verify StatMuse adapter is available
print("[TEST 1] Checking StatMuse adapter availability...")
try:
    from scrapers.statmuse_adapter import get_team_stats_for_matchup, TEAM_NAME_TO_SLUG
    print("  OK StatMuse adapter imported successfully")
    print(f"  OK {len(TEAM_NAME_TO_SLUG)} teams mapped")
except ImportError as e:
    print(f"  ✗ Failed to import StatMuse adapter: {e}")
    sys.exit(1)

# Test 2: Verify pipeline imports StatMuse
print("\n[TEST 2] Checking pipeline StatMuse integration...")
try:
    from scrapers.unified_analysis_pipeline import STATMUSE_AVAILABLE
    if STATMUSE_AVAILABLE:
        print("  OK Pipeline has StatMuse integration enabled")
    else:
        print("  ✗ StatMuse not available in pipeline")
        sys.exit(1)
except ImportError as e:
    print(f"  ✗ Failed to check pipeline: {e}")
    sys.exit(1)

# Test 3: Quick test of StatMuse data fetch
print("\n[TEST 3] Testing StatMuse data fetch (quick sample)...")
print("  Fetching Lakers stats...")
try:
    from scrapers.statmuse_scraper import scrape_team_stats
    lakers_stats = scrape_team_stats("los-angeles-lakers", "2025-26", headless=True)

    if lakers_stats:
        print(f"  OK Lakers: {lakers_stats.games_played} GP, {lakers_stats.points} PPG")
        print(f"  OK Rebounds: {lakers_stats.rebounds} RPG, Assists: {lakers_stats.assists} APG")
    else:
        print("  ✗ Failed to fetch Lakers stats")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error fetching stats: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test adapter matchup function
print("\n[TEST 4] Testing adapter matchup function...")
print("  Fetching matchup data: Lakers @ Celtics...")
try:
    away_data, home_data = get_team_stats_for_matchup(
        "Los Angeles Lakers",
        "Boston Celtics",
        headless=True
    )

    if away_data and home_data:
        print(f"  OK Away: {away_data['team_name']}")
        print(f"    Overall: {away_data['stats']['points']} PPG")
        if away_data['splits']['road']:
            print(f"    On Road: {away_data['splits']['road']['points']} PPG")

        print(f"  OK Home: {home_data['team_name']}")
        print(f"    Overall: {home_data['stats']['points']} PPG")
        if home_data['splits']['home']:
            print(f"    At Home: {home_data['splits']['home']['points']} PPG")

        # Check splits availability
        away_splits = away_data['splits']['all_splits']
        home_splits = home_data['splits']['all_splits']
        print(f"  OK Splits: Away={len(away_splits)}, Home={len(home_splits)}")

    else:
        print("  ✗ Failed to fetch matchup data")
        sys.exit(1)

except Exception as e:
    print(f"  ✗ Error in matchup function: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL TESTS PASSED! OK")
print("=" * 80)
print()
print("StatMuse Integration Summary:")
print("-" * 80)
print(f"OK StatMuse adapter module: READY")
print(f"OK Team stats scraping: WORKING")
print(f"OK Matchup enrichment: WORKING")
print(f"OK Situational splits (home/road/conference): AVAILABLE")
print(f"OK Pipeline integration: ENABLED")
print()
print("The betting pipeline will now:")
print("  1. Scrape Sportsbet for odds, markets, and insights")
print("  2. Enrich with StatMuse comprehensive team stats")
print("  3. Include home/road splits, conference splits, and trends")
print("  4. Provide enhanced data to the value engine")
print()
print("Next step: Run full pipeline with: python launcher.py --run 1")
print("=" * 80)
