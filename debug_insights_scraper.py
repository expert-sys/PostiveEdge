"""
Debug script to test insights extraction
"""

from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
import json

print("="*80)
print("DEBUGGING INSIGHTS EXTRACTION")
print("="*80)
print()

# Get first game
print("Step 1: Getting NBA games...")
games = scrape_nba_overview(headless=False)  # Run with visible browser

if not games:
    print("ERROR: No games found!")
    exit(1)

print(f"Found {len(games)} games")
print()

# Test first game
first_game = games[0]
print(f"Step 2: Testing first game: {first_game['away_team']} @ {first_game['home_team']}")
print(f"URL: {first_game['url']}")
print()

print("Step 3: Scraping complete match data (browser will be visible)...")
print("Watch the browser to see if Stats & Insights tab is clicked")
print()

complete_data = scrape_match_complete(first_game['url'], headless=False)

if not complete_data:
    print("ERROR: Failed to scrape match data!")
    exit(1)

print("="*80)
print("RESULTS")
print("="*80)
print()

print(f"Markets found: {len(complete_data.all_markets)}")
print(f"Insights found: {len(complete_data.match_insights)}")
print(f"Match stats: {'Yes' if complete_data.match_stats else 'No'}")
print()

if complete_data.match_insights:
    print("Sample insights:")
    for i, insight in enumerate(complete_data.match_insights[:5], 1):
        print(f"\n{i}. {insight.fact}")
        if insight.market:
            print(f"   Market: {insight.market}")
        if insight.result:
            print(f"   Result: {insight.result}")
        if insight.odds:
            print(f"   Odds: {insight.odds}")
else:
    print("NO INSIGHTS FOUND!")
    print()
    print("Possible reasons:")
    print("1. Stats & Insights tab didn't load")
    print("2. Page structure has changed")
    print("3. Insights are loaded dynamically after tab click")
    print("4. Need to wait longer after clicking tab")
    print()
    print("Check the debug files:")
    print("  - debug/sportsbet_nba_page.html")
    print("  - debug/sportsbet_nba_page.png")

print()

# Save results
output_file = "debug_insights_output.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(complete_data.to_dict(), f, indent=2, ensure_ascii=False)

print(f"Saved results to: {output_file}")
print()
