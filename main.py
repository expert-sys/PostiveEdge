"""
Main interactive application for the Value Engine.
Handles user input, data loading, and market analysis.
"""

import sys
from typing import Optional, List, Union
from pathlib import Path

from value_engine import (
    ValueEngine, HistoricalData, MarketConfig, OutcomeType, analyze_simple_market
)
from data_processor import DataProcessor, SampleDataGenerator


class ValueEngineApp:
    """Interactive CLI application for value analysis."""
    
    def __init__(self):
        self.engine = ValueEngine()
        self.data_processor = DataProcessor()
        self.running = True
    
    def print_header(self):
        """Print application header."""
        print("\n" + "="*60)
        print("          SPORTS VALUE ENGINE - IMPLIED PROBABILITY CALCULATOR")
        print("="*60 + "\n")
    
    def print_menu(self):
        """Print main menu."""
        print("\nMAIN MENU")
        print("-" * 40)
        print("1. Analyze market with manual input")
        print("2. Analyze market from CSV file")
        print("3. Analyze market from JSON file")
        print("4. Load sample player data (demo)")
        print("5. Batch analyze multiple markets")
        print("6. View help/documentation")
        print("7. Exit")
        print("-" * 40)
    
    def run(self):
        """Main application loop."""
        self.print_header()
        
        while self.running:
            self.print_menu()
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                self.analyze_manual_input()
            elif choice == "2":
                self.analyze_from_csv()
            elif choice == "3":
                self.analyze_from_json()
            elif choice == "4":
                self.analyze_sample_data()
            elif choice == "5":
                self.batch_analyze()
            elif choice == "6":
                self.show_help()
            elif choice == "7":
                print("\nExiting Value Engine. Goodbye!")
                self.running = False
            else:
                print("Invalid option. Please try again.")
    
    def analyze_manual_input(self):
        """Analyze market with manual input."""
        print("\n" + "="*60)
        print("MANUAL MARKET ANALYSIS")
        print("="*60)
        
        try:
            # Get market info
            event_type = input("Event type (e.g., 'Player to Score'): ").strip()
            if not event_type:
                print("Event type required!")
                return
            
            # Get outcome type
            print("\nOutcome type:")
            print("1. Binary (Yes/No, 0/1)")
            print("2. Continuous (Numeric values)")
            outcome_choice = input("Select (1 or 2): ").strip()
            outcome_type = "binary" if outcome_choice == "1" else "continuous"
            
            # Get outcomes
            outcomes_input = input("\nEnter historical outcomes (comma-separated, e.g., 1,0,1,1,0): ").strip()
            if not outcomes_input:
                print("Outcomes required!")
                return
            
            outcomes = []
            for val in outcomes_input.split(","):
                val = val.strip()
                if "." in val:
                    outcomes.append(float(val))
                else:
                    outcomes.append(int(val))
            
            # Get bookmaker odds
            try:
                bookmaker_odds = float(input("Bookmaker odds (decimal): ").strip())
                if bookmaker_odds <= 1.0:
                    print("Odds must be greater than 1.0!")
                    return
            except ValueError:
                print("Invalid odds format!")
                return
            
            # Get optional parameters
            min_sample = input("Minimum sample size (default 5): ").strip()
            min_sample = int(min_sample) if min_sample else 5
            
            threshold = None
            if outcome_type == "continuous":
                threshold_input = input("Threshold value (for continuous outcomes): ").strip()
                threshold = float(threshold_input) if threshold_input else None
            
            # Perform analysis
            analysis = analyze_simple_market(
                event_type=event_type,
                historical_outcomes=outcomes,
                bookmaker_odds=bookmaker_odds,
                outcome_type=outcome_type,
                minimum_sample_size=min_sample,
                threshold=threshold
            )
            
            self.display_analysis(analysis)
            
            # Option to save
            save_choice = input("\nSave results to JSON? (y/n): ").strip().lower()
            if save_choice == "y":
                filename = f"analysis_{event_type.replace(' ', '_').lower()}.json"
                self.data_processor.save_json(analysis.to_dict(), f"results/{filename}")
                print(f"Saved to results/{filename}")
        
        except Exception as e:
            print(f"Error during analysis: {e}")
    
    def analyze_from_csv(self):
        """Analyze market from CSV file."""
        print("\n" + "="*60)
        print("CSV FILE ANALYSIS")
        print("="*60)
        
        try:
            file_path = input("Enter CSV file path: ").strip()
            if not file_path:
                return
            
            # Load CSV
            data = self.data_processor.load_csv(file_path)
            print(f"Loaded {len(data)} records from CSV")
            
            # Get field info
            event_type = input("Event type name: ").strip()
            outcome_field = input("Outcome field name: ").strip()
            
            # Get outcome type
            print("\nOutcome type:")
            print("1. Binary (Yes/No, 0/1)")
            print("2. Continuous (Numeric values)")
            outcome_choice = input("Select (1 or 2): ").strip()
            outcome_type = "binary" if outcome_choice == "1" else "continuous"
            
            # Extract outcomes
            outcomes = self.data_processor.extract_outcomes(data, outcome_field)
            print(f"Extracted {len(outcomes)} outcomes")
            
            # Get bookmaker odds
            try:
                bookmaker_odds = float(input("Bookmaker odds (decimal): ").strip())
            except ValueError:
                print("Invalid odds format!")
                return
            
            # Optional: window filter
            window_input = input("Historical window (games) - leave blank for all: ").strip()
            window_games = int(window_input) if window_input else None
            
            if window_games:
                # Try to filter by recent games
                date_field = input("Date field name (or leave blank): ").strip()
                if date_field:
                    data = self.data_processor.filter_by_window(data, date_field, window_games=window_games)
                    outcomes = self.data_processor.extract_outcomes(data, outcome_field)
                else:
                    outcomes = outcomes[-window_games:] if window_games else outcomes
            
            # Optional threshold
            threshold = None
            if outcome_type == "continuous":
                threshold_input = input("Threshold value (optional): ").strip()
                threshold = float(threshold_input) if threshold_input else None
            
            # Perform analysis
            analysis = analyze_simple_market(
                event_type=event_type,
                historical_outcomes=outcomes,
                bookmaker_odds=bookmaker_odds,
                outcome_type=outcome_type,
                threshold=threshold
            )
            
            self.display_analysis(analysis)
            
            # Option to save
            save_choice = input("\nSave results to JSON? (y/n): ").strip().lower()
            if save_choice == "y":
                filename = f"analysis_{event_type.replace(' ', '_').lower()}.json"
                self.data_processor.save_json(analysis.to_dict(), f"results/{filename}")
                print(f"Saved to results/{filename}")
        
        except Exception as e:
            print(f"Error during CSV analysis: {e}")
    
    def analyze_from_json(self):
        """Analyze market from JSON file."""
        print("\n" + "="*60)
        print("JSON FILE ANALYSIS")
        print("="*60)
        
        try:
            file_path = input("Enter JSON file path: ").strip()
            if not file_path:
                return
            
            data = self.data_processor.load_json(file_path)
            
            if isinstance(data, dict):
                # Single market analysis from dict
                event_type = data.get("event_type", "Unknown")
                outcomes = data.get("outcomes", [])
                bookmaker_odds = data.get("bookmaker_odds")
                outcome_type = data.get("outcome_type", "binary")
                threshold = data.get("threshold")
                
                if not outcomes or not bookmaker_odds:
                    print("JSON must contain 'outcomes' and 'bookmaker_odds' fields")
                    return
                
                analysis = analyze_simple_market(
                    event_type=event_type,
                    historical_outcomes=outcomes,
                    bookmaker_odds=bookmaker_odds,
                    outcome_type=outcome_type,
                    threshold=threshold
                )
                
                self.display_analysis(analysis)
            
            elif isinstance(data, list):
                print(f"Loaded {len(data)} markets from JSON")
                print("Batch analysis would process multiple markets")
        
        except Exception as e:
            print(f"Error during JSON analysis: {e}")
    
    def analyze_sample_data(self):
        """Analyze using generated sample data."""
        print("\n" + "="*60)
        print("SAMPLE DATA ANALYSIS (DEMO)")
        print("="*60)
        
        try:
            print("\nGenerating sample player data...")
            
            # Generate sample data
            sample_data = SampleDataGenerator.generate_sample_player_data(
                game_count=20,
                goal_probability=0.35,
                seed=42
            )
            
            print(f"Generated {len(sample_data)} games of player data")
            
            # Show sample
            print("\nSample data (first 3 games):")
            for i, game in enumerate(sample_data[:3]):
                print(f"  Game {i+1}: {game}")
            
            # Extract goals
            goals = [int(game['goals']) for game in sample_data]
            
            # Display analysis for different odds
            bookmaker_odds_list = [1.50, 2.00, 2.50, 3.00]
            
            print("\n" + "-"*60)
            print("GOAL SCORING ANALYSIS AT DIFFERENT ODDS")
            print("-"*60)
            
            for odds in bookmaker_odds_list:
                analysis = analyze_simple_market(
                    event_type="Player to Score",
                    historical_outcomes=goals,
                    bookmaker_odds=odds,
                    outcome_type="binary"
                )
                
                print(f"\n{'Odds: ' + str(odds):<30} Value: {analysis.value_percentage:+.2f}%  EV: {analysis.ev_per_unit:+.4f}")
        
        except Exception as e:
            print(f"Error generating sample data: {e}")
    
    def batch_analyze(self):
        """Batch analyze multiple markets from JSON file."""
        print("\n" + "="*60)
        print("BATCH MARKET ANALYSIS")
        print("="*60)
        
        try:
            file_path = input("Enter JSON file with market array (path): ").strip()
            if not file_path:
                return
            
            data = self.data_processor.load_json(file_path)
            
            if not isinstance(data, list):
                print("JSON must contain an array of market objects")
                return
            
            results = []
            print(f"\nAnalyzing {len(data)} markets...\n")
            
            for i, market in enumerate(data, 1):
                try:
                    event_type = market.get("event_type", f"Market_{i}")
                    outcomes = market.get("outcomes", [])
                    bookmaker_odds = market.get("bookmaker_odds")
                    outcome_type = market.get("outcome_type", "binary")
                    threshold = market.get("threshold")
                    
                    if not outcomes or not bookmaker_odds:
                        print(f"  Market {i}: Skipped (missing data)")
                        continue
                    
                    analysis = analyze_simple_market(
                        event_type=event_type,
                        historical_outcomes=outcomes,
                        bookmaker_odds=bookmaker_odds,
                        outcome_type=outcome_type,
                        threshold=threshold
                    )
                    
                    results.append(analysis)
                    
                    status = "✓ VALUE" if analysis.has_value else "✗ NO VALUE"
                    print(f"  Market {i}: {event_type:<25} {status}  EV: {analysis.ev_per_unit:+.4f}")
                
                except Exception as e:
                    print(f"  Market {i}: Error - {e}")
            
            # Summary
            print(f"\n{'='*60}")
            print(f"Analyzed {len(results)} markets successfully")
            value_markets = sum(1 for r in results if r.has_value)
            print(f"Markets with value: {value_markets}/{len(results)}")
            
            # Save results
            save_choice = input("\nSave results to JSON? (y/n): ").strip().lower()
            if save_choice == "y":
                results_data = [r.to_dict() for r in results]
                self.data_processor.save_json(results_data, "results/batch_analysis.json")
                print("Saved to results/batch_analysis.json")
        
        except Exception as e:
            print(f"Error during batch analysis: {e}")
    
    def display_analysis(self, analysis):
        """Display analysis results in formatted manner."""
        print("\n" + "="*60)
        print("ANALYSIS RESULTS")
        print("="*60)
        print(analysis)
        print("="*60)
    
    def show_help(self):
        """Display help documentation."""
        help_text = """
VALUE ENGINE - HELP & DOCUMENTATION
====================================

OVERVIEW:
The Value Engine calculates implied probability and expected value (EV) for
sports markets by comparing historical performance data against bookmaker odds.

KEY CONCEPTS:

1. IMPLIED PROBABILITY
   The probability of an event occurring based on historical data.
   Formula: successes / total_attempts
   
2. IMPLIED ODDS
   Decimal odds derived from historical probability.
   Formula: 1 / historical_probability
   
3. VALUE
   Exists when historical probability > bookmaker probability
   Value % = (historical_prob - bookmaker_prob) * 100
   
4. EXPECTED VALUE (EV)
   Average profit/loss per unit staked over many bets.
   Formula: (prob * odds - 1) - (1 - prob)
   
   EV > 0: Good bet (positive value)
   EV < 0: Bad bet (negative value)
   EV = 0: Fair bet
   
5. SAMPLE SIZE HANDLING
   If sample size is small (< minimum):
   - Uses Bayesian shrinkage for binary outcomes
   - Uses fallback probability for continuous
   - This prevents overconfidence with limited data

USAGE TIPS:

- Use at least 5-10 observations for reliable analysis
- Consider using sample-size filters for player performance
- Apply weighting for recent games if trends matter
- Adjust for opponent strength and context
- Batch analyze to find best value opportunities

OUTCOME TYPES:

BINARY: Win/Loss, Goal/No Goal, etc. (0 or 1)
  Input: "1,0,1,1,0" → Probability = 3/5 = 60%
  
CONTINUOUS: Goals, Assists, Shots, etc. (numeric values)
  Input: "2,1,3,2,0" with threshold 1.5
  → Probability = count(outcome >= 1.5) / 5 = 60%

FILE FORMATS:

CSV: Standard format with headers
  date,outcome,opponent,location
  2024-01-01,1,TeamA,home
  2024-01-02,0,TeamB,away

JSON: Array of market objects
  [
    {
      "event_type": "Player to Score",
      "outcomes": [1, 0, 1, 1, 0],
      "bookmaker_odds": 2.50,
      "outcome_type": "binary"
    }
  ]

Examples: See data/ folder for sample files.

For more info, check the code documentation.
        """
        print(help_text)
        input("\nPress Enter to continue...")


def main():
    """Entry point for the application."""
    try:
        app = ValueEngineApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
