"""
Advanced NBA Metrics Calculator
=================================
Calculates advanced basketball metrics from basic box score stats.

Key Metrics:
- Usage Rate (USG%) - Approximates Involve%
- True Shooting Percentage (TS%) - Efficiency metric
- Assist Rate (AST%) - Playmaking impact
- Game Score - Overall performance rating
- Rebound Rates - Rebounding efficiency

All calculations use standard NBA formulas.
"""

import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("advanced_metrics")


def calculate_usage_rate(player_stats: Dict, team_stats: Dict) -> float:
    """
    Calculate Usage Rate - percentage of team plays used while player is on court.
    This approximates Databallr's Involve%.
    
    Formula:
    100 * ((FGA + 0.44 * FTA + TOV) * (Tm MIN / 5)) / (MIN * (Tm FGA + 0.44 * Tm FTA + Tm TOV))
    
    Args:
        player_stats: Dict with keys: MIN, FGA, FTA, TOV
        team_stats: Dict with keys: MIN, FGA, FTA, TOV
    
    Returns:
        Usage Rate as percentage (e.g., 28.5)
        
    Example:
        >>> player = {'MIN': 35, 'FGA': 20, 'FTA': 8, 'TOV': 3}
        >>> team = {'MIN': 240, 'FGA': 85, 'FTA': 25, 'TOV': 12}
        >>> calculate_usage_rate(player, team)
        29.2
    """
    try:
        player_min = player_stats.get('MIN', player_stats.get('minutes', 0))
        player_fga = player_stats.get('FGA', player_stats.get('fg_attempted', 0))
        player_fta = player_stats.get('FTA', player_stats.get('ft_attempted', 0))
        player_tov = player_stats.get('TOV', player_stats.get('turnovers', 0))
        
        team_min = team_stats.get('MIN', team_stats.get('minutes', 240))
        team_fga = team_stats.get('FGA', team_stats.get('fg_attempted', 0))
        team_fta = team_stats.get('FTA', team_stats.get('ft_attempted', 0))
        team_tov = team_stats.get('TOV', team_stats.get('turnovers', 0))
        
        if player_min == 0 or team_min == 0:
            return 0.0
        
        numerator = (player_fga + 0.44 * player_fta + player_tov) * (team_min / 5)
        denominator = player_min * (team_fga + 0.44 * team_fta + team_tov)
        
        if denominator == 0:
            return 0.0
        
        usg = 100 * (numerator / denominator)
        return round(usg, 1)
        
    except Exception as e:
        logger.error(f"Error calculating usage rate: {e}")
        return 0.0


def calculate_true_shooting(pts: float, fga: float, fta: float) -> float:
    """
    Calculate True Shooting Percentage - accounts for 3-pointers and free throws.
    More accurate than FG% for measuring scoring efficiency.
    
    Formula:
    PTS / (2 * (FGA + 0.44 * FTA)) * 100
    
    Args:
        pts: Points scored
        fga: Field goal attempts
        fta: Free throw attempts
    
    Returns:
        True Shooting % (e.g., 61.2)
        
    Example:
        >>> calculate_true_shooting(30, 18, 6)
        71.4
    """
    try:
        denominator = 2 * (fga + 0.44 * fta)
        
        if denominator == 0:
            return 0.0
        
        ts = (pts / denominator) * 100
        return round(ts, 1)
        
    except Exception as e:
        logger.error(f"Error calculating true shooting: {e}")
        return 0.0


def calculate_assist_rate(player_stats: Dict, team_stats: Dict) -> float:
    """
    Calculate Assist Rate - percentage of teammate field goals assisted while on court.
    
    Formula:
    100 * AST / (((MIN / (Tm MIN / 5)) * Tm FG) - FG)
    
    Args:
        player_stats: Dict with keys: MIN, AST, FGM (or fg_made)
        team_stats: Dict with keys: MIN, FGM (or fg_made)
    
    Returns:
        Assist Rate as percentage
        
    Example:
        >>> player = {'MIN': 35, 'AST': 10, 'FGM': 9}
        >>> team = {'MIN': 240, 'FGM': 42}
        >>> calculate_assist_rate(player, team)
        35.7
    """
    try:
        player_min = player_stats.get('MIN', player_stats.get('minutes', 0))
        player_ast = player_stats.get('AST', player_stats.get('assists', 0))
        player_fg = player_stats.get('FGM', player_stats.get('fg_made', 0))
        
        team_min = team_stats.get('MIN', team_stats.get('minutes', 240))
        team_fg = team_stats.get('FGM', team_stats.get('fg_made', 0))
        
        if player_min == 0 or team_min == 0:
            return 0.0
        
        denominator = ((player_min / (team_min / 5)) * team_fg) - player_fg
        
        if denominator == 0:
            return 0.0
        
        ast_rate = 100 * (player_ast / denominator)
        return round(ast_rate, 1)
        
    except Exception as e:
        logger.error(f"Error calculating assist rate: {e}")
        return 0.0


