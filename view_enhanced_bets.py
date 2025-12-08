"""
View Enhanced Bets - Show All Tiers
====================================
View all enhanced bets including D-Tier and those filtered by efficiency checks.

Usage:
    python view_enhanced_bets.py
    python view_enhanced_bets.py --show-all
    python view_enhanced_bets.py --no-filters
"""

import sys
import io
import json
import argparse
from pathlib import Path

# Fix Windows encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from bet_enhancement_system import BetEnhancementSystem, QualityTier


def main():
    parser = argparse.ArgumentParser(description="View all enhanced betting recommendations")
    parser.add_argument('--input', type=str, default='betting_recommendations.json',
                       help="Input recommendations file")
    parser.add_argument('--show-all', action='store_true',
                       help="Show all bets including D-Tier")
    parser.add_argument('--no-filters', action='store_true',
                       help="Disable efficiency and EV ratio filters")
    parser.add_argument('--max-display', type=int, default=30,
                       help="Maximum bets to display per tier")

    args = parser.parse_args()

    # Load recommendations
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {args.input}")
        print(f"\nAvailable files:")
        for f in Path('.').glob('betting_recommendations*.json'):
            print(f"  - {f.name}")
        return 1

    print("=" * 100)
    print("ENHANCED BET VIEWER - ALL TIERS")
    print("=" * 100)
    print(f"\nInput: {args.input}")
    print(f"Show D-Tier: {'Yes' if args.show_all else 'No'}")
    print(f"Filters: {'Disabled' if args.no_filters else 'Enabled'}")
    print()

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            recommendations = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return 1

    if not recommendations:
        print("❌ No recommendations found in file")
        return 1

    print(f"✓ Loaded {len(recommendations)} recommendations")
    print()

    # Enhance
    enhancer = BetEnhancementSystem()
    enhanced_bets = enhancer.enhance_recommendations(recommendations)

    print(f"✓ Enhanced {len(enhanced_bets)} bets")
    print()

    # Show tier distribution
    print("=" * 100)
    print("TIER DISTRIBUTION")
    print("=" * 100)
    print()

    tier_counts = {}
    for bet in enhanced_bets:
        tier = bet.quality_tier.name
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier in ['S', 'A', 'B', 'C', 'D']:
        count = tier_counts.get(tier, 0)
        emoji = {'S': '💎', 'A': '⭐', 'B': '✓', 'C': '~', 'D': '❌'}[tier]
        desc = {
            'S': 'Elite Value',
            'A': 'High Quality',
            'B': 'Playable',
            'C': 'Marginal',
            'D': 'Avoid'
        }[tier]
        print(f"  {emoji} {tier}-Tier ({desc}): {count} bets")

    print()

    # Apply filtering if requested
    if args.no_filters:
        # Show all tiers without filters
        if args.show_all:
            display_bets = enhanced_bets
            print("Showing: ALL BETS (no filters)")
        else:
            display_bets = [b for b in enhanced_bets if b.quality_tier != QualityTier.D]
            print("Showing: ALL EXCEPT D-TIER (no filters)")
    else:
        # Apply filters
        if args.show_all:
            # Show all tiers but apply filters
            display_bets = [b for b in enhanced_bets if b.passes_efficiency_check and b.passes_ev_ratio]
            print("Showing: ALL TIERS (with filters)")
        else:
            # Standard filtering
            display_bets = enhancer.filter_bets(enhanced_bets, min_tier=QualityTier.C, exclude_d_tier=True)
            print("Showing: C-TIER+ (with filters)")

    print(f"Displaying: {len(display_bets)} bets")
    print()

    # Show filter statistics
    print("=" * 100)
    print("FILTER STATISTICS")
    print("=" * 100)
    print()

    failed_efficiency = sum(1 for b in enhanced_bets if not b.passes_efficiency_check)
    failed_ev_ratio = sum(1 for b in enhanced_bets if not b.passes_ev_ratio)
    d_tier = tier_counts.get('D', 0)

    print(f"Bets failing efficiency check: {failed_efficiency}")
    print(f"Bets failing EV/Prob ratio: {failed_ev_ratio}")
    print(f"D-Tier bets (auto-filtered): {d_tier}")
    print(f"Total filtered out: {len(enhanced_bets) - len(display_bets)}")
    print()

    # Display details about filtered bets
    if failed_efficiency > 0:
        print("\nEfficiency Check Failures:")
        for bet in enhanced_bets:
            if not bet.passes_efficiency_check:
                print(f"  • {bet.player_name or 'TEAM'} - {bet.market}: "
                      f"Edge {bet.edge_percentage:.1f}%, Prob {bet.projected_probability:.1%}")

    if failed_ev_ratio > 0:
        print("\nEV/Prob Ratio Failures (< 0.08):")
        for bet in enhanced_bets:
            if not bet.passes_ev_ratio and bet.passes_efficiency_check:
                print(f"  • {bet.player_name or 'TEAM'} - {bet.market}: "
                      f"Ratio {bet.ev_to_prob_ratio:.3f} (EV {bet.expected_value:.1f}%, Prob {bet.projected_probability:.1%})")

    # Display enhanced bets
    print()
    enhancer.display_enhanced_bets(display_bets, max_display=args.max_display)

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()

    if tier_counts.get('S', 0) > 0:
        print(f"💎 {tier_counts['S']} ELITE VALUE bet(s) - Maximum unit size recommended")
    if tier_counts.get('A', 0) > 0:
        print(f"⭐ {tier_counts['A']} HIGH QUALITY bet(s) - Standard unit size")
    if tier_counts.get('B', 0) > 0:
        print(f"✓ {tier_counts['B']} PLAYABLE bet(s) - Reduced unit size")
    if tier_counts.get('C', 0) > 0:
        print(f"~ {tier_counts['C']} MARGINAL bet(s) - Minimal units or parlay only")
    if tier_counts.get('D', 0) > 0:
        print(f"❌ {tier_counts['D']} AVOID - No value")

    print()
    print("Recommendations:")
    if len(display_bets) == 0:
        print("  ⚠️ No quality bets found")
        print("  • Try: python view_enhanced_bets.py --no-filters")
        print("  • Or: python view_enhanced_bets.py --show-all")
    else:
        print(f"  ✓ Focus on top {min(5, len(display_bets))} bets")
        if failed_ev_ratio > 0:
            print(f"  ⚠️ {failed_ev_ratio} bet(s) have low EV/Prob ratio (payoff doesn't justify risk)")
        if failed_efficiency > 0:
            print(f"  ⚠️ {failed_efficiency} bet(s) in sharp markets (minimal edge)")

    # Save enhanced output
    print()
    print("=" * 100)
    print("SAVING OUTPUT")
    print("=" * 100)
    print()

    output_file = 'betting_recommendations_enhanced.json'
    enhanced_output = []
    for bet in display_bets:
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

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_output, f, indent=2, default=str)
        print(f"✓ Saved {len(enhanced_output)} enhanced bets to {output_file}")
    except Exception as e:
        print(f"⚠️ Could not save output file: {e}")

    print()

    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
