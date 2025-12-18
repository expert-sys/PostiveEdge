"""
Player Projection Model
======================
Projection-based model for player props that calculates expected stats and variance
from rolling statistics, minutes projections, matchup adjustments, and role change detection.

This becomes the PRIMARY signal for player prop analysis, replacing historical hit-rate analysis.

Usage:
    from scrapers.player_projection_model import PlayerProjectionModel
    
    model = PlayerProjectionModel()
    projection = model.project_stat(
        player_name="LeBron James",
        stat_type="points",
        game_log=game_log_entries,
        opponent_team="Celtics",
        player_team="Lakers",
        team_stats=team_stats,
        prop_line=25.5
    )
"""

import math
import statistics
import logging
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import data structures
from scrapers.data_models import GameLogEntry
from scrapers.sportsbet_final_enhanced import TeamStats, MatchStats
from scrapers.player_archetype_classifier import classify_player

logger = logging.getLogger(__name__)


class StatType(Enum):
    """Stat types for distribution modeling"""
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    STEALS = "steals"
    BLOCKS = "blocks"
    THREE_PT_MADE = "three_pt_made"
    MINUTES = "minutes"


@dataclass
class RollingStats:
    """Rolling statistics for different time windows"""
    window_size: int
    mean: float
    std_dev: float
    variance: float
    sample_size: int
    weighted_mean: float  # With exponential decay


@dataclass
class MinutesProjection:
    """Minutes projection and analysis"""
    recent_avg: float  # Last 5 games
    historical_avg: float  # Last 20 games
    projected_minutes: float
    volatility: float  # Standard deviation
    trend: str  # "INCREASING", "DECREASING", "STABLE"
    minutes_ratio: float  # projected / historical (for stat adjustment)
    volatility_penalty: float = 0.0  # -0.04 to -0.12 probability reduction


@dataclass
class MatchupAdjustments:
    """Matchup-specific adjustments"""
    pace_multiplier: float  # Based on team pace vs league average
    defense_adjustment: float  # Based on opponent defense
    total_adjustment: float  # Combined adjustment factor


@dataclass
class RoleChange:
    """Role change detection"""
    detected: bool
    change_type: str  # "INCREASE", "DECREASE", "STABLE", "TEMPORARY_SPIKE"
    minutes_change_pct: float
    confidence_penalty: float  # 0.0 to 1.0 (reduces confidence if role changed)
    usage_spike_pct: float = 0.0  # PHASE 3: Percentage spike in usage rate (pts/36)


@dataclass
class StatProjection:
    """Complete stat projection result"""
    expected_value: float
    variance: float
    std_dev: float
    probability_over_line: float  # P(X >= prop_line) - RAW probability before caps/penalties
    calibrated_probability: float = 0.0  # Final probability after all caps and penalties (SINGLE SOURCE OF TRUTH)
    confidence_score: float = 0.0  # 0-100
    rolling_stats_5: Optional[RollingStats] = None
    rolling_stats_10: Optional[RollingStats] = None
    rolling_stats_20: Optional[RollingStats] = None
    minutes_projection: Optional[MinutesProjection] = None
    matchup_adjustments: Optional[MatchupAdjustments] = None
    role_change: Optional[RoleChange] = None
    player_role: str = "secondary_creator"  # FIX #3: Inferred player role for display
    distribution_type: str = "normal"  # "normal", "poisson", "negative_binomial", "zero_inflated_poisson"
    archetype_name: str = "Unknown"  # Player archetype classification
    archetype_cap: float = 0.82  # Maximum probability for this archetype
    historical_hit_rate: float = 0.0  # Historical hit rate against the line
    role_modifier_details: Optional[Dict[str, Any]] = None  # Role modifier details (modifier, confidence, rationale, offensive_role, usage_state, minutes_state)


def blend_probabilities(
    model_prob: float,
    market_prob: float,
    weight_model: float = 0.70,
    weight_market: float = 0.30
) -> float:
    """
    Blend model probability with market-implied probability.
    
    Args:
        model_prob: Model's probability estimate
        market_prob: Market-implied probability (1/odds)
        weight_model: Weight for model probability (default 0.70)
        weight_market: Weight for market probability (default 0.30)
    
    Returns:
        Blended probability
    """
    return (weight_model * model_prob) + (weight_market * market_prob)


def sample_reliability(n: int) -> float:
    """
    Reliability multiplier based on sample size.
    
    Reduces confidence and probabilities for small samples to prevent over-trusting.
    
    Args:
        n: Sample size (number of games)
    
    Returns:
        Multiplier between 0.4 and 1.0
    """
    if n >= 30:
        return 1.0
    if n >= 20:
        return 0.9
    if n >= 10:
        return 0.75
    if n >= 5:
        return 0.6
    return 0.4


