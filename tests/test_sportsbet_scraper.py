"""
Test script to verify Sportsbet scraper extracts correct data
"""

from sportsbet_scraper import SportsbetScraper
import json

def test_match_scrape():
    """Test scraping the Indiana Pacers @ Detroit Pistons match"""

    # URL from the images
    match_url = "https://www.sportsbet.com.au/betting/basketball-us/nba/indiana-pacers-at-detroit-pistons-9852187"

    print("\n" + "="*70)
    print("  TESTING SPORTSBET SCRAPER")
    print("="*70)
    print(f"\nTarget URL: {match_url}")
    print("\nExpected Data (from images):")
    print("  Match: Indiana Pacers @ Detroit Pistons")
    print("  Time: Tue 1:10pm")
    print("  Away ML: 4.35")
    print("  Home ML: 1.22")
    print("  Away Handicap: +9.5 @ 1.90")
    print("  Home Handicap: -9.5 @ 1.90")
    print("  Total: Over/Under +228.5")
    print("\n" + "-"*70)

    scraper = SportsbetScraper(headless=True, slow_mo=50)

    try:
        print("\nStarting browser...")
        scraper.start_browser()

        print("Navigating to match page...")
        data = scraper.scrape_match_detail(match_url)

        if not data:
            print("\n❌ Failed to scrape data")
            return

        print("\n✓ Successfully scraped match data!")
        print("\n" + "="*70)
        print("  EXTRACTED DATA")
        print("="*70)

        # Match Odds
        print("\nMATCH BETTING (MONEYLINE):")
        print(f"  {data.match_odds.away_team}: {data.match_odds.away_ml_odds}")
        print(f"  {data.match_odds.home_team}: {data.match_odds.home_ml_odds}")
        print(f"  Match Time: {data.match_odds.match_time}")

        print("\nHANDICAP BETTING (SPREAD):")
        print(f"  {data.match_odds.away_team} {data.match_odds.away_handicap}: {data.match_odds.away_handicap_odds}")
        print(f"  {data.match_odds.home_team} {data.match_odds.home_handicap}: {data.match_odds.home_handicap_odds}")

        print("\nTOTAL POINTS:")
        print(f"  Over {data.match_odds.over_line}: {data.match_odds.over_odds}")
        print(f"  Under {data.match_odds.under_line}: {data.match_odds.under_odds}")

        print("\nHEAD-TO-HEAD DATA:")
        print(f"  Total H2H games found: {len(data.head_to_head)}")

        if data.head_to_head:
            print("\n  Last 5 H2H games:")
            for i, game in enumerate(data.head_to_head[:5], 1):
                print(f"    {i}. {game.date} - {game.venue}")
                print(f"       {game.home_team}: {game.final_home} | {game.away_team}: {game.final_away}")
                print(f"       Quarters: {game.q1_home}-{game.q1_away}, {game.q2_home}-{game.q2_away}, {game.q3_home}-{game.q3_away}, {game.q4_home}-{game.q4_away}")
                print(f"       Winner: {game.winner}")

        print("\nTEAM STATISTICS:")
        for team_name, stats in data.team_stats.items():
            print(f"  {team_name}:")
            print(f"    Record: {stats.wins}-{stats.losses} ({stats.win_percentage*100:.1f}%)")
            print(f"    Last 5: {stats.last_5_results}")
            print(f"    Season results: {len(stats.season_results)} games")

        print("\nMATCH INSIGHTS:")
        print(f"  Total insights: {len(data.insights)}")
        for insight in data.insights[:5]:
            print(f"    • {insight.team}: {insight.insight}")
            if insight.value:
                print(f"      Value: {insight.value}")

        # Save full data
        print("\n" + "-"*70)
        print("\nSaving full data to test_output.json...")
        scraper.save_to_json(data, "test_output.json")

        # Verification
        print("\n" + "="*70)
        print("  VERIFICATION")
        print("="*70)

        correct_count = 0
        total_checks = 0

        # Check team names
        total_checks += 1
        if "Pacers" in data.match_odds.away_team and "Pistons" in data.match_odds.home_team:
            print("✓ Team names correct")
            correct_count += 1
        else:
            print(f"✗ Team names incorrect: {data.match_odds.away_team} @ {data.match_odds.home_team}")

        # Check moneyline odds (with tolerance)
        total_checks += 2
        if data.match_odds.away_ml_odds and abs(data.match_odds.away_ml_odds - 4.35) < 0.1:
            print(f"✓ Away ML odds correct: {data.match_odds.away_ml_odds}")
            correct_count += 1
        else:
            print(f"✗ Away ML odds incorrect: {data.match_odds.away_ml_odds} (expected ~4.35)")

        if data.match_odds.home_ml_odds and abs(data.match_odds.home_ml_odds - 1.22) < 0.1:
            print(f"✓ Home ML odds correct: {data.match_odds.home_ml_odds}")
            correct_count += 1
        else:
            print(f"✗ Home ML odds incorrect: {data.match_odds.home_ml_odds} (expected ~1.22)")

        # Check handicap
        total_checks += 1
        if data.match_odds.away_handicap and "+9.5" in data.match_odds.away_handicap:
            print(f"✓ Handicap correct: {data.match_odds.away_handicap}")
            correct_count += 1
        else:
            print(f"⚠ Handicap: {data.match_odds.away_handicap} (expected +9.5)")

        # Check H2H data
        total_checks += 1
        if len(data.head_to_head) >= 2:
            print(f"✓ H2H data extracted: {len(data.head_to_head)} games")
            correct_count += 1
        else:
            print(f"⚠ Limited H2H data: {len(data.head_to_head)} games")

        # Check insights
        total_checks += 1
        if len(data.insights) > 0:
            print(f"✓ Insights extracted: {len(data.insights)} insights")
            correct_count += 1
        else:
            print(f"⚠ No insights extracted")

        print("\n" + "-"*70)
        print(f"\nVerification Score: {correct_count}/{total_checks} checks passed")

        if correct_count >= total_checks * 0.8:
            print("\n✓✓✓ SCRAPER WORKING CORRECTLY! ✓✓✓")
        elif correct_count >= total_checks * 0.5:
            print("\n⚠ SCRAPER PARTIALLY WORKING - May need selector updates")
        else:
            print("\n✗ SCRAPER NEEDS FIXES - Selectors likely outdated")

        return data

    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        print("\nClosing browser...")
        scraper.close_browser()


