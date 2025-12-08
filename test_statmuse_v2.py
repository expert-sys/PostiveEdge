"""
Quick test for StatMuse V2 integration with correct URLs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.statmuse_adapter import get_team_stats_for_matchup
from scrapers.statmuse_team_ids import get_statmuse_url, get_team_stats_url, get_team_splits_url

print("="*80)
print("STATMUSE V2 INTEGRATION TEST")
print("="*80)
print()

# Test 1: URL Generation
print("[TEST 1] URL Generation with correct team IDs")
print("-"*80)
test_teams = ["Los Angeles Lakers", "Boston Celtics", "Oklahoma City Thunder"]

for team in test_teams:
    try:
        base_url = get_statmuse_url(team)
        stats_url = get_team_stats_url(team)
        splits_url = get_team_splits_url(team)

        print(f"{team}:")
        print(f"  Stats:  {stats_url}")
        print(f"  Splits: {splits_url}")
        print()
    except Exception as e:
        print(f"{team}: ERROR - {e}")
        print()

# Test 2: Adapter Integration
print("[TEST 2] Adapter fetches data with correct URLs")
print("-"*80)
print("Fetching Lakers @ Celtics (headless mode)...")
print()

try:
    away_data, home_data = get_team_stats_for_matchup(
        "Los Angeles Lakers",
        "Boston Celtics",
        headless=True
    )

    if away_data and home_data:
        print("SUCCESS!")
        print()
        print(f"Away Team: {away_data['team_name']}")
        print(f"  Overall: {away_data['stats']['points']} PPG, {away_data['stats']['rebounds']} RPG")
        if away_data['splits']['road']:
            print(f"  On Road: {away_data['splits']['road']['points']} PPG")
        print(f"  Total Splits: {len(away_data['splits']['all_splits'])}")
        print()

        print(f"Home Team: {home_data['team_name']}")
        print(f"  Overall: {home_data['stats']['points']} PPG, {home_data['stats']['rebounds']} RPG")
        if home_data['splits']['home']:
            print(f"  At Home: {home_data['splits']['home']['points']} PPG")
        print(f"  Total Splits: {len(home_data['splits']['all_splits'])}")
        print()

        print("="*80)
        print("ALL TESTS PASSED!")
        print("="*80)
    else:
        print("FAILED - No data returned")
        print("="*80)

except Exception as e:
    print(f"FAILED - Exception: {e}")
    import traceback
    traceback.print_exc()
    print("="*80)