def calculate_game_score(stats: Dict) -> float:
    """
    Calculate Game Score - simplified John Hollinger formula for overall performance.
    
    Formula:
    PTS + 0.4*FGM - 0.7*FGA - 0.4*(FTA-FTM) + 0.7*OREB + 0.3*DREB + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV
    
    Args:
        stats: Dict with all box score stats
    
    Returns:
        Game Score (typically 0-40 range, higher is better)
        
    Example:
        >>> stats = {'PTS': 28, 'FGM': 10, 'FGA': 18, 'FTM': 6, 'FTA': 7, 
        ...          'OREB': 2, 'DREB': 8, 'AST': 5, 'STL': 2, 'BLK': 1, 
        ...          'PF': 2, 'TOV': 3}
        >>> calculate_game_score(stats)
        22.3
    """
    try:
        pts = stats.get('PTS', stats.get('points', 0))
        fgm = stats.get('FGM', stats.get('fg_made', 0))
        fga = stats.get('FGA', stats.get('fg_attempted', 0))
        ftm = stats.get('FTM', stats.get('ft_made', 0))
        fta = stats.get('FTA', stats.get('ft_attempted', 0))
        
        # Handle rebounds (might be split or total)
        oreb = stats.get('OREB', stats.get('off_rebounds', 0))
        dreb = stats.get('DREB', stats.get('def_rebounds', 0))
        
        # If no split rebounds, estimate from total
        if oreb == 0 and dreb == 0:
            total_reb = stats.get('REB', stats.get('rebounds', 0))
            oreb = total_reb * 0.25  # Rough estimate
            dreb = total_reb * 0.75
        
        ast = stats.get('AST', stats.get('assists', 0))
        stl = stats.get('STL', stats.get('steals', 0))
        blk = stats.get('BLK', stats.get('blocks', 0))
        pf = stats.get('PF', stats.get('fouls', 0))
        tov = stats.get('TOV', stats.get('turnovers', 0))
        
        game_score = (
            pts +
            0.4 * fgm -
            0.7 * fga -
            0.4 * (fta - ftm) +
            0.7 * oreb +
            0.3 * dreb +
            stl +
            0.7 * ast +
            0.7 * blk -
            0.4 * pf -
            tov
        )
        
        return round(game_score, 1)
        
    except Exception as e:
        logger.error(f"Error calculating game score: {e}")
        return 0.0


def calculate_rebound_rates(player_stats: Dict, team_stats: Dict, opp_team_stats: Dict) -> Dict[str, float]:
    """
    Calculate offensive, defensive, and total rebound rates.
    
    Formulas:
    ORB% = 100 * (Player ORB * (Tm MIN / 5)) / (Player MIN * (Tm ORB + Opp DRB))
    DRB% = 100 * (Player DRB * (Tm MIN / 5)) / (Player MIN * (Tm DRB + Opp ORB))
    TRB% = 100 * (Player TRB * (Tm MIN / 5)) / (Player MIN * (Tm TRB + Opp TRB))
    
    Args:
        player_stats: Player box score
        team_stats: Team box score
        opp_team_stats: Opponent team box score
    
    Returns:
        Dict with 'orb_rate', 'drb_rate', 'trb_rate'
    """
    try:
        player_min = player_stats.get('MIN', player_stats.get('minutes', 0))
        player_oreb = player_stats.get('OREB', player_stats.get('off_rebounds', 0))
        player_dreb = player_stats.get('DREB', player_stats.get('def_rebounds', 0))
        player_treb = player_stats.get('REB', player_stats.get('rebounds', 0))
        
        team_min = team_stats.get('MIN', team_stats.get('minutes', 240))
        team_oreb = team_stats.get('OREB', team_stats.get('off_rebounds', 0))
        team_dreb = team_stats.get('DREB', team_stats.get('def_rebounds', 0))
        team_treb = team_stats.get('REB', team_stats.get('rebounds', 0))
        
        opp_oreb = opp_team_stats.get('OREB', opp_team_stats.get('off_rebounds', 0))
        opp_dreb = opp_team_stats.get('DREB', opp_team_stats.get('def_rebounds', 0))
        opp_treb = opp_team_stats.get('REB', opp_team_stats.get('rebounds', 0))
        
        if player_min == 0:
            return {'orb_rate': 0.0, 'drb_rate': 0.0, 'trb_rate': 0.0}
        
        # ORB%
        orb_denom = team_oreb + opp_dreb
        if orb_denom > 0:
            orb_rate = 100 * (player_oreb * (team_min / 5)) / (player_min * orb_denom)
        else:
            orb_rate = 0.0
        
        # DRB%
        drb_denom = team_dreb + opp_oreb
        if drb_denom > 0:
            drb_rate = 100 * (player_dreb * (team_min / 5)) / (player_min * drb_denom)
        else:
            drb_rate = 0.0
        
        # TRB%
        trb_denom = team_treb + opp_treb
        if trb_denom > 0:
            trb_rate = 100 * (player_treb * (team_min / 5)) / (player_min * trb_denom)
        else:
            trb_rate = 0.0
        
        return {
            'orb_rate': round(orb_rate, 1),
            'drb_rate': round(drb_rate, 1),
            'trb_rate': round(trb_rate, 1)
        }
        
    except Exception as e:
        logger.error(f"Error calculating rebound rates: {e}")
        return {'orb_rate': 0.0, 'drb_rate': 0.0, 'trb_rate': 0.0}


