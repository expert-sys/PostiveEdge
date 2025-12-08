"""
Matchup Engine - Advanced Opponent & Pace Modeling
==================================================
Calculates matchup-specific adjustments based on:
- Opponent defensive stats (rebounds/assists/points allowed)
- Pace factors (possessions per game)
- Defensive efficiency ratings
- Blowout risk (score differential trends)
- Player volatility scores

Usage:
    from matchup_engine import MatchupEngine
    
    engine = MatchupEngine()
    adjustments = engine.calculate_matchup_adjustment(
        player_name="Jaden McDaniels",
        stat_type="rebounds",
        opponent_team="Pelicans",
        player_team="Timberwolves"
    )
"""

import statistics
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# NBA League Averages (2024-25 season)
LEAGUE_AVG_PACE = 100.0  # Possessions per 48 minutes
LEAGUE_AVG_POINTS = 114.0
LEAGUE_AVG_REBOUNDS = 43.0
LEAGUE_AVG_ASSISTS = 27.0
LEAGUE_AVG_DEF_RATING = 115.0


class StatType(Enum):
    """Stat types for matchup analysis"""
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    STEALS = "steals"
    BLOCKS = "blocks"
    THREE_PT_MADE = "three_pt_made"


@dataclass
class OpponentDefense:
    """Opponent defensive statistics"""
    team_name: str
    
    # Defensive stats (per game)
    points_allowed: float
    rebounds_allowed: float
    assists_allowed: float
    steals_allowed: float
    blocks_allowed: float
    three_pt_allowed: float
    
    # Efficiency metrics
    defensive_rating: float  # Points allowed per 100 possessions
    pace: float  # Possessions per 48 minutes
    
    # Positional defense (if available)
    points_allowed_vs_position: Optional[Dict[str, float]] = None
    rebounds_allowed_vs_position: Optional[Dict[str, float]] = None
    
    # Blowout tendencies
    avg_margin: float = 0.0  # Positive = winning, negative = losing
    blowout_frequency: float = 0.0  # % of games with 15+ point margin


@dataclass
class PlayerVolatility:
    """Player volatility metrics"""
    stat_type: str
    mean: float
    std_dev: float
    coefficient_of_variation: float  # std_dev / mean
    floor: float  # 10th percentile
    ceiling: float  # 90th percentile
    consistency_score: float  # 0-100, higher = more consistent


@dataclass
class MatchupAdjustment:
    """Complete matchup adjustment result"""
    # Multipliers
    pace_multiplier: float  # Pace adjustment (0.8 - 1.2)
    defense_multiplier: float  # Opponent defense (0.8 - 1.2)
    blowout_risk_multiplier: float  # Blowout risk (0.9 - 1.0)
    
    # Combined adjustment
    total_multiplier: float  # Combined effect on projection
    
    # Probability adjustments
    probability_adjustment: float  # -0.15 to +0.15
    
    # Context
    opponent_rank: Optional[int] = None  # Defensive rank (1-30)
    pace_rank: Optional[int] = None  # Pace rank (1-30)
    favorable_matchup: bool = False
    
    # Detailed breakdown
    notes: list = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


