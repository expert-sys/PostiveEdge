"""
Dynamic Sample Size Optimization for Player Props
==================================================
Calculates optimal sample sizes based on:
- Season stage (early/mid/late) for adaptive thresholds
- Player consistency (coefficient of variation)
- Data availability

Usage:
    from sample_size_optimizer import calculate_optimal_sample_size, get_season_stage

    optimal_n, reasoning = calculate_optimal_sample_size(
        player_name="LeBron James",
        available_games=25,
        recent_stats=[28, 31, 25, 27, 30, ...],
        season_stage=None  # Auto-detect
    )
"""

from datetime import datetime
from typing import List, Tuple
import numpy as np
import logging

logger = logging.getLogger("sample_size_optimizer")


def get_season_stage() -> str:
    """
    Determine current season stage for adaptive thresholds.

    NBA season typically runs:
    - October-December: Early season (players finding rhythm, small samples)
    - January-February: Mid season (sufficient data, stable roles)
    - March-April+: Late season (maximum data, clear patterns)

    Returns:
        "early", "mid", or "late"
    """
    month = datetime.now().month

    if month in [10, 11, 12]:
        return "early"
    elif month in [1, 2]:
        return "mid"
    else:
        # March (3) through April (4) and beyond
        return "late"


def calculate_optimal_sample_size(
    player_name: str,
    available_games: int,
    recent_stats: List[float],
    season_stage: str = None
) -> Tuple[int, str]:
    """
    Determine optimal sample size based on season stage and player consistency.

    The key insight: we want MORE data when:
    1. It's later in the season (more games available)
    2. Player is volatile (high variance needs larger sample)

    We want LESS data when:
    1. It's early in the season (adapt quickly to current form)
    2. Player is consistent (stable stats don't need huge samples)

    Args:
        player_name: Player name for logging
        available_games: Total games available in logs
        recent_stats: Last N game statistics (for variance calculation)
        season_stage: Override season stage ("early", "mid", "late")

    Returns:
        (optimal_games, reasoning_string)
        - optimal_games: Number of games to use (0 = insufficient data)
        - reasoning_string: Human-readable explanation
    """
    if season_stage is None:
        season_stage = get_season_stage()

    # Base thresholds by season stage
    min_threshold = {
        "early": 10,    # Early season: accept 10+ games
        "mid": 15,      # Mid season: require 15+ games
        "late": 20      # Late season: require 20+ games
    }

    max_threshold = {
        "early": 15,    # Early season: use up to 15 games
        "mid": 25,      # Mid season: use up to 25 games
        "late": 30      # Late season: use up to 30 games
    }

    min_games = min_threshold.get(season_stage, 15)
    max_games = max_threshold.get(season_stage, 25)

    # Check if we have minimum data
    if available_games < min_games:
        return (
            0,
            f"Insufficient data: {available_games} games < {min_games} required for {season_stage} season"
        )

    # Calculate consistency (coefficient of variation)
    if len(recent_stats) >= 5:
        mean_val = np.mean(recent_stats)
        std_val = np.std(recent_stats)

        # Avoid division by zero
        if mean_val < 0.01:
            cv = 999.0  # Very high variance for near-zero production
        else:
            cv = std_val / mean_val

        # Determine target sample based on consistency
        if cv < 0.15:
            # Very consistent player (e.g., scores 25-28 every game)
            # Use smaller sample to adapt to recent trends faster
            target = min_games + 5
            reason = "High consistency (CV < 0.15)"
        elif cv < 0.30:
            # Moderately consistent player
            # Use middle-range sample
            target = min_games + 10
            reason = "Moderate consistency (CV 0.15-0.30)"
        else:
            # High variance player (e.g., ranges from 10-35 points)
            # Use maximum sample to smooth out volatility
            target = max_games
            reason = "High variance (CV > 0.30) - need more data"
    else:
        # Not enough data for consistency check
        # Be conservative and use maximum sample
        target = max_games
        reason = "Insufficient data for consistency check"

    # Cap at available games and thresholds
    optimal = min(target, available_games, max_games)

    return (
        optimal,
        f"{reason}, using {optimal} games ({season_stage} season)"
    )


def calculate_consistency_score(values: List[float]) -> float:
    """
    Calculate consistency score (0-1, higher = more consistent).

    Based on coefficient of variation (CV = std/mean).
    - Low CV (0.0-0.15) = high consistency → score ~0.7-1.0
    - Medium CV (0.15-0.30) = moderate consistency → score ~0.4-0.7
    - High CV (0.30+) = low consistency → score ~0.0-0.4

    This score can be used for filtering: reject players with score < 0.35

    Args:
        values: List of stat values (e.g., points per game)

    Returns:
        Consistency score from 0.0 to 1.0
    """
    if len(values) < 5:
        return 0.5  # Default for insufficient data

    mean_val = np.mean(values)

    # Handle near-zero production
    if mean_val < 0.01:
        return 0.3  # Low scoring player, assume high variance

    std_val = np.std(values)
    cv = std_val / mean_val

    # Convert CV to 0-1 score (inverted: low CV = high score)
    # CV of 0.0 = perfect consistency (score 1.0)
    # CV of 0.5 = high variance (score 0.0)
    consistency = max(0.0, min(1.0, 1.0 - (cv / 0.5)))

    return consistency


def get_sample_size_stats(values: List[float]) -> dict:
    """
    Calculate summary statistics for a sample.

    Useful for debugging and understanding why a particular sample size was chosen.

    Args:
        values: List of stat values

    Returns:
        Dictionary with mean, std, cv, consistency_score
    """
    if len(values) < 2:
        return {
            "mean": 0.0,
            "std": 0.0,
            "cv": 0.0,
            "consistency_score": 0.0,
            "n": len(values)
        }

    mean_val = np.mean(values)
    std_val = np.std(values)
    cv = std_val / (mean_val + 0.01)  # Avoid division by zero
    consistency = calculate_consistency_score(values)

    return {
        "mean": float(mean_val),
        "std": float(std_val),
        "cv": float(cv),
        "consistency_score": float(consistency),
        "n": len(values)
    }
