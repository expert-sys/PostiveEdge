"""
Player Role Heuristics
======================
Infers player role from usage patterns and applies role-based probability adjustments.
Since we don't have position data, we infer roles from statistical patterns.
"""

from typing import List, Dict
from scrapers.data_models import GameLogEntry
import statistics


def infer_player_role(game_log: List[GameLogEntry], stat_type: str = 'points') -> Dict[str, str]:
    """
    Infer player role from usage + assists + rebounds + minutes.
    Returns structured role with three dimensions: offensive_role, usage_state, minutes_state.
    
    Offensive Roles:
    - primary: High assists (6+) and usage (22+)
    - secondary: Moderate assists (4-6) or usage (18-22)
    - tertiary: Lower assists (<4) or usage (<18)
    - role_player: Very low usage (<15) but regular minutes
    
    Usage States:
    - elevated: Usage spiking recently (+15% vs historical)
    - normal: Stable usage
    - suppressed: Usage dropping recently (-15% vs historical)
    
    Minutes States:
    - stable: Consistent minutes (std dev < 5)
    - volatile: Inconsistent minutes (std dev >= 5)
    - capped: Minutes trending down or limited
    
    Args:
        game_log: List of GameLogEntry objects
        stat_type: Stat type being projected (for context)
    
    Returns:
        Dict with keys: 'offensive_role', 'usage_state', 'minutes_state', 'display_name'
    """
    if not game_log or len(game_log) == 0:
        return {
            'offensive_role': 'secondary',
            'usage_state': 'normal',
            'minutes_state': 'stable',
            'display_name': 'Secondary Creator'
        }
    
    # Calculate averages
    assists = [g.assists for g in game_log if hasattr(g, 'assists') and g.assists is not None]
    rebounds = [g.rebounds for g in game_log if hasattr(g, 'rebounds') and g.rebounds is not None]
    points = [g.points for g in game_log if hasattr(g, 'points') and g.points is not None]
    minutes = [g.minutes for g in game_log if hasattr(g, 'minutes') and g.minutes is not None]
    
    if not minutes or len(minutes) == 0:
        return {
            'offensive_role': 'secondary',
            'usage_state': 'normal',
            'minutes_state': 'stable',
            'display_name': 'Secondary Creator'
        }
    
    avg_ast = statistics.mean(assists) if assists else 0.0
    avg_reb = statistics.mean(rebounds) if rebounds else 0.0
    avg_pts = statistics.mean(points) if points else 0.0
    avg_min = statistics.mean(minutes) if minutes else 0.0
    
    # Calculate usage (points per 36 minutes)
    usage = (avg_pts / avg_min * 36.0) if avg_min > 0 else 0.0
    
    # P3: Stat-aware role inference - prioritize stats relevant to the stat_type being projected
    sample_size = len(game_log)
    stat_signal_strength = 0  # Track how strong the stat-specific signal is
    
    if stat_type == 'rebounds':
        # For rebounds: prioritize rebounding ability
        if avg_reb > 10:
            offensive_role = 'primary'
            display_base = 'Interior Big'
            stat_signal_strength = 3  # Strong signal
        elif avg_reb > 7:
            offensive_role = 'secondary'
            display_base = 'Rebounder'
            stat_signal_strength = 2  # Moderate signal
        elif avg_reb > 5:
            offensive_role = 'tertiary'
            display_base = 'Defensive Anchor'
            stat_signal_strength = 1  # Weak signal
        else:
            # Weak rebounding signal - fall back to general role
            if avg_ast > 6 and usage > 22:
                offensive_role = 'primary'
                display_base = 'Primary Creator'
            elif avg_reb > 8 and avg_ast < 3:
                offensive_role = 'primary'
                display_base = 'Interior Big'
            elif avg_min < 22:
                offensive_role = 'tertiary'
                display_base = 'Bench'
            elif avg_ast > 4 or usage > 18:
                offensive_role = 'secondary'
                display_base = 'Secondary Creator'
            else:
                offensive_role = 'tertiary'
                display_base = 'Tertiary Option'
            stat_signal_strength = 0
    
    elif stat_type == 'assists':
        # For assists: prioritize playmaking ability
        if avg_ast > 8:
            offensive_role = 'primary'
            display_base = 'Primary Creator'
            stat_signal_strength = 3  # Strong signal
        elif avg_ast > 5:
            offensive_role = 'secondary'
            display_base = 'Creator'
            stat_signal_strength = 2  # Moderate signal
        elif avg_ast > 3:
            offensive_role = 'secondary'
            display_base = 'Playmaker'
            stat_signal_strength = 1  # Weak signal
        else:
            # Weak assist signal - fall back to general role
            if avg_ast > 6 and usage > 22:
                offensive_role = 'primary'
                display_base = 'Primary Creator'
            elif avg_reb > 8 and avg_ast < 3:
                offensive_role = 'primary'
                display_base = 'Interior Big'
            elif usage < 18 and avg_min > 28:
                offensive_role = 'role_player'
                display_base = '3-and-D'
            elif avg_min < 22:
                offensive_role = 'tertiary'
                display_base = 'Bench'
            elif avg_ast > 4 or usage > 18:
                offensive_role = 'secondary'
                display_base = 'Secondary Creator'
            else:
                offensive_role = 'tertiary'
                display_base = 'Tertiary Option'
            stat_signal_strength = 0
    
    elif stat_type == 'points':
        # For points: prioritize usage and scoring
        if usage > 25:
            offensive_role = 'primary'
            display_base = 'Volume Scorer'
            stat_signal_strength = 3  # Strong signal
        elif usage > 20:
            offensive_role = 'secondary'
            display_base = 'Scorer'
            stat_signal_strength = 2  # Moderate signal
        elif usage > 15:
            offensive_role = 'secondary'
            display_base = 'Efficient Scorer'
            stat_signal_strength = 1  # Weak signal
        else:
            # Weak scoring signal - fall back to general role
            if avg_ast > 6 and usage > 22:
                offensive_role = 'primary'
                display_base = 'Primary Creator'
            elif avg_reb > 8 and avg_ast < 3:
                offensive_role = 'primary'
                display_base = 'Interior Big'
            elif usage < 18 and avg_min > 28:
                offensive_role = 'role_player'
                display_base = '3-and-D'
            elif avg_min < 22:
                offensive_role = 'tertiary'
                display_base = 'Bench'
            elif avg_ast > 4 or usage > 18:
                offensive_role = 'secondary'
                display_base = 'Secondary Creator'
            else:
                offensive_role = 'tertiary'
                display_base = 'Tertiary Option'
            stat_signal_strength = 0
    
    else:
        # Other stat types (steals, blocks, etc.) - use general role inference
        if avg_ast > 6 and usage > 22:
            offensive_role = 'primary'
            display_base = 'Primary Creator'
        elif avg_reb > 8 and avg_ast < 3:
            offensive_role = 'primary'
            display_base = 'Interior Big'
        elif usage < 18 and avg_min > 28:
            offensive_role = 'role_player'
            display_base = '3-and-D'
        elif avg_min < 22:
            offensive_role = 'tertiary'
            display_base = 'Bench'
        elif avg_ast > 4 or usage > 18:
            offensive_role = 'secondary'
            display_base = 'Secondary Creator'
        else:
            offensive_role = 'tertiary'
            display_base = 'Tertiary Option'
        stat_signal_strength = 0
    
    # Determine usage state (compare recent vs historical)
    if len(minutes) >= 10:
        recent_minutes = minutes[:5]
        historical_minutes = minutes[5:10] if len(minutes) >= 10 else minutes[5:]
        recent_pts = points[:5] if len(points) >= 5 else points
        historical_pts = points[5:10] if len(points) >= 10 else points[5:] if len(points) > 5 else []
        
        if recent_pts and historical_pts:
            recent_usage = (statistics.mean(recent_pts) / statistics.mean(recent_minutes) * 36) if statistics.mean(recent_minutes) > 0 else usage
            hist_usage = (statistics.mean(historical_pts) / statistics.mean(historical_minutes) * 36) if statistics.mean(historical_minutes) > 0 else usage
            
            if hist_usage > 0:
                usage_change_pct = ((recent_usage - hist_usage) / hist_usage) * 100
                if usage_change_pct > 15:
                    usage_state = 'elevated'
                elif usage_change_pct < -15:
                    usage_state = 'suppressed'
                else:
                    usage_state = 'normal'
            else:
                usage_state = 'normal'
        else:
            usage_state = 'normal'
    else:
        usage_state = 'normal'
    
    # Determine minutes state
    if len(minutes) >= 5:
        min_std = statistics.stdev(minutes) if len(minutes) > 1 else 0.0
        recent_avg = statistics.mean(minutes[:5])
        historical_avg = statistics.mean(minutes[5:10]) if len(minutes) >= 10 else statistics.mean(minutes[5:]) if len(minutes) > 5 else recent_avg
        
        if min_std >= 5:
            minutes_state = 'volatile'
        elif historical_avg > 0 and recent_avg < historical_avg * 0.85:
            minutes_state = 'capped'
        else:
            minutes_state = 'stable'
    else:
        minutes_state = 'stable'
    
    # P3: Build display name - use fallback label if signal is weak or sample is thin
    if sample_size < 8 or stat_signal_strength == 0:
        # Weak signal or thin sample - use neutral label
        display_base = 'Neutral (Stat-agnostic)'
    
    display_parts = [display_base]
    if usage_state != 'normal':
        display_parts.append(f"({usage_state.title()} Usage")
    if minutes_state == 'volatile':
        display_parts.append("Volatile Minutes)" if usage_state != 'normal' else "(Volatile Minutes)")
    elif minutes_state == 'capped':
        display_parts.append("Capped Minutes)" if usage_state != 'normal' else "(Capped Minutes)")
    elif usage_state != 'normal':
        display_parts[-1] += ")"
    
    display_name = ' '.join(display_parts) if len(display_parts) > 1 else display_base
    
    return {
        'offensive_role': offensive_role,
        'usage_state': usage_state,
        'minutes_state': minutes_state,
        'display_name': display_name
    }