class MatchupEngine:
    """
    Advanced matchup modeling engine.
    
    Calculates stat-specific adjustments based on opponent defense,
    pace, blowout risk, and player volatility.
    """
    
    def __init__(self):
        # Opponent defensive stats cache
        self.opponent_cache: Dict[str, OpponentDefense] = {}
        
        # Team pace cache
        self.pace_cache: Dict[str, float] = {}
        
        # Initialize with default NBA team stats (can be updated with real data)
        self._init_default_stats()
    
    def _init_default_stats(self):
        """Initialize with league average stats as defaults"""
        # These should be replaced with real team stats from an API or scraper
        # For now, using league averages as placeholders
        pass
    
    def calculate_matchup_adjustment(
        self,
        player_name: str,
        stat_type: str,
        opponent_team: str,
        player_team: str,
        player_position: Optional[str] = None,
        player_volatility: Optional[PlayerVolatility] = None,
        game_log: Optional[list] = None
    ) -> MatchupAdjustment:
        """
        Calculate complete matchup adjustment.
        
        Args:
            player_name: Player name
            stat_type: Stat to analyze ("points", "rebounds", "assists", etc.)
            opponent_team: Opponent team name
            player_team: Player's team name
            player_position: Player position (for positional matchups)
            player_volatility: Player volatility metrics
            game_log: Recent game log for volatility calculation
            
        Returns:
            MatchupAdjustment with all multipliers and adjustments
        """
        notes = []
        
        # 1. Get opponent defensive stats
        opp_defense = self._get_opponent_defense(opponent_team)
        
        # 2. Calculate pace multiplier
        pace_mult, pace_rank = self._calculate_pace_multiplier(
            player_team, opponent_team
        )
        
        if pace_mult > 1.05:
            notes.append(f"Fast pace matchup ({pace_mult:.2f}x) - more opportunities")
        elif pace_mult < 0.95:
            notes.append(f"Slow pace matchup ({pace_mult:.2f}x) - fewer opportunities")
        
        # 3. Calculate defense multiplier
        defense_mult, opp_rank = self._calculate_defense_multiplier(
            stat_type, opp_defense, player_position
        )
        
        if defense_mult > 1.05:
            notes.append(f"Weak defense vs {stat_type} (rank {opp_rank}) - favorable")
        elif defense_mult < 0.95:
            notes.append(f"Strong defense vs {stat_type} (rank {opp_rank}) - tough matchup")
        
        # 4. Calculate blowout risk multiplier
        blowout_mult = self._calculate_blowout_risk(
            player_team, opponent_team, opp_defense
        )
        
        if blowout_mult < 0.95:
            notes.append(f"High blowout risk - starters may sit early")
        
        # 5. Calculate player volatility adjustment
        if player_volatility is None and game_log:
            player_volatility = self._calculate_player_volatility(
                stat_type, game_log
            )
        
        volatility_adj = 0.0
        if player_volatility:
            if player_volatility.coefficient_of_variation > 0.40:
                volatility_adj = -0.03  # High volatility = reduce confidence
                notes.append(f"High volatility (CV={player_volatility.coefficient_of_variation:.2f})")
            elif player_volatility.coefficient_of_variation < 0.20:
                volatility_adj = +0.02  # Low volatility = increase confidence
                notes.append(f"Consistent player (CV={player_volatility.coefficient_of_variation:.2f})")
        
        # 6. Combine multipliers
        total_mult = pace_mult * defense_mult * blowout_mult
        
        # 7. Convert to probability adjustment
        # Each 10% multiplier change = ~5% probability change
        prob_adj = (total_mult - 1.0) * 0.5 + volatility_adj
        prob_adj = max(-0.15, min(0.15, prob_adj))  # Cap at ±15%
        
        # 8. Determine if favorable matchup
        favorable = (total_mult > 1.05 and blowout_mult > 0.95)
        
        return MatchupAdjustment(
            pace_multiplier=pace_mult,
            defense_multiplier=defense_mult,
            blowout_risk_multiplier=blowout_mult,
            total_multiplier=total_mult,
            probability_adjustment=prob_adj,
            opponent_rank=opp_rank,
            pace_rank=pace_rank,
            favorable_matchup=favorable,
            notes=notes
        )
    
    def _get_opponent_defense(self, team_name: str) -> OpponentDefense:
        """
        Get opponent defensive stats.
        
        In production, this should fetch from:
        - NBA Stats API
        - Basketball Reference
        - Your own database
        
        For now, returns league averages with team-specific adjustments.
        """
        # Check cache first
        if team_name in self.opponent_cache:
            return self.opponent_cache[team_name]
        
        # Default to league averages
        # TODO: Replace with real team stats
        defense = OpponentDefense(
            team_name=team_name,
            points_allowed=LEAGUE_AVG_POINTS,
            rebounds_allowed=LEAGUE_AVG_REBOUNDS,
            assists_allowed=LEAGUE_AVG_ASSISTS,
            steals_allowed=7.5,
            blocks_allowed=5.0,
            three_pt_allowed=12.5,
            defensive_rating=LEAGUE_AVG_DEF_RATING,
            pace=LEAGUE_AVG_PACE,
            avg_margin=0.0,
            blowout_frequency=0.15
        )
        
        # Apply team-specific adjustments (hardcoded for now)
        # TODO: Replace with real data
        team_adjustments = self._get_team_defensive_adjustments(team_name)
        if team_adjustments:
            defense.points_allowed *= team_adjustments.get('points', 1.0)
            defense.rebounds_allowed *= team_adjustments.get('rebounds', 1.0)
            defense.assists_allowed *= team_adjustments.get('assists', 1.0)
            defense.defensive_rating *= team_adjustments.get('def_rating', 1.0)
            defense.pace *= team_adjustments.get('pace', 1.0)
        
        self.opponent_cache[team_name] = defense
        return defense
    
    def _get_team_defensive_adjustments(self, team_name: str) -> Optional[Dict]:
        """
        Get team-specific defensive adjustments.
        
        These are rough estimates based on 2024-25 season trends.
        Should be replaced with real-time data.
        """
        # Simplified team adjustments (top/bottom 5 teams)
        adjustments = {
            # Strong defenses (allow less)
            'Celtics': {'points': 0.95, 'rebounds': 0.97, 'assists': 0.96, 'def_rating': 0.96, 'pace': 1.02},
            'Thunder': {'points': 0.93, 'rebounds': 0.96, 'assists': 0.95, 'def_rating': 0.94, 'pace': 0.98},
            'Timberwolves': {'points': 0.96, 'rebounds': 0.95, 'assists': 0.97, 'def_rating': 0.97, 'pace': 0.99},
            'Cavaliers': {'points': 0.94, 'rebounds': 0.96, 'assists': 0.96, 'def_rating': 0.95, 'pace': 1.01},
            'Knicks': {'points': 0.97, 'rebounds': 0.94, 'assists': 0.98, 'def_rating': 0.98, 'pace': 0.97},
            
            # Weak defenses (allow more)
            'Wizards': {'points': 1.08, 'rebounds': 1.05, 'assists': 1.06, 'def_rating': 1.08, 'pace': 1.03},
            'Trail Blazers': {'points': 1.07, 'rebounds': 1.04, 'assists': 1.05, 'def_rating': 1.07, 'pace': 1.02},
            'Hornets': {'points': 1.06, 'rebounds': 1.03, 'assists': 1.04, 'def_rating': 1.06, 'pace': 1.04},
            'Spurs': {'points': 1.05, 'rebounds': 1.03, 'assists': 1.03, 'def_rating': 1.05, 'pace': 1.05},
            'Nets': {'points': 1.04, 'rebounds': 1.02, 'assists': 1.03, 'def_rating': 1.04, 'pace': 1.01},
            
            # Fast pace teams
            'Pacers': {'points': 1.02, 'rebounds': 1.01, 'assists': 1.02, 'def_rating': 1.02, 'pace': 1.08},
            'Kings': {'points': 1.01, 'rebounds': 1.00, 'assists': 1.02, 'def_rating': 1.01, 'pace': 1.06},
            'Warriors': {'points': 1.00, 'rebounds': 0.99, 'assists': 1.03, 'def_rating': 1.00, 'pace': 1.05},
            
            # Slow pace teams
            'Heat': {'points': 0.99, 'rebounds': 1.00, 'assists': 0.98, 'def_rating': 0.99, 'pace': 0.94},
            'Nuggets': {'points': 0.98, 'rebounds': 0.99, 'assists': 1.01, 'def_rating': 0.99, 'pace': 0.96},
        }
        
        # Try exact match first
        if team_name in adjustments:
            return adjustments[team_name]
        
        # Try partial match (e.g., "Pelicans" matches "New Orleans Pelicans")
        for team, adj in adjustments.items():
            if team.lower() in team_name.lower() or team_name.lower() in team.lower():
                return adj
        
        return None
    
    def _calculate_pace_multiplier(
        self,
        player_team: str,
        opponent_team: str
    ) -> Tuple[float, Optional[int]]:
        """
        Calculate pace multiplier based on both teams' pace.
        
        Returns:
            (pace_multiplier, pace_rank)
        """
        # Get team paces
        player_pace = self._get_team_pace(player_team)
        opp_pace = self._get_team_pace(opponent_team)
        
        # Matchup pace = average of both teams
        matchup_pace = (player_pace + opp_pace) / 2.0
        
        # Calculate multiplier vs league average
        pace_mult = matchup_pace / LEAGUE_AVG_PACE
        
        # Clamp to reasonable range (0.85 - 1.15)
        pace_mult = max(0.85, min(1.15, pace_mult))
        
        # Estimate pace rank (1-30)
        # Higher pace = lower rank number (1 = fastest)
        pace_rank = int(16 - (matchup_pace - LEAGUE_AVG_PACE) / 2)
        pace_rank = max(1, min(30, pace_rank))
        
        return pace_mult, pace_rank
    
    def _get_team_pace(self, team_name: str) -> float:
        """Get team pace (possessions per 48 minutes)"""
        # Check cache
        if team_name in self.pace_cache:
            return self.pace_cache[team_name]
        
        # Get from defensive stats
        defense = self._get_opponent_defense(team_name)
        pace = defense.pace
        
        self.pace_cache[team_name] = pace
        return pace
    
    def _calculate_defense_multiplier(
        self,
        stat_type: str,
        opp_defense: OpponentDefense,
        player_position: Optional[str] = None
    ) -> Tuple[float, Optional[int]]:
        """
        Calculate defense multiplier based on opponent's defensive stats.
        
        Returns:
            (defense_multiplier, opponent_rank)
        """
        # Get stat-specific allowed value
        if stat_type == "points":
            allowed = opp_defense.points_allowed
            league_avg = LEAGUE_AVG_POINTS
        elif stat_type == "rebounds":
            allowed = opp_defense.rebounds_allowed
            league_avg = LEAGUE_AVG_REBOUNDS
        elif stat_type == "assists":
            allowed = opp_defense.assists_allowed
            league_avg = LEAGUE_AVG_ASSISTS
        elif stat_type == "steals":
            allowed = opp_defense.steals_allowed
            league_avg = 7.5
        elif stat_type == "blocks":
            allowed = opp_defense.blocks_allowed
            league_avg = 5.0
        elif stat_type == "three_pt_made":
            allowed = opp_defense.three_pt_allowed
            league_avg = 12.5
        else:
            return 1.0, None
        
        # Calculate multiplier
        # Higher allowed = easier defense = higher multiplier
        defense_mult = allowed / league_avg
        
        # Clamp to reasonable range (0.85 - 1.15)
        defense_mult = max(0.85, min(1.15, defense_mult))
        
        # Estimate defensive rank (1-30)
        # Lower allowed = better defense = lower rank number
        opp_rank = int(16 + (allowed - league_avg) / (league_avg * 0.05))
        opp_rank = max(1, min(30, opp_rank))
        
        return defense_mult, opp_rank
    
    def _calculate_blowout_risk(
        self,
        player_team: str,
        opponent_team: str,
        opp_defense: OpponentDefense
    ) -> float:
        """
        Calculate blowout risk multiplier.
        
        High blowout risk = starters sit early = lower stats
        """
        # Get team strength differential (simplified)
        # In production, use actual win%, point differential, etc.
        
        # For now, use defensive rating as proxy for team strength
        player_def = self._get_opponent_defense(player_team)
        
        # Calculate expected margin
        # Better defense = lower rating = stronger team
        strength_diff = opp_defense.defensive_rating - player_def.defensive_rating
        
        # Convert to blowout risk
        # Large strength difference = high blowout risk
        if abs(strength_diff) > 10:
            # Significant mismatch
            blowout_risk = 0.92  # 8% reduction
        elif abs(strength_diff) > 5:
            # Moderate mismatch
            blowout_risk = 0.96  # 4% reduction
        else:
            # Competitive game
            blowout_risk = 1.0  # No reduction
        
        return blowout_risk
    
    def _calculate_player_volatility(
        self,
        stat_type: str,
        game_log: list
    ) -> Optional[PlayerVolatility]:
        """
        Calculate player volatility from game log.
        
        Args:
            stat_type: Stat to analyze
            game_log: List of GameLogEntry objects
            
        Returns:
            PlayerVolatility object
        """
        if not game_log or len(game_log) < 5:
            return None
        
        # Extract stat values
        values = []
        for game in game_log:
            if game.minutes >= 10:  # Only count games with significant minutes
                value = getattr(game, stat_type, None)
                if value is not None:
                    values.append(value)
        
        if len(values) < 5:
            return None
        
        # Calculate metrics
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        cv = std_dev / mean if mean > 0 else 0.0
        
        # Calculate floor and ceiling (10th and 90th percentiles)
        sorted_values = sorted(values)
        floor_idx = int(len(sorted_values) * 0.1)
        ceiling_idx = int(len(sorted_values) * 0.9)
        floor = sorted_values[floor_idx]
        ceiling = sorted_values[ceiling_idx]
        
        # Calculate consistency score (inverse of CV, scaled to 0-100)
        # CV < 0.2 = 90-100 (very consistent)
        # CV 0.2-0.4 = 60-90 (moderately consistent)
        # CV > 0.4 = 0-60 (inconsistent)
        if cv < 0.2:
            consistency = 90 + (0.2 - cv) * 50
        elif cv < 0.4:
            consistency = 60 + (0.4 - cv) * 150
        else:
            consistency = max(0, 60 - (cv - 0.4) * 100)
        
        consistency = min(100, max(0, consistency))
        
        return PlayerVolatility(
            stat_type=stat_type,
            mean=mean,
            std_dev=std_dev,
            coefficient_of_variation=cv,
            floor=floor,
            ceiling=ceiling,
            consistency_score=consistency
        )
    
    def get_matchup_summary(
        self,
        player_name: str,
        stat_type: str,
        opponent_team: str,
        player_team: str,
        game_log: Optional[list] = None
    ) -> str:
        """
        Get human-readable matchup summary.
        """
        adjustment = self.calculate_matchup_adjustment(
            player_name=player_name,
            stat_type=stat_type,
            opponent_team=opponent_team,
            player_team=player_team,
            game_log=game_log
        )
        
        lines = [
            f"Matchup Analysis: {player_name} vs {opponent_team}",
            f"Stat: {stat_type}",
            f"",
            f"Pace: {adjustment.pace_multiplier:.2f}x (rank {adjustment.pace_rank})",
            f"Defense: {adjustment.defense_multiplier:.2f}x (rank {adjustment.opponent_rank})",
            f"Blowout Risk: {adjustment.blowout_risk_multiplier:.2f}x",
            f"",
            f"Total Multiplier: {adjustment.total_multiplier:.2f}x",
            f"Probability Adjustment: {adjustment.probability_adjustment:+.1%}",
            f"",
            f"Favorable Matchup: {'YES' if adjustment.favorable_matchup else 'NO'}",
        ]
        
        if adjustment.notes:
            lines.append("")
            lines.append("Notes:")
            for note in adjustment.notes:
                lines.append(f"  • {note}")
        
        return "\n".join(lines)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_matchup_factors_for_confidence(
    player_name: str,
    stat_type: str,
    opponent_team: str,
    player_team: str,
    game_log: Optional[list] = None
) -> Dict:
    """
    Get matchup factors in format expected by confidence engine.
    
    Returns dict with:
        - pace_multiplier
        - defense_adjustment
        - opponent_defensive_rank
        - total_adjustment
    """
    engine = MatchupEngine()
    
    adjustment = engine.calculate_matchup_adjustment(
        player_name=player_name,
        stat_type=stat_type,
        opponent_team=opponent_team,
        player_team=player_team,
        game_log=game_log
    )
    
    return {
        'pace_multiplier': adjustment.pace_multiplier,
        'defense_adjustment': adjustment.defense_multiplier,
        'opponent_defensive_rank': adjustment.opponent_rank,
        'total_adjustment': adjustment.total_multiplier,
        'blowout_risk': adjustment.blowout_risk_multiplier,
        'favorable_matchup': adjustment.favorable_matchup,
        'probability_adjustment': adjustment.probability_adjustment
    }


if __name__ == '__main__':
    # Example usage
    engine = MatchupEngine()
    
    # Test matchup
    print("="*70)
    print("MATCHUP ENGINE - TEST")
    print("="*70)
    print()
    
    summary = engine.get_matchup_summary(
        player_name="Jaden McDaniels",
        stat_type="rebounds",
        opponent_team="Pelicans",
        player_team="Timberwolves"
    )
    
    print(summary)
    print()
    
    # Test with different matchups
    print("\n" + "="*70)
    print("FAVORABLE MATCHUP TEST")
    print("="*70)
    print()
    
    summary2 = engine.get_matchup_summary(
        player_name="Player X",
        stat_type="points",
        opponent_team="Wizards",  # Weak defense
        player_team="Celtics"  # Strong team
    )
    
    print(summary2)
