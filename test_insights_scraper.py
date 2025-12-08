"""
Test script for the enhanced insights scraper
Scrapes NBA overview page to find today's games, then scrapes each game
"""
import sys
import json
from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete

print("=" * 80)
print("Testing Enhanced Sportsbet Scraper - Team Insights Extraction")
print("=" * 80)

# Step 1: Get today's games from NBA overview
print("\nStep 1: Finding today's NBA games...")
print("Scraping: https://www.sportsbet.com.au/betting/basketball-us/nba")

games = scrape_nba_overview(headless=False)

if not games:
    print("\n✗ No games found on NBA overview page")
    sys.exit(1)

print(f"\n✓ Found {len(games)} games")
for i, game in enumerate(games, 1):
    print(f"  {i}. {game.get('away_team', 'Unknown')} @ {game.get('home_team', 'Unknown')}")
    print(f"     URL: {game.get('url', 'N/A')}")

# Step 2: Scrape the first game for detailed insights
if games:
    print("\n" + "=" * 80)
    print("Step 2: Scraping first game for detailed insights...")
    print("=" * 80)
    
    first_game = games[0]
    test_url = first_game.get('url')
    
    if not test_url:
        print("\n✗ No URL found for first game")
        sys.exit(1)
    
    print(f"\nScraping: {test_url}")
    print("\nThis will extract:")
    print("  - Season results for both teams")
    print("  - Head-to-head matchup history")
    print("  - Quarter-by-quarter scores")
    print("\n" + "=" * 80)

    # Run the scraper (headless=False to see what's happening)
    data = scrape_match_complete(test_url, headless=False)

if data:
    print("\n✓ Scraping completed successfully!")
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    # Convert to dict for display
    result_dict = data.to_dict()
    
    print(f"\nMatch: {data.away_team} @ {data.home_team}")
    print(f"URL: {data.url}")
    print(f"Scraped at: {data.scraped_at}")
    
    # Team Insights
    if data.team_insights:
        insights = data.team_insights
        print("\n" + "-" * 80)
        print("TEAM INSIGHTS")
        print("-" * 80)
        
        print(f"\n{data.away_team} Season Results: {len(insights.away_season_results)} games")
        if insights.away_season_results:
            print("\nSample games:")
            for game in insights.away_season_results[:3]:
                home_away = "vs" if game.is_home else "@"
                print(f"  {game.date}: {home_away} {game.opponent} - {game.score_for}-{game.score_against} ({game.result})")
        
        print(f"\n{data.home_team} Season Results: {len(insights.home_season_results)} games")
        if insights.home_season_results:
            print("\nSample games:")
            for game in insights.home_season_results[:3]:
                home_away = "vs" if game.is_home else "@"
                print(f"  {game.date}: {home_away} {game.opponent} - {game.score_for}-{game.score_against} ({game.result})")
        
        print(f"\nHead-to-Head Games: {len(insights.head_to_head)} matchups")
        if insights.head_to_head:
            print("\nRecent H2H:")
            for h2h in insights.head_to_head[:3]:
                print(f"\n  {h2h.date} at {h2h.venue}")
                print(f"    {h2h.away_team}: Q1={h2h.away_scores.q1} Q2={h2h.away_scores.q2} Q3={h2h.away_scores.q3} Q4={h2h.away_scores.q4} Final={h2h.away_scores.final} ({h2h.away_result})")
                print(f"    {h2h.home_team}: Q1={h2h.home_scores.q1} Q2={h2h.home_scores.q2} Q3={h2h.home_scores.q3} Q4={h2h.home_scores.q4} Final={h2h.home_scores.final} ({h2h.home_result})")
        
        if insights.extraction_errors:
            print(f"\n⚠ Extraction Errors: {len(insights.extraction_errors)}")
            for error in insights.extraction_errors:
                print(f"  - {error['component']}: {error['error']}")
    else:
        print("\n⚠ No team insights extracted")
    
    # Save full results to JSON
    output_file = "test_insights_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Full results saved to: {output_file}")
    print("\n" + "=" * 80)
    
else:
    print("\n✗ Scraping failed - no data returned")
    sys.exit(1)
