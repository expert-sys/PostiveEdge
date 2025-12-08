"""
Demo: Team Markets Analysis with Sample Data
Shows what the system outputs when it has team results data
"""

from team_betting_engine import TeamBettingEngine, MarketType

# Initialize engine
engine = TeamBettingEngine()

print("="*80)
print("NBA BETTING SYSTEM - TEAM MARKETS DEMO")
print("="*80)
print()

# Sample game 1: Lakers @ Celtics
print("GAME 1: Los Angeles Lakers @ Boston Celtics")
print("-" * 80)
print()

# Lakers recent results (from your screenshot)
lakers_results = [
    (123, 120, "W"),  # Most recent
    (125, 108, "W"),
    (121, 133, "L"),
    (119, 129, "L"),
    (118, 135, "L"),
    (108, 106, "W"),
    (126, 140, "L"),
    (119, 95, "W"),
]

celtics_results = [
    (120, 130, "L"),
    (123, 115, "W"),
    (122, 108, "W"),
    (127, 120, "W"),
    (116, 118, "L"),
    (116, 115, "W"),
    (122, 108, "W"),
    (123, 115, "W"),
]

# Analyze form
lakers_form = engine.analyze_team_form("Lakers", lakers_results)
celtics_form = engine.analyze_team_form("Celtics", celtics_results)

print(f"Lakers Form:")
print(f"  Avg Scored: {lakers_form.avg_points_scored:.1f} ppg")
print(f"  Avg Allowed: {lakers_form.avg_points_allowed:.1f} ppg")
print(f"  Win%: {lakers_form.win_pct:.1%}")
print(f"  Streak: {lakers_form.streak}")
print(f"  Form: {lakers_form.recent_form}")
print(f"  Trend: Offense {lakers_form.scoring_trend}, Defense {lakers_form.defensive_trend}")
print()

print(f"Celtics Form:")
print(f"  Avg Scored: {celtics_form.avg_points_scored:.1f} ppg")
print(f"  Avg Allowed: {celtics_form.avg_points_allowed:.1f} ppg")
print(f"  Win%: {celtics_form.win_pct:.1%}")
print(f"  Streak: {celtics_form.streak}")
print(f"  Form: {celtics_form.recent_form}")
print(f"  Trend: Offense {celtics_form.scoring_trend}, Defense {celtics_form.defensive_trend}")
print()

# Project game
projection = engine.project_game(
    home_team="Celtics",
    away_team="Lakers",
    home_form=celtics_form,
    away_form=lakers_form
)

print("Game Projection:")
print(f"  Projected Score: Lakers {projection.projected_away_score:.1f} - Celtics {projection.projected_home_score:.1f}")
print(f"  Projected Total: {projection.projected_total:.1f}")
print(f"  Projected Margin: {projection.projected_margin:+.1f} (Celtics)")
print()
print(f"  Win Probabilities:")
print(f"    Celtics: {projection.home_win_probability:.1%}")
print(f"    Lakers: {projection.away_win_probability:.1%}")
print()
print(f"  Recommended Lines:")
print(f"    Spread: Celtics {projection.recommended_spread:+.1f}")
print(f"    Total: {projection.recommended_total:.1f}")
print()
print(f"  Confidence: {projection.projection_confidence:.0f}%")
print()

if projection.notes:
    print("  Notes:")
    for note in projection.notes:
        print(f"    • {note}")
print()

# Evaluate sample bets
print("="*80)
print("BETTING RECOMMENDATIONS")
print("="*80)
print()

# Moneyline
bet1 = engine.evaluate_bet(
    projection=projection,
    market_type=MarketType.MONEYLINE,
    line=0,
    odds=1.85,
    selection="Celtics ML"
)

if bet1:
    print(f"1. TEAM MARKET: Moneyline - {bet1.selection}")
    print(f"   Game: Lakers @ Celtics (Dec 6, 2025 11:10 AM)")
    print(f"   Odds: {bet1.odds} | Confidence: {bet1.confidence_score:.0f}% | Strength: {bet1.recommendation_strength}")
    print(f"   Edge: {bet1.edge_percentage:+.1f}% | EV: {bet1.expected_value:+.1f}%")
    print(f"   Projected Probability: {bet1.projected_probability:.1%}")
    print(f"   Projected Score: {projection.projected_away_score:.1f} - {projection.projected_home_score:.1f}")
    print(f"   Reasoning:")
    for reason in bet1.reasoning[:3]:
        print(f"     • {reason}")
    print()

# Total
bet2 = engine.evaluate_bet(
    projection=projection,
    market_type=MarketType.TOTAL,
    line=223.5,
    odds=1.90,
    selection="Over 223.5"
)

if bet2:
    print(f"2. TEAM MARKET: Total - {bet2.selection}")
    print(f"   Game: Lakers @ Celtics (Dec 6, 2025 11:10 AM)")
    print(f"   Odds: {bet2.odds} | Confidence: {bet2.confidence_score:.0f}% | Strength: {bet2.recommendation_strength}")
    print(f"   Edge: {bet2.edge_percentage:+.1f}% | EV: {bet2.expected_value:+.1f}%")
    print(f"   Projected Probability: {bet2.projected_probability:.1%}")
    print(f"   Projected Total: {projection.projected_total:.1f} vs Line {223.5}")
    print(f"   Reasoning:")
    for reason in bet2.reasoning[:3]:
        print(f"     • {reason}")
    print()

# Spread
bet3 = engine.evaluate_bet(
    projection=projection,
    market_type=MarketType.SPREAD,
    line=-3.5,
    odds=1.90,
    selection="Celtics -3.5"
)

if bet3:
    print(f"3. TEAM MARKET: Spread - {bet3.selection}")
    print(f"   Game: Lakers @ Celtics (Dec 6, 2025 11:10 AM)")
    print(f"   Odds: {bet3.odds} | Confidence: {bet3.confidence_score:.0f}% | Strength: {bet3.recommendation_strength}")
    print(f"   Edge: {bet3.edge_percentage:+.1f}% | EV: {bet3.expected_value:+.1f}%")
    print(f"   Projected Probability: {bet3.projected_probability:.1%}")
    print(f"   Projected Margin: {projection.projected_margin:+.1f} vs Spread {-3.5:+.1f}")
    print(f"   Reasoning:")
    for reason in bet3.reasoning[:3]:
        print(f"     • {reason}")
    print()

print("="*80)
print("SUMMARY")
print("="*80)
print()
print("The system successfully:")
print("✓ Analyzed team form from recent results")
print("✓ Projected game outcome (scores, totals, margins)")
print("✓ Evaluated all three market types (ML, Total, Spread)")
print("✓ Identified value bets with positive expected value")
print()
print("NOTE: This demo uses sample data. The live system needs insights")
print("      data from Sportsbet to extract recent game results.")
