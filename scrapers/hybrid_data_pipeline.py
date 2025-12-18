"""
Hybrid NBA Player Data Pipeline
=================================
Unified interface that combines data from multiple sources:
1. StatsMuse (primary) - Player profiles, splits, game logs
2. Databallr (supplementary) - Involve%, OnBall%, POT AST
3. Calculated metrics - USG%, TS%, AST%, Game Score

This pipeline intelligently merges data and handles fallbacks.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Import scrapers
from scrapers.statmuse_player_scraper import (
    scrape_player_profile,
    scrape_player_splits,
    PlayerProfile,
    PlayerSplitStats
)
from scrapers.databallr_scraper import get_player_game_log as databallr_get_game_log
from scrapers.advanced_metrics import calculate_all_metrics

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("hybrid_pipeline")


class HybridPlayerDataPipeline:
    """
    Consolidates player data from multiple sources with intelligent fallbacks.
    
    Priority:
    1. StatsMuse for base stats + splits (most comprehensive)
    2. Databallr for unique metrics (Involve%, OnBall%, POT AST)
    3. Calculated metrics to fill gaps
    """
    
    def __init__(
        self,
        use_cache: bool = True,
        cache_ttl_hours: int = 24,
        default_season: str = "2024-25"
    ):
        """
        Initialize hybrid pipeline.
        
        Args:
            use_cache: Whether to use caching (recommended)
            cache_ttl_hours: Cache time-to-live in hours
            default_season: Default NBA season
        """
        self.use_cache = use_cache
        self.cache_ttl_hours = cache_ttl_hours
        self.default_season = default_season
        self._cache = {}
    
    def get_player_full_profile(
        self,
        player_name: str,
        season: Optional[str] = None,
        include_databallr: bool = True,
        headless: bool = True
    ) -> Optional[Dict]:
        """
        Get complete player profile with all available data.
        
        Args:
            player_name: Player's full name (e.g., "Nikola Jokic")
            season: Season string (defaults to current season)
            include_databallr: Whether to fetch Databallr metrics
            headless: Run browser in headless mode
        
        Returns:
            Dictionary with:
            - profile: PlayerProfile object
            - splits: Dict of split stats by type
            - advanced_metrics: Calculated metrics
            - databallr_metrics: Optional Databallr metrics
            
        Example:
            >>> pipeline = HybridPlayerDataPipeline()
            >>> data = pipeline.get_player_full_profile("Nikola Jokic")
            >>> print(data['profile']['points'], data['splits']['home']['points'])
            26.4 28.2
        """
        season = season or self.default_season
        cache_key = f"{player_name}_{season}_full"
        
        # Check cache
        if self.use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            age = datetime.now() - cached_time
            ttl_delta = timedelta(hours=self.cache_ttl_hours)
            if age < ttl_delta:
                ttl_remaining = (ttl_delta - age).total_seconds() / 3600.0
                logger.debug(f"Cache hit: {player_name} ({season})")
                return cached_data
            else:
                logger.debug(f"Cache miss (expired): {player_name} ({season})")
        
        logger.debug(f"Cache miss: {player_name} ({season}), fetching...")
        
        # 1. Get base profile from StatsMuse
        profile = scrape_player_profile(player_name, season, headless)
        if not profile:
            logger.error(f"Failed to fetch profile for {player_name}")
            return None
        
        # 2. Get splits from StatsMuse
        splits_list = scrape_player_splits(player_name, season, headless)
        
        # Organize splits by type
        splits_dict = {
            'home': None,
            'road': None,
            'wins': None,
            'losses': None,
            'rest_0_days': None,
            'rest_1_day': None,
            'rest_2_plus_days': None,
            'monthly': {},
            'vs_opponent': {},
            'all': splits_list
        }
        
        for split in splits_list:
            split_type_lower = split.split_type.lower()
            split_dict = split.to_dict()
            
            if 'home' in split_type_lower and 'road' not in split_type_lower:
                splits_dict['home'] = split_dict
            elif 'road' in split_type_lower or 'away' in split_type_lower:
                splits_dict['road'] = split_dict
            elif 'win' in split_type_lower:
                splits_dict['wins'] = split_dict
            elif 'loss' in split_type_lower:
                splits_dict['losses'] = split_dict
            elif '0 days' in split_type_lower or 'b2b' in split_type_lower or 'back-to-back' in split_type_lower:
                splits_dict['rest_0_days'] = split_dict
            elif '1 day' in split_type_lower:
                splits_dict['rest_1_day'] = split_dict
            elif '2+ days' in split_type_lower or '2 days' in split_type_lower:
                splits_dict['rest_2_plus_days'] = split_dict
            elif any(month in split_type_lower for month in ['january', 'february', 'march', 'april', 'october', 'november', 'december']):
                splits_dict['monthly'][split.split_type] = split_dict
            elif 'vs' in split_type_lower:
                splits_dict['vs_opponent'][split.split_type] = split_dict
        
        # 3. Calculate advanced metrics (need profile for this)
        player_stats = profile.to_dict()
        
        # For now, calculate what we can without team stats
        # TS% and Game Score don't need team stats
        advanced_metrics = {
            'true_shooting_pct': calculate_all_metrics(player_stats)['true_shooting_pct'],
            'game_score': calculate_all_metrics(player_stats)['game_score']
        }
        
        # Note: USG%, AST%, REB% need team stats - would need to fetch those separately
        # For a complete implementation, you'd scrape team stats here
        
        # 4. Optionally get Databallr metrics
        databallr_metrics = None
        if include_databallr:
            try:
                logger.debug(f"Fetching Databallr data for {player_name}")
                # Get recent games from Databallr to extract advanced metrics
                games = databallr_get_game_log(player_name, season, last_n_games=5, use_cache=True)
                
                if games:
                    # Databallr includes Involve%, OnBall%, POT AST in game logs
                    # Average the last 5 games
                    involve_pct_list = []
                    onball_pct_list = []
                    pot_ast_list = []
                    
                    for game in games:
                        # These metrics might be in different formats depending on Databallr version
                        # Adjust based on actual databallr_scraper.py output format
                        if 'involve_pct' in game:
                            involve_pct_list.append(game['involve_pct'])
                        if 'onball_pct' in game:
                            onball_pct_list.append(game['onball_pct'])
                        if 'pot_ast' in game:
                            pot_ast_list.append(game['pot_ast'])
                    
                    databallr_metrics = {
                        'involve_pct': round(sum(involve_pct_list) / len(involve_pct_list), 1) if involve_pct_list else None,
                        'onball_pct': round(sum(onball_pct_list) / len(onball_pct_list), 1) if onball_pct_list else None,
                        'pot_ast': round(sum(pot_ast_list) / len(pot_ast_list), 1) if pot_ast_list else None,
                        'games_sampled': len(games)
                    }
                    logger.info(f"Got Databallr metrics from {len(games)} games")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch Databallr metrics: {e}")
                databallr_metrics = None
        
        # 5. Compile full profile
        full_profile = {
            'player_name': player_name,
            'season': season,
            'profile': profile.to_dict(),
            'splits': splits_dict,
            'advanced_metrics': advanced_metrics,
            'databallr_metrics': databallr_metrics,
            'last_updated': datetime.now().isoformat()
        }
        
        # Cache result
        if self.use_cache:
            self._cache[cache_key] = (full_profile, datetime.now())
        
        return full_profile
    
    def get_player_context_for_bet(
        self,
        player_name: str,
        opponent: str,
        is_home: bool,
        days_rest: int = 1,
        season: Optional[str] = None,
        headless: bool = True
    ) -> Optional[Dict]:
        """
        Get contextualized player data for a specific bet scenario.
        
        Automatically selects relevant splits based on game context.
        
        Args:
            player_name: Player's name
            opponent: Opponent team name
            is_home: Is player's team at home?
            days_rest: Days since last game (0 = back-to-back)
            season: NBA season
            headless: Run browser in headless mode
        
        Returns:
            Dict with contextualized stats and recommendations
            
        Example:
            >>> context = pipeline.get_player_context_for_bet(
            ...     "Nikola Jokic", 
            ...     "Lakers",
            ...     is_home=False,
            ...     days_rest=1
            ... )
            >>> print(context['relevant_split'])  # Shows road stats
            {'points': 27.2, 'rebounds': 13.1, ...}
        """
        season = season or self.default_season
        
        # Get full profile
        full_profile = self.get_player_full_profile(player_name, season, headless=headless)
        if not full_profile:
            return None
        
        # Select relevant split based on context
        splits = full_profile['splits']
        location_split = splits['home'] if is_home else splits['road']
        
        # Select rest split
        if days_rest == 0:
            rest_split = splits['rest_0_days']
        elif days_rest == 1:
            rest_split = splits['rest_1_day']
        else:
            rest_split = splits['rest_2_plus_days']
        
        # Look for opponent-specific split
        opponent_split = None
        for split_name, split_data in splits['vs_opponent'].items():
            if opponent.lower() in split_name.lower():
                opponent_split = split_data
                break
        
        # Compile context
        context = {
            'player_name': player_name,
            'opponent': opponent,
            'is_home': is_home,
            'days_rest': days_rest,
            'season_average': full_profile['profile'],
            'location_split': location_split,
            'rest_split': rest_split,
            'opponent_split': opponent_split,
            'advanced_metrics': full_profile['advanced_metrics'],
            'databallr_metrics': full_profile['databallr_metrics'],
            'recommendation_factors': self._generate_recommendations(
                full_profile['profile'],
                location_split,
                rest_split
            )
        }
        
        return context
    
    def _generate_recommendations(
        self,
        season_avg: Dict,
        location_split: Optional[Dict],
        rest_split: Optional[Dict]
    ) -> Dict:
        """
        Generate betting recommendations based on splits.
        
        Compares splits to season average to identify advantages/disadvantages.
        """
        recommendations = {
            'location_impact': 'neutral',
            'rest_impact': 'neutral',
            'points_adjustment': 0.0,
            'notes': []
        }
        
        # Analyze location impact
        if location_split:
            pts_diff = location_split['points'] - season_avg['points']
            if pts_diff > 2:
                recommendations['location_impact'] = 'positive'
                recommendations['points_adjustment'] += pts_diff
                recommendations['notes'].append(f"Strong in this location (+{pts_diff:.1f} PPG)")
            elif pts_diff < -2:
                recommendations['location_impact'] = 'negative'
                recommendations['points_adjustment'] += pts_diff
                recommendations['notes'].append(f"Weaker in this location ({pts_diff:.1f} PPG)")
        
        # Analyze rest impact
        if rest_split:
            pts_diff = rest_split['points'] - season_avg['points']
            if pts_diff > 1.5:
                recommendations['rest_impact'] = 'positive'
                recommendations['notes'].append(f"Performs well with this rest ({pts_diff:+.1f} PPG)")
            elif pts_diff < -1.5:
                recommendations['rest_impact'] = 'negative'
                recommendations['notes'].append(f"Struggles with this rest ({pts_diff:+.1f} PPG)")
        
        return recommendations

    def get_player_game_log(
        self,
        player_name: str,
        last_n_games: int = 20,
        season: Optional[str] = None,
        headless: bool = True,
        retries: int = 3,
        use_cache: bool = True
    ) -> Optional[List[Dict]]:
        """
        Get player game logs using DataballR (best source for detailed game-by-game data).

        This is a convenience wrapper that uses DataballR for game logs while
        the rest of the pipeline uses StatsMuse for profiles/splits.

        Args:
            player_name: Player's full name
            last_n_games: Number of recent games to fetch
            season: NBA season (e.g., "2024-25")
            headless: Run browser in headless mode
            retries: Number of retry attempts
            use_cache: Whether to use cached data

        Returns:
            List of game dictionaries with stats, or None if failed

        Example:
            >>> pipeline = HybridPlayerDataPipeline()
            >>> games = pipeline.get_player_game_log("Nikola Jokic", last_n_games=10)
            >>> print(f"Last game: {games[0]['points']} points")
        """
        season = season or self.default_season

        try:
            # Use DataballR for game logs - it's excellent for this
            logger.debug(f"Fetching game log for {player_name} (last {last_n_games} games)")
            game_log = databallr_get_game_log(
                player_name=player_name,
                season=season,
                last_n_games=last_n_games,
                use_cache=use_cache
            )

            if game_log:
                logger.info(f"Successfully fetched {len(game_log)} games for {player_name}")
            else:
                logger.warning(f"No game log data returned for {player_name}")

            return game_log

        except Exception as e:
            logger.error(f"Error fetching game log for {player_name}: {e}")
            return None


# Export main class
__all__ = ['HybridPlayerDataPipeline']


if __name__ == "__main__":
    # Demo script
    print("=" * 80)
    print("HYBRID PLAYER DATA PIPELINE - DEMO")
    print("=" * 80)
    print()
    
    pipeline = HybridPlayerDataPipeline()
    
    # Test player
    test_player = "Nikola Jokic"
    
    print(f"Fetching full profile for {test_player}...")
    print()
    
    # Get full profile
    profile = pipeline.get_player_full_profile(test_player, include_databallr=False, headless=True)
    
    if profile:
        print("✓ Profile fetched successfully")
        print()
        
        print("Season Average:")
        print(f"  {profile['profile']['points']} PPG | {profile['profile']['rebounds']} RPG | {profile['profile']['assists']} APG")
        print()
        
        print("Splits:")
        if profile['splits']['home']:
            print(f"  Home: {profile['splits']['home']['points']} PPG ({profile['splits']['home']['games_played']} GP)")
        if profile['splits']['road']:
            print(f"  Road: {profile['splits']['road']['points']} PPG ({profile['splits']['road']['games_played']} GP)")
        if profile['splits']['wins']:
            print(f"  Wins: {profile['splits']['wins']['points']} PPG")
        if profile['splits']['losses']:
            print(f"  Losses: {profile['splits']['losses']['points']} PPG")
        print()
        
        print("Advanced Metrics:")
        for metric, value in profile['advanced_metrics'].items():
            print(f"  {metric}: {value}")
        print()
        
        # Test context-aware betting
        print("=" * 80)
        print("BETTING CONTEXT EXAMPLE")
        print("=" * 80)
        print()
        
        print("Scenario: Jokic vs Lakers, on the road, 1 day rest")
        context = pipeline.get_player_context_for_bet(
            test_player,
            "Lakers",
            is_home=False,
            days_rest=1,
            headless=True
        )
        
        if context:
            print()
            print("Context:")
            print(f"  Season Average: {context['season_average']['points']} PPG")
            if context['location_split']:
                print(f"  Road Average: {context['location_split']['points']} PPG")
            
            print()
            print("Recommendations:")
            for note in context['recommendation_factors']['notes']:
                print(f"  • {note}")
            
            if context['recommendation_factors']['points_adjustment'] != 0:
                adj = context['recommendation_factors']['points_adjustment']
                print(f"  → Suggested adjustment: {adj:+.1f} points")
        
    else:
        print("✗ Failed to fetch profile")
    
    print()
    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
