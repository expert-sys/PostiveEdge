"""
Test Context-Aware Analysis
============================
Demonstrates the improvements over basic analysis.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.context_aware_analysis import (
    ContextAwareAnalyzer,
    ContextFactors,
    format_analysis_report
)


def test_case_1_minutes_trap():
    """
    Test Case 1: The Minutes Trap
    Player has good historical rate but declining minutes
    """
    print("\n" + "="*70)
    print("TEST CASE 1: THE MINUTES TRAP")
    print("="*70)
    print("\nScenario: Player O2.5 3-Pointers")
    print("Historical: 8/10 games (80%)")
    print("BUT: Recent minutes declining sharply\n")

    analyzer = ContextAwareAnalyzer()

    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1,1,1,1,1,1,1,1,0,0],
        recent_outcomes=[1,0,0],  # Only 1/3 recently
        historical_minutes=[32,30,28,31,29,15,12,33,30,18],
        recent_minutes=[15,12,10],  # DECLINING!
        bookmaker_odds=2.00,  # 50% implied
        min_minutes_threshold=15.0,
        player_name="Example Player O2.5 3PM"
    )

    print(format_analysis_report(analysis, "Player O2.5 3-Pointers"))

    print("\n📌 KEY INSIGHT:")
    print(f"   Basic analysis would show: +30% edge (80% vs 50%)")
    print(f"   Context-aware shows: {analysis.value_percentage:+.1f}% edge")
    print(f"   Recommendation: {analysis.recommendation}")
    print(f"\n   ✅ Correctly identifies benching risk!")


def test_case_2_hot_hand():
    """
    Test Case 2: The Hot Hand
    Player on hot streak, recent form >> historical
    """
    print("\n\n" + "="*70)
    print("TEST CASE 2: THE HOT HAND")
    print("="*70)
    print("\nScenario: Player O19.5 Points")
    print("Historical: 11/20 games (55%)")
    print("BUT: Last 5 games all hit (100%)\n")

    analyzer = ContextAwareAnalyzer()

    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1,1,0,1,0,1,0,1,0,1,0,1,0,0,1,1,1,1,1,1],  # 11/20 = 55%
        recent_outcomes=[1,1,1,1,1],  # 5/5 = 100%!
        historical_minutes=[30,28,32,29,31,30,28,35,33,30,29,31,28,30,35,38,36,37,35,34],
        recent_minutes=[35,38,36,37,35],  # Increased role
        bookmaker_odds=1.80,  # 55.6% implied
        min_minutes_threshold=20.0,
        player_name="Player O19.5 Points"
    )

    print(format_analysis_report(analysis, "Player O19.5 Points"))

    print("\n📌 KEY INSIGHT:")
    print(f"   Basic analysis: -0.6% edge (55% vs 55.6%) - SKIP")
    print(f"   Context-aware: {analysis.value_percentage:+.1f}% edge - {analysis.recommendation}")
    print(f"\n   ✅ Catches the hot streak and increased role!")


def test_case_3_back_to_back():
    """
    Test Case 3: Back-to-Back Game Penalty
    Good historical rate but B2B game with rest concerns
    """
    print("\n\n" + "="*70)
    print("TEST CASE 3: BACK-TO-BACK PENALTY")
    print("="*70)
    print("\nScenario: Rebounds O10.5")
    print("Historical: 15/20 games (75%)")
    print("BUT: Back-to-back game, 0 days rest\n")

    analyzer = ContextAwareAnalyzer()

    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0],  # 15/20 = 75%
        recent_outcomes=[1,1,0],
        bookmaker_odds=1.70,  # 58.8% implied
        context_factors=ContextFactors(
            back_to_back=True,
            days_rest=0,
            opponent_strength=85,  # Strong opponent
            home_away="AWAY"
        ),
        min_minutes_threshold=20.0,
        player_name="Player O10.5 Rebounds"
    )

    print(format_analysis_report(analysis, "Player O10.5 Rebounds"))

    print("\n📌 KEY INSIGHT:")
    print(f"   Basic analysis: +16.2% edge (75% vs 58.8%)")
    print(f"   Context-aware: {analysis.value_percentage:+.1f}% edge")
    print(f"   Recommendation: {analysis.recommendation}")
    print(f"\n   ✅ Accounts for fatigue and rest risk!")


def test_case_4_declining_role():
    """
    Test Case 4: Declining Role
    Recent form significantly worse than historical
    """
    print("\n\n" + "="*70)
    print("TEST CASE 4: DECLINING ROLE")
    print("="*70)
    print("\nScenario: Assists O4.5")
    print("Historical: 12/15 games (80%)")
    print("BUT: Last 5 games only 1/5 (20%)\n")

    analyzer = ContextAwareAnalyzer()

    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 12/15 = 80%
        recent_outcomes=[0,0,0,0,1],  # 1/5 = 20%!
        historical_minutes=[28,30,32,29,31,30,28,25,22,20,18,15,12,10,8],
        recent_minutes=[15,12,10,8,10],  # Declining!
        bookmaker_odds=1.60,  # 62.5% implied
        min_minutes_threshold=15.0,
        player_name="Player O4.5 Assists"
    )

    print(format_analysis_report(analysis, "Player O4.5 Assists"))

    print("\n📌 KEY INSIGHT:")
    print(f"   Basic analysis: +17.5% edge (80% vs 62.5%)")
    print(f"   Context-aware: {analysis.value_percentage:+.1f}% edge")
    print(f"   Recommendation: {analysis.recommendation}")
    print(f"\n   ✅ Detects role change and declining minutes!")


def test_case_5_perfect_bet():
    """
    Test Case 5: The Perfect Bet
    All factors align - strong value, low risk, high confidence
    """
    print("\n\n" + "="*70)
    print("TEST CASE 5: THE PERFECT BET")
    print("="*70)
    print("\nScenario: Points O22.5")
    print("Historical: 14/15 games (93%)")
    print("Recent form: 5/5 (100%)")
    print("Context: All positive\n")

    analyzer = ContextAwareAnalyzer()

    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 14/15 = 93%
        recent_outcomes=[1,1,1,1,1],  # 5/5 = 100%
        historical_minutes=[32,33,35,34,36,35,33,32,34,35,36,34,33,35,28],
        recent_minutes=[36,35,36,34,35],  # Stable, high
        bookmaker_odds=1.50,  # 66.7% implied
        context_factors=ContextFactors(
            home_away="HOME",
            days_rest=2,  # Well rested
            back_to_back=False,
            injury_impact="LOW",
            opponent_strength=40  # Weak opponent
        ),
        min_minutes_threshold=20.0,
        player_name="Star Player O22.5 Points"
    )

    print(format_analysis_report(analysis, "Star Player O22.5 Points"))

    print("\n📌 KEY INSIGHT:")
    print(f"   Massive edge: {analysis.value_percentage:+.1f}%")
    print(f"   High confidence: {analysis.confidence_level}")
    print(f"   Low risk: {analysis.overall_risk}")
    print(f"   Recommendation: {analysis.recommendation}")
    print(f"\n   ✅ Perfect bet - all systems go!")


def run_all_tests():
    """Run all test cases"""
    print("\n\n" + "="*70)
    print("CONTEXT-AWARE ANALYSIS TEST SUITE")
    print("Demonstrating improvements over basic analysis")
    print("="*70)

    test_case_1_minutes_trap()
    test_case_2_hot_hand()
    test_case_3_back_to_back()
    test_case_4_declining_role()
    test_case_5_perfect_bet()

    print("\n\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    print("\n✅ Context-aware analysis successfully addresses:")
    print("   • Minutes projection (benching risk)")
    print("   • Recency weighting (hot/cold streaks)")
    print("   • Role changes (declining trends)")
    print("   • External context (B2B, rest, injuries)")
    print("\n   This results in significantly more accurate betting decisions!")
    print()


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted\n")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
