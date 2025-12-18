"""
NBA Trend Calculator
====================
Calculates trends from game log data (StatsMuse/DataballR sources) instead of relying on Sportsbet insights.

This module:
1. Parses Sportsbet insights to determine what trend to calculate
2. Fetches actual game logs from StatsMuse/DataballR sources
3. Calculates the trend from real data
4. Returns outcomes in the format expected by the value engine

Note: Team game logs and H2H matchups are not available from current data sources
and will return empty results.

Usage:
  from nba_trend_calculator import calculate_trend_from_insight
  outcomes, n = calculate_trend_from_insight(insight_dict)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from scrapers.player_data_fetcher import get_player_game_log
from scrapers.data_models import GameLogEntry
# Note: get_team_game_log and get_h2h_matchups are disabled (return empty lists)
# These functions are not available from StatMuse/DataballR sources
# Code should handle empty results gracefully
from scrapers.nba_stats_api_scraper import get_team_game_log, get_h2h_matchups, calculate_trend_from_game_log
import logging

# Initialize player cache on import
try:
    from scrapers.nba_player_cache import initialize_cache
    initialize_cache()
except ImportError:
    pass  # Cache module optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nba_trend_calculator")


def parse_insight_for_trend(insight: Dict) -> Optional[Dict]:
    """
    Parse a Sportsbet insight to determine what trend to calculate from NBA.com data
    
    Returns:
        Dict with keys: type, entity, stat_type, threshold, filter_type, opponent
        or None if can't parse
    """
    fact = insight.get('fact', '').lower()
    market = insight.get('market', '').lower()
    result = insight.get('result', '')
    
    # Pattern 1: Player prop trends
    # "Player X has scored 20+ points in each of his last N games"
    # "Player X has recorded 10+ rebounds in each of his last N games"
    player_pattern = r'(\w+\s+\w+)\s+has\s+(scored|recorded|made)\s+(\d+)\+\s+(\w+)'
    player_match = re.search(player_pattern, fact)
    
    if player_match:
        player_name = player_match.group(1)
        stat_verb = player_match.group(2)
        threshold = int(player_match.group(3))
        stat_word = player_match.group(4)
        
        # Map stat words to stat types
        stat_map = {
            'points': 'points',
            'point': 'points',
            'rebounds': 'rebounds',
            'rebound': 'rebounds',
            'assists': 'assists',
            'assist': 'assists',
            'steals': 'steals',
            'steal': 'steals',
            'blocks': 'blocks',
            'block': 'blocks'
        }
        
        stat_type = stat_map.get(stat_word, 'points')
        
        # Extract filter conditions
        filter_type = None
        opponent = None
        
        if 'home' in fact or 'at home' in fact:
            filter_type = 'home'
        elif 'road' in fact or 'away' in fact or '@' in fact:
            filter_type = 'away'
        elif 'vs' in fact or 'against' in fact:
            # Extract opponent
            vs_match = re.search(r'(?:vs|against)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', fact)
            if vs_match:
                opponent = vs_match.group(1)
                filter_type = 'vs_opponent'
        
        # Extract "last N" count
        last_n_match = re.search(r'last\s+(\d+)\s+(?:games?|appearances?)', fact)
        last_n = int(last_n_match.group(1)) if last_n_match else None
        
        return {
            'type': 'player',
            'entity': player_name,
            'stat_type': stat_type,
            'threshold': threshold,
            'filter_type': filter_type,
            'opponent': opponent,
            'last_n': last_n
        }
    
    # Pattern 2: Team win/loss trends
    # "Team X has won each of their last N games"
    # "Team X has won N of their last M games"
    team_win_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+have\s+won'
    team_win_match = re.search(team_win_pattern, fact)
    
    if team_win_match:
        team_name = team_win_match.group(1)
        
        # Check for opponent filter
        filter_type = None
        opponent = None
        
        if 'vs' in fact or 'against' in fact:
            vs_match = re.search(r'(?:vs|against)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', fact)
            if vs_match:
                opponent = vs_match.group(1)
                filter_type = 'vs_opponent'
        elif 'road' in fact or 'away' in fact:
            filter_type = 'away'
        elif 'home' in fact:
            filter_type = 'home'
        
        last_n_match = re.search(r'last\s+(\d+)\s+games?', fact)
        last_n = int(last_n_match.group(1)) if last_n_match else None
        
        return {
            'type': 'team',
            'entity': team_name,
            'stat_type': 'won',
            'threshold': 1.0,
            'filter_type': filter_type,
            'opponent': opponent,
            'last_n': last_n
        }
    
    # Pattern 3: Total points trends
    # "Each of Team X's last N games have gone UNDER"
    # "N of Team X's last M games have gone OVER"
    total_pattern = r'(\w+(?:\s+\w+)?)\'?s?\s+last\s+(\d+)\s+games?\s+have\s+gone\s+(over|under)'
    total_match = re.search(total_pattern, fact)
    
    if total_match:
        team_name = total_match.group(1)
        last_n = int(total_match.group(2))
        over_under = total_match.group(3)
        
        # Get total points threshold from market
        threshold = None
        if 'total' in market or 'over/under' in market:
            threshold_match = re.search(r'(\d+\.?\d*)', market)
            if threshold_match:
                threshold = float(threshold_match.group(1))
        
        return {
            'type': 'team',
            'entity': team_name,
            'stat_type': 'total_points',
            'threshold': threshold,
            'filter_type': None,
            'opponent': None,
            'last_n': last_n,
            'over_under': over_under
        }
    
    return None


def calculate_trend_from_insight(insight: Dict, season: str = "2024-25") -> Tuple[Optional[List[int]], int]:
    """
    Calculate trend outcomes from actual NBA.com data based on Sportsbet insight
    
    Args:
        insight: Dictionary with 'fact', 'market', 'result', 'odds', etc.
        season: NBA season (default: "2024-25")
    
    Returns:
        (outcomes, sample_size) where outcomes is list of 1s and 0s, or (None, 0) if can't calculate
    """
    trend_info = parse_insight_for_trend(insight)
    
    if not trend_info:
        logger.debug(f"Could not parse insight: {insight.get('fact', '')}")
        return (None, 0)
    
    try:
        # Get game log based on trend type
        if trend_info['type'] == 'player':
            game_log = get_player_game_log(trend_info['entity'], season, trend_info.get('last_n'))
            
            if not game_log:
                logger.warning(f"Could not get game log for player: {trend_info['entity']}")
                return (None, 0)
            
            # Create filter function
            filter_func = None
            if trend_info['filter_type'] == 'home':
                filter_func = lambda g: g.home_away == "HOME"
            elif trend_info['filter_type'] == 'away':
                filter_func = lambda g: g.home_away == "AWAY"
            elif trend_info['filter_type'] == 'vs_opponent' and trend_info.get('opponent'):
                opponent_id = get_team_id(trend_info['opponent'])
                if opponent_id:
                    filter_func = lambda g: g.opponent_id == opponent_id
            
            # Calculate trend
            outcomes, n = calculate_trend_from_game_log(
                game_log,
                trend_info['stat_type'],
                trend_info['threshold'],
                filter_func
            )
            
            return (outcomes, n)
        
        elif trend_info['type'] == 'team':
            # Check if it's H2H
            if trend_info['filter_type'] == 'vs_opponent' and trend_info.get('opponent'):
                game_log = get_h2h_matchups(
                    trend_info['entity'],
                    trend_info['opponent'],
                    season,
                    trend_info.get('last_n')
                )
            else:
                game_log = get_team_game_log(trend_info['entity'], season, trend_info.get('last_n'))
            
            if not game_log:
                logger.warning(f"Could not get game log for team: {trend_info['entity']}")
                return (None, 0)
            
            # Create filter function
            filter_func = None
            if trend_info['filter_type'] == 'home':
                filter_func = lambda g: g.home_away == "HOME"
            elif trend_info['filter_type'] == 'away':
                filter_func = lambda g: g.home_away == "AWAY"
            
            # Calculate trend
            if trend_info['stat_type'] == 'total_points':
                # Need threshold from market
                threshold = trend_info.get('threshold')
                if not threshold:
                    logger.warning("Total points trend requires threshold from market")
                    return (None, 0)
                
                outcomes, n = calculate_trend_from_game_log(
                    game_log,
                    'total_points',
                    threshold,
                    filter_func
                )
                
                # Flip outcomes if it's UNDER
                if trend_info.get('over_under') == 'under':
                    outcomes = [1 - o for o in outcomes]
            else:
                outcomes, n = calculate_trend_from_game_log(
                    game_log,
                    trend_info['stat_type'],
                    trend_info['threshold'],
                    filter_func
                )
            
            return (outcomes, n)
        
        else:
            return (None, 0)
    
    except Exception as e:
        logger.error(f"Error calculating trend from insight: {e}")
        import traceback
        traceback.print_exc()
        return (None, 0)


# Import get_team_id from team_ids (uses StatMuse IDs)
from scrapers.team_ids import get_team_id


def validate_insight_against_nba_data(
    insight: Dict,
    outcomes: List[int],
    sample_size: int,
    game_log: Optional[List] = None,
    max_age_days: int = 30
) -> Dict:
    """
    Validate Sportsbet insight against actual game log data (StatsMuse/DataballR sources)

    Args:
        insight: Sportsbet insight dictionary
        outcomes: Calculated outcomes from NBA data
        sample_size: Number of games in sample
        game_log: Optional game log to check staleness
        max_age_days: Maximum age of most recent game (default 30 days)

    Returns:
        Dictionary with validation results:
        {
            'is_valid': bool,
            'warnings': List[str],
            'mismatch_percentage': float,
            'is_stale': bool,
            'last_game_date': Optional[datetime]
        }
    """
    validation = {
        'is_valid': True,
        'warnings': [],
        'mismatch_percentage': 0.0,
        'is_stale': False,
        'last_game_date': None
    }

    # Extract claimed success rate from insight fact
    fact = insight.get('fact', '').lower()
    result = insight.get('result', '')

    # Try to parse "X of last Y" or "each of last Y"
    claimed_pattern = r'(?:(\d+)\s+of\s+(?:his|their|its)\s+last\s+(\d+)|each\s+of\s+(?:his|their|its)\s+last\s+(\d+))'
    match = re.search(claimed_pattern, fact)

    if match:
        if match.group(3):  # "each of last N" means N/N
            claimed_successes = int(match.group(3))
            claimed_total = int(match.group(3))
        else:  # "X of last Y"
            claimed_successes = int(match.group(1))
            claimed_total = int(match.group(2))

        # Compare with actual NBA data
        actual_successes = sum(outcomes) if outcomes else 0
        actual_total = sample_size

        # Check if sample sizes match
        if claimed_total != actual_total:
            validation['warnings'].append(
                f"Sample size mismatch: Sportsbet claims {claimed_total} games, NBA data shows {actual_total}"
            )

        # Check if success counts match (allow 1 game tolerance)
        if abs(claimed_successes - actual_successes) > 1:
            mismatch_pct = abs(claimed_successes - actual_successes) / max(claimed_total, actual_total) * 100
            validation['mismatch_percentage'] = round(mismatch_pct, 2)
            validation['warnings'].append(
                f"Trend mismatch: Sportsbet claims {claimed_successes}/{claimed_total}, NBA data shows {actual_successes}/{actual_total} ({mismatch_pct:.1f}% difference)"
            )

            # Reject if mismatch > 20%
            if mismatch_pct > 20:
                validation['is_valid'] = False
                validation['warnings'].append("REJECTED: Mismatch exceeds 20% threshold")

    # Check for staleness (if game log provided)
    if game_log and len(game_log) > 0:
        try:
            # Get most recent game date
            # Game log entries should have a 'game_date' attribute
            if hasattr(game_log[0], 'game_date'):
                most_recent = game_log[0].game_date
                if isinstance(most_recent, str):
                    # Parse date string (format: 'YYYY-MM-DD' or similar)
                    try:
                        last_game_date = datetime.strptime(most_recent, '%Y-%m-%d')
                    except ValueError:
                        try:
                            last_game_date = datetime.strptime(most_recent, '%m/%d/%Y')
                        except ValueError:
                            last_game_date = None
                else:
                    last_game_date = most_recent

                if last_game_date:
                    validation['last_game_date'] = last_game_date
                    age_days = (datetime.now() - last_game_date).days

                    if age_days > max_age_days:
                        validation['is_stale'] = True
                        validation['is_valid'] = False
                        validation['warnings'].append(
                            f"REJECTED: Trend is stale (last game {age_days} days ago, max allowed: {max_age_days})"
                        )
        except Exception as e:
            logger.warning(f"Could not check staleness: {e}")

    return validation


def calculate_and_validate_trend(
    insight: Dict,
    season: str = "2024-25",
    require_validation: bool = True
) -> Tuple[Optional[List[int]], int, Optional[Dict]]:
    """
    Calculate trend AND validate it against Sportsbet's claim

    Args:
        insight: Sportsbet insight dictionary
        season: NBA season
        require_validation: If True, return None for invalid trends

    Returns:
        (outcomes, sample_size, validation_result)
        - outcomes: List of 1s/0s or None if invalid
        - sample_size: Number of games
        - validation_result: Dict with validation details or None
    """
    # Calculate trend from NBA data
    outcomes, sample_size = calculate_trend_from_insight(insight, season)

    if not outcomes:
        return (None, 0, None)

    # Validate against Sportsbet claim
    validation = validate_insight_against_nba_data(insight, outcomes, sample_size)

    # Log validation results
    if validation['warnings']:
        for warning in validation['warnings']:
            if 'REJECTED' in warning:
                logger.warning(f"[VALIDATION] {warning}")
            else:
                logger.info(f"[VALIDATION] {warning}")

    # Return None if validation failed and it's required
    if require_validation and not validation['is_valid']:
        logger.warning(f"Insight failed validation: {insight.get('fact', '')[:80]}...")
        return (None, 0, validation)

    return (outcomes, sample_size, validation)


if __name__ == "__main__":
    # Test the trend calculator
    print("\n" + "="*70)
    print("  NBA TREND CALCULATOR TEST")
    print("="*70 + "\n")
    
    # Test player trend
    test_insight = {
        'fact': 'LeBron James has scored 20+ points in each of his last 10 games',
        'market': 'LeBron James To Score 20+ Points',
        'result': 'LeBron James',
        'odds': 1.85
    }
    
    print("Testing player trend calculation...")
    outcomes, n = calculate_trend_from_insight(test_insight)
    if outcomes:
        print(f"✓ Calculated trend: {sum(outcomes)}/{n} successes")
        print(f"  Outcomes: {outcomes[:10]}...")
    else:
        print("✗ Could not calculate trend")
    
    print()
    
    # Test team trend
    test_insight2 = {
        'fact': 'The Lakers have won each of their last 5 games',
        'market': 'Match Winner',
        'result': 'Lakers',
        'odds': 2.1
    }
    
    print("Testing team trend calculation...")
    outcomes2, n2 = calculate_trend_from_insight(test_insight2)
    if outcomes2:
        print(f"✓ Calculated trend: {sum(outcomes2)}/{n2} successes")
        print(f"  Outcomes: {outcomes2}")
    else:
        print("✗ Could not calculate trend")