def test_overview_scrape():
    """Test scraping NBA overview"""

    print("\n" + "="*70)
    print("  TESTING NBA OVERVIEW SCRAPE")
    print("="*70)

    scraper = SportsbetScraper(headless=True, slow_mo=50)

    try:
        scraper.start_browser()

        print("\nScraping NBA overview page...")
        matches = scraper.scrape_nba_overview()

        print(f"\n✓ Found {len(matches)} matches")

        if matches:
            print("\nFirst 3 matches:")
            for i, match in enumerate(matches[:3], 1):
                print(f"\n{i}. {match.away_team} @ {match.home_team}")
                print(f"   Time: {match.match_time}")
                print(f"   ML: {match.away_ml_odds} / {match.home_ml_odds}")
                print(f"   Handicap: {match.away_handicap} ({match.away_handicap_odds}) / {match.home_handicap} ({match.home_handicap_odds})")
                print(f"   Markets: {match.num_markets}")
                print(f"   URL: {match.match_url[:80]}..." if match.match_url else "   URL: None")

        return matches

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        scraper.close_browser()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  SPORTSBET SCRAPER VERIFICATION TEST")
    print("="*70)
    print("\nThis will test the scraper against the data shown in your images.")
    print("\nTest 1: Scraping specific match detail")
    print("Test 2: Scraping NBA overview")
    print("\n" + "-"*70)

    # Test 1: Match detail
    match_data = test_match_scrape()

    print("\n\n")

    # Test 2: Overview
    overview_matches = test_overview_scrape()

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)
    print("\nCheck test_output.json for full extracted data")
    print("\n")