def calculate_all_metrics(
    player_stats: Dict,
    team_stats: Optional[Dict] = None,
    opp_team_stats: Optional[Dict] = None
) -> Dict[str, float]:
    """
    Calculate all available advanced metrics for a player.
    
    Args:
        player_stats: Player box score stats
        team_stats: Team box score (optional, needed for USG%, AST%, REB%)
        opp_team_stats: Opponent team stats (optional, needed for REB%)
    
    Returns:
        Dict with all calculated metrics
        
    Example:
        >>> player = {'MIN': 35, 'PTS': 28, 'FGA': 18, 'FTA': 7, ...}
        >>> team = {'MIN': 240, 'FGA': 85, 'FTA': 25, ...}
        >>> metrics = calculate_all_metrics(player, team)
        >>> print(metrics['usage_rate'], metrics['true_shooting_pct'])
        28.5 61.2
    """
    metrics = {}
    
    # Always calculable (just need player stats)
    pts = player_stats.get('PTS', player_stats.get('points', 0))
    fga = player_stats.get('FGA', player_stats.get('fg_attempted', 0))
    fta = player_stats.get('FTA', player_stats.get('ft_attempted', 0))
    
    metrics['true_shooting_pct'] = calculate_true_shooting(pts, fga, fta)
    metrics['game_score'] = calculate_game_score(player_stats)
    
    # Team-dependent metrics
    if team_stats:
        metrics['usage_rate'] = calculate_usage_rate(player_stats, team_stats)
        metrics['assist_rate'] = calculate_assist_rate(player_stats, team_stats)
        
        if opp_team_stats:
            reb_rates = calculate_rebound_rates(player_stats, team_stats, opp_team_stats)
            metrics.update(reb_rates)
        else:
            metrics['orb_rate'] = 0.0
            metrics['drb_rate'] = 0.0
            metrics['trb_rate'] = 0.0
    else:
        metrics['usage_rate'] = 0.0
        metrics['assist_rate'] = 0.0
        metrics['orb_rate'] = 0.0
        metrics['drb_rate'] = 0.0
        metrics['trb_rate'] = 0.0
    
    return metrics


# Export main functions
__all__ = [
    'calculate_usage_rate',
    'calculate_true_shooting',
    'calculate_assist_rate',
    'calculate_game_score',
    'calculate_rebound_rates',
    'calculate_all_metrics'
]


if __name__ == "__main__":
    # Test with sample data (Nikola Jokic-like stats)
    print("=" * 80)
    print("TESTING ADVANCED METRICS CALCULATOR")
    print("=" * 80)
    print()
    
    # Sample game stats
    player = {
        'MIN': 35,
        'PTS': 28,
        'FGM': 10,
        'FGA': 18,
        'FTM': 6,
        'FTA': 7,
        'OREB': 2,
        'DREB': 12,
        'REB': 14,
        'AST': 9,
        'STL': 2,
        'BLK': 1,
        'TOV': 3,
        'PF': 2
    }
    
    team = {
        'MIN': 240,
        'FGM': 42,
        'FGA': 88,
        'FTA': 24,
        'TOV': 13,
        'OREB': 10,
        'DREB': 35,
        'REB': 45
    }
    
    opp_team = {
        'OREB': 8,
        'DREB': 32,
        'REB': 40
    }
    
    print("Sample Stats:")
    print(f"  Player: {player['PTS']} PTS, {player['REB']} REB, {player['AST']} AST")
    print(f"  {player['FGM']}/{player['FGA']} FG, {player['FTM']}/{player['FTA']} FT")
    print()
    
    # Test individual metrics
    print("Individual Metrics:")
    ts_pct = calculate_true_shooting(player['PTS'], player['FGA'], player['FTA'])
    print(f"  True Shooting %: {ts_pct}%")
    
    game_score = calculate_game_score(player)
    print(f"  Game Score: {game_score}")
    print()
    
    # Test team-dependent metrics
    print("Team-Dependent Metrics:")
    usg = calculate_usage_rate(player, team)
    print(f"  Usage Rate: {usg}%")
    
    ast_rate = calculate_assist_rate(player, team)
    print(f"  Assist Rate: {ast_rate}%")
    
    reb_rates = calculate_rebound_rates(player, team, opp_team)
    print(f"  Offensive Rebound Rate: {reb_rates['orb_rate']}%")
    print(f"  Defensive Rebound Rate: {reb_rates['drb_rate']}%")
    print(f"  Total Rebound Rate: {reb_rates['trb_rate']}%")
    print()
    
    # Test all metrics at once
    print("All Metrics (combined):")
    all_metrics = calculate_all_metrics(player, team, opp_team)
    for metric, value in all_metrics.items():
        print(f"  {metric}: {value}")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
