"""
Test script for enhanced Sportsbet scraper

This script tests the new insights extraction functionality.
"""

import json
from scrapers.sportsbet_final_enhanced import scrape_match_complete

# Test URL - you can replace this with any current NBA match URL from Sportsbet
TEST_URL = "https://www.sportsbet.com.au/betting/basketball-us/nba"  # Replace with actual match URL

def test_enhanced_scraper():
    """Test the enhanced scraper with comprehensive logging"""

    print("=" * 80)
    print("TESTING ENHANCED SPORTSBET SCRAPER")
    print("=" * 80)
    print()

    # Note: Set headless=False to see the browser in action
    # Set headless=True for automated/production runs
    print(f"Scraping URL: {TEST_URL}")
    print("Note: This will take 3-5 minutes to complete...")
    print()

    # Run the scraper (with browser visible for debugging)
    result = scrape_match_complete(TEST_URL, headless=False)

    if not result:
        print("\n❌ Scraping failed! Check the logs above for errors.")
        return

    # Convert to dict for easier inspection
    data = result.to_dict()

    # Display results
    print("\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    print()

    print(f"Match: {data['away_team']} @ {data['home_team']}")
    print(f"URL: {data['url']}")
    print(f"Scraped at: {data['scraped_at']}")
    print()

    # Insights summary
    print("INSIGHTS EXTRACTION:")
    print("-" * 40)
    stats = data.get('insights_extraction_stats', {})
    print(f"  JSON Insights (embedded): {stats.get('total_json_insights', 0)}")
    print(f"  DOM Insights (from cards): {stats.get('total_dom_insights', 0)}")
    print(f"  Combined Total: {stats.get('combined_insights', 0)}")
    print(f"  Show Tip clicks: {stats.get('show_tip_buttons_clicked', 0)}")
    print(f"  Display More clicks: {stats.get('display_more_clicks', 0)}")
    print()

    # Match preview
    print("MATCH PREVIEW:")
    print("-" * 40)
    if data.get('match_preview'):
        preview_text = data['match_preview']['preview_text']
        print(f"  ✓ Found ({len(preview_text)} characters)")
        print(f"  Preview: {preview_text[:150]}...")
    else:
        print("  ✗ Not found")
    print()

    # Insight cards
    print("INSIGHT CARDS (DOM Extracted):")
    print("-" * 40)
    insight_cards = data.get('insight_cards', [])
    if insight_cards:
        print(f"  ✓ Found {len(insight_cards)} cards")
        for i, card in enumerate(insight_cards[:5], 1):  # Show first 5
            print(f"\n  Card {i}:")
            print(f"    Title: {card['title']}")
            print(f"    Description: {card['description'][:80]}...")
            print(f"    Odds: {card['odds']}")
            print(f"    Market Type: {card['market_type']}")
            if card['player']:
                print(f"    Player: {card['player']}")
        if len(insight_cards) > 5:
            print(f"\n  ... and {len(insight_cards) - 5} more cards")
    else:
        print("  ✗ No cards extracted")
    print()

    # Season results
    print("SEASON RESULTS:")
    print("-" * 40)
    if data.get('team_insights'):
        away_results = data['team_insights'].get('away_season_results', [])
        home_results = data['team_insights'].get('home_season_results', [])
        print(f"  Away team: {len(away_results)} games")
        print(f"  Home team: {len(home_results)} games")
    else:
        print("  ✗ Not extracted")
    print()

    # Head-to-head
    print("HEAD-TO-HEAD:")
    print("-" * 40)
    if data.get('team_insights'):
        h2h = data['team_insights'].get('head_to_head', [])
        print(f"  {len(h2h)} games")
    else:
        print("  ✗ Not extracted")
    print()

    # Markets
    print("BETTING MARKETS:")
    print("-" * 40)
    markets = data.get('markets', {})
    print(f"  Total: {markets.get('total', 0)}")
    print(f"  Moneyline: {len(markets.get('moneyline', []))}")
    print(f"  Handicap: {len(markets.get('handicap', []))}")
    print(f"  Totals: {len(markets.get('totals', []))}")
    print(f"  Props: {len(markets.get('props', []))}")
    print()

    # Save to file
    output_file = "test_enhanced_scraper_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Full results saved to: {output_file}")
    print()

    # Success criteria
    print("=" * 80)
    print("SUCCESS CRITERIA CHECK")
    print("=" * 80)
    print()

    success_count = 0
    total_checks = 6

    # Check 1: Insight cards extracted
    if len(insight_cards) > 0:
        print("✓ Insight cards extracted (> 0)")
        success_count += 1
    else:
        print("✗ No insight cards extracted")

    # Check 2: Combined insights increased
    if stats.get('combined_insights', 0) > stats.get('total_json_insights', 0):
        print("✓ Combined insights > JSON insights (DOM extraction working)")
        success_count += 1
    else:
        print("✗ DOM extraction may not be working")

    # Check 3: Match preview found
    if data.get('match_preview'):
        print("✓ Match preview extracted")
        success_count += 1
    else:
        print("⚠ Match preview not found (may not be available for this match)")

    # Check 4: Extraction stats populated
    if stats:
        print("✓ Extraction statistics tracked")
        success_count += 1
    else:
        print("✗ Extraction statistics missing")

    # Check 5: Button interactions
    if stats.get('show_tip_buttons_clicked', 0) > 0 or stats.get('display_more_clicks', 0) > 0:
        print("✓ Button interactions occurred")
        success_count += 1
    else:
        print("⚠ No button interactions (buttons may not be present)")

    # Check 6: No crashes
    print("✓ Scraper completed without crashing")
    success_count += 1

    print()
    print(f"Score: {success_count}/{total_checks} checks passed")
    print()

    if success_count >= 4:
        print("🎉 SCRAPER ENHANCEMENT SUCCESSFUL!")
    else:
        print("⚠ Some features may need adjustment. Check logs and screenshots.")

    print("=" * 80)


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                SPORTSBET SCRAPER ENHANCEMENT TEST                        ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Before running this test:
    1. Update TEST_URL with a current NBA match URL from Sportsbet
    2. Make sure you have a stable internet connection
    3. The browser will open in visible mode (headless=False) for debugging

    Expected improvements:
    - 5-10x more insights extracted (from ~4 to 20-40+)
    - Match preview text captured
    - Detailed extraction statistics
    - Screenshot saved to debug/insights_expanded.png

    Press Ctrl+C to cancel, or Enter to continue...
    """)

    try:
        input()
        test_enhanced_scraper()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
