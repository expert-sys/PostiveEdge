"""
Test StatMuse V2 Scraper - Visible Browser Mode
"""

from scrapers.statmuse_scraper_v2 import scrape_team_stats, scrape_player_stats, scrape_team_splits

print("=" * 80)
print("STATMUSE V2 SCRAPER - VISIBLE BROWSER MODE")
print("=" * 80)
print()
print("You will see the browser windows open...")
print("This demonstrates the scraper working in real-time")
print()

# Test with Lakers - headless=False to show browser
team = "los-angeles-lakers"
season = "2025-26"

print(f"[1/3] Scraping team stats for {team}...")
print()
team_stats = scrape_team_stats(team, season, headless=False)

if team_stats:
    print()
    print(f"SUCCESS: {team_stats.games_played} GP, {team_stats.points} PPG")
else:
    print("FAILED")

print()
input("Press Enter to continue to player stats...")
print()

print(f"[2/3] Scraping player stats for {team}...")
print()
players = scrape_player_stats(team, season, headless=False)

if players:
    print()
    print(f"SUCCESS: {len(players)} players")
    for p in players[:5]:
        print(f"  - {p.player_name}: {p.points} PPG")
else:
    print("FAILED")

print()
input("Press Enter to continue to splits...")
print()

print(f"[3/3] Scraping team splits for {team}...")
print()
splits = scrape_team_splits(team, season, headless=False)

if splits:
    print()
    print(f"SUCCESS: {len(splits)} splits")
    for s in splits[:8]:
        print(f"  - {s.split_type}: {s.games_played} GP, {s.points} PPG")
else:
    print("FAILED")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
