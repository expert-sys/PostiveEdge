"""
Run Full Analysis with StatMuse Enrichment
==========================================
Demonstrates the complete pipeline with StatMuse data enrichment.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("BETTING ANALYSIS WITH STATMUSE ENRICHMENT")
print("=" * 80)
print()

# Load Sportsbet data
print("[1/4] Loading Sportsbet data...")
with open('test_scraper_output.json', 'r', encoding='utf-8') as f:
    sportsbet_data = json.load(f)

away_team = sportsbet_data['away_team']
home_team = sportsbet_data['home_team']
print(f"  Match: {away_team} @ {home_team}")

# Get StatMuse enrichment
print(f"\n[2/4] Fetching StatMuse data...")
from scrapers.statmuse_adapter import get_team_stats_for_matchup

away_stats, home_stats = get_team_stats_for_matchup(away_team, home_team, headless=True)

if away_stats and home_stats:
    print(f"  OK {away_team}:")
    print(f"    Overall: {away_stats['stats']['points']:.1f} PPG, {away_stats['stats']['rebounds']:.1f} RPG")
    if away_stats['splits']['road']:
        print(f"    On Road: {away_stats['splits']['road']['points']:.1f} PPG, {away_stats['splits']['road']['fg_pct']:.1f}% FG")

    print(f"  OK {home_team}:")
    print(f"    Overall: {home_stats['stats']['points']:.1f} PPG, {home_stats['stats']['rebounds']:.1f} RPG")
    if home_stats['splits']['home']:
        print(f"    At Home: {home_stats['splits']['home']['points']:.1f} PPG, {home_stats['splits']['home']['fg_pct']:.1f}% FG")

    # Show win/loss differential
    if away_stats['splits']['wins'] and away_stats['splits']['losses']:
        away_diff = away_stats['splits']['wins']['points'] - away_stats['splits']['losses']['points']
        print(f"    Win/Loss: +{away_diff:.1f} PPG in wins")

    if home_stats['splits']['wins'] and home_stats['splits']['losses']:
        home_diff = home_stats['splits']['wins']['points'] - home_stats['splits']['losses']['points']
        print(f"    Win/Loss: +{home_diff:.1f} PPG in wins")
else:
    print(f"  WARNING: StatMuse data unavailable, using Sportsbet data only")

# Prepare enriched data structure
print(f"\n[3/4] Preparing enriched data structure...")
enriched_game = {
    'game_info': {
        'away_team': away_team,
        'home_team': home_team,
        'url': sportsbet_data['url']
    },
    'team_markets': sportsbet_data.get('markets', {}),
    'team_insights': sportsbet_data.get('match_insights', []),
    'match_stats': sportsbet_data.get('team_stats', {}),
    'statmuse_stats': {
        'away_team': away_stats,
        'home_team': home_stats
    } if away_stats and home_stats else None,
    'player_props': [],
    'market_players': []
}

print(f"  OK Combined data structure created")
print(f"    - Sportsbet insights: {len(enriched_game['team_insights'])}")
print(f"    - Betting markets: {enriched_game['team_markets'].get('total', 0)}")
if away_stats:
    print(f"    - StatMuse splits: {len(away_stats['splits']['all_splits'])} per team")
else:
    print(f"    - StatMuse splits: unavailable (using Sportsbet data only)")

# Analyze with value engine
print(f"\n[4/4] Running value analysis...")
from scrapers.context_aware_analysis import analyze_team_bets_with_context

team_bets = analyze_team_bets_with_context([enriched_game], min_confidence=0.50)

print()
print("=" * 80)
print("BETTING RECOMMENDATIONS")
print("=" * 80)
print()

if team_bets:
    # Sort by confidence
    team_bets_sorted = sorted(team_bets, key=lambda x: x.get('confidence', 0), reverse=True)

    for i, bet in enumerate(team_bets_sorted[:5], 1):
        print(f"{i}. {bet['team']} - {bet['market_type']}")
        print(f"   Odds: {bet['odds']} | Confidence: {bet['confidence']:.0%}")
        print(f"   Bet: {bet['bet_type']}")

        # Show key factors
        factors = bet.get('factors', [])
        if factors:
            print(f"   Key Factors:")
            for factor in factors[:3]:
                print(f"     • {factor}")

        # Show StatMuse context if available
        context_summary = bet.get('context_summary', '')
        if 'StatMuse' in context_summary or 'road' in context_summary.lower() or 'home' in context_summary.lower():
            print(f"   Context: {context_summary[:100]}...")

        print()
else:
    print("No high-confidence bets found.")

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print()
print("StatMuse Integration:")
if away_stats and home_stats:
    print(f"  OK Team stats: ENRICHED")
    print(f"  OK Situational splits: {len(away_stats['splits']['all_splits'])} per team")
    print(f"  OK Home/Road context: AVAILABLE")
    print(f"  OK Win/Loss patterns: AVAILABLE")
else:
    print(f"  WARNING: StatMuse unavailable (browser issues)")
    print(f"  NOTE: Analysis using Sportsbet data only")
print()
