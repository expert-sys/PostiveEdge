"""
Test Sample Size Regression Fix
================================
Demonstrates that small samples with 100% success rates are now properly regressed.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.context_aware_analysis import ContextAwareAnalyzer

def test_small_sample_regression():
    """Test that 5/5 and 6/6 are no longer treated as 100% locked"""

    analyzer = ContextAwareAnalyzer()

    print("\n" + "="*70)
    print("TESTING SAMPLE SIZE REGRESSION")
    print("="*70)
    print("\nBefore fix: 5/5 would be treated as 100% probability")
    print("After fix: 5/5 is regressed toward league average (50%)")
    print()

    test_cases = [
        {
            'name': '5/5 Perfect Record (VERY SMALL SAMPLE)',
            'outcomes': [1, 1, 1, 1, 1],
            'odds': 1.5,
            'fact': 'Player has scored 20+ points in each of his last 5 games',
            'market': 'Over 19.5 Points'
        },
        {
            'name': '6/6 Perfect Record (VERY SMALL SAMPLE)',
            'outcomes': [1, 1, 1, 1, 1, 1],
            'odds': 1.5,
            'fact': 'Player has scored 20+ points in each of his last 6 games',
            'market': 'Over 19.5 Points'
        },
        {
            'name': '10/10 Perfect Record (SMALL SAMPLE)',
            'outcomes': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            'odds': 1.5,
            'fact': 'Player has scored 20+ points in each of his last 10 games',
            'market': 'Over 19.5 Points'
        },
        {
            'name': '20/20 Perfect Record (MEDIUM SAMPLE)',
            'outcomes': [1] * 20,
            'odds': 1.5,
            'fact': 'Player has scored 20+ points in each of his last 20 games',
            'market': 'Over 19.5 Points'
        },
        {
            'name': '30/30 Perfect Record (LARGE SAMPLE)',
            'outcomes': [1] * 30,
            'odds': 1.5,
            'fact': 'Player has scored 20+ points in each of his last 30 games',
            'market': 'Over 19.5 Points'
        }
    ]

    for test in test_cases:
        print("-"*70)
        print(f"\nTest: {test['name']}")
        print(f"Sample: {len(test['outcomes'])} games, {sum(test['outcomes'])}/{len(test['outcomes'])} success")

        raw_prob = sum(test['outcomes']) / len(test['outcomes'])

        analysis = analyzer.analyze_with_context(
            historical_outcomes=test['outcomes'],
            bookmaker_odds=test['odds'],
            insight_fact=test['fact'],
            market=test['market']
        )

        print(f"\nRaw Historical Probability: {raw_prob*100:.1f}%")
        print(f"Regressed Probability: {analysis.historical_probability*100:.1f}%")
        print(f"Adjusted Probability (after all factors): {analysis.adjusted_probability*100:.1f}%")
        print(f"Regression Applied: {(raw_prob - analysis.historical_probability)*100:.1f} percentage points")
        print(f"\nConfidence: {analysis.confidence_level} ({analysis.confidence_score}/100)")
        print(f"Recommendation: {analysis.recommendation}")
        print()

    print("="*70)


def test_trend_quality_scoring():
    """Test that different trend types get different confidence scores"""

    analyzer = ContextAwareAnalyzer()

    print("\n" + "="*70)
    print("TESTING TREND QUALITY SCORING")
    print("="*70)
    print("\nDifferent trend types should get different confidence scores:")
    print()

    # Same outcomes, same odds, but different trend types
    outcomes = [1, 1, 1, 1, 1, 1, 1, 0, 1, 1]  # 9/10 = 90%
    odds = 1.5

    test_trends = [
        {
            'type': 'PLAYER_STATS_FLOOR',
            'fact': 'Player has scored 20+ points in 9 of his last 10 games',
            'market': 'Over 19.5 Points',
            'expected': 'HIGH confidence (player stats floor prop)'
        },
        {
            'type': 'STREAK',
            'fact': 'Team has won 9 of their last 10 games',
            'market': 'Match Winner',
            'expected': 'VERY LOW confidence (win/loss streak)'
        },
        {
            'type': 'H2H_TREND',
            'fact': 'Player has scored 20+ points in 9 of his last 10 games against the Lakers',
            'market': 'Over 19.5 Points',
            'expected': 'LOW confidence (opponent-specific)'
        },
        {
            'type': 'NARRATIVE_SPLIT',
            'fact': 'Team has won 9 of their last 10 games after trailing at halftime',
            'market': 'Match Winner',
            'expected': 'ZERO confidence (narrative split)'
        }
    ]

    for test in test_trends:
        print("-"*70)
        print(f"\nTrend Type: {test['type']}")
        print(f"Fact: {test['fact']}")
        print(f"Expected: {test['expected']}")

        analysis = analyzer.analyze_with_context(
            historical_outcomes=outcomes,
            bookmaker_odds=odds,
            insight_fact=test['fact'],
            market=test['market']
        )

        print(f"\nConfidence: {analysis.confidence_level} ({analysis.confidence_score}/100)")
        print(f"Recommendation: {analysis.recommendation}")

        if analysis.warnings:
            print(f"\nWarnings:")
            for warning in analysis.warnings:
                print(f"  - {warning}")

        print()

    print("="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  VALUE ENGINE FIX - SAMPLE SIZE REGRESSION TEST")
    print("="*70)
    print("\nThis test demonstrates the fixes for:")
    print("  1. Sample size regression (prevents 5/5 = 100% problem)")
    print("  2. Trend quality scoring (different confidence for different trend types)")
    print("  3. Context penalties (auto-avoid narrative splits, streaks, etc.)")

    test_small_sample_regression()
    test_trend_quality_scoring()

    print("\n" + "="*70)
    print("  ALL TESTS COMPLETE")
    print("="*70)
    print()
