"""
Enhanced Filtering & Display Demo
==================================
Demonstrates the bet enhancement system with sample data.

Shows all 10 enhancements:
1. Quality Tier Classification
2. Sample Size Penalty
3. Correlation Detection
4. Line Difficulty
5. Market Efficiency
6. Consistency Ranking
7. EV/Prob Ratio
8. Fair Odds
9. Projection Margin
10. Auto-Sorting
"""

import sys
import io

# Fix Windows encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from bet_enhancement_system import BetEnhancementSystem, QualityTier
import json


# ============================================================================
# SAMPLE BETTING RECOMMENDATIONS
# ============================================================================

sample_recommendations = [
    # S-Tier Example: Elite Value
    {
        "player_name": "Luka Dončić",
        "player_team": "Dallas Mavericks",
        "opponent_team": "Houston Rockets",
        "market": "Points",
        "selection": "Over",
        "line": 28.5,
        "odds": 1.90,
        "projected_value": 32.4,
        "projected_probability": 0.75,
        "implied_probability": 0.526,
        "edge_percentage": 22.4,
        "expected_value": 21.3,
        "confidence_score": 82.0,
        "sample_size": 18,
        "game": "Dallas Mavericks @ Houston Rockets",
        "databallr_stats": {
            "avg_value": 31.2,
            "std_dev": 5.1
        }
    },

    # A-Tier Example: High Quality
    {
        "player_name": "Jayson Tatum",
        "player_team": "Boston Celtics",
        "opponent_team": "Atlanta Hawks",
        "market": "Rebounds",
        "selection": "Over",
        "line": 7.5,
        "odds": 1.85,
        "projected_value": 9.2,
        "projected_probability": 0.68,
        "implied_probability": 0.541,
        "edge_percentage": 13.9,
        "expected_value": 11.5,
        "confidence_score": 76.0,
        "sample_size": 22,
        "game": "Boston Celtics @ Atlanta Hawks",
        "databallr_stats": {
            "avg_value": 8.9,
            "std_dev": 2.1
        }
    },

    # B-Tier Example: Playable but lower sample
    {
        "player_name": "De'Aaron Fox",
        "player_team": "Sacramento Kings",
        "opponent_team": "Portland Trail Blazers",
        "market": "Assists",
        "selection": "Over",
        "line": 5.5,
        "odds": 1.95,
        "projected_value": 6.8,
        "projected_probability": 0.64,
        "implied_probability": 0.513,
        "edge_percentage": 12.7,
        "expected_value": 7.2,
        "confidence_score": 68.0,
        "sample_size": 3,  # Small sample - will get penalty
        "game": "Sacramento Kings @ Portland Trail Blazers",
        "databallr_stats": {
            "avg_value": 6.5,
            "std_dev": 2.3
        }
    },

    # Correlation Example: Same team, same stat
    {
        "player_name": "Domantas Sabonis",
        "player_team": "Sacramento Kings",
        "opponent_team": "Portland Trail Blazers",
        "market": "Assists",
        "selection": "Over",
        "line": 6.5,
        "odds": 1.88,
        "projected_value": 7.4,
        "projected_probability": 0.62,
        "implied_probability": 0.532,
        "edge_percentage": 8.8,
        "expected_value": 5.4,
        "confidence_score": 71.0,
        "sample_size": 15,
        "game": "Sacramento Kings @ Portland Trail Blazers",
        "databallr_stats": {
            "avg_value": 7.1,
            "std_dev": 1.8
        }
    },

    # High Line Example: 30+ points
    {
        "player_name": "Stephen Curry",
        "player_team": "Golden State Warriors",
        "opponent_team": "Los Angeles Lakers",
        "market": "Points",
        "selection": "Over",
        "line": 32.5,  # High line - gets penalty
        "odds": 2.10,
        "projected_value": 34.1,
        "projected_probability": 0.58,
        "implied_probability": 0.476,
        "edge_percentage": 10.4,
        "expected_value": 6.8,
        "confidence_score": 65.0,
        "sample_size": 12,
        "game": "Golden State Warriors @ Los Angeles Lakers",
        "databallr_stats": {
            "avg_value": 28.5,
            "std_dev": 8.2
        }
    },

    # Sharp Market Example: Low edge in efficient zone
    {
        "player_name": "LeBron James",
        "player_team": "Los Angeles Lakers",
        "opponent_team": "Golden State Warriors",
        "market": "Points",
        "selection": "Over",
        "line": 24.5,
        "odds": 1.78,
        "projected_value": 25.9,
        "projected_probability": 0.57,  # In 55-60% zone
        "implied_probability": 0.562,
        "edge_percentage": 0.8,  # Low edge < 3%
        "expected_value": 0.5,
        "confidence_score": 72.0,  # Not high enough to override
        "sample_size": 20,
        "game": "Golden State Warriors @ Los Angeles Lakers",
        "databallr_stats": {
            "avg_value": 25.3,
            "std_dev": 4.8
        }
    },

    # C-Tier Example: Marginal
    {
        "player_name": "Anthony Edwards",
        "player_team": "Minnesota Timberwolves",
        "opponent_team": "Denver Nuggets",
        "market": "Points",
        "selection": "Over",
        "line": 26.5,
        "odds": 1.92,
        "projected_value": 27.8,
        "projected_probability": 0.56,
        "implied_probability": 0.521,
        "edge_percentage": 3.9,
        "expected_value": 2.1,
        "confidence_score": 74.0,  # Confidence saves it
        "sample_size": 16,
        "game": "Minnesota Timberwolves @ Denver Nuggets",
        "databallr_stats": {
            "avg_value": 27.2,
            "std_dev": 6.1
        }
    },

    # D-Tier Example: Negative EV
    {
        "player_name": "Jordan Poole",
        "player_team": "Washington Wizards",
        "opponent_team": "Miami Heat",
        "market": "Points",
        "selection": "Over",
        "line": 22.5,
        "odds": 1.70,
        "projected_value": 20.8,
        "projected_probability": 0.48,  # Below 50%
        "implied_probability": 0.588,
        "edge_percentage": -10.8,
        "expected_value": -5.2,
        "confidence_score": 52.0,
        "sample_size": 8,
        "game": "Washington Wizards @ Miami Heat",
        "databallr_stats": {
            "avg_value": 21.1,
            "std_dev": 7.3
        }
    }
]


