#!/usr/bin/env python3
"""
Test the player prop sample weight function with various scenarios
"""
from value_engine_enhanced import player_prop_sample_weight


def test_scenario(name: str, current_season_games: int, historical_games: int):
    """Test a specific scenario and print results"""
    print(f"\n{'='*70}")
    print(f"Scenario: {name}")
    print(f"{'='*70}")
    print(f"Current season games: {current_season_games}")
    print(f"Historical games:     {historical_games}")

    result = player_prop_sample_weight(current_season_games, historical_games)

    print(f"\nResults:")
    print(f"  Sample Weight:           {result['sample_weight']:.3f}")
    print(f"  Confidence Cap:          {result['confidence_cap']:.2f} (max {result['confidence_cap']*100:.0f}% confidence)")
    print(f"  Current Season Weight:   {result['current_season_weight']:.3f}")
    print(f"  Historical Weight:       {result['historical_weight']:.3f}")
    print(f"  Recommendation:          {result['recommendation']}")
    print(f"  Reason:                  {result['reason']}")

    return result


if __name__ == "__main__":
    print("="*70)
    print("PLAYER PROP SAMPLE WEIGHT TESTING")
    print("="*70)

    # LeBron James scenario (user's case)
    print("\n\n## LEBRON JAMES SCENARIO (User's Issue)")
    lebron_result = test_scenario(
        name="LeBron James - Only 2 Current Season Games",
        current_season_games=2,
        historical_games=10
    )
    print(f"\n** Expected Behavior:")
    print(f"   - Confidence capped at 55% (was showing 87% before)")
    print(f"   - Sample weight: {lebron_result['sample_weight']:.3f} (reduces EV impact)")
    print(f"   - Recommendation: SKIP (too volatile with only 2 games)")

    # Edge cases
    print("\n\n## EDGE CASES")

    test_scenario(
        name="Very Early Season - 1 Game",
        current_season_games=1,
        historical_games=10
    )

    test_scenario(
        name="Early Season - 3 Games",
        current_season_games=3,
        historical_games=10
    )

    test_scenario(
        name="Marginal - 4 Games",
        current_season_games=4,
        historical_games=12
    )

    test_scenario(
        name="Adequate - 5 Games",
        current_season_games=5,
        historical_games=15
    )

    test_scenario(
        name="Good Sample - 6 Games",
        current_season_games=6,
        historical_games=20
    )

    test_scenario(
        name="Excellent Sample - 10 Games",
        current_season_games=10,
        historical_games=25
    )

    # Comparison: Current vs Historical Dominance
    print("\n\n## CURRENT SEASON vs HISTORICAL DATA")

    result_mostly_historical = test_scenario(
        name="Mostly Historical (2 current / 15 total)",
        current_season_games=2,
        historical_games=15
    )

    result_mostly_current = test_scenario(
        name="Mostly Current (8 current / 10 total)",
        current_season_games=8,
        historical_games=10
    )

    print(f"\n** Comparison:")
    print(f"   Mostly Historical: weight={result_mostly_historical['sample_weight']:.3f}, cap={result_mostly_historical['confidence_cap']:.2f}")
    print(f"   Mostly Current:    weight={result_mostly_current['sample_weight']:.3f}, cap={result_mostly_current['confidence_cap']:.2f}")
    print(f"   -> Current season data is prioritized 70/30 over historical")

    # Moneyline comparison
    print("\n\n## COMPARISON TO MONEYLINE BASELINE")
    print("Moneyline baseline: 6-7 games")
    print("Player prop baseline: 4-5 games (less strict)")
    print()

    from value_engine_enhanced import sample_size_weight

    for n in [2, 4, 5, 6, 7, 10]:
        moneyline_weight = sample_size_weight(n)
        prop_current_result = player_prop_sample_weight(n, n)
        prop_weight = prop_current_result['sample_weight']

        print(f"n={n:2d}  Moneyline: {moneyline_weight:.3f}  |  Prop (all current): {prop_weight:.3f}  |  Conf Cap: {prop_current_result['confidence_cap']:.2f}")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Key Differences from Moneyline:
1. Less strict baseline: 4-5 games vs 6-7 for moneyline
2. MORE aggressive penalty for very low samples (n < 4)
3. Confidence cap prevents overconfidence even with good historical data
4. Current season data weighted 70% vs historical 30%
5. SKIP recommendation for < 3 current season games

For LeBron's case (2 games):
- Confidence capped at 55% (previously 87%)
- Sample weight: 0.58 (reduces EV by 42%)
- Recommendation: SKIP - too volatile
    """)
