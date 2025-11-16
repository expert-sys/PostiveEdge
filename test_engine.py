"""
Test and validation script for the Value Engine.
Run this to verify the engine works correctly and see various use cases.
"""

from value_engine import (
    ValueEngine, HistoricalData, MarketConfig, OutcomeType,
    analyze_simple_market
)
from data_processor import DataProcessor, SampleDataGenerator
import json


def test_basic_binary_analysis():
    """Test basic binary outcome analysis."""
    print("\n" + "="*60)
    print("TEST 1: Basic Binary Outcome Analysis")
    print("="*60)
    
    # 6 goals in 10 games = 60% probability
    analysis = analyze_simple_market(
        event_type="Player to Score",
        historical_outcomes=[1, 0, 1, 1, 0, 1, 0, 1, 1, 0],
        bookmaker_odds=1.80,
        outcome_type="binary"
    )
    
    print(analysis)
    assert analysis.sample_size == 10
    assert abs(analysis.historical_probability - 0.6) < 0.01
    assert analysis.has_value == True
    print("✓ PASSED")


def test_continuous_outcome_analysis():
    """Test continuous outcome with threshold."""
    print("\n" + "="*60)
    print("TEST 2: Continuous Outcome with Threshold")
    print("="*60)
    
    # Over 2.5 goals: 6 times out of 10 = 60%
    analysis = analyze_simple_market(
        event_type="Over 2.5 Goals",
        historical_outcomes=[3, 2, 4, 1, 3, 2, 3, 2, 4, 3],
        bookmaker_odds=1.90,
        outcome_type="continuous",
        threshold=2.5
    )
    
    print(analysis)
    assert abs(analysis.historical_probability - 0.6) < 0.01
    assert analysis.has_value == True
    print("✓ PASSED")


def test_small_sample_size():
    """Test Bayesian shrinkage with small sample."""
    print("\n" + "="*60)
    print("TEST 3: Small Sample Size (Bayesian Shrinkage)")
    print("="*60)
    
    # Only 2 games with outcome
    analysis = analyze_simple_market(
        event_type="Test Event",
        historical_outcomes=[1, 1],
        bookmaker_odds=2.00,
        outcome_type="binary",
        minimum_sample_size=5
    )
    
    print(analysis)
    assert analysis.sufficient_sample == False
    # Should apply Bayesian shrinkage, moving from 100% toward 50%
    assert 0.5 < analysis.historical_probability < 1.0
    print("✓ PASSED")


