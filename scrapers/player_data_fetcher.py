"""
Player Data Fetcher
===================
Fetches player game logs with priority: StatsMuse → DataballR → Inference.

This module provides a clean interface for fetching player game logs without
any dependencies on external APIs that don't work.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Optional
from datetime import datetime
import logging

from scrapers.data_models import GameLogEntry

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("player_data_fetcher")

# Fix #4: Per-run in-memory session cache to prevent duplicate scraping
_session_cache = {}  # {(player_name, season): game_log}


def get_player_game_log(
    player_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 2,
    use_cache: bool = True
) -> List[GameLogEntry]:
    """
    Get player game log - Priority: StatsMuse → DataballR → Inference.
    
    Data Priority (with confidence):
    1. StatsMuse (primary): confidence = 0.85
    2. DataballR (secondary): confidence = 0.90
    3. Inference (fallback): confidence = 0.60
    
    Args:
        player_name: Full player name (e.g., "LeBron James")
        season: Season in format "YYYY-YY"
        last_n_games: Optional limit to last N games
        retries: Number of retry attempts
        use_cache: Whether to use cached data
    
    Returns:
        List of GameLogEntry objects, most recent first
    """
    # Fix #1: Check per-run session cache FIRST (before any HTTP calls or SQLite checks)
    session_cache_key = (player_name, season)
    if session_cache_key in _session_cache:
        logger.debug(f"Session cache hit: {player_name} ({season})")
        cached_log = _session_cache[session_cache_key]
        if last_n_games:
            return cached_log[:last_n_games]
        return cached_log
    
    # Check persistent SQLite cache BEFORE any HTTP calls
    if use_cache:
        try:
            from scrapers.data_cache import get_cache
            from scrapers.data_models import GameLogEntry
            
            cache = get_cache()
            cached_games = cache.get_game_log(player_name, season)
            
            if cached_games:
                # Convert dicts back to GameLogEntry objects
                game_log_entries = []
                for game_dict in cached_games:
                    try:
                        entry = GameLogEntry(**game_dict)
                        game_log_entries.append(entry)
                    except Exception as e:
                        logger.debug(f"[CACHE] Error converting cached game entry: {e}")
                        continue
                
                if game_log_entries:
                    logger.debug(f"Cache hit: {player_name} ({season}), {len(game_log_entries)} games")
                    # Store in session cache for this run
                    _session_cache[session_cache_key] = game_log_entries
                    result = game_log_entries[:last_n_games] if last_n_games else game_log_entries
                    return result
        except Exception as e:
            logger.debug(f"[CACHE] Cache check failed: {e}, proceeding with scrape")
    
    # 1. Try StatsMuse FIRST (primary source)
    try:
        from scrapers.statmuse_player_scraper import scrape_player_game_log
        
        logger.debug(f"[STATSMUSE] Fetching game log for {player_name} (primary)")
        statmuse_logs = scrape_player_game_log(player_name, season=season, headless=True)
        
        if statmuse_logs and len(statmuse_logs) > 0:
            # Convert StatMuse PlayerGameLog to GameLogEntry format
            game_log_entries = []
            for log in statmuse_logs[:last_n_games] if last_n_games else statmuse_logs:
                # Create GameLogEntry from StatMuse data
                try:
                    # Parse date - GameLogEntry.game_date is a string, so keep as string
                    date_str = log.date
                    # Try to parse and validate, but keep as string for GameLogEntry
                    try:
                        # Try parsing to validate, then convert back to string in standard format
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                        game_date_str = parsed_date.strftime('%Y-%m-%d')
                    except:
                        try:
                            parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
                            game_date_str = parsed_date.strftime('%Y-%m-%d')
                        except:
                            # Use today's date as fallback
                            game_date_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # Create GameLogEntry (match GameLogEntry dataclass structure)
                    won = False
                    if hasattr(log, 'win_loss'):
                        won = log.win_loss == "W" or log.win_loss == "Win"
                    
                    # Create matchup string
                    matchup_str = f"{log.opponent or 'Unknown'}"
                    if log.home_away == "HOME":
                        matchup_str = f"vs {matchup_str}"
                    else:
                        matchup_str = f"@ {matchup_str}"
                    
                    entry = GameLogEntry(
                        game_date=game_date_str,  # string in YYYY-MM-DD format
                        game_id="",  # Not available from StatMuse
                        matchup=matchup_str,
                        home_away=log.home_away or "HOME",
                        opponent=log.opponent or "Unknown",
                        opponent_id=0,  # Not available from StatMuse
                        won=won,
                        points=int(log.points) if log.points else 0,
                        rebounds=int(log.rebounds) if log.rebounds else 0,
                        assists=int(log.assists) if log.assists else 0,
                        steals=int(log.steals) if log.steals else 0,
                        blocks=int(log.blocks) if log.blocks else 0,
                        turnovers=int(log.turnovers) if log.turnovers else 0,
                        minutes=float(log.minutes) if log.minutes else 0.0,
                        fg_made=int(log.fg_made) if log.fg_made else 0,
                        fg_attempted=int(log.fg_attempted) if log.fg_attempted else 0,
                        three_pt_made=int(log.three_made) if log.three_made else 0,
                        three_pt_attempted=int(log.three_attempted) if log.three_attempted else 0,
                        ft_made=int(log.ft_made) if log.ft_made else 0,
                        ft_attempted=int(log.ft_attempted) if log.ft_attempted else 0,
                        plus_minus=int(log.plus_minus) if hasattr(log, 'plus_minus') and log.plus_minus else 0,
                        team_points=0,  # Not available from StatMuse player logs
                        opponent_points=0,  # Not available from StatMuse player logs
                        total_points=0  # Not available from StatMuse player logs
                    )
                    game_log_entries.append(entry)
                except Exception as e:
                    logger.debug(f"[STATSMUSE] Error converting log entry: {e}")
                    continue
            
            if game_log_entries:
                logger.debug(f"StatsMuse: {len(game_log_entries)} games for {player_name}")
                # Store in session cache using (player_name, season) key
                _session_cache[session_cache_key] = game_log_entries
                
                # Store in persistent cache
                if use_cache:
                    try:
                        from scrapers.data_cache import get_cache
                        cache = get_cache()
                        # Try to get team from first game log entry, or use "N/A"
                        team = "N/A"
                        if game_log_entries and hasattr(game_log_entries[0], 'matchup'):
                            # Extract team from matchup if possible
                            pass  # Keep as "N/A" for now
                        cache.set_game_log(
                            player_name=player_name,
                            season=season,
                            game_logs=game_log_entries,
                            source='statsmuse',
                            confidence_score=0.85,
                            team=team
                        )
                    except Exception as e:
                        logger.debug(f"[CACHE] Failed to store game log in persistent cache: {e}")
                
                result = game_log_entries[:last_n_games] if last_n_games else game_log_entries
                return result
                
    except Exception as e:
        logger.debug(f"[STATSMUSE] Failed for {player_name}: {e}")
    
    # 2. Try DataballR SECONDARY (fallback)
    try:
        from scrapers.databallr_robust.integration import get_player_game_log as get_databallr_log
        
        logger.debug(f"[DATABALLR] Fetching game log for {player_name} (secondary)")
        result = get_databallr_log(
            player_name=player_name,
            season=season,
            last_n_games=last_n_games,
            retries=retries,
            use_cache=use_cache,
            headless=True
        )
        
        if result and len(result) > 0:
            logger.debug(f"DataballR: {len(result)} games for {player_name}")
            # Store in session cache
            _session_cache[session_cache_key] = result
            
            # Store in persistent cache
            if use_cache:
                try:
                    from scrapers.data_cache import get_cache
                    cache = get_cache()
                    cache.set_game_log(
                        player_name=player_name,
                        season=season,
                        game_logs=result,
                        source='databallr',
                        confidence_score=0.90,
                        team="N/A"
                    )
                except Exception as e:
                    logger.debug(f"[CACHE] Failed to store game log in persistent cache: {e}")
            
            return_result = result[:last_n_games] if last_n_games else result
            return return_result
            
    except Exception as e:
        logger.debug(f"[DATABALLR] Failed for {player_name}: {e}")
    
    # 3. Try original DataballR scraper as final fallback
    try:
        from scrapers.databallr_scraper import get_player_game_log as get_databallr_log_old
        
        logger.debug(f"[DATABALLR-OLD] Fetching game log for {player_name} (fallback)")
        result = get_databallr_log_old(
            player_name=player_name,
            season=season,
            last_n_games=last_n_games,
            retries=retries,
            use_cache=use_cache,
            headless=True
        )
        
        if result and len(result) > 0:
            logger.debug(f"DataballR (old): {len(result)} games for {player_name}")
            # Store in session cache using (player_name, season) key
            _session_cache[session_cache_key] = result
            
            # Store in persistent cache
            if use_cache:
                try:
                    from scrapers.data_cache import get_cache
                    cache = get_cache()
                    cache.set_game_log(
                        player_name=player_name,
                        season=season,
                        game_logs=result,
                        source='databallr',
                        confidence_score=0.90,
                        team="N/A"
                    )
                except Exception as e:
                    logger.debug(f"[CACHE] Failed to store game log in persistent cache: {e}")
            
            return_result = result[:last_n_games] if last_n_games else result
            return return_result
            
    except Exception as e:
        logger.debug(f"[DATABALLR-OLD] Failed for {player_name}: {e}")
    
    logger.warning(f"[DATA] No game log found for {player_name} from any source (StatsMuse, DataballR)")
    return []
