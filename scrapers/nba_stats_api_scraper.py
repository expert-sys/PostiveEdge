"""
NBA Stats API Scraper
=====================
Scrapes historical player and team statistics from stats.nba.com API endpoints.

Uses the official NBA stats API to get:
- Player game logs (points, rebounds, assists, etc.)
- Team game logs (points for/against, pace, etc.)
- Head-to-head matchups
- Situational splits (home/away, vs conference, etc.)

Usage:
  from nba_stats_api_scraper import get_player_game_log, get_team_game_log, get_h2h_matchups
  player_log = get_player_game_log("LeBron James", season="2024-25")
  team_log = get_team_game_log("Lakers", season="2024-25")
  h2h = get_h2h_matchups("Lakers", "Celtics", season="2024-25")
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import time
from threading import Lock

# Rate limiting lock
_rate_limit_lock = Lock()
_last_request_time = 0
_min_request_interval = 0.5  # Minimum 0.5 seconds between requests

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("nba_stats_api")

# Initialize player cache on import
try:
    from scrapers.nba_player_cache import initialize_cache
    initialize_cache()
except ImportError:
    pass  # Cache module optional

# NBA.com API base URL
NBA_STATS_API = "https://stats.nba.com/stats"

# Team name to ID mapping
TEAM_IDS = {
    "Atlanta Hawks": 1610612737, "Boston Celtics": 1610612738, "Brooklyn Nets": 1610612751,
    "Charlotte Hornets": 1610612766, "Chicago Bulls": 1610612741, "Cleveland Cavaliers": 1610612739,
    "Dallas Mavericks": 1610612742, "Denver Nuggets": 1610612743, "Detroit Pistons": 1610612765,
    "Golden State Warriors": 1610612744, "Houston Rockets": 1610612745, "Indiana Pacers": 1610612754,
    "LA Clippers": 1610612746, "Los Angeles Clippers": 1610612746, "Los Angeles Lakers": 1610612747,
    "Memphis Grizzlies": 1610612763, "Miami Heat": 1610612748, "Milwaukee Bucks": 1610612749,
    "Minnesota Timberwolves": 1610612750, "New Orleans Pelicans": 1610612740, "New York Knicks": 1610612752,
    "Oklahoma City Thunder": 1610612760, "Orlando Magic": 1610612753, "Philadelphia 76ers": 1610612755,
    "Phoenix Suns": 1610612756, "Portland Trail Blazers": 1610612757, "Sacramento Kings": 1610612758,
    "San Antonio Spurs": 1610612759, "Toronto Raptors": 1610612761, "Utah Jazz": 1610612762,
    "Washington Wizards": 1610612764
}

# Team abbreviations for matching
TEAM_ABBREVIATIONS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans", "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "WAS": "Washington Wizards"
}


@dataclass
class GameLogEntry:
    """Single game entry from game log"""
    game_date: str
    game_id: str
    matchup: str  # "LAL vs. BOS" or "LAL @ BOS"
    home_away: str  # "HOME" or "AWAY"
    opponent: str
    opponent_id: int
    won: bool
    minutes: float
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    fg_made: int
    fg_attempted: int
    three_pt_made: int
    three_pt_attempted: int
    ft_made: int
    ft_attempted: int
    plus_minus: int
    team_points: int  # For team logs
    opponent_points: int  # For team logs
    total_points: int  # team_points + opponent_points
    
    def to_dict(self):
        return asdict(self)


def get_season_id(season: str) -> str:
    """Convert season string to NBA API season ID"""
    # "2024-25" -> "2024-25"
    # "2024" -> "2024-25"
    if len(season) == 4:
        next_year = str(int(season) + 1)[-2:]
        return f"{season}-{next_year}"
    return season


def _rate_limit():
    """Enforce rate limiting between API requests"""
    global _last_request_time
    with _rate_limit_lock:
        current_time = time.time()
        time_since_last = current_time - _last_request_time
        if time_since_last < _min_request_interval:
            time.sleep(_min_request_interval - time_since_last)
        _last_request_time = time.time()


def get_player_id(player_name: str) -> Optional[int]:
    """
    Get player ID from local cache (no API calls)
    
    Uses the PlayerIDCache which:
    - Downloads full player list once per day
    - Normalizes names for consistent matching
    - Supports fuzzy matching
    - Uses manual overrides
    
    Args:
        player_name: Player name in any format
    
    Returns:
        Player ID or None if not found
    """
    try:
        from scrapers.nba_player_cache import get_player_cache
        cache = get_player_cache()
        return cache.get_player_id(player_name)
    except ImportError:
        # Fallback if cache module not available
        logger.warning("Player cache module not available, falling back to API")
        return None
    except Exception as e:
        logger.error(f"Error getting player ID from cache: {e}")
        return None


def get_team_id(team_name: str) -> Optional[int]:
    """Get team ID from team name"""
    # Try direct lookup
    if team_name in TEAM_IDS:
        return TEAM_IDS[team_name]
    
    # Try abbreviation
    team_upper = team_name.upper()
    if team_upper in TEAM_ABBREVIATIONS:
        full_name = TEAM_ABBREVIATIONS[team_upper]
        return TEAM_IDS.get(full_name)
    
    # Try partial match
    team_lower = team_name.lower()
    for full_name, team_id in TEAM_IDS.items():
        if team_lower in full_name.lower() or full_name.lower() in team_lower:
            return team_id
    
    return None


def get_player_game_log(
    player_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 2
) -> List[GameLogEntry]:
    """
    Get player game log from NBA.com API
    
    Args:
        player_name: Full player name (e.g., "LeBron James")
        season: Season in format "YYYY-YY"
        last_n_games: Optional limit to last N games
        retries: Number of retry attempts (only for network errors)
    
    Returns:
        List of GameLogEntry objects, most recent first
    """
    logger.info(f"Fetching game log for {player_name} ({season})")
    
    # Get player ID from cache (no API call, no retries needed)
    player_id = get_player_id(player_name)
    if not player_id:
        logger.warning(f"Could not find player ID for {player_name}")
        return []  # Logical failure - don't retry
    
    # Only retry on network errors, not logical failures
    for attempt in range(retries):
        try:
            # Rate limit
            _rate_limit()
            
            url = f"{NBA_STATS_API}/playergamelog"
            params = {
                "PlayerID": player_id,
                "Season": get_season_id(season),
                "SeasonType": "Regular Season"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.nba.com/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.nba.com"
            }
            
            # Increase timeout
            timeout = 30 + (attempt * 10)
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            result_set = data.get("resultSets", [{}])[0]
            headers_list = result_set.get("headers", [])
            rows = result_set.get("rowSet", [])
            
            game_log = []
            for row in rows:
                try:
                    entry = parse_player_game_log_row(row, headers_list)
                    if entry:
                        game_log.append(entry)
                except Exception as e:
                    logger.debug(f"Error parsing game log row: {e}")
                    continue
            
            # Sort by date (most recent first)
            game_log.sort(key=lambda x: x.game_date, reverse=True)
            
            # Limit to last N games if specified
            if last_n_games:
                game_log = game_log[:last_n_games]
            
            logger.info(f"Retrieved {len(game_log)} games for {player_name}")
            return game_log
            
        except requests.exceptions.Timeout:
            # Network timeout - retry
            logger.warning(f"Timeout fetching game log for {player_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch game log for {player_name} after {retries} attempts")
                return []
        except requests.exceptions.RequestException as e:
            # Network error - retry
            logger.warning(f"Request error fetching game log for {player_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch game log for {player_name} after {retries} attempts")
                return []
        except (KeyError, IndexError, ValueError) as e:
            # Logical error (bad response format) - don't retry
            logger.error(f"Error parsing game log response for {player_name}: {e}")
            return []
        except Exception as e:
            # Unknown error - don't retry
            logger.error(f"Error fetching player game log: {e}")
            return []
    
    return []


def get_team_game_log(
    team_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 2
) -> List[GameLogEntry]:
    """
    Get team game log from NBA.com API
    
    Args:
        team_name: Team name (e.g., "Lakers", "Los Angeles Lakers")
        season: Season in format "YYYY-YY"
        last_n_games: Optional limit to last N games
    
    Returns:
        List of GameLogEntry objects, most recent first
    """
    logger.info(f"Fetching game log for {team_name} ({season})")
    
    team_id = get_team_id(team_name)
    if not team_id:
        logger.warning(f"Could not find team ID for {team_name}")
        return []
    
    for attempt in range(retries):
        try:
            # Rate limit
            _rate_limit()
            
            url = f"{NBA_STATS_API}/teamgamelog"
            params = {
                "TeamID": team_id,
                "Season": get_season_id(season),
                "SeasonType": "Regular Season"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.nba.com/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.nba.com"
            }
            
            timeout = 30 + (attempt * 10)
            if attempt > 0:
                time.sleep(2 ** attempt)
            
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            result_set = data.get("resultSets", [{}])[0]
            headers_list = result_set.get("headers", [])
            rows = result_set.get("rowSet", [])
            
            game_log = []
            for row in rows:
                try:
                    entry = parse_team_game_log_row(row, headers_list, team_id)
                    if entry:
                        game_log.append(entry)
                except Exception as e:
                    logger.debug(f"Error parsing game log row: {e}")
                    continue
            
            # Sort by date (most recent first)
            game_log.sort(key=lambda x: x.game_date, reverse=True)
            
            # Limit to last N games if specified
            if last_n_games:
                game_log = game_log[:last_n_games]
            
            logger.info(f"Retrieved {len(game_log)} games for {team_name}")
            return game_log
            
        except requests.exceptions.Timeout:
            # Network timeout - retry
            logger.warning(f"Timeout fetching team game log for {team_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch team game log for {team_name} after {retries} attempts")
                return []
        except requests.exceptions.RequestException as e:
            # Network error - retry
            logger.warning(f"Request error fetching team game log for {team_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch team game log for {team_name} after {retries} attempts")
                return []
        except (KeyError, IndexError, ValueError) as e:
            # Logical error (bad response format) - don't retry
            logger.error(f"Error parsing team game log response for {team_name}: {e}")
            return []
        except Exception as e:
            # Unknown error - don't retry
            logger.error(f"Error fetching team game log: {e}")
            return []
    
    return []


def get_h2h_matchups(
    team1_name: str,
    team2_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None
) -> List[GameLogEntry]:
    """
    Get head-to-head matchups between two teams
    
    Args:
        team1_name: First team name
        team2_name: Second team name
        season: Season in format "YYYY-YY"
        last_n_games: Optional limit to last N games
    
    Returns:
        List of GameLogEntry objects from team1's perspective
    """
    logger.info(f"Fetching H2H matchups: {team1_name} vs {team2_name} ({season})")
    
    team1_id = get_team_id(team1_name)
    team2_id = get_team_id(team2_name)
    
    if not team1_id or not team2_id:
        logger.warning(f"Could not find team IDs")
        return []
    
    # Get team1's game log and filter for games vs team2
    team1_log = get_team_game_log(team1_name, season)
    h2h_games = [game for game in team1_log if game.opponent_id == team2_id]
    
    # Sort by date (most recent first)
    h2h_games.sort(key=lambda x: x.game_date, reverse=True)
    
    # Limit to last N games if specified
    if last_n_games:
        h2h_games = h2h_games[:last_n_games]
    
    logger.info(f"Found {len(h2h_games)} H2H games")
    return h2h_games


def parse_player_game_log_row(row: List, headers: List[str]) -> Optional[GameLogEntry]:
    """Parse a single row from player game log"""
    try:
        # Create mapping from headers to indices
        header_map = {h: i for i, h in enumerate(headers)}
        
        # Extract data
        game_date = row[header_map.get("GAME_DATE", 0)]
        game_id = str(row[header_map.get("Game_ID", 1)])
        matchup = row[header_map.get("MATCHUP", 2)]
        
        # Parse matchup (e.g., "LAL vs. BOS" or "LAL @ BOS")
        if "@" in matchup:
            home_away = "AWAY"
            opponent = matchup.split("@")[1].strip()
        else:
            home_away = "HOME"
            opponent = matchup.split("vs.")[1].strip() if "vs." in matchup else matchup.split("VS")[1].strip()
        
        # Get opponent ID
        opponent_id = get_team_id(opponent) or 0
        
        # Win/Loss
        wl = row[header_map.get("WL", 3)]
        won = wl == "W"
        
        # Minutes
        min_str = row[header_map.get("MIN", 4)]
        minutes = parse_minutes(min_str)
        
        # Stats
        points = int(row[header_map.get("PTS", 5)])
        rebounds = int(row[header_map.get("REB", 6)])
        assists = int(row[header_map.get("AST", 7)])
        steals = int(row[header_map.get("STL", 8)])
        blocks = int(row[header_map.get("BLK", 9)])
        turnovers = int(row[header_map.get("TOV", 10)])
        
        # Shooting
        fg_made = int(row[header_map.get("FGM", 11)])
        fg_attempted = int(row[header_map.get("FGA", 12)])
        three_pt_made = int(row[header_map.get("FG3M", 13)])
        three_pt_attempted = int(row[header_map.get("FG3A", 14)])
        ft_made = int(row[header_map.get("FTM", 15)])
        ft_attempted = int(row[header_map.get("FTA", 16)])
        
        # Plus/minus
        plus_minus = int(row[header_map.get("PLUS_MINUS", 17)])
        
        # For player logs, we don't have team/opponent points directly
        # Would need to fetch from box score if needed
        team_points = 0
        opponent_points = 0
        total_points = 0
        
        return GameLogEntry(
            game_date=game_date,
            game_id=game_id,
            matchup=matchup,
            home_away=home_away,
            opponent=opponent,
            opponent_id=opponent_id,
            won=won,
            minutes=minutes,
            points=points,
            rebounds=rebounds,
            assists=assists,
            steals=steals,
            blocks=blocks,
            turnovers=turnovers,
            fg_made=fg_made,
            fg_attempted=fg_attempted,
            three_pt_made=three_pt_made,
            three_pt_attempted=three_pt_attempted,
            ft_made=ft_made,
            ft_attempted=ft_attempted,
            plus_minus=plus_minus,
            team_points=team_points,
            opponent_points=opponent_points,
            total_points=total_points
        )
    except Exception as e:
        logger.debug(f"Error parsing player game log row: {e}")
        return None


def parse_team_game_log_row(row: List, headers: List[str], team_id: int) -> Optional[GameLogEntry]:
    """Parse a single row from team game log"""
    try:
        header_map = {h: i for i, h in enumerate(headers)}
        
        game_date = row[header_map.get("GAME_DATE", 0)]
        game_id = str(row[header_map.get("Game_ID", 1)])
        matchup = row[header_map.get("MATCHUP", 2)]
        
        # Parse matchup
        if "@" in matchup:
            home_away = "AWAY"
            opponent = matchup.split("@")[1].strip()
        else:
            home_away = "HOME"
            opponent = matchup.split("vs.")[1].strip() if "vs." in matchup else matchup.split("VS")[1].strip()
        
        opponent_id = get_team_id(opponent) or 0
        
        # Win/Loss
        wl = row[header_map.get("WL", 3)]
        won = wl == "W"
        
        # Team points
        team_points = int(row[header_map.get("PTS", 4)])
        
        # Opponent points (would need to fetch from box score or use different endpoint)
        # For now, estimate from margin if available
        margin = int(row[header_map.get("PLUS_MINUS", 5)]) if "PLUS_MINUS" in header_map else 0
        opponent_points = team_points - margin if won else team_points + abs(margin)
        total_points = team_points + opponent_points
        
        # Player stats don't apply to team logs
        return GameLogEntry(
            game_date=game_date,
            game_id=game_id,
            matchup=matchup,
            home_away=home_away,
            opponent=opponent,
            opponent_id=opponent_id,
            won=won,
            minutes=0.0,
            points=0,
            rebounds=0,
            assists=0,
            steals=0,
            blocks=0,
            turnovers=0,
            fg_made=0,
            fg_attempted=0,
            three_pt_made=0,
            three_pt_attempted=0,
            ft_made=0,
            ft_attempted=0,
            plus_minus=margin,
            team_points=team_points,
            opponent_points=opponent_points,
            total_points=total_points
        )
    except Exception as e:
        logger.debug(f"Error parsing team game log row: {e}")
        return None


def parse_minutes(min_str: str) -> float:
    """Parse minutes from "MM:SS" format to float"""
    try:
        if ":" in min_str:
            parts = min_str.split(":")
            return float(parts[0]) + float(parts[1]) / 60.0
        return float(min_str)
    except:
        return 0.0


def calculate_trend_from_game_log(
    game_log: List[GameLogEntry],
    stat_type: str,
    threshold: float,
    filter_func: Optional[callable] = None
) -> Tuple[List[int], int]:
    """
    Calculate trend outcomes from game log
    
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