class PlayerProjectionModel:
    """
    Projection-based model for player props.
    
    Calculates expected stats using:
    - Rolling statistics (5, 10, 20 games)
    - Minutes projection
    - Matchup pace and defense adjustments
    - Role change detection
    """
    
    def __init__(self):
        self.min_minutes_threshold = 10.0  # Filter games with <10 minutes
        self.league_avg_pace = 100.0  # Approximate NBA league average pace
        self.role_change_threshold = 0.20  # 20% minutes change = role change
        
    def project_stat(
        self,
        player_name: str,
        stat_type: str,
        game_log: List[GameLogEntry],
        prop_line: float,
        opponent_team: Optional[str] = None,
        player_team: Optional[str] = None,
        team_stats: Optional[MatchStats] = None,
        min_games: int = 5
    ) -> Optional[StatProjection]:
        """
        Project a player stat for the next game.
        
        Args:
            player_name: Player name
            stat_type: Stat to project ("points", "rebounds", "assists", etc.)
            game_log: List of GameLogEntry objects (most recent first)
            prop_line: The betting line (e.g., 25.5 for points)
            opponent_team: Opponent team name
            player_team: Player's team name
            team_stats: MatchStats with team statistics
            min_games: Minimum games required for projection
            
        Returns:
            StatProjection object or None if insufficient data
        """
        if not game_log or len(game_log) < min_games:
            return None
            
        # Filter games with sufficient minutes
        valid_games = [g for g in game_log if g.minutes >= self.min_minutes_threshold]
        
        if len(valid_games) < min_games:
            return None
            
        # 1. Calculate rolling stats (5, 10, 20 games)
        rolling_stats_5 = self._calculate_rolling_stats(valid_games[:5], stat_type)
        rolling_stats_10 = self._calculate_rolling_stats(valid_games[:10], stat_type) if len(valid_games) >= 10 else None
        rolling_stats_20 = self._calculate_rolling_stats(valid_games[:20], stat_type) if len(valid_games) >= 20 else None
        
        # Use best available rolling stats (prefer 20, then 10, then 5)
        primary_stats = rolling_stats_20 or rolling_stats_10 or rolling_stats_5
        if not primary_stats:
            return None
            
        # 2. Project minutes
        minutes_proj = self._project_minutes(valid_games)
        
        # 3. Calculate matchup adjustments
        matchup_adj = self._calculate_matchup_adjustments(
            opponent_team, player_team, team_stats, stat_type
        )

        # 4. Detect role changes (PHASE 3: Now includes usage spike detection)
        role_change = self._detect_role_change(valid_games, stat_type)

        # 5. Adjust base projection for minutes and matchup
        base_expected = primary_stats.weighted_mean
        
        # Minutes adjustment: scale by projected minutes ratio
        minutes_adjusted = base_expected * minutes_proj.minutes_ratio
        
        # Matchup adjustment: apply pace and defense multipliers
        adjusted_expected = minutes_adjusted * matchup_adj.total_adjustment
        
        # 6. Calculate variance (use primary stats variance, adjusted for minutes)
        adjusted_variance = primary_stats.variance * (minutes_proj.minutes_ratio ** 2)
        adjusted_std_dev = math.sqrt(adjusted_variance)
        
        # 7. Calculate RAW probability using appropriate distribution
        prob_over_line = self._calculate_probability_over_line(
            stat_type, adjusted_expected, adjusted_std_dev, prop_line
        )

        # 8. INFER PLAYER ROLE and apply role-based adjustments (FIX #3)
        from scrapers.player_role_heuristics import infer_player_role, apply_role_adjustment
        role_info = infer_player_role(valid_games, stat_type)
        player_role = role_info.get('display_name', role_info.get('offensive_role', 'secondary_creator'))  # Use display name for compatibility
        # Apply role adjustment to raw probability before calibration (use offensive_role for adjustment lookup)
        role_for_adjustment = role_info.get('offensive_role', 'secondary_creator')
        prob_over_line = apply_role_adjustment(prob_over_line, role_for_adjustment, stat_type)

        # 8b. Apply advanced role modifier (minutes increase + teammate impact)
        role_modifier_result = None
        try:
            from scrapers.role_modifier import calculate_role_modifier
            from datetime import datetime
            
            # Extract minutes from recent games
            recent_minutes = [g.minutes for g in valid_games[:5] if hasattr(g, 'minutes') and g.minutes > 0]
            historical_minutes = [g.minutes for g in valid_games[:15] if hasattr(g, 'minutes') and g.minutes > 0]
            
            # Get game date (use most recent game date or current date)
            game_date = datetime.now().strftime('%Y-%m-%d')
            if valid_games and hasattr(valid_games[0], 'game_date'):
                try:
                    game_date = valid_games[0].game_date.strftime('%Y-%m-%d') if hasattr(valid_games[0].game_date, 'strftime') else str(valid_games[0].game_date)[:10]
                except:
                    pass
            
            # Calculate role modifier (teammate roster would need to be passed in, skip for now)
            role_modifier_result = calculate_role_modifier(
                player_name=player_name,
                team=player_team or "Unknown",
                date=game_date,
                recent_minutes=recent_minutes,
                historical_minutes=historical_minutes,
                teammate_roster=None,  # TODO: Pass teammate roster when available
                game_log=valid_games
            )
            
            # Apply modifier to probability
            if role_modifier_result and role_modifier_result.modifier > 0:
                prob_over_line = min(0.99, prob_over_line + role_modifier_result.modifier)
        except Exception as e:
            logger.debug(f"[ROLE MODIFIER] Failed to apply role modifier for {player_name}: {e}")
            role_modifier_result = None

        # 9. CLASSIFY PLAYER ARCHETYPE (determines probability cap)
        archetype = classify_player(
            player_name=player_name,
            game_log=valid_games,
            stat_type=stat_type
        )

        # 10. Calculate CALIBRATED probability (single source of truth)
        # Apply volatility penalty, role penalty, and archetype cap
        calibrated_prob = self.get_calibrated_probability(
            base_probability=prob_over_line,
            archetype_cap=archetype.max_probability,
            volatility_penalty=minutes_proj.volatility_penalty,
            role_penalty=role_change.confidence_penalty
        )

        # CRITICAL FIX: Sample size should ONLY affect confidence, NOT probability
        # Probability reflects the true model estimate - sample size uncertainty is captured in confidence
        # DO NOT apply sample_reliability to probability - it silently kills valid props
        sample_size = len(valid_games)
        
        # Ensure probability stays in valid range (but don't artificially reduce it)
        calibrated_prob = max(0.01, min(0.99, calibrated_prob))

        # 11. PHASE 6: Calculate historical hit rate for confidence formula
        historical_hit_rate = self._calculate_historical_hit_rate(
            valid_games, stat_type, prop_line
        )

        # 12. Calculate confidence score (4 components)
        # P2: Track base confidence BEFORE any penalties
        base_confidence = self._calculate_confidence_score(
            primary_stats, minutes_proj, role_change, matchup_adj, historical_hit_rate
        )
        confidence = base_confidence
        
        # Fix #4: Rebounds-specific volatility penalty (-5% confidence unless stability conditions met)
        if stat_type == 'rebounds':
            avg_reb = primary_stats.mean if primary_stats else 0.0
            avg_minutes = minutes_proj.historical_avg if minutes_proj else 0.0
            opponent_pace_ok = False
            if matchup_adj and matchup_adj.pace_multiplier:
                # pace_multiplier >= 1.0 means matchup pace >= league average
                opponent_pace_ok = matchup_adj.pace_multiplier >= 1.0
            
            # Apply penalty unless ALL conditions met: avg_reb >= 10.5 AND minutes >= 30 AND pace >= league_avg
            if not (avg_reb >= 10.5 and avg_minutes >= 30.0 and opponent_pace_ok):
                confidence_before_rebounds_penalty = confidence
                confidence *= 0.95  # -5% confidence penalty
                logger.debug(f"[REBOUNDS-VOLATILITY] {player_name}: -5% penalty applied (avg_reb={avg_reb:.1f}, min={avg_minutes:.1f}, pace_ok={opponent_pace_ok})")
            else:
                logger.debug(f"[REBOUNDS-VOLATILITY] {player_name}: penalty waived (avg_reb={avg_reb:.1f}>=10.5, min={avg_minutes:.1f}>=30, pace_ok={opponent_pace_ok})")
        
        # Apply Prop Volatility Index (PVI) penalty to confidence
        pvi_penalty = self._calculate_volatility_penalty(
            game_log=valid_games,
            stat_type=stat_type,
            minutes_proj=minutes_proj,
            primary_stats=primary_stats
        )
        # Max 50% confidence reduction from volatility
        confidence *= (1 - pvi_penalty * 0.5)
        
        # CRITICAL FIX: Apply sample-size reliability dampening to confidence ONLY
        # Sample size uncertainty affects how much we trust the probability, not the probability itself
        reliability_mult = sample_reliability(sample_size)
        confidence = confidence * reliability_mult
        confidence = max(0.0, min(100.0, confidence))

        # PHASE 6: Confidence must LAG probability (never exceed it)
        if confidence > (calibrated_prob * 100):
            confidence = calibrated_prob * 100

        # Apply sample size confidence dampening
        # Get sample size from game log
        sample_size = len(game_log) if game_log else 0
        if sample_size > 0:
            from scrapers.bet_validation import apply_sample_size_confidence_dampener
            confidence_before_dampening = confidence
            confidence = apply_sample_size_confidence_dampener(confidence, sample_size)
            if confidence != confidence_before_dampening:
                logger.debug(f"[CONFIDENCE] {player_name} {stat_type}: before_damp={confidence_before_dampening:.1f}%, sample_size={sample_size}, dampened={confidence:.1f}%")
        
        # P2: Apply confidence stack cap (relative cap prevents catastrophic drops)
        # Note: Edge boost will be applied later when probabilities are available for blending
        from scrapers.bet_validation import apply_confidence_stack_cap
        confidence_before_cap = confidence
        confidence = apply_confidence_stack_cap(
            confidence=confidence,
            base_confidence=base_confidence,
            max_total_dampening=None,  # Auto-calculate relative cap
            probability=None,  # Not available here, will be applied later during blending
            bookmaker_probability=None
        )
        if confidence != confidence_before_cap:
            total_dampening = base_confidence - confidence
            logger.debug(f"[CONFIDENCE CAP] {player_name} {stat_type}: base={base_confidence:.1f}%, after_penalties={confidence_before_cap:.1f}%, capped={confidence:.1f}% (total_dampening={total_dampening:.1f}%)")

        # Store role modifier details if available
        role_modifier_dict = None
        if role_modifier_result:
            role_modifier_dict = {
                'modifier': role_modifier_result.modifier,
                'confidence': role_modifier_result.confidence,
                'rationale': role_modifier_result.rationale,
                'offensive_role': role_modifier_result.offensive_role,
                'usage_state': role_modifier_result.usage_state,
                'minutes_state': role_modifier_result.minutes_state
            }
        
        return StatProjection(
            expected_value=adjusted_expected,
            variance=adjusted_variance,
            std_dev=adjusted_std_dev,
            probability_over_line=prob_over_line,  # RAW probability (after role adjustment)
            calibrated_probability=calibrated_prob,  # CALIBRATED probability (use this for EV/Fair Odds)
            confidence_score=confidence,
            rolling_stats_5=rolling_stats_5,
            rolling_stats_10=rolling_stats_10,
            rolling_stats_20=rolling_stats_20,
            minutes_projection=minutes_proj,
            matchup_adjustments=matchup_adj,
            role_change=role_change,
            player_role=player_role,  # FIX #3: Store inferred role for display
            distribution_type=self._get_distribution_type(stat_type),
            archetype_name=archetype.name,  # Player archetype classification
            archetype_cap=archetype.max_probability,  # Maximum probability for this archetype
            historical_hit_rate=historical_hit_rate,  # Percentage of games hitting the line
            role_modifier_details=role_modifier_dict  # Role modifier details for display
        )

    def get_calibrated_probability(
        self,
        base_probability: float,
        archetype_cap: float,
        volatility_penalty: float,
        role_penalty: float
    ) -> float:
        """
        SINGLE SOURCE OF TRUTH for probability calculation.
        Apply all penalties and caps in consistent order.

        Args:
            base_probability: Raw probability from distribution model
            archetype_cap: Maximum probability for player archetype (≤0.82)
            volatility_penalty: Minutes volatility penalty (-0.04 to -0.12)
            role_penalty: Role change penalty (0.0 to 0.15)

        Returns:
            Calibrated probability after all adjustments (0.01 to 0.99)

        Order of operations (CRITICAL - DO NOT CHANGE):
        1. Apply volatility penalty (multiplicative)
        2. Apply role penalty (multiplicative)
        3. Apply archetype cap
        4. Ensure valid range [0.01, 0.99]
        """
        # 1. Apply volatility penalty (multiplicative)
        # volatility_penalty is negative (-0.04 to -0.12)
        prob = base_probability * (1.0 + volatility_penalty)

        # 2. Apply role penalty (multiplicative)
        # role_penalty is 0.0 to 0.15
        prob = prob * (1.0 - role_penalty)

        # 3. Apply archetype cap (hard maximum)
        prob = min(prob, archetype_cap)

        # 4. Ensure valid probability range
        prob = max(0.01, min(0.99, prob))

        return prob

    def _calculate_rolling_stats(
        self, 
        games: List[GameLogEntry], 
        stat_type: str
    ) -> Optional[RollingStats]:
        """Calculate rolling statistics with exponential decay weighting"""
        if not games:
            return None
            
        # Extract stat values
        stat_values = []
        for game in games:
            value = getattr(game, stat_type, None)
            if value is not None:
                stat_values.append(value)
                
        if not stat_values:
            return None
            
        n = len(stat_values)
        mean = statistics.mean(stat_values)
        
        # Calculate variance and std dev
        if n > 1:
            variance = statistics.variance(stat_values)
            std_dev = math.sqrt(variance)
        else:
            variance = 0.0
            std_dev = 0.0
            
        # Calculate weighted mean with exponential decay (more recent = higher weight)
        # Weight = exp(-decay_rate * index), where index 0 is most recent
        decay_rate = 0.1  # Adjustable decay rate
        weights = [math.exp(-decay_rate * i) for i in range(n)]
        total_weight = sum(weights)
        
        weighted_sum = sum(val * weight for val, weight in zip(stat_values, weights))
        weighted_mean = weighted_sum / total_weight if total_weight > 0 else mean
        
        return RollingStats(
            window_size=n,
            mean=mean,
            std_dev=std_dev,
            variance=variance,
            sample_size=n,
            weighted_mean=weighted_mean
        )
    
    def _project_minutes(self, games: List[GameLogEntry]) -> MinutesProjection:
        """Project minutes based on recent trend"""
        if not games:
            return MinutesProjection(
                recent_avg=0.0,
                historical_avg=0.0,
                projected_minutes=0.0,
                volatility=0.0,
                trend="STABLE",
                minutes_ratio=1.0,
                volatility_penalty=0.0  # No penalty for missing data
            )
            
        # Last 5 games
        recent_games = games[:5] if len(games) >= 5 else games
        recent_minutes = [g.minutes for g in recent_games]
        recent_avg = statistics.mean(recent_minutes) if recent_minutes else 0.0
        
        # Last 20 games (or all available)
        historical_games = games[:20] if len(games) >= 20 else games
        historical_minutes = [g.minutes for g in historical_games]
        historical_avg = statistics.mean(historical_minutes) if historical_minutes else recent_avg
        
        # Calculate volatility
        if len(historical_minutes) > 1:
            volatility = statistics.stdev(historical_minutes)
        else:
            volatility = 0.0

        # PHASE 2.3: Calculate volatility penalty based on standard deviation
        # High volatility = role inconsistency = reduced confidence in projection
        if volatility > 8.0:
            # Very high volatility: -8% to -12% penalty
            volatility_penalty = min(-0.12, -(volatility - 8.0) * 0.02)
        elif volatility > 6.0:
            # Moderate-high volatility: -4% to -8% penalty
            volatility_penalty = min(-0.08, -(volatility - 6.0) * 0.02)
        else:
            # Low volatility: no penalty
            volatility_penalty = 0.0

        # Project minutes (weight recent more heavily)
        # 70% recent, 30% historical
        projected_minutes = 0.7 * recent_avg + 0.3 * historical_avg
        
        # Detect trend
        if recent_avg > historical_avg * 1.05:  # 5% increase
            trend = "INCREASING"
        elif recent_avg < historical_avg * 0.95:  # 5% decrease
            trend = "DECREASING"
        else:
            trend = "STABLE"
            
        # Minutes ratio for stat adjustment
        minutes_ratio = projected_minutes / historical_avg if historical_avg > 0 else 1.0

        return MinutesProjection(
            recent_avg=recent_avg,
            historical_avg=historical_avg,
            projected_minutes=projected_minutes,
            volatility=volatility,
            trend=trend,
            minutes_ratio=minutes_ratio,
            volatility_penalty=volatility_penalty  # PHASE 2.3: Include penalty for use in calibrated probability
        )
    
    def _calculate_matchup_adjustments(
        self,
        opponent_team: Optional[str],
        player_team: Optional[str],
        team_stats: Optional[MatchStats],
        stat_type: str
    ) -> MatchupAdjustments:
        """Calculate pace and defense adjustments"""
        pace_multiplier = 1.0
        defense_adjustment = 1.0
        
        if not team_stats:
            return MatchupAdjustments(
                pace_multiplier=pace_multiplier,
                defense_adjustment=defense_adjustment,
                total_adjustment=1.0
            )
            
        # Determine which team stats to use
        player_team_stats = None
        opponent_team_stats = None
        
        if player_team and team_stats.away_team_stats.team_name == player_team:
            player_team_stats = team_stats.away_team_stats
            opponent_team_stats = team_stats.home_team_stats
        elif player_team and team_stats.home_team_stats.team_name == player_team:
            player_team_stats = team_stats.home_team_stats
            opponent_team_stats = team_stats.away_team_stats
        elif opponent_team:
            # Try to match by opponent
            if team_stats.away_team_stats.team_name == opponent_team:
                opponent_team_stats = team_stats.away_team_stats
                player_team_stats = team_stats.home_team_stats
            elif team_stats.home_team_stats.team_name == opponent_team:
                opponent_team_stats = team_stats.home_team_stats
                player_team_stats = team_stats.away_team_stats
                
        # Pace adjustment: based on team scoring pace
        if player_team_stats and opponent_team_stats:
            # Calculate pace: (points_for + points_against) / 2
            player_pace = 0.0
            opponent_pace = 0.0
            
            if player_team_stats.avg_points_for and player_team_stats.avg_points_against:
                player_pace = (player_team_stats.avg_points_for + player_team_stats.avg_points_against) / 2.0
                
            if opponent_team_stats.avg_points_for and opponent_team_stats.avg_points_against:
                opponent_pace = (opponent_team_stats.avg_points_for + opponent_team_stats.avg_points_against) / 2.0
                
            # Matchup pace = average of both teams
            if player_pace > 0 and opponent_pace > 0:
                matchup_pace = (player_pace + opponent_pace) / 2.0
                # Pace multiplier: how much faster/slower than league average
                pace_multiplier = matchup_pace / self.league_avg_pace
                
        # Defense adjustment: based on opponent's points allowed
        if opponent_team_stats and opponent_team_stats.avg_points_against:
            # Higher points allowed = easier defense = positive adjustment
            # Normalize: (opponent_pa - league_avg) / league_avg
            # League average ~110 points allowed
            league_avg_pa = 110.0
            pa_diff = opponent_team_stats.avg_points_against - league_avg_pa
            # Each point difference = 1% adjustment
            defense_adjustment = 1.0 + (pa_diff / league_avg_pa) * 0.01
            
        # Total adjustment
        total_adjustment = pace_multiplier * defense_adjustment
        
        return MatchupAdjustments(
            pace_multiplier=pace_multiplier,
            defense_adjustment=defense_adjustment,
            total_adjustment=total_adjustment
        )
    
    def _detect_role_change(
        self,
        games: List[GameLogEntry],
        stat_type: str = 'points'
    ) -> RoleChange:
        """
        Detect role changes based on minutes trends and usage spikes.

        PHASE 3 Enhancement: Now detects temporary usage spikes (e.g., hot streaks,
        injury replacements) that may not be sustainable long-term.
        """
        if len(games) < 10:
            return RoleChange(
                detected=False,
                change_type="STABLE",
                minutes_change_pct=0.0,
                confidence_penalty=0.0
            )

        # PHASE 3: Check for usage spike FIRST (higher priority than minutes)
        # Usage spikes indicate temporary role elevation that may not sustain
        if len(games) >= 5:
            recent_usage = self._calculate_usage_proxy(games[:5], stat_type)
            season_usage = self._calculate_usage_proxy(games, stat_type)

            # Calculate usage spike percentage
            if season_usage > 0:
                usage_spike = (recent_usage - season_usage) / season_usage

                # If usage spiked >25%, flag as temporary spike
                if usage_spike > 0.25:
                    return RoleChange(
                        detected=True,
                        change_type="TEMPORARY_SPIKE",
                        minutes_change_pct=0.0,  # Not minutes-based
                        usage_spike_pct=usage_spike * 100,
                        confidence_penalty=min(0.15, usage_spike * 0.3)  # Cap at 15% penalty
                    )

        # Existing minutes-based detection
        # Last 5 games
        recent_minutes = [g.minutes for g in games[:5]]
        recent_avg = statistics.mean(recent_minutes)
        
        # Last 20 games (or all available)
        historical_games = games[:20] if len(games) >= 20 else games[5:]
        if not historical_games:
            return RoleChange(
                detected=False,
                change_type="STABLE",
                minutes_change_pct=0.0,
                confidence_penalty=0.0
            )
            
        historical_minutes = [g.minutes for g in historical_games]
        historical_avg = statistics.mean(historical_minutes)
        
        if historical_avg == 0:
            return RoleChange(
                detected=False,
                change_type="STABLE",
                minutes_change_pct=0.0,
                confidence_penalty=0.0
            )
            
        # Calculate percentage change
        change_pct = (recent_avg - historical_avg) / historical_avg
        
        # Detect if significant change
        detected = abs(change_pct) >= self.role_change_threshold
        
        if change_pct > self.role_change_threshold:
            change_type = "INCREASE"
            confidence_penalty = min(0.3, abs(change_pct) * 0.5)  # Max 30% penalty
        elif change_pct < -self.role_change_threshold:
            change_type = "DECREASE"
            confidence_penalty = min(0.3, abs(change_pct) * 0.5)
        else:
            change_type = "STABLE"
            confidence_penalty = 0.0
            
        return RoleChange(
            detected=detected,
            change_type=change_type,
            minutes_change_pct=change_pct * 100,
            confidence_penalty=confidence_penalty
        )

    def _calculate_volatility_penalty(
        self,
        game_log: List[GameLogEntry],
        stat_type: str,
        minutes_proj: MinutesProjection,
        primary_stats: RollingStats
    ) -> float:
        """
        Calculate Prop Volatility Index (PVI) penalty.
        
        Penalizes:
        - Bench players (avg minutes < 20)
        - Low-minute players (avg minutes < 15)
        - High standard deviation (std_dev > threshold)
        
        Args:
            game_log: List of game log entries
            stat_type: Type of stat being projected
            minutes_proj: Minutes projection object
            primary_stats: Rolling stats for the stat type
        
        Returns:
            Volatility score (0.0-1.0) where higher = more penalty
        """
        volatility_score = 0.0
        
        # Check if bench player (avg minutes < 20)
        if minutes_proj.historical_avg < 20:
            if minutes_proj.historical_avg < 15:
                volatility_score += 0.4  # Very low minutes
            else:
                volatility_score += 0.3  # Bench player
        
        # High standard deviation penalty
        if primary_stats.std_dev > 0:
            # Threshold depends on stat type
            if stat_type == 'points':
                threshold = 8.0  # Points: std_dev > 8 is high variance
            elif stat_type == 'rebounds':
                threshold = 5.0  # Rebounds: std_dev > 5 is high variance
            elif stat_type == 'assists':
                threshold = 4.0  # Assists: std_dev > 4 is high variance
            else:
                threshold = primary_stats.mean * 0.4  # 40% of mean
            
            if primary_stats.std_dev > threshold:
                volatility_score += 0.3
        
        # High minutes volatility (inconsistent playing time)
        if minutes_proj.volatility > 8.0:  # Standard deviation of minutes > 8
            volatility_score += 0.2
        
        # Cap at 1.0
        return min(volatility_score, 1.0)

    def _calculate_usage_proxy(
        self,
        games: List[GameLogEntry],
        stat_type: str = 'points'
    ) -> float:
        """
        PHASE 3: Calculate usage proxy (stat per 36 minutes).

        This simplified usage metric helps detect temporary role spikes
        (e.g., player scoring more due to injuries, hot streak).

        Args:
            games: List of game log entries
            stat_type: Stat to calculate (default: 'points')

        Returns:
            Stat value per 36 minutes (usage proxy)
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

        # Calculate per 36 minutes (standard NBA usage metric)
        per_36 = (total_stat / total_minutes) * 36.0
        return per_36

    def _calculate_probability_over_line(
        self,
        stat_type: str,
        expected_value: float,
        std_dev: float,
        prop_line: float
    ) -> float:
        """
        Calculate P(X >= prop_line) using appropriate distribution.
        
        Distributions:
        - Points → Negative binomial
        - 3s/steals/blocks → Poisson
        - Rebounds/assists → Zero-inflated Poisson
        - Minutes → Truncated normal
        - Default → Normal approximation
        """
        stat_lower = stat_type.lower()
        
        if stat_lower == "points":
            return self._negative_binomial_prob(expected_value, std_dev, prop_line)
        elif stat_lower in ["three_pt_made", "steals", "blocks"]:
            return self._poisson_prob(expected_value, prop_line)
        elif stat_lower in ["rebounds", "assists"]:
            return self._zero_inflated_poisson_prob(expected_value, std_dev, prop_line)
        elif stat_lower == "minutes":
            return self._truncated_normal_prob(expected_value, std_dev, prop_line, min_val=0.0, max_val=48.0)
        else:
            # Normal approximation
            if std_dev == 0:
                return 1.0 if expected_value >= prop_line else 0.0
            z_score = (prop_line - expected_value) / std_dev
            prob = self._normal_cdf(z_score)
            return 1.0 - prob
    
    def _normal_cdf(self, z: float) -> float:
        """Approximate standard normal CDF"""
        # Using error function approximation
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))
    
    def _poisson_prob(self, mean: float, threshold: float) -> float:
        """
        Calculate P(X >= threshold) for Poisson distribution.
        
        Uses cumulative distribution: P(X >= k) = 1 - sum(i=0 to k-1) of P(X=i)
        """
        if mean <= 0:
            return 0.0
        if threshold <= 0:
            return 1.0
            
        # For large means, use normal approximation
        if mean > 20:
            std_dev = math.sqrt(mean)
            z_score = (threshold - 0.5 - mean) / std_dev  # Continuity correction
            return 1.0 - self._normal_cdf(z_score)
        
        # For small means, calculate exact Poisson CDF
        k = int(math.floor(threshold))
        if k == 0:
            return 1.0
            
        # P(X >= k) = 1 - P(X < k) = 1 - sum(i=0 to k-1) of (lambda^i * e^-lambda) / i!
        prob_less = 0.0
        for i in range(k):
            prob_less += (mean ** i) * math.exp(-mean) / math.factorial(i)
            
        return 1.0 - prob_less
    
    def _negative_binomial_prob(self, mean: float, variance: float, threshold: float) -> float:
        """
        Calculate P(X >= threshold) for Negative Binomial distribution.
        
        Negative binomial is used for overdispersed count data (like points).
        Parameters: r (number of failures), p (success probability)
        Mean = r * p / (1-p)
        Variance = r * p / (1-p)^2
        
        For large means, use normal approximation.
        """
        if mean <= 0:
            return 0.0
        if threshold <= 0:
            return 1.0
            
        # Estimate parameters from mean and variance
        if variance <= mean:
            # Underdispersed - use Poisson instead
            return self._poisson_prob(mean, threshold)
            
        # Calculate r and p from mean and variance
        # mean = r * p / (1-p)
        # variance = r * p / (1-p)^2
        # variance / mean = 1 / (1-p) => p = 1 - mean / variance
        p = 1.0 - (mean / variance) if variance > mean else 0.5
        p = max(0.01, min(0.99, p))  # Clamp to valid range
        r = mean * (1.0 - p) / p
        
        # For large means, use normal approximation
        if mean > 15:
            std_dev = math.sqrt(variance)
            z_score = (threshold - 0.5 - mean) / std_dev
            return 1.0 - self._normal_cdf(z_score)
        
        # For smaller means, approximate using Poisson (simpler)
        # Negative binomial is complex to compute exactly
        return self._poisson_prob(mean, threshold)
    
    def _zero_inflated_poisson_prob(self, mean: float, variance: float, threshold: float) -> float:
        """
        Calculate P(X >= threshold) for Zero-Inflated Poisson distribution.
        
        Zero-inflated Poisson models data with excess zeros (like rebounds/assists).
        P(X = 0) = pi + (1-pi) * e^-lambda
        P(X = k) = (1-pi) * (lambda^k * e^-lambda) / k! for k > 0
        
        For simplicity, we approximate using the mean and adjust for zero inflation.
        """
        if mean <= 0:
            return 0.0
        if threshold <= 0:
            return 1.0
            
        # Estimate zero inflation parameter from variance
        # Higher variance relative to mean suggests more zero inflation
        if variance > mean * 1.5:
            # Significant zero inflation
            # Approximate: use Poisson but adjust threshold upward slightly
            adjusted_mean = mean * 1.1  # Slight adjustment
            return self._poisson_prob(adjusted_mean, threshold)
        else:
            # Less zero inflation, use standard Poisson
            return self._poisson_prob(mean, threshold)
    
    def _truncated_normal_prob(self, mean: float, std_dev: float, threshold: float, 
                                min_val: float = 0.0, max_val: float = 48.0) -> float:
        """
        Calculate P(X >= threshold) for Truncated Normal distribution.
        
        Used for minutes (bounded between 0 and 48).
        """
        if std_dev == 0:
            return 1.0 if mean >= threshold else 0.0
            
        # Truncated normal: adjust for bounds
        # P(X >= k | a <= X <= b) = [Phi((k - mu)/sigma) - Phi((a - mu)/sigma)] / [Phi((b - mu)/sigma) - Phi((a - mu)/sigma)]
        
        z_threshold = (threshold - mean) / std_dev
        z_min = (min_val - mean) / std_dev
        z_max = (max_val - mean) / std_dev
        
        # Standard normal CDFs
        phi_threshold = self._normal_cdf(z_threshold)
        phi_min = self._normal_cdf(z_min)
        phi_max = self._normal_cdf(z_max)
        
        # Normalization constant
        norm_const = phi_max - phi_min
        if norm_const == 0:
            return 1.0 if mean >= threshold else 0.0
            
        # P(X >= threshold) = 1 - P(X < threshold)
        prob_less = (phi_threshold - phi_min) / norm_const
        
        return 1.0 - prob_less
    
    def _calculate_historical_hit_rate(
        self,
        games: List[GameLogEntry],
        stat_type: str,
        prop_line: float
    ) -> float:
        """
        PHASE 6: Calculate historical hit rate (% of games player hit the prop line).

        This provides empirical evidence of how often the player actually
        exceeds this specific line, complementing the statistical probability.

        Args:
            games: List of game log entries
            stat_type: Stat type to check (points, rebounds, etc.)
            prop_line: The prop line to check against

        Returns:
            Hit rate as decimal (0.0 to 1.0)
        """
        if not games:
            return 0.5  # Neutral baseline with no data

        hits = 0
        for game in games:
            stat_value = getattr(game, stat_type, None)
            if stat_value is not None and stat_value > prop_line:
                hits += 1

        return hits / len(games)

    def _calculate_confidence_score(
        self,
        rolling_stats: RollingStats,
        minutes_proj: MinutesProjection,
        role_change: RoleChange,
        matchup_adj: MatchupAdjustments,
        historical_hit_rate: float
    ) -> float:
        """
        PHASE 6: NEW CONFIDENCE FORMULA (4 components)

        Components:
        1. Minutes stability (30%): Low volatility = stable role
        2. Role clarity (25%): No recent role changes or usage spikes
        3. Historical hit rate (25%): Empirical success rate on this line
        4. Matchup consistency (20%): Stable matchup factors

        Returns confidence score (0-100)
        """
        # 1. MINUTES STABILITY (30%): Stable role = higher confidence
        if minutes_proj.volatility < 4.0:
            minutes_score = 30.0  # Very stable (<4 min std dev)
        elif minutes_proj.volatility < 6.0:
            minutes_score = 22.0  # Stable (4-6 min std dev)
        elif minutes_proj.volatility < 8.0:
            minutes_score = 15.0  # Moderate (6-8 min std dev)
        else:
            minutes_score = 5.0   # Volatile (>8 min std dev)

        # 2. ROLE CLARITY (25%): No role changes or usage spikes
        if not role_change.detected:
            role_score = 25.0
        else:
            # Reduce score based on confidence penalty
            role_score = max(0.0, 25.0 - (role_change.confidence_penalty * 100))

        # 3. HISTORICAL HIT RATE (25%): Direct empirical evidence
        # hit_rate is 0.0-1.0, multiply by 25 for score
        hit_rate_score = historical_hit_rate * 25.0

        # 4. MATCHUP CONSISTENCY (20%): Stable matchup factors
        # Use matchup adjustment magnitude as proxy
        # Closer to 1.0 = more stable matchup
        matchup_deviation = abs(matchup_adj.total_adjustment - 1.0)
        if matchup_deviation < 0.05:  # Very stable (within 5%)
            matchup_score = 20.0
        elif matchup_deviation < 0.10:  # Stable (within 10%)
            matchup_score = 15.0
        elif matchup_deviation < 0.15:  # Moderate (within 15%)
            matchup_score = 10.0
        else:
            matchup_score = 5.0  # High variance matchup

        # Combine all components
        total = minutes_score + role_score + hit_rate_score + matchup_score

        return max(0.0, min(100.0, total))
    
    def _get_distribution_type(self, stat_type: str) -> str:
        """Get appropriate distribution type for stat"""
        stat_lower = stat_type.lower()
        
        if stat_lower == "points":
            return "negative_binomial"
        elif stat_lower in ["three_pt_made", "steals", "blocks"]:
            return "poisson"
        elif stat_lower in ["rebounds", "assists"]:
            return "zero_inflated_poisson"
        elif stat_lower == "minutes":
            return "truncated_normal"
        else:
            return "normal"

