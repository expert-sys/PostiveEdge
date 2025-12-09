"""
Sportsbet Data Collector
========================
Collects NBA betting data from Sportsbet including games, odds, insights, and player props.
"""

import logging
from typing import List, Dict, Optional
import re

from utils.error_handling import safe_call, handle_import_error

logger = logging.getLogger(__name__)


class SportsbetCollector:
    """Collects NBA betting data from Sportsbet"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    def collect_games(self, max_games: int = None) -> List[Dict]:
        """
        Scrape NBA games with odds, insights, and player props
        
        Returns:
            List of game dicts with:
            - game_info: {home_team, away_team, match_time, url}
            - team_markets: List of team betting markets
            - insights: List of Sportsbet insights/trends
            - player_props: List of player prop markets
            - team_recent_results: Recent game results for both teams
        """
        logger.info("=" * 80)
        logger.info("STEP 1: SCRAPING SPORTSBET NBA DATA")
        logger.info("=" * 80)
        
        # Safely import scraper module
        scraper_module = handle_import_error(
            'scrapers.sportsbet_final_enhanced',
            fallback=None,
            error_message="Sportsbet scraper not found. Install dependencies."
        )
        
        if not scraper_module:
            return []
        
        scrape_nba_overview = getattr(scraper_module, 'scrape_nba_overview', None)
        scrape_match_complete = getattr(scraper_module, 'scrape_match_complete', None)
        
        if not scrape_nba_overview or not scrape_match_complete:
            logger.error("Required scraping functions not found in scraper module")
            return []
        
        # Get all NBA games with error handling
        logger.info("Fetching NBA games from Sportsbet...")
        games = safe_call(
            lambda: scrape_nba_overview(headless=self.headless),
            default=[],
            error_context="scraping NBA overview"
        )
        
        if not games:
            logger.warning("No games found on Sportsbet")
            return []
        
        # Limit games if specified
        if max_games:
            games = games[:max_games]
        
        logger.info(f"Found {len(games)} games to analyze")
        
        # Collect detailed data for each game
        game_data = []
        for i, game in enumerate(games, 1):
            logger.info(f"\n[{i}/{len(games)}] Collecting: {game['away_team']} @ {game['home_team']}")
            
            # Scrape complete match data with error handling
            match_data = safe_call(
                lambda: scrape_match_complete(game['url'], headless=self.headless),
                default=None,
                error_context=f"scraping match data for {game.get('away_team', 'unknown')} @ {game.get('home_team', 'unknown')}"
            )
            
            if not match_data:
                logger.warning("  Failed to scrape match data")
                continue
            
            # Extract components with safe attribute access
            all_markets = getattr(match_data, 'all_markets', []) or []
            insights = getattr(match_data, 'match_insights', []) or []
            match_stats = getattr(match_data, 'match_stats', None)
            
            # Extract team recent results from insights (if available)
            team_results = safe_call(
                lambda: self._extract_team_results_from_insights(insights, game['home_team'], game['away_team']),
                default=None,
                error_context="extracting team results from insights"
            )
            
            logger.info(f"  ✓ {len(all_markets)} markets, {len(insights)} insights")
            if team_results:
                logger.info(f"  ✓ Found recent results for team markets")
            
            game_data.append({
                'game_info': game,
                'team_markets': all_markets,
                'insights': insights,
                'match_stats': match_stats,
                'team_recent_results': team_results
            })
        
        logger.info(f"\n✓ Collected data for {len(game_data)} games")
        return game_data
    
    def _extract_team_results_from_insights(self, insights: List, home_team: str, away_team: str) -> Optional[Dict]:
        """
        Extract recent game results from insights data.
        
        Looks for insights showing "2025/26 Season Results" with scores.
        
        Returns:
            Dict with 'home_results' and 'away_results' lists of (score_for, score_against, result) tuples
        """
        results = {
            'home_team': home_team,
            'away_team': away_team,
            'home_results': [],
            'away_results': []
        }
        
        # Look through insights for season results
        for insight in insights:
            fact = str(getattr(insight, 'fact', ''))
            result = str(getattr(insight, 'result', ''))
            market = str(getattr(insight, 'market', ''))
            
            # Check if this is a season results insight
            combined = (fact + ' ' + result + ' ' + market).lower()
            
            if 'season results' in combined or 'last 5' in combined or 'recent games' in combined:
                # Try to extract scores in format "123-120" or "W 123-120"
                score_pattern = r'(\d{2,3})-(\d{2,3})'
                scores = re.findall(score_pattern, fact + ' ' + result)
                
                # Try to determine which team this is for
                team_name = None
                if home_team.lower() in combined:
                    team_name = 'home'
                elif away_team.lower() in combined:
                    team_name = 'away'
                
                if scores and team_name:
                    # Parse results
                    for score_for, score_against in scores[:10]:  # Max 10 games
                        score_for = int(score_for)
                        score_against = int(score_against)
                        result_char = "W" if score_for > score_against else "L"
                        
                        if team_name == 'home':
                            results['home_results'].append((score_for, score_against, result_char))
                        else:
                            results['away_results'].append((score_for, score_against, result_char))
        
        # Return None if no results found
        if not results['home_results'] and not results['away_results']:
            return None
        
        return results
    
    def _extract_player_props(self, markets: List) -> List:
        """Extract player prop markets from all markets"""
        props = []
        
        for market in markets:
            # Check if this is a player prop
            selection_text = str(getattr(market, 'selection_text', ''))
            market_category = str(getattr(market, 'market_category', '')).lower()
            
            # Player props have player names and stat keywords
            has_stat_keyword = any(keyword in selection_text.lower() for keyword in 
                                  ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-point'])
            
            # Check if it looks like a player name (starts with capital letter, has space)
            has_player_name = bool(re.match(r'^[A-Z][a-z]+\s+[A-Z]', selection_text))
            
            if has_stat_keyword and has_player_name:
                props.append(market)
        
        logger.debug(f"  Extracted {len(props)} player props from {len(markets)} markets")
        return props

