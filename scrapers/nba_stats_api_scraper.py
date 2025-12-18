"""
Legacy Utility Functions
========================
Minimal utility functions kept for backward compatibility.

These functions are deprecated stubs that return empty results.
Team game logs and H2H matchups are not available from current data sources
(StatsMuse/DataballR). New code should use player_data_fetcher for player logs.

The calculate_trend_from_game_log function is a pure utility that processes
GameLogEntry objects and has no external dependencies.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Optional, Tuple
import logging

from scrapers.data_models import GameLogEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("legacy_utils")


def get_team_game_log(
    team_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 2,
    use_cache: bool = True
) -> List[GameLogEntry]:
    """
    Get team game log - DISABLED (not available from current data sources)
    
    Team game logs are not available from StatsMuse/DataballR sources.
    Returns empty list.
    
    Returns:
        Empty list
    """
    logger.debug(f"Team game log requested for {team_name} - not available from current data sources")
    return []


def get_h2h_matchups(
    team1_name: str,
    team2_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None
) -> List[GameLogEntry]:
    """
    Get head-to-head matchups - DISABLED (not available from current data sources)
    
    H2H matchups are not available from StatsMuse/DataballR sources.
    Returns empty list.

    Returns:
        Empty list
    """
    logger.debug(f"H2H matchups requested: {team1_name} vs {team2_name} - not available from current data sources")
    return []


def calculate_trend_from_game_log(
    game_log: List[GameLogEntry],
    stat_type: str,
    threshold: float,
    filter_func: Optional[callable] = None
) -> Tuple[List[int], int]:
    """
    Calculate trend outcomes from game log.
    
    Pure utility function that processes GameLogEntry objects.
    No external API calls or dependencies.
    
    Args:
        game_log: List of GameLogEntry objects
        stat_type: "points", "rebounds", "assists", "total_points", "won", etc.
        threshold: Threshold value (e.g., 10 for "10+ points")
        filter_func: Optional function to filter games (e.g., lambda g: g.home_away == "HOME")
    
    Returns:
        (outcomes, sample_size) where outcomes is list of 1s (success) and 0s (failure)
    """
    if filter_func:
        filtered_log = [g for g in game_log if filter_func(g)]
    else:
        filtered_log = game_log
    
    outcomes = []
    for game in filtered_log:
        success = False
        
        if stat_type == "points":
            success = game.points >= threshold
        elif stat_type == "rebounds":
            success = game.rebounds >= threshold
        elif stat_type == "assists":
            success = game.assists >= threshold
        elif stat_type == "total_points":
            success = game.total_points >= threshold
        elif stat_type == "won":
            success = game.won
        elif stat_type == "lost":
            success = not game.won
        else:
            continue
        
        outcomes.append(1 if success else 0)
    
    return (outcomes, len(outcomes))
