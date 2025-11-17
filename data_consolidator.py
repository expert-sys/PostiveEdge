"""
Sports Data Consolidator & Cleaner
----------------------------------
Combines multiple scraped JSON files into one clean dataset
- Removes duplicates
- Normalizes data
- Validates entries
- Prepares for analysis
"""

import json
import os
import glob
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
import re
import logging
import pandas as pd
from collections import defaultdict

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger("data_consolidator")


# ---------------------------------------------------------------------
# Data Consolidator Class
# ---------------------------------------------------------------------
class SportsDataConsolidator:

    def __init__(self, input_pattern: str = "scraped_*.json"):
        self.input_pattern = input_pattern
        self.all_games = []
        self.all_json = []
        self.all_tables = []
        self.metadata = {
            "files_processed": 0,
            "total_games": 0,
            "duplicates_removed": 0,
            "invalid_entries": 0,
            "sources": [],
            "consolidation_date": datetime.now().isoformat()
        }

    # --------------------------
    # Load All Scraped Files
    # --------------------------
    def load_all_files(self, directory: str = ".") -> int:
        """Load all scraped JSON files from directory"""
        files = glob.glob(os.path.join(directory, self.input_pattern))

        if not files:
            logger.warning(f"No files found matching pattern: {self.input_pattern}")
            return 0

        logger.info(f"Found {len(files)} files to process")

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._process_file(data, file_path)
                    self.metadata["files_processed"] += 1
                    self.metadata["sources"].append(os.path.basename(file_path))
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        return self.metadata["files_processed"]

    # --------------------------
    # Process Individual File
    # --------------------------
    def _process_file(self, data: Dict, source_file: str):
        """Process data from a single file"""
        source_name = os.path.basename(source_file)

        # Extract games
        if "games" in data and isinstance(data["games"], list):
            for game in data["games"]:
                if isinstance(game, dict):
                    game["_source"] = source_name
                    game["_scraped_at"] = self._extract_timestamp(source_name)
                    self.all_games.append(game)

        # Extract JSON data
        if "json" in data and isinstance(data["json"], list):
            self.all_json.extend(data["json"])

        # Extract tables
        if "tables" in data and isinstance(data["tables"], list):
            for table in data["tables"]:
                if isinstance(table, dict):
                    self.all_tables.append({
                        "data": table,
                        "source": source_name
                    })

    # --------------------------
    # Extract Timestamp from Filename
    # --------------------------
    def _extract_timestamp(self, filename: str) -> str:
        """Extract timestamp from filename"""
        # Pattern: scraped_Name_YYYYMMDD_HHMMSS.json
        match = re.search(r'(\d{8}_\d{6})', filename)
        if match:
            timestamp_str = match.group(1)
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                return dt.isoformat()
            except:
                pass
        return datetime.now().isoformat()

    # --------------------------
    # Generate Game Hash for Deduplication
    # --------------------------
    def _generate_game_hash(self, game: Dict) -> str:
        """Generate unique hash for a game to detect duplicates"""
        # Extract key identifiers
        teams = []

        # Handle different team name formats
        for key, value in game.items():
            if 'team' in key.lower():
                if isinstance(value, list):
                    teams.extend([str(t).strip().lower() for t in value if t])
                elif isinstance(value, str):
                    teams.append(value.strip().lower())

        # Sort teams for consistent hashing
        teams = sorted(set(teams))

        # Include date if available
        date_str = game.get('date', game.get('time', ''))

        # Create hash
        hash_str = f"{'-'.join(teams)}_{date_str}"
        return hash_str

    # --------------------------
    # Remove Duplicates
    # --------------------------
    def remove_duplicates(self) -> int:
        """Remove duplicate games based on team names and date"""
        if not self.all_games:
            return 0

        seen_hashes = {}
        unique_games = []
        duplicates = 0

        for game in self.all_games:
            game_hash = self._generate_game_hash(game)

            if game_hash in seen_hashes:
                # Keep the most recent scrape
                existing_game = seen_hashes[game_hash]
                existing_time = existing_game.get('_scraped_at', '')
                new_time = game.get('_scraped_at', '')

                if new_time > existing_time:
                    # Replace with newer data
                    seen_hashes[game_hash] = game
                    unique_games.remove(existing_game)
                    unique_games.append(game)

                duplicates += 1
            else:
                seen_hashes[game_hash] = game
                unique_games.append(game)

        self.all_games = unique_games
        self.metadata["duplicates_removed"] = duplicates
        self.metadata["total_games"] = len(unique_games)

        logger.info(f"Removed {duplicates} duplicates. {len(unique_games)} unique games remaining.")
        return duplicates

    # --------------------------
    # Clean and Normalize Data
    # --------------------------
    def clean_data(self):
        """Clean and normalize all game data"""
        cleaned_games = []
        invalid_count = 0

        for game in self.all_games:
            cleaned_game = self._clean_game(game)
            if cleaned_game:
                cleaned_games.append(cleaned_game)
            else:
                invalid_count += 1

        self.all_games = cleaned_games
        self.metadata["invalid_entries"] = invalid_count
        logger.info(f"Cleaned {len(cleaned_games)} games. Removed {invalid_count} invalid entries.")

    # --------------------------
    # Clean Individual Game
    # --------------------------
    def _clean_game(self, game: Dict) -> Dict:
        """Clean and normalize a single game entry"""
        if not isinstance(game, dict):
            return None

        cleaned = {}

        # Extract and clean each field
        for key, value in game.items():
            if key.startswith('_'):
                # Keep metadata as-is
                cleaned[key] = value
            elif value is None or value == "":
                # Skip empty values
                continue
            elif isinstance(value, str):
                # Clean string values
                cleaned_value = value.strip()
                if cleaned_value:
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                # Clean list values
                cleaned_list = []
                for item in value:
                    if isinstance(item, str):
                        cleaned_item = item.strip()
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    elif item is not None:
                        cleaned_list.append(item)
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value

        # Must have at least some team or game data
        has_data = any(
            key for key in cleaned.keys()
            if not key.startswith('_') and key != 'source'
        )

        return cleaned if has_data else None

    # --------------------------
    # Normalize Field Names
    # --------------------------
    def normalize_fields(self):
        """Normalize field names across all games"""
        normalized_games = []

        for game in self.all_games:
            normalized = self._normalize_game_fields(game)
            normalized_games.append(normalized)

        self.all_games = normalized_games
        logger.info(f"Normalized {len(normalized_games)} game entries")

    # --------------------------
    # Normalize Individual Game Fields
    # --------------------------
    def _normalize_game_fields(self, game: Dict) -> Dict:
        """Normalize field names for a single game"""
        normalized = {}

        # Field name mappings
        field_mappings = {
            # Teams
            'team1': 'home_team',
            'team_name': 'teams',
            'participant': 'teams',
            'team': 'teams',

            # Scores
            'final_score': 'score',
            'final': 'score',

            # Odds
            'moneyline': 'ml',
            'money_line': 'ml',
            'pointspread': 'spread',
            'point_spread': 'spread',
            'over_under': 'total',
            'ou': 'total',

            # Time
            'time': 'game_time',
            'date': 'game_date',
            'start_time': 'game_time',
        }

        for key, value in game.items():
            # Check if field should be renamed
            normalized_key = field_mappings.get(key.lower(), key)
            normalized[normalized_key] = value

        return normalized

    # --------------------------
    # Export Consolidated Data
    # --------------------------
    def export_consolidated(self, output_file: str = "consolidated_sports_data.json") -> bool:
        """Export all consolidated data to a single file"""
        try:
            output = {
                "metadata": self.metadata,
                "games": self.all_games,
                "statistics": {
                    "total_games": len(self.all_games),
                    "total_json_objects": len(self.all_json),
                    "total_tables": len(self.all_tables)
                }
            }

            # Only include non-empty sections
            if self.all_json:
                output["json_data"] = self.all_json
            if self.all_tables:
                output["tables"] = self.all_tables

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Exported consolidated data to {output_file}")
            logger.info(f"  - {len(self.all_games)} unique games")
            logger.info(f"  - {len(self.all_json)} JSON objects")
            logger.info(f"  - {len(self.all_tables)} tables")

            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    # --------------------------
    # Export to CSV for Analysis
    # --------------------------
    def export_to_csv(self, output_file: str = "consolidated_sports_data.csv") -> bool:
        """Export games data to CSV for easy analysis"""
        if not self.all_games:
            logger.warning("No games to export")
            return False

        try:
            # Flatten nested structures for CSV
            flattened_games = []

            for game in self.all_games:
                flattened = {}

                for key, value in game.items():
                    if isinstance(value, list):
                        # Convert lists to comma-separated strings
                        if all(isinstance(x, str) for x in value):
                            flattened[key] = ", ".join(value)
                        else:
                            flattened[key] = str(value)
                    elif isinstance(value, dict):
                        # Skip nested dicts in CSV
                        continue
                    else:
                        flattened[key] = value

                flattened_games.append(flattened)

            # Create DataFrame
            df = pd.DataFrame(flattened_games)

            # Reorder columns - put important ones first
            priority_cols = ['_source', '_scraped_at', 'teams', 'home_team', 'score',
                           'spread', 'ml', 'total', 'game_date', 'game_time']

            existing_priority = [col for col in priority_cols if col in df.columns]
            other_cols = [col for col in df.columns if col not in existing_priority]

            df = df[existing_priority + other_cols]

            # Export
            df.to_csv(output_file, index=False, encoding='utf-8')

            logger.info(f"✓ Exported to CSV: {output_file}")
            logger.info(f"  - {len(df)} rows")
            logger.info(f"  - {len(df.columns)} columns")

            return True

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False

    # --------------------------
    # Generate Summary Report
    # --------------------------
    def generate_report(self) -> Dict:
        """Generate summary report of consolidated data"""
        report = {
            "summary": {
                "files_processed": self.metadata["files_processed"],
                "total_games": len(self.all_games),
                "duplicates_removed": self.metadata["duplicates_removed"],
                "invalid_entries": self.metadata["invalid_entries"],
                "consolidation_date": self.metadata["consolidation_date"]
            },
            "sources": self.metadata["sources"],
            "data_quality": self._calculate_data_quality()
        }

        return report

    # --------------------------
    # Calculate Data Quality Metrics
    # --------------------------
    def _calculate_data_quality(self) -> Dict:
        """Calculate data quality metrics"""
        if not self.all_games:
            return {"completeness": 0, "fields_coverage": {}}

        # Count field coverage
        field_counts = defaultdict(int)
        total_games = len(self.all_games)

        for game in self.all_games:
            for key in game.keys():
                if not key.startswith('_'):
                    field_counts[key] += 1

        # Calculate percentages
        field_coverage = {
            field: round((count / total_games) * 100, 2)
            for field, count in field_counts.items()
        }

        # Overall completeness
        avg_completeness = sum(field_coverage.values()) / len(field_coverage) if field_coverage else 0

        return {
            "completeness": round(avg_completeness, 2),
            "field_coverage": field_coverage,
            "total_unique_fields": len(field_counts)
        }

    # --------------------------
    # Full Consolidation Pipeline
    # --------------------------
    def consolidate(self, directory: str = ".",
                   export_json: bool = True,
                   export_csv: bool = True) -> Dict:
        """
        Run full consolidation pipeline

        Returns:
            Summary report
        """
        logger.info("="*60)
        logger.info("  SPORTS DATA CONSOLIDATION")
        logger.info("="*60)

        # Load files
        logger.info("\n[1/5] Loading files...")
        files_loaded = self.load_all_files(directory)

        if files_loaded == 0:
            logger.error("No files loaded. Exiting.")
            return {"error": "No files found"}

        # Remove duplicates
        logger.info("\n[2/5] Removing duplicates...")
        self.remove_duplicates()

        # Clean data
        logger.info("\n[3/5] Cleaning data...")
        self.clean_data()

        # Normalize fields
        logger.info("\n[4/5] Normalizing fields...")
        self.normalize_fields()

        # Export
        logger.info("\n[5/5] Exporting data...")
        if export_json:
            self.export_consolidated()
        if export_csv:
            self.export_to_csv()

        # Generate report
        report = self.generate_report()

        logger.info("\n" + "="*60)
        logger.info("  CONSOLIDATION COMPLETE")
        logger.info("="*60)
        logger.info(f"\n✓ Processed {report['summary']['files_processed']} files")
        logger.info(f"✓ {report['summary']['total_games']} unique games")
        logger.info(f"✓ Removed {report['summary']['duplicates_removed']} duplicates")
        logger.info(f"✓ Data quality: {report['data_quality']['completeness']:.1f}%")
        logger.info("")

        return report


