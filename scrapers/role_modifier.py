"""
Role Modifier Module
====================
Calculates role-based probability adjustments for player props.

Features:
- Usage rate fetch with priority: StatsMuse → DataballR → Inference
- Teammate usage impact calculation
- Starter minutes increase detection
- Role modifier with confidence scaling (max +5% probability boost)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from scrapers.data_cache import get_cache
from scrapers.data_models import GameLogEntry

logger = logging.getLogger(__name__)


@dataclass
class RoleModifierResult:
    """Result of role modifier calculation"""
    modifier: float  # Probability adjustment (-0.05 to +0.05)
    confidence: float  # Confidence in modifier (0.0-1.0)
    rationale: List[str]  # List of reasons for modifier
    offensive_role: str = "secondary_creator"  # primary/secondary/tertiary/role_player
    usage_state: str = "normal"  # normal/elevated/suppressed
    minutes_state: str = "stable"  # stable/volatile/capped


def fetch_usage_rate(
    player_name: str,
    team: str,
    date: str,
    game_log: Optional[List[GameLogEntry]] = None
) -> Tuple[Optional[float], float]:
    """
    Fetch usage rate with priority: StatsMuse → DataballR → Inference.
    
    Data Priority (with confidence):
    1. StatsMuse (primary): confidence = 0.85 (if usage found directly) or 0.75 (if estimated)
    2. DataballR (secondary): confidence = 0.90 (from game logs with usage data)
    3. Inference (fallback): confidence = 0.60 (calculated from stats)
    
    Args:
        player_name: Player name
        team: Team name
        date: Game date (YYYY-MM-DD)
        game_log: Optional game log for inference
    
    Returns:
        Tuple of (usage_rate, confidence) where:
        - usage_rate: Usage rate as percentage (0-100) or None if unavailable
        - confidence: Confidence in data source (0.0-1.0)
    """
    cache = get_cache()
    
    # Check cache first
    cached = cache.get(player_name, team, date, 'usage')
    if cached:
        usage_data = cached['data']
        return usage_data.get('usage_rate'), cached['confidence_score']
    
    usage_rate = None
    confidence = 0.0
    source = None
    
    # 1. Try StatsMuse (primary) - HIGHEST CONFIDENCE
    try:
        from scrapers.statmuse_player_scraper import scrape_player_profile
        from scrapers.statmuse_scraper import scrape_team_stats
        from scrapers.advanced_metrics import calculate_usage_rate
        
        # Get player profile from StatsMuse
        profile = scrape_player_profile(player_name, season="2024-25", headless=True)
        
        if profile and profile.minutes > 0:
            # Try to calculate actual usage rate using team stats
            try:
                # Get team stats for accurate usage calculation
                team_stats = scrape_team_stats(profile.team or team, season="2024-25", headless=True)
                
                if team_stats:
                    # Build player stats dict for usage calculation
                    player_stats_dict = {
                        'MIN': profile.minutes,
                        'FGA': profile.fg_attempted,
                        'FTA': profile.ft_attempted,
                        'TOV': profile.turnovers
                    }
                    
                    # Build team stats dict
                    team_stats_dict = {
                        'MIN': team_stats.points * 0.4 if team_stats.points > 0 else 240,  # Estimate team minutes
                        'FGA': team_stats.points * 3.0 if team_stats.points > 0 else 85,  # Estimate team FGA
                        'FTA': team_stats.points * 0.3 if team_stats.points > 0 else 25,  # Estimate team FTA
                        'TOV': team_stats.turnovers if team_stats.turnovers > 0 else 12
                    }
                    
                    # Calculate actual usage rate
                    usage_rate = calculate_usage_rate(player_stats_dict, team_stats_dict)
                    
                    if usage_rate > 0:
                        confidence = 0.85  # High confidence from StatsMuse with team stats
                        source = 'statsmuse_calculated'
                    else:
                        raise ValueError("Usage rate calculation returned 0")
                        
            except Exception as calc_e:
                logger.debug(f"[ROLE] StatsMuse usage calculation failed, using estimate: {calc_e}")
                
                # Fallback: Estimate usage from player stats only
                fga = profile.fg_attempted if hasattr(profile, 'fg_attempted') and profile.fg_attempted > 0 else 0
                fta = profile.ft_attempted if hasattr(profile, 'ft_attempted') and profile.ft_attempted > 0 else 0
                tov = profile.turnovers if hasattr(profile, 'turnovers') and profile.turnovers > 0 else 0
                
                if fga > 0 or fta > 0:
                    # Estimate usage: (FGA + 0.44 * FTA + TOV) per game
                    usage_factors = fga + (0.44 * fta) + tov
                    usage_per_36 = (usage_factors / profile.minutes) * 36
                    
                    # Convert to usage rate estimate
                    if usage_per_36 > 35:
                        usage_rate = 30.0
                    elif usage_per_36 > 28:
                        usage_rate = 26.0
                    elif usage_per_36 > 22:
                        usage_rate = 22.0
                    elif usage_per_36 > 15:
                        usage_rate = 18.0
                    else:
                        usage_rate = 15.0
                    
                    confidence = 0.80  # Good confidence from StatsMuse estimated usage
                    source = 'statsmuse_estimated'
                else:
                    # Final fallback: Estimate from points/minutes
                    pp36 = (profile.points / profile.minutes) * 36
                    if pp36 > 22:
                        usage_rate = 28.0
                    elif pp36 > 18:
                        usage_rate = 24.0
                    elif pp36 > 15:
                        usage_rate = 20.0
                    else:
                        usage_rate = 16.0
                    confidence = 0.75  # Lower confidence for points-based estimate
                    source = 'statsmuse_points_estimate'
                    
    except Exception as e:
        logger.debug(f"[ROLE] StatsMuse usage fetch failed for {player_name}: {e}")
    
    # 2. Try DataballR (secondary) - HIGH CONFIDENCE
    if usage_rate is None:
        try:
            # Try to get DataballR player data with usage rate
            if game_log and len(game_log) > 0:
                # Check if game log entries have usage data
                recent_games = game_log[:10]  # Check last 10 games
                
                # Look for usage_rate attribute in game log entries
                usage_rates = []
                for game in recent_games:
                    if hasattr(game, 'usage_rate') and game.usage_rate:
                        usage_rates.append(game.usage_rate)
                    elif hasattr(game, 'usage') and game.usage:
                        usage_rates.append(game.usage)
                
                if usage_rates:
                    # Average usage from recent games
                    usage_rate = sum(usage_rates) / len(usage_rates)
                    confidence = 0.90  # High confidence from DataballR direct usage data
                    source = 'databallr'
                else:
                    # Infer from DataballR game log stats
                    total_fga = sum(getattr(g, 'fg_attempted', 0) for g in recent_games)
                    total_fta = sum(getattr(g, 'ft_attempted', 0) for g in recent_games)
                    total_tov = sum(getattr(g, 'turnovers', 0) for g in recent_games)
                    total_minutes = sum(getattr(g, 'minutes', 0) for g in recent_games)
                    total_points = sum(getattr(g, 'points', 0) for g in recent_games)
                    
                    if total_minutes > 0:
                        # Calculate usage proxy
                        usage_factors = total_fga + (0.44 * total_fta) + total_tov
                        usage_per_36 = (usage_factors / total_minutes) * 36 if total_minutes > 0 else 0
                        
                        if usage_per_36 > 35:
                            usage_rate = 29.0
                        elif usage_per_36 > 28:
                            usage_rate = 25.0
                        elif usage_per_36 > 22:
                            usage_rate = 21.0
                        elif usage_per_36 > 15:
                            usage_rate = 17.0
                        else:
                            usage_rate = 14.0
                        
                        # Fallback to points per 36 if no FGA data
                        if usage_per_36 == 0 and total_points > 0:
                            pp36 = (total_points / total_minutes) * 36
                            if pp36 > 22:
                                usage_rate = 27.0
                            elif pp36 > 18:
                                usage_rate = 23.0
                            elif pp36 > 15:
                                usage_rate = 19.0
                            else:
                                usage_rate = 15.0
                        
                        confidence = 0.85  # Good confidence from DataballR game logs
                        source = 'databallr_calculated'
                        
        except Exception as e:
            logger.debug(f"[ROLE] DataballR usage fetch failed for {player_name}: {e}")
    
    # 3. Infer from game logs (fallback) - LOWER CONFIDENCE
    if usage_rate is None and game_log:
        usage_rate, inferred_conf = infer_usage_from_logs(player_name, team, game_log)
        if usage_rate is not None:
            confidence = inferred_conf  # 0.60 from infer_usage_from_logs
            source = 'inferred'
    
    # Cache result if found
    if usage_rate is not None and source:
        cache.set(
            player_name, team, date, 'usage',
            {'usage_rate': usage_rate, 'source': source},
            source, confidence
        )
        logger.debug(f"[ROLE] Fetched usage rate for {player_name}: {usage_rate:.1f}% (source: {source}, confidence: {confidence:.2f})")
    
    return usage_rate, confidence


def infer_usage_from_logs(
    player_name: str,
    team: str,
    game_log: List[GameLogEntry]
) -> Tuple[Optional[float], float]:
    """
    Infer usage rate from game log data.
    
    Usage rate approximation:
    - Points per 36 minutes
    - Field goal attempts
    - Assist rate (indicates ball handling)
    
    Args:
        player_name: Player name
        team: Team name
        game_log: List of game log entries
    
    Returns:
        Tuple of (usage_rate, confidence) where usage_rate is 0-100
    """
    if not game_log or len(game_log) < 5:
        return None, 0.0
    
    recent_games = game_log[:10]  # Last 10 games
    
    # Calculate points per 36 minutes
    total_points = sum(getattr(g, 'points', 0) for g in recent_games)
    total_minutes = sum(getattr(g, 'minutes', 0) for g in recent_games)
    
    if total_minutes == 0:
        return None, 0.0
    
    pp36 = (total_points / total_minutes) * 36
    
    # Calculate assist rate (rough indicator of ball handling)
    total_assists = sum(getattr(g, 'assists', 0) for g in recent_games)
    ap36 = (total_assists / total_minutes) * 36 if total_minutes > 0 else 0
    
    # Estimate usage rate
    # High usage: pp36 > 20 or (pp36 > 18 and ap36 > 6)
    # Medium usage: 15 < pp36 <= 20 or (pp36 > 12 and ap36 > 4)
    # Low usage: pp36 <= 15
    
    if pp36 > 20 or (pp36 > 18 and ap36 > 6):
        usage_rate = 27.0  # High usage
    elif pp36 > 15 or (pp36 > 12 and ap36 > 4):
        usage_rate = 21.0  # Medium usage
    else:
        usage_rate = 16.0  # Low usage
    
    confidence = 0.6  # Lower confidence for inference
    
    return usage_rate, confidence


def calculate_teammate_impact(
    player_name: str,
    team: str,
    date: str,
    teammate_roster: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, List[str]]:
    """
    Calculate impact score from unavailable teammates.
    
    Args:
        player_name: Player name
        team: Team name
        date: Game date
        teammate_roster: List of dicts with 'name', 'usage_rate', 'availability' ('OUT', 'QUESTIONABLE', 'AVAILABLE')
    
    Returns:
        Tuple of (impact_score, rationale_list)
        impact_score: Sum of (usage_rate * availability_weight)
        - Full modifier if impact_score >= 18
        - Partial modifier if impact_score >= 10
    """
    if not teammate_roster:
        return 0.0, []
    
    impact_score = 0.0
    rationale = []
    cache = get_cache()
    
    for teammate in teammate_roster:
        teammate_name = teammate.get('name', '')
        if teammate_name == player_name:
            continue
        
        availability = teammate.get('availability', 'AVAILABLE').upper()
        availability_weight = {
            'OUT': 1.0,
            'QUESTIONABLE': 0.5,
            'AVAILABLE': 0.0
        }.get(availability, 0.0)
        
        if availability_weight == 0.0:
            continue
        
        # Get teammate usage rate
        usage_rate = teammate.get('usage_rate')
        if usage_rate is None:
            # Try to fetch from cache or estimate
            cached = cache.get(teammate_name, team, date, 'usage')
            if cached:
                usage_rate = cached['data'].get('usage_rate', 15.0)
            else:
                usage_rate = 15.0  # Default estimate
        
        teammate_impact = usage_rate * availability_weight
        impact_score += teammate_impact
        
        if teammate_impact >= 10:  # Significant impact
            rationale.append(
                f"{teammate_name} OUT (usage {usage_rate:.1f}%, impact +{teammate_impact:.1f})"
            )
    
    return impact_score, rationale


def calculate_role_modifier(
    player_name: str,
    team: str,
    date: str,
    recent_minutes: List[float],
    historical_minutes: List[float],
    teammate_roster: Optional[List[Dict[str, Any]]] = None,
    game_log: Optional[List[GameLogEntry]] = None
) -> RoleModifierResult:
    """
    Calculate role modifier for probability adjustment.
    
    Modifier calculation:
    - Starter minutes increase (≥6 min): +3%
    - Teammate impact (≥18): +2%
    - Teammate impact (10-18): +1%
    - Max modifier: +5%
    - Scaled by usage confidence
    
    Args:
        player_name: Player name
        team: Team name
        date: Game date (YYYY-MM-DD)
        recent_minutes: List of minutes from last 3-5 games
        historical_minutes: List of minutes from last 15-20 games
        teammate_roster: Optional list of teammate availability/usage data
        game_log: Optional game log for usage inference
    
    Returns:
        RoleModifierResult with modifier, confidence, and rationale
    """
    modifier = 0.0
    rationale = []
    
    # 1. Check starter minutes increase
    if recent_minutes and historical_minutes:
        recent_avg = sum(recent_minutes) / len(recent_minutes) if recent_minutes else 0
        historical_avg = sum(historical_minutes) / len(historical_minutes) if historical_minutes else 0
        
        if historical_avg > 0:
            minutes_delta = recent_avg - historical_avg
            if minutes_delta >= 6:
                modifier += 0.03
                rationale.append(f"Starter minutes +{minutes_delta:.1f} (recent avg: {recent_avg:.1f}, historical: {historical_avg:.1f})")
    
    # 2. Calculate teammate impact
    impact_score, impact_rationale = calculate_teammate_impact(
        player_name, team, date, teammate_roster
    )
    
    if impact_score >= 18:
        modifier += 0.02
        rationale.extend(impact_rationale)
    elif impact_score >= 10:
        modifier += 0.01
        rationale.extend(impact_rationale)
    
    # Cap at +5%
    modifier = min(modifier, 0.05)
    
    # 3. Scale by usage confidence
    usage_rate, usage_conf = fetch_usage_rate(player_name, team, date, game_log)
    modifier *= usage_conf
    
    # Overall confidence is minimum of usage confidence and minutes confidence
    minutes_conf = 0.9 if recent_minutes and len(recent_minutes) >= 3 else 0.7
    overall_confidence = min(usage_conf, minutes_conf) if usage_conf > 0 else minutes_conf
    
    # Infer structured role information
    from scrapers.player_role_heuristics import infer_player_role
    if game_log:
        role_info = infer_player_role(game_log, stat_type='points')  # stat_type not critical for role inference
    else:
        role_info = {
            'offensive_role': 'secondary',
            'usage_state': 'normal',
            'minutes_state': 'stable',
            'display_name': 'Secondary Creator'
        }
    
    return RoleModifierResult(
        modifier=modifier,
        confidence=overall_confidence,
        rationale=rationale,
        offensive_role=role_info.get('offensive_role', 'secondary'),
        usage_state=role_info.get('usage_state', 'normal'),
        minutes_state=role_info.get('minutes_state', 'stable')
    )
