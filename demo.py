"""
Demo script showing how to use the Value Engine programmatically.
"""

from value_engine import analyze_simple_market
from data_processor import DataProcessor, SampleDataGenerator


def demo_simple_analysis():
    """Demo 1: Simple market analysis."""
    print("\n" + "="*60)
    print("DEMO 1: Simple Market Analysis")
    print("="*60)
    
    # Player scored in 7 of last 10 games
    analysis = analyze_simple_market(
        event_type="Player to Score",
        historical_outcomes=[1, 0, 1, 1, 0, 1, 0, 1, 1, 0],
        bookmaker_odds=1.95,
        outcome_type="binary"
    )
    
    print(analysis)
    print("\nConclusion:", "✓ BUY" if analysis.has_value else "✗ AVOID")


def demo_over_under():
    """Demo 2: Over/under goals analysis."""
    print("\n" + "="*60)
    print("DEMO 2: Over/Under Goals Analysis")
    print("="*60)
    
    # Over 2.5 goals in 12 of last 20 games (60%)
    analysis = analyze_simple_market(
        event_type="Over 2.5 Goals",
        historical_outcomes=[3, 2, 4, 1, 3, 2, 3, 2, 4, 3, 2, 1, 3, 2, 4, 1, 3, 2, 3, 2],
        bookmaker_odds=1.85,
        outcome_type="continuous",
        threshold=2.5
    )
    
    print(analysis)
    print("\nConclusion:", "✓ BUY" if analysis.has_value else "✗ AVOID")


def demo_csv_analysis():
    """Demo 3: Analysis from CSV data."""
    print("\n" + "="*60)
    print("DEMO 3: CSV Data Analysis")
    print("="*60)
    
    try:
        # Load sample CSV
        data = DataProcessor.load_csv("sample_player_data.csv")
        print(f"Loaded {len(data)} games from CSV")
        
        # Extract goals scored
        goals = DataProcessor.extract_outcomes(data, "goals")
        print(f"Goals scored in recent games: {goals[:10]}")
        
        # Analyze
        analysis = analyze_simple_market(
            event_type="Real Player Performance - Goals",
            historical_outcomes=goals,
            bookmaker_odds=1.90,
            outcome_type="binary"
        )
        
        print("\n" + str(analysis))
        print("\nConclusion:", "✓ BUY" if analysis.has_value else "✗ AVOID")
    except Exception as e:
        print(f"Error: {e}")


def demo_batch_markets():
    """Demo 4: Batch analysis of multiple markets."""
    print("\n" + "="*60)
    print("DEMO 4: Batch Market Analysis")
    print("="*60)
    
    try:
        # Load markets
        markets = DataProcessor.load_json("sample_markets.json")
        print(f"Analyzing {len(markets)} markets...\n")
        
        results = []
        for market in markets:
            analysis = analyze_simple_market(
                event_type=market["event_type"],
                historical_outcomes=market["outcomes"],
                bookmaker_odds=market["bookmaker_odds"],
                outcome_type=market.get("outcome_type", "binary"),
                threshold=market.get("threshold")
            )
            results.append(analysis)
        
        # Display results
        print("Market Analysis Summary:")
        print("-" * 80)
        print(f"{'Event Type':<40} {'Probability':<15} {'Value':<12} {'EV':<12}")
        print("-" * 80)
        
        value_count = 0
        for result in results:
            event = result.event_type[:38]
            prob_str = f"{result.historical_probability:.1%}"
            value_str = "✓ YES" if result.has_value else "✗ NO"
            ev_str = f"{result.ev_per_unit:+.3f}"
            
            print(f"{event:<40} {prob_str:<15} {value_str:<12} {ev_str:<12}")
            
            if result.has_value:
                value_count += 1
        
        print("-" * 80)
        print(f"Markets with value: {value_count}/{len(results)}")
        
        # Best opportunity
        if results:
            best = max(results, key=lambda x: x.ev_per_unit)
            print(f"\nBest opportunity: {best.event_type}")
            print(f"  EV per unit: {best.ev_per_unit:+.4f}")
            print(f"  Expected return per $100: ${best.expected_return_per_100:+.2f}")
    
    except Exception as e:
        print(f"Error: {e}")


def demo_comparison():
    """Demo 5: Compare same event at different odds."""
    print("\n" + "="*60)
    print("DEMO 5: Odds Comparison")
    print("="*60)
    
    outcomes = [1, 0, 1, 1, 0, 1, 0, 1]  # 62.5% probability
    
    print("Same player performance (62.5%) at different bookmaker odds:\n")
    print(f"{'Odds':<8} {'Implied %':<15} {'Value':<10} {'EV':<12} {'ROI %':<10}")
    print("-" * 60)
    
    for odds in [1.50, 1.80, 2.00, 2.50, 3.00]:
        analysis = analyze_simple_market(
            event_type="Test",
            historical_outcomes=outcomes,
            bookmaker_odds=odds,
            outcome_type="binary"
        )
        
        implied_prob = 1 / odds * 100
        value = "✓" if analysis.has_value else "✗"
        roi = (analysis.ev_per_unit * 100)
        
        print(f"{odds:<8.2f} {implied_prob:<15.1f} {value:<10} {analysis.ev_per_unit:+.4f}    {roi:+.1f}%")


def main():
    """Run all demos."""
    print("\n")
    print("█" * 60)
    print("█  SPORTS VALUE ENGINE - DEMO")
    print("█" * 60)
    
    demo_simple_analysis()
    demo_over_under()
    demo_csv_analysis()
    demo_batch_markets()
    demo_comparison()
    
    print("\n" + "="*60)
    print("Demo completed!")
    print("="*60)
    print("\nNext: Run 'python main.py' for interactive mode")


if __name__ == "__main__":
    main()
