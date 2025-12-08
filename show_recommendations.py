"""
Show Betting Recommendations
=============================
Display betting insights and markets scraped from Sportsbet.
"""

import json

print("=" * 80)
print("BETTING RECOMMENDATIONS - Lakers @ Celtics")
print("=" * 80)
print()

# Load Sportsbet data
with open('test_scraper_output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

away_team = data['away_team']
home_team = data['home_team']
scraped_at = data['scraped_at']

print(f"Match: {away_team} @ {home_team}")
print(f"Scraped: {scraped_at}")
print()

# Show betting markets
print("=" * 80)
print("BETTING MARKETS")
print("=" * 80)
print()

markets = data.get('markets', {})

# Moneyline
if markets.get('moneyline'):
    print("MONEYLINE:")
    for market in markets['moneyline']:
        team = market['team']
        odds = market['odds']
        print(f"  {team}: {odds}")
print()

# Handicap
if markets.get('handicap'):
    print("HANDICAP:")
    for market in markets['handicap']:
        team = market['team']
        line = market['line']
        odds = market['odds']
        print(f"  {team} ({line}): {odds}")
print()

# Totals
if markets.get('totals'):
    print("TOTALS:")
    for market in markets['totals']:
        selection = market['selection_text']
        odds = market['odds']
        print(f"  {selection}: {odds}")
print()

# Show match insights
print("=" * 80)
print(f"MATCH INSIGHTS ({len(data.get('match_insights', []))} total)")
print("=" * 80)
print()

insights = data.get('match_insights', [])
for i, insight in enumerate(insights[:15], 1):  # Show top 15
    fact = insight.get('fact', '')
    tags = insight.get('tags', [])
    result = insight.get('result', '')
    market = insight.get('market', '')
    odds = insight.get('odds', '')

    print(f"{i}. {fact}")
    print(f"   Suggested Bet: {result} - {market} @ {odds}")
    print(f"   Tags: {', '.join(tags)}")
    print()

# Team Stats
print("=" * 80)
print("TEAM STATISTICS")
print("=" * 80)
print()

team_stats = data.get('team_stats', {})
if team_stats:
    # Away team
    away_stats = team_stats.get('away_team', {})
    if away_stats:
        print(f"{away_team}:")
        records = away_stats.get('records', {})
        for key, value in records.items():
            print(f"  {key}: {value}")
        print()

    # Home team
    home_stats = team_stats.get('home_team', {})
    if home_stats:
        print(f"{home_team}:")
        records = home_stats.get('records', {})
        for key, value in records.items():
            print(f"  {key}: {value}")
        print()

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print()
print("NOTE: StatMuse integration is complete but experiencing browser issues.")
print("Once browser is stable, the system will add:")
print("  - 52 situational splits per team (home/road, conference, monthly, etc.)")
print("  - Win/Loss scoring differentials")
print("  - Opponent-specific matchup history")
print("  - Enhanced confidence scoring using home/road context")
print()
print("For now, analysis is based on Sportsbet insights and markets.")
print("=" * 80)
