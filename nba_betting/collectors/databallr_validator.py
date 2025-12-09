"""
DataBallr Validator
==================
Validates betting insights with DataBallr player/team statistics.
"""

import logging
from typing import Dict, Optional

from utils.error_handling import handle_import_error

logger = logging.getLogger(__name__)


class DataBallrValidator:
    """Validates betting insights with DataBallr player/team stats"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._init_databallr()
    
    def _init_databallr(self):
        """Initialize DataBallr scraper"""
        databallr_module = handle_import_error(
            'scrapers.databallr_scraper',
            fallback=None,
            error_message="DataBallr scraper not found"
        )
        
        if databallr_module:
            get_player_game_log = getattr(databallr_module, 'get_player_game_log', None)
            if get_player_game_log:
                self.get_player_stats = get_player_game_log
                logger.info("✓ DataBallr scraper initialized")
            else:
                logger.error("DataBallr get_player_game_log function not found")
                self.get_player_stats = None
        else:
            self.get_player_stats = None
    
    def validate_player_prop(self, player_name: str, stat_type: str, line: float, last_n_games: int = 20) -> Optional[Dict]:
        """
        Fetch player stats from DataBallr and calculate hit rate
        
        Returns:
            Dict with:
            - game_log: List of recent games
            - hit_rate: % of games over the line
            - avg_value: Average stat value
            - sample_size: Number of games
            - trend: Recent trend (improving/declining)
        """
        if not self.get_player_stats:
            return None
        
        logger.debug(f"  Validating {player_name} {stat_type} {line}+ with DataBallr...")
        
        try:
            # Fetch game log
            game_log = self.get_player_stats(
                player_name=player_name,
                last_n_games=last_n_games,
                headless=self.headless,
                use_cache=True
            )
            
            if not game_log or len(game_log) < 5:
                logger.debug(f"    Insufficient data (n={len(game_log) if game_log else 0})")
                return None
            
            # Extract stat values
            stat_values = []
            for game in game_log:
                if game.minutes >= 10:  # Only count games with significant minutes
                    value = getattr(game, stat_type, None)
                    if value is not None:
                        stat_values.append(value)
            
            if len(stat_values) < 5:
                return None
            
            # Calculate metrics
            over_count = sum(1 for v in stat_values if v > line)
            hit_rate = over_count / len(stat_values)
            avg_value = sum(stat_values) / len(stat_values)
            
            # Calculate trend (last 5 vs previous 5)
            recent_avg = sum(stat_values[:5]) / 5 if len(stat_values) >= 5 else avg_value
            previous_avg = sum(stat_values[5:10]) / 5 if len(stat_values) >= 10 else avg_value
            trend = "improving" if recent_avg > previous_avg * 1.1 else "declining" if recent_avg < previous_avg * 0.9 else "stable"
            
            return {
                'game_log': game_log,
                'hit_rate': hit_rate,
                'avg_value': avg_value,
                'sample_size': len(stat_values),
                'trend': trend,
                'recent_avg': recent_avg,
                'season_avg': avg_value
            }
            
        except Exception as e:
            logger.debug(f"    Error validating: {e}")
            return None

