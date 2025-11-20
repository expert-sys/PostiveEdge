"""
Test Stats Extraction from Sportsbet
=====================================
Quick test to verify the enhanced scraper extracts team statistics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete

def test_stats_extraction():
    print("\n" + "="*70)
    print("  TESTING STATS EXTRACTION FROM SPORTSBET")
    print("="*70)
    print()

    # Get games
    print("Getting NBA games...\n")
    games = scrape_nba_overview(headless=True)

    if not games:
        print("Failed to get games\n")
        return

    print(f"Found {len(games)} games\n")
    print(f"Testing with: {games[0]['away_team']} @ {games[0]['home_team']}\n")

    # Scrape first game with complete data
    complete_data = scrape_match_complete(games[0]['url'], headless=True)

    if not complete_data:
        print("Failed to scrape match\n")
        return

    print("\n" + "="*70)
    print("  EXTRACTION RESULTS")
    print("="*70)

    print(f"\nMatch: {complete_data.away_team} @ {complete_data.home_team}")
    print(f"Markets: {len(complete_data.all_markets)}")
    print(f"Insights: {len(complete_data.match_insights)}")

    if complete_data.match_stats:
        print("\n✅ STATS EXTRACTED SUCCESSFULLY!")
        print("\n" + "-"*70)

        stats = complete_data.match_stats
        away = stats.away_team_stats
        home = stats.home_team_stats

        print(f"\nData Range: {stats.data_range}")
        print(f"\n{away.team_name} (Away) vs {home.team_name} (Home)")
        print("-"*70)

        # Check what was extracted
        extracted_fields = []

        if away.avg_points_for:
            extracted_fields.append("✅ Average Points For/Against")
        if away.avg_winning_margin:
            extracted_fields.append("✅ Winning/Losing Margins")
        if away.avg_total_points:
            extracted_fields.append("✅ Average Total Points")
        if away.favorite_win_pct:
            extracted_fields.append("✅ Favorite Win %")
        if away.underdog_win_pct:
            extracted_fields.append("✅ Underdog Win %")
        if away.night_win_pct:
            extracted_fields.append("✅ Night Record")
        if away.clutch_win_pct:
            extracted_fields.append("✅ Clutch Win %")
        if away.reliability_pct:
            extracted_fields.append("✅ Reliability % (lead at HT)")
        if away.comeback_pct:
            extracted_fields.append("✅ Comeback % (trail at HT)")
        if away.choke_pct:
            extracted_fields.append("✅ Choke % (blow lead)")

        print("\nExtracted Fields:")
        for field in extracted_fields:
            print(f"  {field}")

        if not extracted_fields:
            print("  ❌ No stats were extracted!")

        # Show sample values
        print("\nSample Values:")
        if away.avg_points_for and home.avg_points_for:
            print(f"  Points For: {away.avg_points_for:.1f} (away) | {home.avg_points_for:.1f} (home)")
        if away.clutch_win_pct and home.clutch_win_pct:
            print(f"  Clutch Win: {away.clutch_win_pct:.1f}% (away) | {home.clutch_win_pct:.1f}% (home)")
        if away.reliability_pct and home.reliability_pct:
            print(f"  Reliability: {away.reliability_pct:.1f}% (away) | {home.reliability_pct:.1f}% (home)")

    else:
        print("\n❌ NO STATS EXTRACTED")
        print("   The Stats & Insights tab may not have been clicked or parsed correctly")

    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    test_stats_extraction()
