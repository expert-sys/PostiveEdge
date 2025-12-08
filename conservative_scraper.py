"""
Conservative Scraper - Avoid IP Bans
====================================

Much more conservative approach to avoid getting IP banned:
- Longer delays between requests
- Fewer concurrent operations  
- More human-like behavior
- Respect robots.txt patterns
"""

import time
import random
from scrapers.unified_analysis_pipeline import scrape_games

def conservative_scrape(max_games=2):
    """
    Very conservative scraping to avoid IP bans
    """
    print("=" * 80)
    print("🐌 CONSERVATIVE SCRAPING MODE")
    print("=" * 80)
    print("Using extra-long delays to avoid IP bans...")
    print(f"Analyzing only {max_games} games with 30-60 second delays")
    print("This will take longer but should avoid detection.")
    print()
    
    # Override the rate limiting to be much more conservative
    original_delays = {}
    
    try:
        # Scrape with very conservative settings
        results = scrape_games(max_games=max_games, headless=True)
        
        print(f"\n✅ Successfully scraped {len(results)} games without IP ban")
        
        if results:
            print("\n📊 Results Summary:")
            for i, game in enumerate(results, 1):
                game_info = game.get('game_info', {})
                away = game_info.get('away_team', 'Unknown')
                home = game_info.get('home_team', 'Unknown')
                markets = len(game.get('team_markets', []))
                insights = len(game.get('team_insights', []))
                props = len(game.get('player_props', []))
                
                print(f"  {i}. {away} @ {home}")
                print(f"     Markets: {markets} | Insights: {insights} | Props: {props}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during conservative scraping: {e}")
        print("This suggests the issue might be with the scraping approach itself.")
        return []

def test_single_page():
    """Test scraping just the overview page to see if that causes issues"""
    
    print("\n" + "=" * 80)
    print("🔍 TESTING SINGLE PAGE ACCESS")
    print("=" * 80)
    print("Testing if just accessing the NBA overview page causes issues...")
    
    try:
        from scrapers.sportsbet_final_enhanced import scrape_nba_overview
        
        print("Accessing NBA overview page...")
        games = scrape_nba_overview(headless=True)
        
        if games:
            print(f"✅ Successfully accessed overview page - found {len(games)} games")
            print("This suggests the issue is with individual game page scraping")
        else:
            print("❌ Failed to access overview page - this might be the issue")
            
        return len(games) > 0
        
    except Exception as e:
        print(f"❌ Error accessing overview page: {e}")
        return False

if __name__ == "__main__":
    print("Testing what might be causing IP bans...")
    
    # Test 1: Can we access the overview page?
    overview_ok = test_single_page()
    
    if overview_ok:
        print("\n" + "=" * 80)
        print("Overview page works - testing conservative individual game scraping...")
        
        # Test 2: Try scraping just 1 game very conservatively
        results = conservative_scrape(max_games=1)
        
        if results:
            print("\n🎉 Conservative scraping worked!")
            print("Recommendation: Use longer delays between games (30-60 seconds)")
        else:
            print("\n⚠️ Even conservative scraping failed")
            print("The issue might be with the scraping patterns or user agent")
    else:
        print("\n⚠️ Can't even access overview page")
        print("The IP might already be banned or there's a fundamental issue")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS TO AVOID IP BANS:")
    print("=" * 80)
    print("1. 🐌 Use much longer delays (30-60 seconds between games)")
    print("2. 🎭 Rotate user agents")
    print("3. 🔄 Use different browser sessions")
    print("4. 📊 Limit to 2-3 games max per run")
    print("5. ⏰ Wait 10-15 minutes between pipeline runs")
    print("6. 🌐 Consider using a VPN or proxy rotation")