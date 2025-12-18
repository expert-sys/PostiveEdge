"""
CLV Metrics Analysis Script
============================
Display CLV metrics by tier and confidence bucket.

Usage:
    python scripts/analyze_clv.py [days] [tier] [confidence_bucket]
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.clv_tracker import get_clv_tracker


def main():
    days = 30
    tier = None
    confidence_bucket = None
    
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    if len(sys.argv) > 2:
        tier = sys.argv[2] if sys.argv[2] != 'None' else None
    if len(sys.argv) > 3:
        confidence_bucket = sys.argv[3] if sys.argv[3] != 'None' else None
    
    tracker = get_clv_tracker()
    metrics = tracker.get_clv_metrics(days=days, tier=tier, confidence_bucket=confidence_bucket)
    
    print("="*70)
    print(f"CLV Metrics (Last {metrics['period_days']} days)")
    print("="*70)
    
    if not metrics['metrics']:
        print("\nNo data available for the specified period/filters.")
        return
    
    print("\nBreakdown by Tier and Confidence:")
    print("-"*70)
    
    for m in metrics['metrics']:
        print(f"\nTier: {m['tier']} | Confidence: {m['confidence_bucket']}")
        print(f"  Total Bets: {m['total_bets']}")
        print(f"  Wins: {m['wins']} | Hit Rate: {m['hit_rate']:.1%}")
        print(f"  Avg CLV: {m['avg_clv']:+.2f}%")
        print(f"  Positive CLV: {m['positive_clv_count']}/{m['total_bets']}")
        print(f"  Variance Flags: {m['variance_flag_count']} (good CLV + loss)")
        print(f"  Luck Flags: {m['luck_flag_count']} (bad CLV + win)")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