if __name__ == "__main__":
    # Test the scraper
    print("\n" + "="*70)
    print("  NBA STATS API SCRAPER TEST")
    print("="*70 + "\n")
    
    # Test player game log
    print("Testing player game log...")
    player_log = get_player_game_log("LeBron James", season="2024-25", last_n_games=10)
    if player_log:
        print(f"✓ Retrieved {len(player_log)} games")
        print(f"  Most recent: {player_log[0].game_date} - {player_log[0].points} pts, {player_log[0].rebounds} reb")
        
        # Test trend calculation
        outcomes, n = calculate_trend_from_game_log(player_log, "points", 20.0)
        print(f"  Games with 20+ points: {sum(outcomes)}/{n}")
    else:
        print("✗ Could not retrieve player game log")
    
    print()
    
    # Test team game log
    print("Testing team game log...")
    team_log = get_team_game_log("Lakers", season="2024-25", last_n_games=10)
    if team_log:
        print(f"✓ Retrieved {len(team_log)} games")
        print(f"  Most recent: {team_log[0].game_date} - {'W' if team_log[0].won else 'L'} vs {team_log[0].opponent}")
        
        # Test trend calculation
        outcomes, n = calculate_trend_from_game_log(team_log, "won", 1.0)
        print(f"  Wins: {sum(outcomes)}/{n}")
    else:
        print("✗ Could not retrieve team game log")
    
    print()
    
    # Test H2H
    print("Testing H2H matchups...")
    h2h = get_h2h_matchups("Lakers", "Celtics", season="2024-25")
    if h2h:
        print(f"✓ Retrieved {len(h2h)} H2H games")
        wins = sum(1 for g in h2h if g.won)
        print(f"  Lakers record: {wins}-{len(h2h)-wins}")
    else:
        print("✗ Could not retrieve H2H matchups")

