"""
Test script for databallr scraper
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.databallr_scraper import get_player_game_log

def test_scraper():
    """Test the databallr scraper with a known player"""

    print("\n" + "="*70)
    print("  TESTING DATABALLR SCRAPER")
    print("="*70)
    print()

    # Test with LeBron James (should be easy to find)
    test_player = "LeBron James"

    print(f"Testing with: {test_player}")
    print(f"Fetching last 5 games...\n")

    try:
        game_log = get_player_game_log(
            player_name=test_player,
            last_n_games=5,
            headless=False,  # Show browser for debugging
            retries=1
        )

        if game_log:
            print(f"\n✓ SUCCESS: Retrieved {len(game_log)} games\n")
            print("Game Log (Full Stats):")
            print("-" * 100)
            for i, game in enumerate(game_log, 1):
                print(f"\n{i}. {game.game_date}:")
                print(f"   Basic: {game.points} pts, {game.rebounds} reb, {game.assists} ast, {game.minutes:.1f} min")
                print(f"   Defense: {game.steals} stl, {game.blocks} blk, {game.turnovers} tov")
                print(f"   Shooting: FT {game.ft_attempted} att, +/- {game.plus_minus}")
                # Note: Advanced stats (Involve%, TS%, etc.) are in the raw game dict but not in GameLogEntry
            print("\n" + "-" * 100)
            print()

            # Validate data quality
            has_points = any(game.points > 0 for game in game_log)
            has_dates = all(game.game_date != "Unknown" for game in game_log)
            has_defense = any(game.steals > 0 or game.blocks > 0 for game in game_log)

            print("Data Quality Check:")
            print(f"  - Has valid points: {'✓' if has_points else '✗'}")
            print(f"  - Has valid dates: {'✓' if has_dates else '✗'}")
            print(f"  - Has defensive stats: {'✓' if has_defense else '✗'}")
            print()

            if has_points and has_dates:
                print("✓ Scraper is working correctly!")
            else:
                print("⚠ Scraper retrieved data but quality may be low")

        else:
            print("\n✗ FAILED: No games retrieved")
            print("This could mean:")
            print("  - Player not found on databallr.com")
            print("  - Website structure has changed")
            print("  - Network/timeout issues")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print()

if __name__ == "__main__":
    test_scraper()
