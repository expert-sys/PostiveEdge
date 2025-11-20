"""
Historical Data Helper
======================
Helper script to create and manage historical outcome data for the value engine.

This makes it easy to:
- Create historical data files from CSV
- Generate sample data for testing
- Validate historical data format
"""

import json
import os
import csv
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("hist_data_helper")


# ---------------------------------------------------------------------
# Historical Data Manager
# ---------------------------------------------------------------------
class HistoricalDataManager:
    """Manage historical outcome data for teams and players"""

    def __init__(self, data_dir: str = "./historical_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def create_from_csv(
        self,
        csv_file: str,
        team_name: str,
        market_type: str,
        outcome_column: str,
        threshold: Optional[float] = None
    ) -> bool:
        """
        Create historical data file from a CSV

        Args:
            csv_file: Path to CSV file with historical games
            team_name: Team name (e.g., "Lakers", "Patriots")
            market_type: Market type (e.g., "moneyline", "spread", "total")
            outcome_column: Column name with outcomes (e.g., "won", "covered_spread", "total_points")
            threshold: For continuous outcomes, threshold to convert to binary (e.g., 220.5 for totals)

        Returns:
            Success status
        """
        try:
            # Read CSV
            outcomes = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if outcome_column in row:
                        val = row[outcome_column]

                        # Try to convert to number
                        try:
                            num_val = float(val)
                            # Apply threshold if provided
                            if threshold is not None:
                                outcomes.append(1 if num_val >= threshold else 0)
                            else:
                                outcomes.append(num_val)
                        except ValueError:
                            # Handle string values like "W", "L", "True", "False"
                            if val.lower() in ['w', 'win', 'won', 'true', 'yes', '1', 'covered']:
                                outcomes.append(1)
                            elif val.lower() in ['l', 'loss', 'lost', 'false', 'no', '0', 'missed']:
                                outcomes.append(0)

            if not outcomes:
                logger.error(f"No outcomes found in column '{outcome_column}'")
                return False

            # Save to file
            output_file = self._get_filename(team_name, market_type)
            self.save_outcomes(output_file, outcomes, {
                'team': team_name,
                'market_type': market_type,
                'source_csv': csv_file,
                'outcome_column': outcome_column,
                'threshold': threshold,
                'created_at': datetime.now().isoformat()
            })

            logger.info(f"✓ Created {output_file}")
            logger.info(f"  - {len(outcomes)} outcomes")
            logger.info(f"  - Win rate: {sum(outcomes)/len(outcomes)*100:.1f}%")

            return True

        except Exception as e:
            logger.error(f"Error creating from CSV: {e}")
            return False

    def create_sample_data(
        self,
        team_name: str,
        market_type: str,
        num_games: int = 20,
        win_probability: float = 0.55
    ) -> bool:
        """
        Create sample historical data for testing

        Args:
            team_name: Team name
            market_type: Market type
            num_games: Number of games to generate
            win_probability: Probability of success (0.0 to 1.0)
        """
        import random

        outcomes = [1 if random.random() < win_probability else 0 for _ in range(num_games)]

        output_file = self._get_filename(team_name, market_type)
        self.save_outcomes(output_file, outcomes, {
            'team': team_name,
            'market_type': market_type,
            'type': 'sample_data',
            'win_probability': win_probability,
            'created_at': datetime.now().isoformat()
        })

        logger.info(f"✓ Created sample data: {output_file}")
        logger.info(f"  - {num_games} games")
        logger.info(f"  - Target win rate: {win_probability*100:.1f}%")
        logger.info(f"  - Actual win rate: {sum(outcomes)/len(outcomes)*100:.1f}%")

        return True

    def save_outcomes(self, filename: str, outcomes: List, metadata: Dict = None):
        """Save outcomes to a JSON file"""
        data = {
            'outcomes': outcomes,
            'metadata': metadata or {}
        }

        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_outcomes(self, filename: str) -> Optional[List]:
        """Load outcomes from a file"""
        filepath = os.path.join(self.data_dir, filename)

        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('outcomes', [])

    def list_all(self):
        """List all historical data files"""
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]

        if not files:
            logger.info("No historical data files found")
            return

        logger.info(f"\nHistorical Data Files ({len(files)}):")
        logger.info("-" * 60)

        for f in sorted(files):
            filepath = os.path.join(self.data_dir, f)
            try:
                with open(filepath, 'r') as file:
                    data = json.load(file)
                    outcomes = data.get('outcomes', [])
                    win_rate = sum(outcomes) / len(outcomes) * 100 if outcomes else 0

                    logger.info(f"  {f}")
                    logger.info(f"    - {len(outcomes)} outcomes | Win rate: {win_rate:.1f}%")
            except:
                logger.info(f"  {f} (invalid format)")

    def _get_filename(self, team_name: str, market_type: str) -> str:
        """Generate filename for historical data"""
        safe_team = team_name.replace(' ', '_').replace('/', '_')
        safe_market = market_type.replace(' ', '_')
        return f"{safe_team}_{safe_market}.json"