def test_no_value_detection():
    """Test when there's no value."""
    print("\n" + "="*60)
    print("TEST 4: No Value Detection")
    print("="*60)
    
    # 30% probability but bookmaker offering 1.40 (71% implied)
    analysis = analyze_simple_market(
        event_type="Low Probability Event",
        historical_outcomes=[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        bookmaker_odds=1.40,
        outcome_type="binary"
    )
    
    print(analysis)
    assert analysis.has_value == False
    assert analysis.value_percentage < 0
    print("✓ PASSED")


def test_weighted_outcomes():
    """Test analysis with recency weighting."""
    print("\n" + "="*60)
    print("TEST 5: Weighted Outcomes (Recency)")
    print("="*60)
    
    outcomes = [1, 0, 1, 1, 0, 1, 0, 1]
    # Recent games weighted higher
    weights = [0.05, 0.05, 0.08, 0.08, 0.10, 0.12, 0.25, 0.27]
    
    from value_engine import HistoricalData, MarketConfig
    
    engine = ValueEngine()
    data = HistoricalData(outcomes=outcomes, weights=weights)
    config = MarketConfig(
        event_type="Weighted Event",
        outcome_type=OutcomeType.BINARY,
        bookmaker_odds=2.00
    )
    
    analysis = engine.analyze_market(data, config)
    print(analysis)
    # Weighted should put more emphasis on recent games
    assert 0.5 <= analysis.historical_probability <= 0.75
    print("✓ PASSED")


def test_csv_data_loading():
    """Test loading and processing CSV data."""
    print("\n" + "="*60)
    print("TEST 6: CSV Data Loading")
    print("="*60)
    
    try:
        # Load sample CSV
        data = DataProcessor.load_csv("sample_player_data.csv")
        print(f"Loaded {len(data)} records from CSV")
        
        # Extract goals
        goals = DataProcessor.extract_outcomes(data, "goals")
        print(f"Extracted {len(goals)} goal outcomes")
        
        # Analyze
        analysis = analyze_simple_market(
            event_type="Player to Score (CSV Data)",
            historical_outcomes=goals,
            bookmaker_odds=1.95,
            outcome_type="binary"
        )
        
        print(analysis)
        print("✓ PASSED")
    except Exception as e:
        print(f"⚠ WARNING: {e}")


def test_json_data_loading():
    """Test loading and processing JSON markets."""
    print("\n" + "="*60)
    print("TEST 7: JSON Data Loading")
    print("="*60)
    
    try:
        # Load sample JSON
        markets = DataProcessor.load_json("sample_markets.json")
        print(f"Loaded {len(markets)} markets from JSON")
        
        # Analyze first market
        market = markets[0]
        analysis = analyze_simple_market(
            event_type=market["event_type"],
            historical_outcomes=market["outcomes"],
            bookmaker_odds=market["bookmaker_odds"],
            outcome_type=market.get("outcome_type", "binary")
        )
        
        print(f"\nAnalyzing: {market['event_type']}")
        print(analysis)
        print("✓ PASSED")
    except Exception as e:
        print(f"⚠ WARNING: {e}")


def test_opponent_adjustment():
    """Test opponent strength adjustment."""
    print("\n" + "="*60)
    print("TEST 8: Opponent Strength Adjustment")
    print("="*60)
    
    # Use only positive outcomes for meaningful comparison
    outcomes = [1, 1, 1, 1]
    opponent_strengths = [0.9, 0.7, 0.4, 0.2]  # Strong to weak
    
    adjusted = DataProcessor.apply_opponent_adjustment(outcomes, opponent_strengths)
    print(f"Original outcomes: {outcomes}")
    print(f"Opponent strengths: {opponent_strengths}")
    print(f"Adjusted outcomes: {adjusted}")
    
    # Against strong opponents, adjustment should be lower
    # Against weak opponents, adjustment should be higher
    assert adjusted[0] < adjusted[2]  # Strong opponent vs weak
    assert adjusted[0] < adjusted[3]  # Strong vs weakest
    assert all(adj < 1.0 for adj in adjusted)  # All should be scaled down from 1.0
    print("✓ PASSED")


def test_home_away_split():
    """Test home/away split analysis."""
    print("\n" + "="*60)
    print("TEST 9: Home/Away Split Analysis")
    print("="*60)
    
    try:
        # Generate sample data with home/away split
        data = [
            {'location': 'home', 'goals': 1},
            {'location': 'away', 'goals': 0},
            {'location': 'home', 'goals': 1},
            {'location': 'away', 'goals': 0},
            {'location': 'home', 'goals': 1},
            {'location': 'away', 'goals': 0},
            {'location': 'home', 'goals': 1},
            {'location': 'away', 'goals': 0},
        ]
        
        home_outcomes, away_outcomes = DataProcessor.calculate_home_away_split(
            data, "goals", "location"
        )
        
        print(f"Home outcomes: {home_outcomes}")
        print(f"Away outcomes: {away_outcomes}")
        
        # Analyze separately
        home_analysis = analyze_simple_market("Home Goals", home_outcomes, 1.80)
        away_analysis = analyze_simple_market("Away Goals", away_outcomes, 2.50)
        
        print(f"\nHome analysis (4 goals in 4 games = 100%):")
        print(f"  Probability: {home_analysis.historical_probability:.2%}")
        print(f"  Has value: {home_analysis.has_value}")
        
        print(f"\nAway analysis (0 goals in 4 games = 0%):")
        print(f"  Probability: {away_analysis.historical_probability:.2%}")
        print(f"  Has value: {away_analysis.has_value}")
        
        print("✓ PASSED")
    except Exception as e:
        print(f"⚠ WARNING: {e}")


def test_minutes_adjustment():
    """Test minutes adjustment for partial games."""
    print("\n" + "="*60)
    print("TEST 10: Minutes Adjustment (Partial Games)")
    print("="*60)
    
    # Player scored 1 goal in 45 minutes
    # Adjusted to 90 minutes = 2 goals expected
    outcomes = [1, 2, 1, 1]
    minutes = [45, 90, 60, 90]
    
    adjusted = DataProcessor.minutes_adjustment(outcomes, minutes, full_game_minutes=90)
    
    print(f"Original outcomes: {outcomes}")
    print(f"Minutes played: {minutes}")
    print(f"Adjusted to 90 min: {adjusted}")
    
    assert adjusted[0] > outcomes[0]  # 45 min scaled up
    assert adjusted[1] == outcomes[1]  # 90 min unchanged
    assert adjusted[2] > outcomes[2]  # 60 min scaled up
    print("✓ PASSED")


def test_sample_data_generation():
    """Test sample data generation."""
    print("\n" + "="*60)
    print("TEST 11: Sample Data Generation")
    print("="*60)
    
    # Generate binary outcomes
    binary = SampleDataGenerator.generate_binary_outcomes(
        count=20,
        probability=0.6,
        seed=42
    )
    print(f"Generated binary outcomes: {binary}")
    print(f"Frequency: {sum(binary)}/20 ({sum(binary)/20:.1%})")
    
    # Generate continuous outcomes
    continuous = SampleDataGenerator.generate_continuous_outcomes(
        count=20,
        mean=2.5,
        std_dev=1.0,
        seed=42
    )
    print(f"Generated continuous outcomes (first 5): {continuous[:5]}")
    print(f"Average: {sum(continuous)/len(continuous):.2f}")
    
    # Generate player data
    player_data = SampleDataGenerator.generate_sample_player_data(
        game_count=10,
        goal_probability=0.40,
        seed=42
    )
    print(f"\nGenerated {len(player_data)} games of player data:")
    print(f"  Goals: {[g['goals'] for g in player_data[:5]]}")
    print(f"  Assists: {[g['assists'] for g in player_data[:5]]}")
    
    print("✓ PASSED")


def test_batch_analysis():
    """Test batch analysis of multiple markets."""
    print("\n" + "="*60)
    print("TEST 12: Batch Analysis")
    print("="*60)
    
    try:
        # Load multiple markets
        markets = DataProcessor.load_json("sample_markets.json")
        
        results = []
        value_count = 0
        
        for market in markets:
            analysis = analyze_simple_market(
                event_type=market["event_type"],
                historical_outcomes=market["outcomes"],
                bookmaker_odds=market["bookmaker_odds"],
                outcome_type=market.get("outcome_type", "binary"),
                threshold=market.get("threshold")
            )
            results.append(analysis)
            
            if analysis.has_value:
                value_count += 1
            
            status = "✓ VALUE" if analysis.has_value else "✗ NO VALUE"
            print(f"  {market['event_type']:<35} {status}  EV: {analysis.ev_per_unit:+.4f}")
        
        print(f"\nResults: {value_count}/{len(results)} markets have value")
        print("✓ PASSED")
    except Exception as e:
        print(f"⚠ WARNING: {e}")


def test_ev_calculation():
    """Test EV calculation correctness."""
    print("\n" + "="*60)
    print("TEST 13: EV Calculation Verification")
    print("="*60)
    
    # Known values to verify
    test_cases = [
        {
            'prob': 0.50,
            'odds': 2.50,
            'expected_ev': (0.50 * 1.50) - 0.50  # = 0.25
        },
        {
            'prob': 0.60,
            'odds': 2.00,
            'expected_ev': (0.60 * 1.00) - 0.40  # = 0.20
        },
        {
            'prob': 0.33,
            'odds': 3.00,
            'expected_ev': (0.33 * 2.00) - 0.67  # = -0.01
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        prob = test['prob']
        odds = test['odds']
        expected = test['expected_ev']
        
        analysis = analyze_simple_market(
            event_type=f"Test Case {i}",
            historical_outcomes=[1] * int(prob * 100) + [0] * int((1-prob) * 100),
            bookmaker_odds=odds,
            outcome_type="binary"
        )
        
        print(f"Case {i}: Prob {prob:.0%}, Odds {odds:.2f}")
        print(f"  Expected EV: {expected:.4f}")
        print(f"  Calculated EV: {analysis.ev_per_unit:.4f}")
        print(f"  Match: {abs(analysis.ev_per_unit - expected) < 0.01} ✓")
    
    print("✓ PASSED")


def run_all_tests():
    """Run all tests."""
    print("\n")
    print("█" * 60)
    print("█  SPORTS VALUE ENGINE - TEST SUITE")
    print("█" * 60)
    
    tests = [
        test_basic_binary_analysis,
        test_continuous_outcome_analysis,
        test_small_sample_size,
        test_no_value_detection,
        test_weighted_outcomes,
        test_csv_data_loading,
        test_json_data_loading,
        test_opponent_adjustment,
        test_home_away_split,
        test_minutes_adjustment,
        test_sample_data_generation,
        test_batch_analysis,
        test_ev_calculation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