# ============================================================================
# RUN DEMO
# ============================================================================

def main():
    print("=" * 100)
    print("BET ENHANCEMENT SYSTEM - DEMONSTRATION")
    print("=" * 100)
    print()
    print("This demo shows all 10 enhancements in action:")
    print("  1. Quality Tier Classification (S/A/B/C/D)")
    print("  2. Sample Size Weighting Penalty")
    print("  3. Conflict Score for Correlated Bets")
    print("  4. Line Difficulty Filter")
    print("  5. Market Efficiency Check Override")
    print("  6. Consistency Ranking")
    print("  7. EV-to-Prob Ratio Filter")
    print("  8. True Fair Odds Display")
    print("  9. Projected Margin vs Line")
    print(" 10. Auto-Sorting Rules")
    print()
    print("=" * 100)
    print()

    # Create enhancer
    enhancer = BetEnhancementSystem()

    # Enhance recommendations
    print("Processing sample recommendations...")
    enhanced_bets = enhancer.enhance_recommendations(sample_recommendations)

    print(f"✓ Enhanced {len(enhanced_bets)} recommendations\n")

    # Display all bets (including D-Tier to show filtering)
    print("\n" + "=" * 100)
    print("ALL ENHANCED BETS (Before Filtering)")
    print("=" * 100)
    enhancer.display_enhanced_bets(enhanced_bets, max_display=20)

    # Filter to quality bets
    print("\n" + "=" * 100)
    print("QUALITY BETS ONLY (C-Tier or Better)")
    print("=" * 100)
    quality_bets = enhancer.filter_bets(enhanced_bets, min_tier=QualityTier.C, exclude_d_tier=True)
    print(f"\nFiltered: {len(enhanced_bets)} total → {len(quality_bets)} quality bets\n")

    enhancer.display_enhanced_bets(quality_bets, max_display=20)

    # Show tier distribution
    print("\n" + "=" * 100)
    print("TIER DISTRIBUTION")
    print("=" * 100)

    tier_counts = {}
    for bet in enhanced_bets:
        tier = bet.quality_tier.name
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier in ['S', 'A', 'B', 'C', 'D']:
        count = tier_counts.get(tier, 0)
        emoji = {'S': '💎', 'A': '⭐', 'B': '✓', 'C': '~', 'D': '❌'}[tier]
        print(f"  {emoji} {tier}-Tier: {count} bets")

    # Show filtering impact
    print("\n" + "=" * 100)
    print("FILTERING IMPACT")
    print("=" * 100)

    filtered_out = len(enhanced_bets) - len(quality_bets)
    print(f"  Total Recommendations: {len(enhanced_bets)}")
    print(f"  Passed Quality Filter: {len(quality_bets)}")
    print(f"  Filtered Out: {filtered_out}")
    print()

    # Show specific examples
    print("=" * 100)
    print("ENHANCEMENT EXAMPLES")
    print("=" * 100)
    print()

    # Find specific examples
    small_sample = next((b for b in enhanced_bets if b.sample_size < 5), None)
    if small_sample:
        print("⚠ SAMPLE SIZE PENALTY EXAMPLE:")
        print(f"  Player: {small_sample.player_name}")
        print(f"  Sample Size: {small_sample.sample_size}")
        print(f"  Penalty: {small_sample.sample_size_penalty:.0f} confidence points")
        print(f"  Effective Confidence: {small_sample.effective_confidence:.0f}%")
        print()

    correlated = next((b for b in enhanced_bets if b.correlation_penalty < 0), None)
    if correlated:
        print("⚠ CORRELATION PENALTY EXAMPLE:")
        print(f"  Player: {correlated.player_name}")
        print(f"  Penalty: {correlated.correlation_penalty:.0f} confidence points")
        print(f"  Reason: {correlated.warnings[0] if correlated.warnings else 'N/A'}")
        print()

    high_line = next((b for b in enhanced_bets if b.line and b.line >= 30), None)
    if high_line:
        print("⚠ LINE DIFFICULTY EXAMPLE:")
        print(f"  Player: {high_line.player_name}")
        print(f"  Line: {high_line.line}")
        print(f"  Penalty: {high_line.line_difficulty_penalty:.0f} points")
        print()

    sharp_market = next((b for b in enhanced_bets if b.market_efficiency_flag), None)
    if sharp_market:
        print("⚠ MARKET EFFICIENCY CHECK EXAMPLE:")
        print(f"  Player: {sharp_market.player_name}")
        print(f"  Edge: {sharp_market.edge_percentage:.1f}%")
        print(f"  Probability: {sharp_market.projected_probability:.1%}")
        print(f"  Passes Check: {sharp_market.passes_efficiency_check}")
        print()

    # Save results
    output_file = 'demo_enhanced_bets.json'
    enhanced_output = []
    for bet in quality_bets:
        bet_dict = bet.original_rec.copy()
        bet_dict['enhanced_metrics'] = {
            'quality_tier': bet.quality_tier.name,
            'tier_emoji': bet.tier_emoji,
            'effective_confidence': bet.effective_confidence,
            'adjusted_confidence': bet.adjusted_confidence,
            'sample_size_penalty': bet.sample_size_penalty,
            'correlation_penalty': bet.correlation_penalty,
            'line_difficulty_penalty': bet.line_difficulty_penalty,
            'consistency_rank': bet.consistency_rank.value if bet.consistency_rank else None,
            'consistency_score': bet.consistency_score,
            'ev_to_prob_ratio': bet.ev_to_prob_ratio,
            'fair_odds': bet.fair_odds,
            'odds_mispricing': bet.odds_mispricing,
            'projection_margin': bet.projection_margin,
            'final_score': bet.final_score,
            'notes': bet.notes,
            'warnings': bet.warnings
        }
        enhanced_output.append(bet_dict)

    with open(output_file, 'w') as f:
        json.dump(enhanced_output, f, indent=2)

    print(f"✓ Saved enhanced bets to {output_file}")
    print()
    print("=" * 100)
    print("DEMO COMPLETE")
    print("=" * 100)


if __name__ == '__main__':
    main()
