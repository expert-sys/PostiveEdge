"""
Automated Sports Betting Analysis Pipeline
===========================================
Automatically processes scraped data and feeds it into the value engine for insights.

Flow:
1. Consolidate all scraped JSON files
2. Extract betting markets (spreads, moneylines, totals, props)
3. Match with historical data
4. Run value analysis via the implied probability engine
5. Generate actionable insights
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import glob
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import logging

from scrapers.data_consolidator import SportsDataConsolidator
from value_engine import ValueEngine, HistoricalData, MarketConfig, OutcomeType, analyze_simple_market
from data_processor import DataProcessor

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger("auto_pipeline")


# ---------------------------------------------------------------------
# Market Extractor
# ---------------------------------------------------------------------
class MarketExtractor:
    """Extracts betting markets from consolidated scraped data"""

    def __init__(self):
        self.markets = []

    def extract_from_consolidated(self, consolidated_data: Dict) -> List[Dict]:
        """Extract all betting markets from consolidated data"""
        self.markets = []

        if "games" not in consolidated_data:
            logger.warning("No games found in consolidated data")
            return []

        games = consolidated_data["games"]
        logger.info(f"Extracting markets from {len(games)} games...")

        for game in games:
            self._extract_game_markets(game)

        logger.info(f"✓ Extracted {len(self.markets)} betting markets")
        return self.markets

    def _extract_game_markets(self, game: Dict):
        """Extract markets from a single game"""
        # Get team names
        teams = self._extract_teams(game)
        if not teams or len(teams) < 2:
            return

        home_team = teams[0] if len(teams) >= 1 else "Unknown"
        away_team = teams[1] if len(teams) >= 2 else "Unknown"

        source = game.get('_source', 'Unknown')
        scraped_at = game.get('_scraped_at', '')

        # Extract spread market
        if game.get('spread') or game.get('pointspread'):
            spread = game.get('spread') or game.get('pointspread')
            self.markets.append({
                'market_type': 'spread',
                'home_team': home_team,
                'away_team': away_team,
                'line': spread,
                'odds': None,  # To be filled
                'source': source,
                'scraped_at': scraped_at,
                'event_description': f"{away_team} @ {home_team} - Spread {spread}"
            })

        # Extract moneyline market
        if game.get('moneyline') or game.get('ml'):
            ml = game.get('moneyline') or game.get('ml')
            self.markets.append({
                'market_type': 'moneyline',
                'home_team': home_team,
                'away_team': away_team,
                'line': ml,
                'odds': self._american_to_decimal(ml) if isinstance(ml, str) else None,
                'source': source,
                'scraped_at': scraped_at,
                'event_description': f"{away_team} @ {home_team} - Moneyline"
            })

        # Extract total (over/under) market
        if game.get('total') or game.get('over_under'):
            total = game.get('total') or game.get('over_under')
            self.markets.append({
                'market_type': 'total',
                'home_team': home_team,
                'away_team': away_team,
                'line': total,
                'odds': None,  # To be filled
                'source': source,
                'scraped_at': scraped_at,
                'event_description': f"{away_team} @ {home_team} - Total {total}"
            })

        # Extract props if available
        if game.get('prop'):
            prop = game.get('prop')
            self.markets.append({
                'market_type': 'prop',
                'home_team': home_team,
                'away_team': away_team,
                'line': prop,
                'odds': None,  # To be filled
                'source': source,
                'scraped_at': scraped_at,
                'event_description': f"{away_team} @ {home_team} - Prop: {prop}"
            })

    def _extract_teams(self, game: Dict) -> List[str]:
        """Extract team names from game data"""
        teams = []

        # Try different field names
        if 'teams' in game:
            val = game['teams']
            if isinstance(val, list):
                teams = [str(t).strip() for t in val if t and str(t).strip()]
            elif isinstance(val, str):
                teams = [t.strip() for t in val.split(',') if t.strip()]

        if not teams and 'team_name' in game:
            val = game['team_name']
            if isinstance(val, list):
                teams = [str(t).strip() for t in val if t and str(t).strip()]

        if not teams and 'home_team' in game:
            teams.append(str(game['home_team']).strip())
            if 'away_team' in game:
                teams.insert(0, str(game['away_team']).strip())

        # Remove duplicates while preserving order
        seen = set()
        unique_teams = []
        for team in teams:
            if team and team not in seen:
                seen.add(team)
                unique_teams.append(team)

        return unique_teams

    def _american_to_decimal(self, american_odds: str) -> Optional[float]:
        """Convert American odds to decimal odds"""
        try:
            odds_str = str(american_odds).strip().replace('+', '')
            odds_int = int(odds_str)

            if odds_int > 0:
                return (odds_int / 100) + 1
            else:
                return (100 / abs(odds_int)) + 1
        except:
            return None


# ---------------------------------------------------------------------
# Historical Data Matcher
# ---------------------------------------------------------------------
class HistoricalDataMatcher:
    """Matches markets with historical data for analysis"""

    def __init__(self, historical_data_dir: str = "./historical_data"):
        self.historical_data_dir = historical_data_dir
        self.cache = {}

    def find_historical_data(self, market: Dict) -> Optional[List]:
        """Find historical outcomes for a market"""
        # This is a placeholder - you'll need to implement based on your data sources
        # Options:
        # 1. Load from CSV files (e.g., team_stats.csv, player_stats.csv)
        # 2. Query from a database
        # 3. Fetch from an API
        # 4. Use pre-computed historical data files

        team = market.get('home_team', '') or market.get('away_team', '')
        market_type = market.get('market_type', '')

        # Try to load from cache
        cache_key = f"{team}_{market_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try to load from file
        historical_file = os.path.join(
            self.historical_data_dir,
            f"{team.replace(' ', '_')}_{market_type}.json"
        )

        if os.path.exists(historical_file):
            try:
                with open(historical_file, 'r') as f:
                    data = json.load(f)
                    outcomes = data.get('outcomes', [])
                    self.cache[cache_key] = outcomes
                    return outcomes
            except Exception as e:
                logger.debug(f"Could not load {historical_file}: {e}")

        # No historical data found
        return None


# ---------------------------------------------------------------------
# Analysis Pipeline
# ---------------------------------------------------------------------
class AutoAnalysisPipeline:
    """Main pipeline for automated analysis"""

    def __init__(self, historical_data_dir: str = "./historical_data"):
        self.consolidator = SportsDataConsolidator()
        self.extractor = MarketExtractor()
        self.matcher = HistoricalDataMatcher(historical_data_dir)
        self.engine = ValueEngine()
        self.results = []

    def run(self,
            scraped_files_dir: str = ".",
            output_file: str = "betting_insights.json",
            min_sample_size: int = 5) -> Dict:
        """
        Run the complete analysis pipeline

        Args:
            scraped_files_dir: Directory containing scraped_*.json files
            output_file: Where to save the insights
            min_sample_size: Minimum number of historical outcomes needed

        Returns:
            Analysis summary
        """
        logger.info("="*70)
        logger.info("  AUTOMATED BETTING ANALYSIS PIPELINE")
        logger.info("="*70)

        # Step 1: Consolidate scraped data
        logger.info("\n[1/5] Consolidating scraped data...")
        consolidation_report = self.consolidator.consolidate(
            directory=scraped_files_dir,
            export_json=True,
            export_csv=False
        )

        if "error" in consolidation_report:
            logger.error("Consolidation failed")
            return {"error": "Consolidation failed"}

        # Load consolidated data
        consolidated_file = "consolidated_sports_data.json"
        if not os.path.exists(consolidated_file):
            logger.error(f"Consolidated file not found: {consolidated_file}")
            return {"error": "Consolidated file not found"}

        with open(consolidated_file, 'r') as f:
            consolidated_data = json.load(f)

        # Step 2: Extract betting markets
        logger.info("\n[2/5] Extracting betting markets...")
        markets = self.extractor.extract_from_consolidated(consolidated_data)

        if not markets:
            logger.warning("No markets extracted")
            return {"warning": "No markets found in scraped data"}

        # Step 3: Match with historical data and analyze
        logger.info("\n[3/5] Matching markets with historical data...")
        analyzed_count = 0
        skipped_count = 0

        for market in markets:
            historical_outcomes = self.matcher.find_historical_data(market)

            if historical_outcomes and len(historical_outcomes) >= min_sample_size:
                # Run value analysis
                analysis = self._analyze_market(market, historical_outcomes, min_sample_size)
                if analysis:
                    self.results.append(analysis)
                    analyzed_count += 1
            else:
                skipped_count += 1

        logger.info(f"✓ Analyzed {analyzed_count} markets")
        logger.info(f"⚠ Skipped {skipped_count} markets (no historical data)")

        # Step 4: Sort and filter results
        logger.info("\n[4/5] Identifying value opportunities...")
        value_bets = [r for r in self.results if r.get('has_value', False)]
        logger.info(f"✓ Found {len(value_bets)} potential value bets")

        # Sort by expected value
        value_bets.sort(key=lambda x: x.get('ev_per_unit', 0), reverse=True)

        # Step 5: Export insights
        logger.info("\n[5/5] Exporting insights...")
        summary = self._export_insights(output_file, value_bets)

        logger.info("\n" + "="*70)
        logger.info("  ANALYSIS COMPLETE")
        logger.info("="*70)
        logger.info(f"\n✓ Total markets analyzed: {analyzed_count}")
        logger.info(f"✓ Value opportunities found: {len(value_bets)}")
        logger.info(f"✓ Insights saved to: {output_file}")
        logger.info("")

        return summary

    def _analyze_market(self, market: Dict, historical_outcomes: List, min_sample_size: int) -> Optional[Dict]:
        """Analyze a single market with historical data"""
        try:
            # Determine outcome type
            market_type = market.get('market_type', '')

            # For now, assume binary outcomes (win/loss)
            # You can extend this for continuous outcomes (totals, player props)
            outcome_type = "binary"
            threshold = None

            # Get bookmaker odds
            bookmaker_odds = market.get('odds')

            # If no odds in market, try to extract from line
            if not bookmaker_odds:
                line = market.get('line')
                if line:
                    # Try to parse odds from line
                    # Common formats: "-110", "+150", "1.91", etc.
                    if isinstance(line, str):
                        if line.startswith('-') or line.startswith('+'):
                            # American odds
                            bookmaker_odds = self._american_to_decimal(line)
                        else:
                            try:
                                bookmaker_odds = float(line)
                            except:
                                pass

            # Skip if no valid odds
            if not bookmaker_odds or bookmaker_odds <= 1.0:
                return None

            # Run analysis
            analysis = analyze_simple_market(
                event_type=market.get('event_description', 'Unknown'),
                historical_outcomes=historical_outcomes,
                bookmaker_odds=bookmaker_odds,
                outcome_type=outcome_type,
                minimum_sample_size=min_sample_size,
                threshold=threshold
            )

            # Convert to dict and add market info
            result = analysis.to_dict()
            result['market_info'] = {
                'type': market_type,
                'home_team': market.get('home_team'),
                'away_team': market.get('away_team'),
                'line': market.get('line'),
                'source': market.get('source'),
                'scraped_at': market.get('scraped_at')
            }

            return result

        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            return None

    def _american_to_decimal(self, american_odds: str) -> Optional[float]:
        """Convert American odds to decimal"""
        try:
            odds_str = str(american_odds).strip().replace('+', '')
            odds_int = int(odds_str)

            if odds_int > 0:
                return (odds_int / 100) + 1
            else:
                return (100 / abs(odds_int)) + 1
        except:
            return None

    def _export_insights(self, output_file: str, value_bets: List[Dict]) -> Dict:
        """Export insights to file"""
        output = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_opportunities": len(value_bets),
                "total_analyzed": len(self.results),
                "avg_ev": sum(r.get('ev_per_unit', 0) for r in value_bets) / len(value_bets) if value_bets else 0
            },
            "value_opportunities": value_bets[:50],  # Top 50
            "all_results": self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        # Also create a human-readable report
        self._create_text_report(value_bets)

        return output["summary"]

    def _create_text_report(self, value_bets: List[Dict]):
        """Create a human-readable text report"""
        report_file = "betting_insights_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("  BETTING VALUE ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Value Opportunities: {len(value_bets)}\n\n")

            if value_bets:
                f.write("-"*70 + "\n")
                f.write("TOP VALUE OPPORTUNITIES (Sorted by Expected Value)\n")
                f.write("-"*70 + "\n\n")

                for i, bet in enumerate(value_bets[:20], 1):
                    f.write(f"{i}. {bet['event_type']}\n")
                    f.write(f"   Market: {bet['market_info']['type']}\n")
                    f.write(f"   Teams: {bet['market_info']['away_team']} @ {bet['market_info']['home_team']}\n")
                    f.write(f"   Bookmaker Odds: {bet['bookmaker_odds']:.2f}\n")
                    f.write(f"   Fair Odds (from history): {bet['implied_odds']:.2f}\n")
                    f.write(f"   Edge: {bet['value_percentage']:+.2f}%\n")
                    f.write(f"   Expected Value: {bet['ev_per_unit']:+.4f} per unit\n")
                    f.write(f"   Expected Return per $100: ${bet['expected_return_per_100']:+.2f}\n")
                    f.write(f"   Sample Size: {bet['sample_size']} games\n")
                    f.write(f"   Source: {bet['market_info']['source']}\n")
                    f.write(f"\n")
            else:
                f.write("No value opportunities found with current data.\n\n")
                f.write("This could be because:\n")
                f.write("1. No historical data available for the scraped markets\n")
                f.write("2. Current market odds accurately reflect historical probabilities\n")
                f.write("3. Sample sizes are too small for reliable analysis\n\n")
                f.write("To improve results:\n")
                f.write("- Add historical data to ./historical_data/ directory\n")
                f.write("- Ensure historical data files match team/market names\n")
                f.write("- Scrape more betting sites for better odds comparison\n")

        logger.info(f"✓ Text report saved to: {report_file}")


# ---------------------------------------------------------------------
# Quick Run Function
# ---------------------------------------------------------------------
def run_auto_analysis(
    scraped_dir: str = ".",
    historical_dir: str = "./historical_data",
    output_file: str = "betting_insights.json"
):
    """Quick function to run the full pipeline"""
    pipeline = AutoAnalysisPipeline(historical_data_dir=historical_dir)
    return pipeline.run(
        scraped_files_dir=scraped_dir,
        output_file=output_file
    )


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    print("\n" + "="*70)
    print("  AUTOMATED BETTING ANALYSIS PIPELINE")
    print("="*70)
    print("\nThis pipeline will:")
    print("1. Consolidate all scraped_*.json files")
    print("2. Extract betting markets (spreads, moneylines, totals)")
    print("3. Match with historical data")
    print("4. Calculate implied probabilities and expected value")
    print("5. Identify value betting opportunities\n")

    # Check for historical data directory
    hist_dir = "./historical_data"
    if not os.path.exists(hist_dir):
        print(f"⚠ Historical data directory not found: {hist_dir}")
        print(f"Creating directory...")
        os.makedirs(hist_dir, exist_ok=True)
        print(f"\nℹ To analyze markets, add historical outcome files to: {hist_dir}/")
        print(f"  Format: {{TeamName}}_{{market_type}}.json")
        print(f"  Example: Lakers_moneyline.json with content: {{\"outcomes\": [1,0,1,1,0,...]}}\n")

    # Run pipeline
    confirm = input("Run analysis pipeline? (y/n) [y]: ").strip().lower()
    if confirm != 'n':
        summary = run_auto_analysis()

        if "error" not in summary:
            print(f"\n✓ Pipeline completed successfully!")
            print(f"✓ Check betting_insights.json for detailed results")
            print(f"✓ Check betting_insights_report.txt for human-readable summary\n")
