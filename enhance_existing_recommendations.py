"""
Enhance Existing Betting Recommendations
=========================================
Applies the bet enhancement system to existing betting_recommendations.json

Usage:
    python enhance_existing_recommendations.py
    python enhance_existing_recommendations.py --input betting_recommendations.json
    python enhance_existing_recommendations.py --min-tier A
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
    parser = argparse.ArgumentParser(description="Enhance existing betting recommendations")
    parser.add_argument('--input', type=str, default='betting_recommendations.json',
                       help="Input recommendations file (default: betting_recommendations.json)")
    parser.add_argument('--output', type=str, default=None,
                       help="Output file (default: input_enhanced.json)")
    parser.add_argument('--min-tier', type=str, default='C', choices=['S', 'A', 'B', 'C'],
                       help="Minimum quality tier (default: C)")
    parser.add_argument('--max-display', type=int, default=20,
                       help="Maximum bets to display (default: 20)")

    args = parser.parse_args()

    # Set output file
    if args.output is None:
        args.output = args.input.replace('.json', '_enhanced.json')

    # Load recommendations
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {args.input}")
        print(f"\nAvailable files:")
        for f in Path('.').glob('betting_recommendations*.json'):
            print(f"  - {f.name}")
        return 1

    print("=" * 100)
    print("BET ENHANCEMENT SYSTEM")
    print("=" * 100)
    print(f"\nInput:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Min Tier: {args.min_tier}-Tier or better")
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
    print("=" * 100)
    print("APPLYING ENHANCEMENTS")
    print("=" * 100)
    print()

    enhancer = BetEnhancementSystem()

    try:
        enhanced_bets = enhancer.enhance_recommendations(recommendations)
        print(f"✓ Enhanced {len(enhanced_bets)} bets")
        print()
    except Exception as e:
        print(f"❌ Error during enhancement: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Map tier string to enum
    tier_map = {
        'S': QualityTier.S,
        'A': QualityTier.A,
        'B': QualityTier.B,
        'C': QualityTier.C
    }
    min_tier = tier_map[args.min_tier]

    # Filter
    quality_bets = enhancer.filter_bets(enhanced_bets, min_tier=min_tier, exclude_d_tier=True)

    print("=" * 100)
    print("FILTERING RESULTS")
    print("=" * 100)
    print()

    # Show tier distribution
    tier_counts = {}
    for bet in enhanced_bets:
        tier = bet.quality_tier.name
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("Tier Distribution:")
    for tier in ['S', 'A', 'B', 'C', 'D']:
        count = tier_counts.get(tier, 0)
        emoji = {'S': '💎', 'A': '⭐', 'B': '✓', 'C': '~', 'D': '❌'}[tier]
        print(f"  {emoji} {tier}-Tier: {count} bets")

    print()
    print(f"Total Bets: {len(enhanced_bets)}")
    print(f"Quality Bets ({args.min_tier}+ Tier): {len(quality_bets)}")
    print(f"Filtered Out: {len(enhanced_bets) - len(quality_bets)}")
    print()

    if not quality_bets:
        print(f"⚠️ No bets meet the {args.min_tier}-Tier threshold")
        print(f"   Try: python {sys.argv[0]} --min-tier C")
        return 0

    # Display enhanced bets
    enhancer.display_enhanced_bets(quality_bets, max_display=args.max_display)

    # Save enhanced bets
    print("\n" + "=" * 100)
    print("SAVING RESULTS")
    print("=" * 100)
    print()

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

    try:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_output, f, indent=2, default=str)
        print(f"✓ Saved {len(enhanced_output)} enhanced bets to {args.output}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return 1

    print()
    print("=" * 100)
    print("ENHANCEMENT COMPLETE")
    print("=" * 100)

    # Show quick summary
    print()
    print("Quick Summary:")
    if tier_counts.get('S', 0) > 0:
        print(f"  💎 {tier_counts['S']} Elite Value bet(s)")
    if tier_counts.get('A', 0) > 0:
        print(f"  ⭐ {tier_counts['A']} High Quality bet(s)")
    if tier_counts.get('B', 0) > 0:
        print(f"  ✓ {tier_counts['B']} Playable bet(s)")
    if tier_counts.get('C', 0) > 0:
        print(f"  ~ {tier_counts['C']} Marginal bet(s)")

    print()
    print("Next Steps:")
    print(f"  - Review enhanced bets in: {args.output}")
    print(f"  - Focus on S/A-Tier bets for best value")
    print(f"  - Watch for correlation penalties in parlays")
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
