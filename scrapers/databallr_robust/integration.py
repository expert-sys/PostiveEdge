"""
Integration Wrapper
===================
Provides compatibility with existing databallr_scraper.py interface.
"""

import logging
from typing import List, Optional
from pathlib import Path

from .databallr.players import DataballrPlayerScraper

# Import GameLogEntry for compatibility
try:
    from scrapers.nba_stats_api_scraper import GameLogEntry
except ImportError:
    from nba_stats_api_scraper import GameLogEntry

logger = logging.getLogger(__name__)


def get_player_game_log(
    player_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 3,
    use_cache: bool = True,
    headless: bool = True
) -> List[GameLogEntry]:
    """
    Get player game log from DataballR (compatible with existing interface).
    
    This is a drop-in replacement for the original get_player_game_log function.
    
    Args:
        player_name: Player name
        season: Season string (not used, kept for compatibility)
        last_n_games: Number of games to fetch (default: 20)
        retries: Number of retry attempts
        use_cache: Whether to use cached data (not implemented yet)
        headless: Run browser in headless mode
    
    Returns:
        List of GameLogEntry objects
    """
    if last_n_games is None:
        last_n_games = 20
    
    logger.info(f"[DataballR Robust] Fetching {last_n_games} games for {player_name}")
    
    # Initialize scraper
    scraper = DataballrPlayerScraper(headless=headless)
    
    try:
        # Get game log
        games = scraper.get_player_game_log(player_name, last_n_games=last_n_games, retries=retries)
        
        # Convert to GameLogEntry format
        game_log_entries = []
        for game in games:
            entry = _convert_to_game_log_entry(game, player_name)
            if entry:
                game_log_entries.append(entry)
        
        logger.info(f"✓ [DataballR Robust] Retrieved {len(game_log_entries)} games for {player_name}")
        return game_log_entries
        
    except Exception as e:
        logger.error(f"[DataballR Robust] Failed to get game log for {player_name}: {e}")
        return []
    finally:
        # Cleanup handled by Playwright context manager
        pass


def _convert_to_game_log_entry(game: dict, player_name: str) -> Optional[GameLogEntry]:
    """Convert game dict to GameLogEntry"""
    try:
        date_str = game.get('date', 'Unknown')
        game_id = f"DB_{date_str.replace('/', '').replace('-', '')}_{player_name.replace(' ', '_')}"
        
        return GameLogEntry(
            game_date=date_str,
            game_id=game_id,
            matchup=f"{player_name} vs Unknown",
            home_away="UNKNOWN",
            opponent="Unknown",
            opponent_id=0,
            won=False,
            minutes=game.get('minutes', 0.0),
            points=game.get('points', 0),
            rebounds=game.get('rebounds', 0),
            assists=game.get('assists', 0),
            steals=game.get('steals', 0),
            blocks=game.get('blocks', 0),
            turnovers=game.get('turnovers', 0),
            fg_made=game.get('fg_made', 0),
            fg_attempted=game.get('fg_attempted', 0),
            three_pt_made=game.get('three_pt_made', 0),
            three_pt_attempted=0,
            ft_made=0,
            ft_attempted=game.get('fta', 0),
            plus_minus=game.get('plus_minus', 0),
            team_points=0,
            opponent_points=0,
            total_points=0
        )
    except Exception as e:
        logger.debug(f"Failed to convert game to GameLogEntry: {e}")
        return None

