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


@dataclass
class AdvancedPlayerStats:
    player_id: int
    player_name: str
    season: str
    usg_pct: float
    ts_pct: float
    pie: float
    ast_ratio: float
    ast_pct: float
    efg_pct: float
    off_rating: float
    def_rating: float
    net_rating: float


@dataclass
class AdvancedTeamStats:
    team_id: int
    team_name: str
    season: str
    pace: float
    off_rating: float
    def_rating: float
    net_rating: float
    efg_pct: float
    oreb_pct: float
    dreb_pct: float
    reb_pct: float


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


def _cache_dir() -> Path:
    return Path(__file__).parent.parent / "data" / "cache"


def _read_cache(filename: str) -> Optional[List[Dict]]:
    try:
        p = _cache_dir() / filename
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(filename: str, rows: List[Dict]) -> None:
    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception:
        pass


def get_player_game_log(
    player_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 2,
    use_cache: bool = True
) -> List[GameLogEntry]:
    """
    Get player game log - uses Databallr instead of NBA API.
    
    System uses only Databallr and Sportsbet as data sources.
    This function now delegates to Databallr scraper.
    
    Args:
        player_name: Full player name (e.g., "LeBron James")
        season: Season in format "YYYY-YY" (not used, kept for compatibility)
        last_n_games: Optional limit to last N games
        retries: Number of retry attempts
        use_cache: Whether to use cached data
    
    Returns:
        List of GameLogEntry objects, most recent first
    """
    # Use Databallr instead of NBA API (system uses only Databallr and Sportsbet)
    try:
        from scrapers.databallr_scraper import get_player_game_log as get_databallr_log
        logger.debug(f"Fetching game log for {player_name} from Databallr (NBA API disabled)")
        result = get_databallr_log(
            player_name=player_name,
            season=season,
            last_n_games=last_n_games,
            retries=retries,
            use_cache=use_cache,
            headless=True
        )
        return result if result else []
    except ImportError:
        logger.warning("Databallr scraper not available, returning empty list")
        return []
    except Exception as e:
        logger.warning(f"Error fetching from Databallr: {e}, returning empty list")
        return []
    
    # OLD NBA API CODE BELOW - DISABLED (never reached)
    # This code is kept for reference but will never execute
    return []  # Safety return
    
    # DISABLED: NBA API code removed - system uses only Databallr
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
            if use_cache:
                _write_cache(f"player_log_{player_id}_{get_season_id(season)}.json", [g.to_dict() for g in game_log])
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
                if use_cache:
                    cached = _read_cache(f"player_log_{player_id}_{get_season_id(season)}.json")
                    if cached:
                        out = []
                        for row in cached:
                            try:
                                out.append(GameLogEntry(**row))
                            except Exception:
                                continue
                        return out[:last_n_games] if last_n_games else out
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
    retries: int = 2,
    use_cache: bool = True
) -> List[GameLogEntry]:
    """
    Get team game log - DISABLED (system uses only Databallr and Sportsbet)
    
    Returns empty list - team logs not available from Databallr/Sportsbet sources.
    """
    logger.debug(f"Team game log requested for {team_name} - not available (NBA API disabled)")
    return []
    
    # DISABLED: NBA API code removed
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
            if use_cache:
                _write_cache(f"team_log_{team_id}_{get_season_id(season)}.json", [g.to_dict() for g in game_log])
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
                if use_cache:
                    cached = _read_cache(f"team_log_{team_id}_{get_season_id(season)}.json")
                    if cached:
                        out = []
                        for row in cached:
                            try:
                                out.append(GameLogEntry(**row))
                            except Exception:
                                continue
                        return out[:last_n_games] if last_n_games else out
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
    Get head-to-head matchups - DISABLED (system uses only Databallr and Sportsbet)
    
    Returns empty list - H2H matchups not available from Databallr/Sportsbet sources.
    """
    logger.debug(f"H2H matchups requested: {team1_name} vs {team2_name} - not available (NBA API disabled)")
    return []
    
    # DISABLED: NBA API code removed - system uses only Databallr and Sportsbet
    # logger.info(f"Fetching H2H matchups: {team1_name} vs {team2_name} ({season})")
    # team1_id = get_team_id(team1_name)
    # team2_id = get_team_id(team2_name)
    # ... rest of code disabled


def get_advanced_player_stats(
    player_name: str,
    season: str = "2024-25",
    retries: int = 2
) -> Optional[AdvancedPlayerStats]:
    logger.info(f"Fetching advanced player stats for {player_name} ({season})")
    player_id = get_player_id(player_name)
    if not player_id:
        logger.warning(f"Could not find player ID for {player_name}")
        return None
    for attempt in range(retries):
        try:
            _rate_limit()
            url = f"{NBA_STATS_API}/leaguedashplayerstats"
            params = {
                "Season": get_season_id(season),
                "SeasonType": "Regular Season",
                "MeasureType": "Advanced",
                "PerMode": "PerGame"
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
            rs = data.get("resultSets", [{}])[0]
            headers_list = rs.get("headers", [])
            rows = rs.get("rowSet", [])
            idx = {h: i for i, h in enumerate(headers_list)}
            target_row = None
            for row in rows:
                try:
                    if int(row[idx.get("PLAYER_ID", -1)]) == player_id:
                        target_row = row
                        break
                except Exception:
                    continue
            if not target_row:
                logger.warning("Player not found in advanced stats list")
                return None
            player_name_val = target_row[idx.get("PLAYER_NAME", 0)]
            usg_pct = float(target_row[idx.get("USG_PCT", 0)] or 0)
            ts_pct = float(target_row[idx.get("TS_PCT", 0)] or 0)
            pie = float(target_row[idx.get("PIE", 0)] or 0)
            ast_ratio = float(target_row[idx.get("AST_TO", 0)] or 0)
            ast_pct = float(target_row[idx.get("AST_PCT", 0)] or 0)
            efg_pct = float(target_row[idx.get("EFG_PCT", 0)] or 0)
            off_rating = float(target_row[idx.get("OFF_RATING", 0)] or 0)
            def_rating = float(target_row[idx.get("DEF_RATING", 0)] or 0)
            net_rating = float(target_row[idx.get("NET_RATING", 0)] or 0)
            return AdvancedPlayerStats(
                player_id=player_id,
                player_name=str(player_name_val),
                season=get_season_id(season),
                usg_pct=usg_pct,
                ts_pct=ts_pct,
                pie=pie,
                ast_ratio=ast_ratio,
                ast_pct=ast_pct,
                efg_pct=efg_pct,
                off_rating=off_rating,
                def_rating=def_rating,
                net_rating=net_rating
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching advanced stats for {player_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching advanced stats for {player_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
        except Exception as e:
            logger.error(f"Error fetching advanced player stats: {e}")
            return None
    return None


def get_advanced_team_stats(
    team_name: str,
    season: str = "2024-25",
    retries: int = 2
) -> Optional[AdvancedTeamStats]:
    logger.info(f"Fetching advanced team stats for {team_name} ({season})")
    team_id = get_team_id(team_name)
    if not team_id:
        logger.warning(f"Could not find team ID for {team_name}")
        return None
    for attempt in range(retries):
        try:
            _rate_limit()
            url = f"{NBA_STATS_API}/leaguedashteamstats"
            params = {
                "Season": get_season_id(season),
                "SeasonType": "Regular Season",
                "MeasureType": "Advanced",
                "PerMode": "PerGame"
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
            rs = data.get("resultSets", [{}])[0]
            headers_list = rs.get("headers", [])
            rows = rs.get("rowSet", [])
            idx = {h: i for i, h in enumerate(headers_list)}
            target_row = None
            for row in rows:
                try:
                    if int(row[idx.get("TEAM_ID", -1)]) == team_id:
                        target_row = row
                        break
                except Exception:
                    continue
            if not target_row:
                logger.warning("Team not found in advanced stats list")
                return None
            team_name_val = target_row[idx.get("TEAM_NAME", 0)]
            pace = float(target_row[idx.get("PACE", 0)] or 0)
            off_rating = float(target_row[idx.get("OFF_RATING", 0)] or 0)
            def_rating = float(target_row[idx.get("DEF_RATING", 0)] or 0)
            net_rating = float(target_row[idx.get("NET_RATING", 0)] or 0)
            efg_pct = float(target_row[idx.get("EFG_PCT", 0)] or 0)
            oreb_pct = float(target_row[idx.get("OREB_PCT", 0)] or 0)
            dreb_pct = float(target_row[idx.get("DREB_PCT", 0)] or 0)
            reb_pct = float(target_row[idx.get("REB_PCT", 0)] or 0)
            return AdvancedTeamStats(
                team_id=team_id,
                team_name=str(team_name_val),
                season=get_season_id(season),
                pace=pace,
                off_rating=off_rating,
                def_rating=def_rating,
                net_rating=net_rating,
                efg_pct=efg_pct,
                oreb_pct=oreb_pct,
                dreb_pct=dreb_pct,
                reb_pct=reb_pct
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching advanced stats for {team_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching advanced stats for {team_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
        except Exception as e:
            logger.error(f"Error fetching advanced team stats: {e}")
            return None
    return None


def get_opponent_defensive_context(
    opponent_team: str,
    player_position: str = "SG",
    season: str = "2024-25"
) -> Dict[str, any]:
    """
    Get opponent's defensive strength for matchup analysis.

    Uses advanced team stats to determine if opponent has strong/weak defense.
    This helps identify favorable matchups for player props.

    Args:
        opponent_team: Team name (e.g., "Lakers", "Boston Celtics")
        player_position: Position (PG, SG, SF, PF, C) - currently not position-specific
        season: NBA season

    Returns:
        Dict with:
            - def_rating: Overall defensive rating (lower = better defense)
            - pace: Team pace (possessions per 48 minutes)
            - defensive_rank: Estimated ranking (1-30, lower = better)
            - notes: Human-readable description
    """
    logger.info(f"Fetching defensive context for {opponent_team} vs {player_position} ({season})")

    # Get advanced team stats (includes def_rating and pace)
    adv_stats = get_advanced_team_stats(opponent_team, season)

    if not adv_stats:
        # No data available - return league average defaults
        logger.warning(f"No defensive stats for {opponent_team} - using league average")
        return {
            "def_rating": 110.0,  # League average defensive rating
            "pace": 100.0,  # League average pace
            "defensive_rank": 15,  # Middle of pack
            "notes": "No data - using league average"
        }

    # Categorize defense strength
    # Typical range: 105-115 (lower is better)
    if adv_stats.def_rating < 108:
        defense_quality = "Elite defense (top 10)"
    elif adv_stats.def_rating < 110:
        defense_quality = "Above average defense"
    elif adv_stats.def_rating < 112:
        defense_quality = "Average defense"
    elif adv_stats.def_rating < 114:
        defense_quality = "Below average defense"
    else:
        defense_quality = "Weak defense (bottom 10)"

    # Estimate ranking (rough approximation)
    # Best def_rating ~105, worst ~115
    # Normalize to 1-30 ranking
    defensive_rank = int((adv_stats.def_rating - 105) / 10 * 30)
    defensive_rank = max(1, min(30, defensive_rank))

    return {
        "def_rating": adv_stats.def_rating,
        "pace": adv_stats.pace,
        "defensive_rank": defensive_rank,
        "notes": f"{defense_quality} (DEF RTG: {adv_stats.def_rating:.1f}, Pace: {adv_stats.pace:.1f})"
    }


def get_player_shooting_splits(
    player_name: str,
    season: str = "2024-25",
    retries: int = 2
) -> Dict:
    logger.info(f"Fetching shooting splits for {player_name} ({season})")
    player_id = get_player_id(player_name)
    if not player_id:
        logger.warning(f"Could not find player ID for {player_name}")
        return {}
    for attempt in range(retries):
        try:
            _rate_limit()
            url = f"{NBA_STATS_API}/playerdashboardbyshootingsplits"
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
            timeout = 30 + (attempt * 10)
            if attempt > 0:
                time.sleep(2 ** attempt)
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            result = {}
            for rs in data.get("resultSets", []):
                name = rs.get("name") or rs.get("name", "")
                headers_list = rs.get("headers", [])
                rows = rs.get("rowSet", [])
                if rows:
                    result[name or "splits"] = {headers_list[i]: rows[0][i] for i in range(len(headers_list))}
            return result
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching shooting splits for {player_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return {}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching shooting splits for {player_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return {}
        except Exception as e:
            logger.error(f"Error fetching shooting splits: {e}")
            return {}
    return {}


def get_team_lineups(
    team_name: str,
    season: str = "2024-25",
    group_quantity: int = 5,
    retries: int = 2
) -> List[Dict]:
    logger.info(f"Fetching team lineups for {team_name} ({season})")
    team_id = get_team_id(team_name)
    if not team_id:
        logger.warning(f"Could not find team ID for {team_name}")
        return []
    for attempt in range(retries):
        try:
            _rate_limit()
            url = f"{NBA_STATS_API}/teamdashlineups"
            params = {
                "TeamID": team_id,
                "Season": get_season_id(season),
                "SeasonType": "Regular Season",
                "GroupQuantity": group_quantity
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
            rs = data.get("resultSets", [{}])[0]
            headers_list = rs.get("headers", [])
            rows = rs.get("rowSet", [])
            idx = {h: i for i, h in enumerate(headers_list)}
            lineups = []
            for row in rows:
                item = {h: row[i] for h, i in idx.items()}
                lineups.append(item)
            return lineups
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching lineups for {team_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching lineups for {team_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return []
        except Exception as e:
            logger.error(f"Error fetching team lineups: {e}")
            return []
    return []


def get_player_tracking(
    player_name: str,
    pt_measure_type: str = "Touches",
    season: str = "2024-25",
    retries: int = 2
) -> Dict:
    logger.info(f"Fetching player tracking for {player_name} ({pt_measure_type}, {season})")
    player_id = get_player_id(player_name)
    if not player_id:
        logger.warning(f"Could not find player ID for {player_name}")
        return {}
    for attempt in range(retries):
        try:
            _rate_limit()
            url = f"{NBA_STATS_API}/leagueplayertracking"
            params = {
                "PlayerOrTeam": "Player",
                "Season": get_season_id(season),
                "SeasonType": "Regular Season",
                "PtMeasureType": pt_measure_type
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
            rs = data.get("resultSets", [{}])[0]
            headers_list = rs.get("headers", [])
            rows = rs.get("rowSet", [])
            idx = {h: i for i, h in enumerate(headers_list)}
            for row in rows:
                try:
                    if int(row[idx.get("PLAYER_ID", -1)]) == player_id:
                        return {headers_list[i]: row[i] for i in range(len(headers_list))}
                except Exception:
                    continue
            return {}
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching player tracking for {player_name} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return {}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching player tracking for {player_name}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return {}
        except Exception as e:
            logger.error(f"Error fetching player tracking: {e}")
            return {}
    return {}


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


def compute_rolling_averages(
    game_log: List[GameLogEntry],
    windows: List[int] = [5, 10, 20],
    metrics: List[str] = ["points", "rebounds", "assists", "minutes", "three_pt_made"]
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for w in windows:
        recent = game_log[:w]
        if not recent:
            for m in metrics:
                result[f"{m}_last_{w}"] = 0.0
            continue
        for m in metrics:
            vals = [getattr(g, m) for g in recent]
            avg = sum(vals) / float(len(vals)) if vals else 0.0
            result[f"{m}_last_{w}"] = avg
    return result


def compute_home_away_splits(game_log: List[GameLogEntry]) -> Dict[str, float]:
    home = [g for g in game_log if g.home_away == "HOME"]
    away = [g for g in game_log if g.home_away == "AWAY"]
    def avg(lst: List[GameLogEntry], attr: str) -> float:
        return sum(getattr(g, attr) for g in lst) / float(len(lst)) if lst else 0.0
    return {
        "points_home": avg(home, "points"),
        "points_away": avg(away, "points"),
        "rebounds_home": avg(home, "rebounds"),
        "rebounds_away": avg(away, "rebounds"),
        "assists_home": avg(home, "assists"),
        "assists_away": avg(away, "assists"),
        "minutes_home": avg(home, "minutes"),
        "minutes_away": avg(away, "minutes")
    }


def compute_rest_features(game_log: List[GameLogEntry]) -> Dict[str, float]:
    if not game_log:
        return {
            "last_game_rest_days": 0.0,
            "is_b2b": 0.0,
            "games_last_3_days": 0.0,
            "is_3_in_4": 0.0
        }
    dates = []
    for g in game_log:
        try:
            dates.append(datetime.strptime(g.game_date, "%m/%d/%Y"))
        except Exception:
            try:
                dates.append(datetime.strptime(g.game_date, "%Y-%m-%d"))
            except Exception:
                continue
    dates.sort(reverse=True)
    last_rest = 0.0
    is_b2b = 0.0
    games_last_3 = 0.0
    is_3_in_4 = 0.0
    if len(dates) >= 2:
        delta = (dates[0] - dates[1]).days
        last_rest = float(delta)
        is_b2b = 1.0 if delta == 1 else 0.0
    cutoff = dates[0] - timedelta(days=3) if dates else datetime.now() - timedelta(days=3)
    games_last_3 = float(sum(1 for d in dates if d >= cutoff))
    if len(dates) >= 4:
        span = (dates[0] - dates[3]).days
        is_3_in_4 = 1.0 if span <= 4 else 0.0
    return {
        "last_game_rest_days": last_rest,
        "is_b2b": is_b2b,
        "games_last_3_days": games_last_3,
        "is_3_in_4": is_3_in_4
    }


def compute_matchup_pace_features(
    team_name: str,
    opponent_name: str,
    season: str = "2024-25"
) -> Dict[str, float]:
    team_adv = get_advanced_team_stats(team_name, season)
    opp_adv = get_advanced_team_stats(opponent_name, season)
    if not team_adv or not opp_adv:
        return {"team_pace": 0.0, "opponent_pace": 0.0, "tempo_diff": 0.0}
    diff = float(team_adv.pace) - float(opp_adv.pace)
    return {"team_pace": float(team_adv.pace), "opponent_pace": float(opp_adv.pace), "tempo_diff": diff}


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