# ---------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------
def interactive_mode():
    """Run interactive mode for managing historical data"""
    manager = HistoricalDataManager()

    print("\n" + "="*60)
    print("  HISTORICAL DATA HELPER")
    print("="*60)

    while True:
        print("\nOptions:")
        print("  1. Create from CSV file")
        print("  2. Create sample data")
        print("  3. List all historical data")
        print("  4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == '1':
            print("\n--- Create from CSV ---")
            csv_file = input("CSV file path: ").strip()
            team_name = input("Team name: ").strip()
            market_type = input("Market type (moneyline/spread/total): ").strip()
            outcome_column = input("Outcome column name: ").strip()

            use_threshold = input("Use threshold for continuous outcomes? (y/n): ").strip().lower()
            threshold = None
            if use_threshold == 'y':
                threshold = float(input("Threshold value: ").strip())

            manager.create_from_csv(csv_file, team_name, market_type, outcome_column, threshold)

        elif choice == '2':
            print("\n--- Create Sample Data ---")
            team_name = input("Team name: ").strip()
            market_type = input("Market type (moneyline/spread/total): ").strip()
            num_games = int(input("Number of games [20]: ").strip() or "20")
            win_prob = float(input("Win probability (0.0-1.0) [0.55]: ").strip() or "0.55")

            manager.create_sample_data(team_name, market_type, num_games, win_prob)

        elif choice == '3':
            manager.list_all()

        elif choice == '4':
            print("\nGoodbye!\n")
            break


# ---------------------------------------------------------------------
# Quick Helper Functions
# ---------------------------------------------------------------------
def quick_create_sample(team_name: str, market_type: str, num_games: int = 20, win_rate: float = 0.55):
    """Quickly create sample data"""
    manager = HistoricalDataManager()
    return manager.create_sample_data(team_name, market_type, num_games, win_rate)


def quick_create_from_csv(csv_file: str, team_name: str, market_type: str, outcome_column: str):
    """Quickly create from CSV"""
    manager = HistoricalDataManager()
    return manager.create_from_csv(csv_file, team_name, market_type, outcome_column)


# ---------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    # If run with arguments, create sample data for demo
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        print("\n" + "="*60)
        print("  CREATING DEMO DATA")
        print("="*60)

        manager = HistoricalDataManager()

        # Create sample data for a few teams
        teams = [
            ("Lakers", "moneyline", 0.58),
            ("Warriors", "moneyline", 0.62),
            ("Bulls", "spread", 0.51),
            ("Cavaliers", "total", 0.48),
        ]

        for team, market, prob in teams:
            manager.create_sample_data(team, market, num_games=25, win_probability=prob)

        print("\n✓ Demo data created!")
        print("✓ Run the auto_analysis_pipeline.py to analyze these markets\n")

    else:
        # Run interactive mode
        interactive_mode()
