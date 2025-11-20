"""
Sportsbet → Value Engine Integration
=====================================
Connects the Sportsbet scraper to the automated analysis pipeline.

Flow:
1. Scrape current odds from Sportsbet
2. Scrape historical H2H data from Sportsbet
3. Convert to format for value engine
4. Run implied probability analysis
5. Generate betting insights
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging

from scrapers.sportsbet_scraper import (
    SportsbetScraper,
    MatchOdds,
    ComprehensiveMatchData,
    scrape_nba_overview,
    scrape_match_detail
)

from value_engine import (
    ValueEngine,
    HistoricalData,
    MarketConfig,
    OutcomeType,
    analyze_simple_market
)

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger("sportsbet_integration")


# ---------------------------------------------------------------------
# Data Converter
# ---------------------------------------------------------------------
class SportsbetToValueEngineConverter:
    """
    Converts Sportsbet data into format for value engine analysis
    """

    def __init__(self):
        self.engine = ValueEngine()

    def convert_h2h_to_outcomes(
        self,
        h2h_games: List,
        team_name: str,
        market_type: str = "moneyline"
    ) -> List[int]:
        """
        Convert head-to-head games to binary outcomes

        Args:
            h2h_games: List of HeadToHeadGame objects
            team_name: Team to analyze (e.g., "Indiana Pacers")
            market_type: Type of market (moneyline, spread, total)

        Returns:
            List of binary outcomes (1 = success, 0 = failure)
        """
        outcomes = []

        for game in h2h_games:
            if market_type == "moneyline":
                # Did the team win?
                if game.winner and team_name.lower() in game.winner.lower():
                    outcomes.append(1)
                elif game.winner:
                    outcomes.append(0)
                # If no clear winner, skip
                continue

            elif market_type == "spread":
                # For spread, we'd need the actual spread line
                # For now, just use win/loss
                if game.winner and team_name.lower() in game.winner.lower():
                    outcomes.append(1)
                elif game.winner:
                    outcomes.append(0)

            elif market_type == "total":
                # For totals, check if combined score went over
                if game.final_home is not None and game.final_away is not None:
                    total = game.final_home + game.final_away
                    # We'd need the actual line, for now use average
                    outcomes.append(1 if total > 210 else 0)

        return outcomes

    def convert_season_results_to_outcomes(
        self,
        season_results: List,
        market_type: str = "moneyline"
    ) -> List[int]:
        """
        Convert season results to binary outcomes

        Args:
            season_results: List of SeasonResult objects
            market_type: Type of market

        Returns:
            List of binary outcomes
        """
        outcomes = []

        for result in season_results:
            if market_type == "moneyline":
                outcomes.append(1 if result.result == 'W' else 0)

        return outcomes

    def analyze_match_from_sportsbet(
        self,
        match_data: ComprehensiveMatchData,
        min_sample_size: int = 5
    ) -> Dict:
        """
        Analyze a match using Sportsbet data and value engine

        Args:
            match_data: ComprehensiveMatchData from scraper
            min_sample_size: Minimum historical games needed

        Returns:
            Dictionary with all analysis results
        """
        results = {
            'match': {
                'away_team': match_data.match_odds.away_team,
                'home_team': match_data.match_odds.home_team,
                'time': match_data.match_odds.match_time
            },
            'analysis': {}
        }

        # Analyze each market type

        # 1. AWAY TEAM MONEYLINE
        if match_data.match_odds.away_ml_odds:
            away_h2h_outcomes = self.convert_h2h_to_outcomes(
                match_data.head_to_head,
                match_data.match_odds.away_team,
                "moneyline"
            )

            # Also use season results if available
            if match_data.match_odds.away_team in match_data.team_stats:
                away_stats = match_data.team_stats[match_data.match_odds.away_team]
                if away_stats.season_results:
                    season_outcomes = self.convert_season_results_to_outcomes(
                        away_stats.season_results,
                        "moneyline"
                    )
                    # Combine H2H and season (give more weight to H2H)
                    away_h2h_outcomes = away_h2h_outcomes + season_outcomes

            if len(away_h2h_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"{match_data.match_odds.away_team} Moneyline",
                        historical_outcomes=away_h2h_outcomes,
                        bookmaker_odds=match_data.match_odds.away_ml_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['away_moneyline'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze away ML: {e}")

        # 2. HOME TEAM MONEYLINE
        if match_data.match_odds.home_ml_odds:
            home_h2h_outcomes = self.convert_h2h_to_outcomes(
                match_data.head_to_head,
                match_data.match_odds.home_team,
                "moneyline"
            )

            # Add season results
            if match_data.match_odds.home_team in match_data.team_stats:
                home_stats = match_data.team_stats[match_data.match_odds.home_team]
                if home_stats.season_results:
                    season_outcomes = self.convert_season_results_to_outcomes(
                        home_stats.season_results,
                        "moneyline"
                    )
                    home_h2h_outcomes = home_h2h_outcomes + season_outcomes

            if len(home_h2h_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"{match_data.match_odds.home_team} Moneyline",
                        historical_outcomes=home_h2h_outcomes,
                        bookmaker_odds=match_data.match_odds.home_ml_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['home_moneyline'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze home ML: {e}")

        # 3. AWAY TEAM HANDICAP
        if match_data.match_odds.away_handicap_odds:
            # For handicap, use similar logic but would need to apply spread
            # For now, use same outcomes as moneyline
            if len(away_h2h_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"{match_data.match_odds.away_team} Handicap {match_data.match_odds.away_handicap}",
                        historical_outcomes=away_h2h_outcomes,
                        bookmaker_odds=match_data.match_odds.away_handicap_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['away_handicap'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze away handicap: {e}")

        # 4. HOME TEAM HANDICAP
        if match_data.match_odds.home_handicap_odds:
            if len(home_h2h_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"{match_data.match_odds.home_team} Handicap {match_data.match_odds.home_handicap}",
                        historical_outcomes=home_h2h_outcomes,
                        bookmaker_odds=match_data.match_odds.home_handicap_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['home_handicap'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze home handicap: {e}")

        # 5. TOTALS (OVER/UNDER)
        if match_data.match_odds.over_odds:
            total_outcomes = []
            for game in match_data.head_to_head:
                if game.final_home is not None and game.final_away is not None:
                    combined = game.final_home + game.final_away
                    # Extract line from over_line (e.g., "+228.5")
                    if match_data.match_odds.over_line:
                        try:
                            line = float(match_data.match_odds.over_line.replace('+', ''))
                            total_outcomes.append(1 if combined > line else 0)
                        except:
                            pass

            if len(total_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"Over {match_data.match_odds.over_line}",
                        historical_outcomes=total_outcomes,
                        bookmaker_odds=match_data.match_odds.over_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['over'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze over: {e}")

        if match_data.match_odds.under_odds:
            under_outcomes = [1 - o for o in total_outcomes]  # Inverse of over

            if len(under_outcomes) >= min_sample_size:
                try:
                    analysis = analyze_simple_market(
                        event_type=f"Under {match_data.match_odds.under_line}",
                        historical_outcomes=under_outcomes,
                        bookmaker_odds=match_data.match_odds.under_odds,
                        outcome_type="binary",
                        minimum_sample_size=min_sample_size
                    )

                    results['analysis']['under'] = analysis.to_dict()
                except Exception as e:
                    logger.error(f"Failed to analyze under: {e}")

        # Add metadata
        results['h2h_sample_size'] = len(match_data.head_to_head)
        results['insights'] = [
            {'team': i.team, 'insight': i.insight, 'value': i.value}
            for i in match_data.insights
        ]

        return results


# ---------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------
class SportsbetAnalysisPipeline:
    """
    Complete pipeline: Scrape Sportsbet → Analyze with Value Engine
    """

    def __init__(self):
        self.scraper = None
        self.converter = SportsbetToValueEngineConverter()
        self.results = []

    def run_full_analysis(
        self,
        headless: bool = True,
        max_matches: int = 5
    ) -> List[Dict]:
        """
        Run complete analysis pipeline

        Args:
            headless: Run browser in headless mode
            max_matches: Maximum number of matches to analyze in detail

        Returns:
            List of analysis results
        """
        logger.info("="*70)
        logger.info("  SPORTSBET → VALUE ENGINE PIPELINE")
        logger.info("="*70)

        # Step 1: Scrape NBA overview
        logger.info("\n[1/3] Scraping NBA overview from Sportsbet...")
        matches = scrape_nba_overview(headless=headless)

        if not matches:
            logger.error("No matches found")
            return []

        logger.info(f"Found {len(matches)} matches")

        # Step 2: Scrape detailed data for each match
        logger.info(f"\n[2/3] Scraping detailed data for up to {max_matches} matches...")

        detailed_matches = []

        for i, match in enumerate(matches[:max_matches], 1):
            if not match.match_url:
                logger.warning(f"Match {i} has no URL, skipping")
                continue

            logger.info(f"\n  [{i}/{min(len(matches), max_matches)}] {match.away_team} @ {match.home_team}")
            logger.info(f"  URL: {match.match_url}")

            try:
                detailed_data = scrape_match_detail(match.match_url, headless=headless)
                if detailed_data:
                    detailed_matches.append(detailed_data)
                    logger.info(f"  ✓ Scraped: {len(detailed_data.head_to_head)} H2H games")
            except Exception as e:
                logger.error(f"  ✗ Failed to scrape: {e}")
                continue

        # Step 3: Analyze with value engine
        logger.info(f"\n[3/3] Analyzing {len(detailed_matches)} matches with value engine...")

        for i, match_data in enumerate(detailed_matches, 1):
            logger.info(f"\n  [{i}/{len(detailed_matches)}] Analyzing {match_data.match_odds.away_team} @ {match_data.match_odds.home_team}")

            try:
                analysis = self.converter.analyze_match_from_sportsbet(match_data)
                self.results.append(analysis)

                # Show value opportunities
                for market, result in analysis['analysis'].items():
                    if result.get('has_value'):
                        logger.info(f"    ✓ VALUE FOUND: {market}")
                        logger.info(f"      EV: {result['ev_per_unit']:+.4f} | Edge: {result['value_percentage']:+.2f}%")

            except Exception as e:
                logger.error(f"  ✗ Analysis failed: {e}")
                continue

        # Step 4: Save results
        logger.info("\n[4/4] Saving results...")
        self._save_results()

        # Summary
        logger.info("\n" + "="*70)
        logger.info("  ANALYSIS COMPLETE")
        logger.info("="*70)

        total_value_bets = sum(
            1 for r in self.results
            for market, analysis in r['analysis'].items()
            if analysis.get('has_value')
        )

        logger.info(f"\n✓ Analyzed {len(self.results)} matches")
        logger.info(f"✓ Found {total_value_bets} value betting opportunities")
        logger.info(f"✓ Results saved to sportsbet_analysis_results.json\n")

        return self.results

    def _save_results(self):
        """Save results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sportsbet_analysis_results_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_matches': len(self.results),
                'results': self.results
            }, f, indent=2, default=str)

        logger.info(f"✓ Saved to {filename}")

        # Also create human-readable report
        self._create_report(filename.replace('.json', '_report.txt'))

    def _create_report(self, filename: str):
        """Create human-readable report"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("  SPORTSBET VALUE BETTING REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Matches Analyzed: {len(self.results)}\n\n")

            for i, result in enumerate(self.results, 1):
                f.write("-"*70 + "\n")
                f.write(f"MATCH {i}: {result['match']['away_team']} @ {result['match']['home_team']}\n")
                f.write(f"Time: {result['match']['time']}\n")
                f.write(f"H2H Sample Size: {result['h2h_sample_size']} games\n")
                f.write("-"*70 + "\n\n")

                # Show all markets
                for market_name, analysis in result['analysis'].items():
                    f.write(f"  {market_name.upper().replace('_', ' ')}\n")
                    f.write(f"  {'─'*66}\n")
                    f.write(f"  Event: {analysis['event_type']}\n")
                    f.write(f"  Bookmaker Odds: {analysis['bookmaker_odds']:.2f}\n")
                    f.write(f"  Fair Odds: {analysis['implied_odds']:.2f}\n")
                    f.write(f"  Historical Probability: {analysis['historical_probability']*100:.1f}%\n")
                    f.write(f"  Bookmaker Probability: {analysis['bookmaker_probability']*100:.1f}%\n")
                    f.write(f"  Edge: {analysis['value_percentage']:+.2f}%\n")
                    f.write(f"  Expected Value: {analysis['ev_per_unit']:+.4f} per unit\n")
                    f.write(f"  Expected Return per $100: ${analysis['expected_return_per_100']:+.2f}\n")
                    f.write(f"  Sample Size: {analysis['sample_size']}\n")

                    if analysis['has_value']:
                        f.write(f"  >>> VALUE BET ✓ <<<\n")
                    else:
                        f.write(f"  No value\n")

                    f.write(f"\n")

                # Show insights
                if result['insights']:
                    f.write(f"  MATCH INSIGHTS\n")
                    f.write(f"  {'─'*66}\n")
                    for insight in result['insights']:
                        f.write(f"  • {insight['team']}: {insight['insight']}\n")
                    f.write(f"\n")

                f.write("\n")

        logger.info(f"✓ Report saved to {filename}")


# ---------------------------------------------------------------------
# Quick Run Function
# ---------------------------------------------------------------------
def run_sportsbet_pipeline(headless: bool = True, max_matches: int = 3):
    """
    Quick function to run the full Sportsbet analysis pipeline

    Args:
        headless: Run browser in headless mode
        max_matches: Maximum matches to analyze in detail

    Returns:
        List of analysis results
    """
    pipeline = SportsbetAnalysisPipeline()
    return pipeline.run_full_analysis(headless=headless, max_matches=max_matches)


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    print("\n" + "="*70)
    print("  SPORTSBET → VALUE ENGINE INTEGRATION")
    print("="*70)
    print("\nThis will:")
    print("1. Scrape current NBA odds from Sportsbet.com.au")
    print("2. Scrape historical H2H data for each match")
    print("3. Run value analysis using the implied probability engine")
    print("4. Identify positive EV betting opportunities\n")

    headless = input("Run in headless mode (no browser window)? (y/n) [y]: ").strip().lower() != 'n'
    max_matches = input("Max matches to analyze in detail [3]: ").strip() or "3"

    try:
        max_matches = int(max_matches)
    except:
        max_matches = 3

    print("\nStarting pipeline...\n")

    results = run_sportsbet_pipeline(headless=headless, max_matches=max_matches)

    if results:
        print("\n" + "="*70)
        print("  SUCCESS!")
        print("="*70)
        print(f"\nCheck the output files for detailed results:")
        print("  - sportsbet_analysis_results_*.json (detailed data)")
        print("  - sportsbet_analysis_results_*_report.txt (human-readable)")
        print("\nHappy betting!\n")