# Role-based probability adjustments
# These adjust the raw model probability based on role-specific tendencies
ROLE_ADJUSTMENTS = {
    "primary_handler": {
        "assists": +0.07,   # Primary handlers typically exceed assist props
        "points": +0.04,    # High usage = more scoring opportunities
        "rebounds": 0.0,    # No adjustment
        "steals": 0.0,
        "blocks": 0.0,
        "three_pt_made": 0.0
    },
    "secondary_creator": {
        "assists": +0.03,   # Some playmaking responsibility
        "points": +0.03,    # Secondary scoring option
        "rebounds": 0.0,
        "steals": 0.0,
        "blocks": 0.0,
        "three_pt_made": 0.0
    },
    "interior_big": {
        "rebounds": +0.08,   # Bigs are more reliable for rebounds
        "assists": -0.05,    # Less playmaking
        "points": +0.02,     # Some scoring boost from paint opportunities
        "steals": 0.0,
        "blocks": +0.05,     # Bigs block more shots
        "three_pt_made": -0.04  # Less 3-point shooting
    },
    "3_and_d": {
        "threes": +0.06,     # 3-and-D players specialize in threes
        "three_pt_made": +0.06,
        "points": -0.03,     # Lower overall scoring (role players)
        "rebounds": +0.02,   # Some rebounding from perimeter
        "assists": 0.0,
        "steals": +0.03,     # Good defenders get steals
        "blocks": 0.0
    },
    "bench": {
        "all": -0.12,        # Bench players have more volatility
        # Individual stats can override "all" if specified
        "assists": -0.12,
        "points": -0.12,
        "rebounds": -0.12,
        "steals": -0.12,
        "blocks": -0.12,
        "three_pt_made": -0.12
    }
}


def apply_role_adjustment(base_probability: float, role: str, stat_type: str) -> float:
    """
    Apply role-based probability adjustment.
    
    Args:
        base_probability: Base probability from model (0.0 to 1.0)
        role: Player role (from infer_player_role)
        stat_type: Stat type being projected
    
    Returns:
        Adjusted probability
    """
    if role not in ROLE_ADJUSTMENTS:
        return base_probability
    
    adjustments = ROLE_ADJUSTMENTS[role]
    
    # Check for "all" adjustment first (applies to bench players)
    if "all" in adjustments and stat_type not in adjustments:
        adjustment = adjustments["all"]
    else:
        # Get stat-specific adjustment, default to 0
        adjustment = adjustments.get(stat_type, 0.0)
    
    # Apply adjustment (additive)
    adjusted_prob = base_probability + adjustment
    
    # Ensure valid range
    adjusted_prob = max(0.01, min(0.99, adjusted_prob))
    
    return adjusted_prob
