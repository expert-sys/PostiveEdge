"""
Player Archetype Classifier
============================
Classifies NBA players into archetypes with probability caps.

NO player prop can exceed 82% probability under any condition.

Archetype Categories:
- Elite Star: 78-82% (heavy minutes, high usage, consistent)
- Starter: 74-78% (regular starter minutes and usage)
- Bench Scorer: 68-74% (bench role with scoring)
- Rookie/Volatile: 65-72% (inconsistent role or rookie)
- Defensive First: 70-75% (high minutes, low offensive usage)
- Low-Usage Big: 66-72% (big man with limited touches)

Classification based on:
- Average minutes (L15 games)
- Usage proxy (points per 36 minutes)
- Minutes consistency (variance)
- Position detection (rebounds vs assists)

Usage:
    from scrapers.player_archetype_classifier import classify_player

    archetype = classify_player(
        player_name="LeBron James",
        game_log=game_log_entries,
        stat_type="points"
    )
    print(f"Archetype: {archetype.name}, Max Prob: {archetype.max_probability:.0%}")
"""

from dataclasses import dataclass
from typing import List, Optional
import statistics

# Import game log entry type
try:
    from scrapers.nba_stats_api_scraper import GameLogEntry
except ImportError:
    # Fallback if import fails
    GameLogEntry = None


@dataclass
class PlayerArchetype:
    """Player archetype with probability cap and thresholds"""
    name: str
    max_probability: float  # Hard cap (≤0.82)
    min_minutes: float  # Minimum average minutes
    min_usage_proxy: float  # Minimum points per 36
    description: str


# Define 6 archetype categories with probability caps
ARCHETYPES = {
    'elite_star': PlayerArchetype(
        name='Elite Star',
        max_probability=0.80,  # Maximum allowed: 78-80% (lowered from 82%)
        min_minutes=34.0,
        min_usage_proxy=22.0,  # 22+ points per 36 minutes
        description='Elite scorer with stable minutes and high usage'
    ),
    'starter': PlayerArchetype(
        name='Starter',
        max_probability=0.75,  # 72-75% (lowered from 78%)
        min_minutes=28.0,
        min_usage_proxy=16.0,  # 16+ points per 36
        description='Regular starter with moderate to high usage'
    ),
    'bench_scorer': PlayerArchetype(
        name='Bench Scorer',
        max_probability=0.70,  # 68-70% (lowered from 74%)
        min_minutes=20.0,
        min_usage_proxy=14.0,  # 14+ points per 36
        description='Bench player with defined scoring role'
    ),
    'rookie_volatile': PlayerArchetype(
        name='Rookie/Volatile',
        max_probability=0.65,  # 62-65% (lowered from 72%)
        min_minutes=18.0,
        min_usage_proxy=10.0,
        description='Inconsistent role, rookie, or high volatility player'
    ),
    'defensive_first': PlayerArchetype(
        name='Defensive First',
        max_probability=0.68,  # 65-68% (lowered from 75%)
        min_minutes=28.0,
        min_usage_proxy=8.0,  # Low offensive usage (< 12 pts/36)
        description='Defensive specialist with limited offensive role'
    ),
    'low_usage_big': PlayerArchetype(
        name='Low-Usage Big',
        max_probability=0.68,  # 65-68% (lowered from 72%)
        min_minutes=22.0,
        min_usage_proxy=10.0,
        description='Big man (center/PF) with limited touches'
    ),
}