# ---------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------
def interactive_consolidation():
    """Run interactive consolidation"""
    print("\n" + "="*60)
    print("  SPORTS DATA CONSOLIDATOR")
    print("="*60)

    # Get directory
    directory = input("\nEnter directory containing scraped files [.]: ").strip() or "."

    if not os.path.exists(directory):
        print(f"\n✗ Directory not found: {directory}")
        return

    # Count files
    files = glob.glob(os.path.join(directory, "scraped_*.json"))
    print(f"\nFound {len(files)} scraped JSON files")

    if len(files) == 0:
        print("\n✗ No files to consolidate")
        return

    # Show file list
    print("\nFiles to process:")
    for i, f in enumerate(files[:10], 1):
        print(f"  {i}. {os.path.basename(f)}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")

    # Confirm
    confirm = input("\nProceed with consolidation? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("\nCancelled.")
        return

    # Export options
    export_json = input("Export to JSON? (y/n) [y]: ").strip().lower() != 'n'
    export_csv = input("Export to CSV? (y/n) [y]: ").strip().lower() != 'n'

    # Run consolidation
    consolidator = SportsDataConsolidator()
    report = consolidator.consolidate(directory, export_json, export_csv)

    # Show report
    if "error" not in report:
        print("\n" + "="*60)
        print("  DATA QUALITY REPORT")
        print("="*60)
        print(f"\nCompleteness: {report['data_quality']['completeness']:.1f}%")
        print(f"Unique Fields: {report['data_quality']['total_unique_fields']}")
        print("\nTop Fields Coverage:")

        coverage = report['data_quality']['field_coverage']
        sorted_coverage = sorted(coverage.items(), key=lambda x: x[1], reverse=True)

        for field, pct in sorted_coverage[:10]:
            print(f"  - {field}: {pct:.1f}%")

    print("\n✓ Consolidation complete!\n")


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    interactive_consolidation()