def classify_player(
    player_name: str,
    game_log: List,
    stat_type: str = 'points'
) -> PlayerArchetype:
    """
    Classify player archetype based on game log statistics.

    Uses heuristics based on:
    - Average minutes (last 15 games)
    - Usage proxy (points per 36 minutes)
    - Minutes consistency (low variance = stable role)
    - Position detection (rebounds > assists = big man)

    Args:
        player_name: Player name (for logging)
        game_log: List of GameLogEntry objects (most recent first)
        stat_type: Stat type ('points', 'rebounds', etc.)

    Returns:
        PlayerArchetype with name, max_probability, and description
    """
    if not game_log or len(game_log) == 0:
        # No data - use most conservative archetype
        return ARCHETYPES['rookie_volatile']

    # Use last 15 games for classification (or all if < 15)
    recent_games = game_log[:min(15, len(game_log))]

    # Calculate average minutes
    avg_minutes = _calculate_avg_minutes(recent_games)

    # Calculate usage proxy (points per 36 minutes)
    usage_proxy = _calculate_usage_proxy(recent_games, stat_type)

    # Calculate minutes consistency (low variance = stable)
    minutes_variance = _calculate_minutes_variance(recent_games)
    is_consistent = minutes_variance < 25.0  # Std dev < 5 minutes

    # Detect position via heuristics (rebounds vs assists)
    is_big_man = _infer_big_man(recent_games)

    # Classification logic (order matters - most specific first)

    # 1. Elite Star: 34+ min, 22+ pts/36, consistent
    if avg_minutes >= 34.0 and usage_proxy >= 22.0 and is_consistent:
        return ARCHETYPES['elite_star']

    # 2. Starter: 28+ min, 16+ pts/36
    if avg_minutes >= 28.0 and usage_proxy >= 16.0:
        return ARCHETYPES['starter']

    # 3. Bench Scorer: 20+ min, 14+ pts/36
    if avg_minutes >= 20.0 and usage_proxy >= 14.0:
        return ARCHETYPES['bench_scorer']

    # 4. Low-Usage Big: Big man with < 12 pts/36
    if is_big_man and usage_proxy < 12.0 and avg_minutes >= 22.0:
        return ARCHETYPES['low_usage_big']

    # 5. Defensive First: 28+ min but low offensive usage (< 12 pts/36)
    if avg_minutes >= 28.0 and usage_proxy < 12.0:
        return ARCHETYPES['defensive_first']

    # 6. Default: Rookie/Volatile (catchall for uncertain cases)
    return ARCHETYPES['rookie_volatile']


def _calculate_avg_minutes(games: List) -> float:
    """Calculate average minutes played"""
    if not games:
        return 0.0

    total_minutes = 0.0
    count = 0

    for game in games:
        minutes = getattr(game, 'minutes', 0)
        if minutes is not None:
            total_minutes += minutes
            count += 1

    return total_minutes / count if count > 0 else 0.0


def _calculate_usage_proxy(games: List, stat_type: str) -> float:
    """
    Calculate usage proxy: points per 36 minutes.

    This is a simplified usage metric since we don't have
    full team stats (possessions, etc.) in the game log.
    """
    if not games:
        return 0.0

    total_stat = 0.0
    total_minutes = 0.0

    for game in games:
        stat_value = getattr(game, stat_type, 0)
        minutes = getattr(game, 'minutes', 0)

        if stat_value is not None and minutes is not None and minutes > 0:
            total_stat += stat_value
            total_minutes += minutes

    if total_minutes == 0:
        return 0.0

    # Points per 36 minutes
    per_36 = (total_stat / total_minutes) * 36.0
    return per_36


def _calculate_minutes_variance(games: List) -> float:
    """
    Calculate variance in minutes played.

    Low variance = stable role
    High variance = inconsistent role
    """
    if not games or len(games) < 2:
        return 100.0  # High variance for insufficient data

    minutes_list = []
    for game in games:
        minutes = getattr(game, 'minutes', None)
        if minutes is not None:
            minutes_list.append(minutes)

    if len(minutes_list) < 2:
        return 100.0

    try:
        variance = statistics.variance(minutes_list)
        return variance
    except:
        return 100.0  # High variance if calculation fails


def _infer_big_man(games: List) -> bool:
    """
    Infer if player is a big man (Center/PF) using heuristics.

    Heuristic: If rebounds > 2x assists, likely a big man
    """
    if not games:
        return False

    total_rebounds = 0.0
    total_assists = 0.0

    for game in games:
        reb = getattr(game, 'rebounds', 0) or 0
        ast = getattr(game, 'assists', 0) or 0

        total_rebounds += reb
        total_assists += ast

    # Avoid division by zero
    if total_rebounds + total_assists == 0:
        return False

    # If rebounds > 2x assists, likely a big man
    return total_rebounds > (2.0 * total_assists)


def get_archetype_by_name(archetype_name: str) -> Optional[PlayerArchetype]:
    """Get archetype by name (case insensitive)"""
    archetype_name_lower = archetype_name.lower().replace(' ', '_').replace('/', '_')

    for key, archetype in ARCHETYPES.items():
        if key == archetype_name_lower or archetype.name.lower() == archetype_name.lower():
            return archetype

    return None


# Export for convenience
__all__ = [
    'PlayerArchetype',
    'ARCHETYPES',
    'classify_player',
    'get_archetype_by_name'
]
