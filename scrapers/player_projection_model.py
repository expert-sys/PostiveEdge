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
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# Import data structures
from scrapers.nba_stats_api_scraper import GameLogEntry
from scrapers.sportsbet_final_enhanced import TeamStats, MatchStats


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
    change_type: str  # "INCREASE", "DECREASE", "STABLE"
    minutes_change_pct: float
    confidence_penalty: float  # 0.0 to 1.0 (reduces confidence if role changed)


@dataclass
class StatProjection:
    """Complete stat projection result"""
    expected_value: float
    variance: float
    std_dev: float
    probability_over_line: float  # P(X >= prop_line)
    confidence_score: float  # 0-100
    rolling_stats_5: Optional[RollingStats] = None
    rolling_stats_10: Optional[RollingStats] = None
    rolling_stats_20: Optional[RollingStats] = None
    minutes_projection: Optional[MinutesProjection] = None
    matchup_adjustments: Optional[MatchupAdjustments] = None
    role_change: Optional[RoleChange] = None
    distribution_type: str = "normal"  # "normal", "poisson", "negative_binomial", "zero_inflated_poisson"


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
        
        # 4. Detect role changes
        role_change = self._detect_role_change(valid_games)
        
        # 5. Adjust base projection for minutes and matchup
        base_expected = primary_stats.weighted_mean
        
        # Minutes adjustment: scale by projected minutes ratio
        minutes_adjusted = base_expected * minutes_proj.minutes_ratio
        
        # Matchup adjustment: apply pace and defense multipliers
        adjusted_expected = minutes_adjusted * matchup_adj.total_adjustment
        
        # 6. Calculate variance (use primary stats variance, adjusted for minutes)
        adjusted_variance = primary_stats.variance * (minutes_proj.minutes_ratio ** 2)
        adjusted_std_dev = math.sqrt(adjusted_variance)
        
        # 7. Calculate probability using appropriate distribution
        prob_over_line = self._calculate_probability_over_line(
            stat_type, adjusted_expected, adjusted_std_dev, prop_line
        )
        
        # 8. Calculate confidence score
        confidence = self._calculate_confidence_score(
            primary_stats, minutes_proj, role_change, matchup_adj
        )
        
        return StatProjection(
            expected_value=adjusted_expected,
            variance=adjusted_variance,
            std_dev=adjusted_std_dev,
            probability_over_line=prob_over_line,
            confidence_score=confidence,
            rolling_stats_5=rolling_stats_5,
            rolling_stats_10=rolling_stats_10,
            rolling_stats_20=rolling_stats_20,
            minutes_projection=minutes_proj,
            matchup_adjustments=matchup_adj,
            role_change=role_change,
            distribution_type=self._get_distribution_type(stat_type)
        )
    
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
                minutes_ratio=1.0
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
            minutes_ratio=minutes_ratio
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
    
    def _detect_role_change(self, games: List[GameLogEntry]) -> RoleChange:
        """Detect role changes based on minutes trends"""
        if len(games) < 10:
            return RoleChange(
                detected=False,
                change_type="STABLE",
                minutes_change_pct=0.0,
                confidence_penalty=0.0
            )
            
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
    
    def _calculate_confidence_score(
        self,
        rolling_stats: RollingStats,
        minutes_proj: MinutesProjection,
        role_change: RoleChange,
        matchup_adj: MatchupAdjustments
    ) -> float:
        """Calculate confidence score (0-100)"""
        # Base confidence from sample size
        sample_size_score = min(100, rolling_stats.sample_size * 5)  # 20 games = 100
        
        # Consistency score (inverse of coefficient of variation)
        if rolling_stats.mean > 0:
            cv = rolling_stats.std_dev / rolling_stats.mean
            consistency_score = max(0, 100 - (cv * 100))
        else:
            consistency_score = 50
            
        # Minutes stability (lower volatility = higher confidence)
        if minutes_proj.historical_avg > 0:
            minutes_cv = minutes_proj.volatility / minutes_proj.historical_avg
            minutes_stability = max(0, 100 - (minutes_cv * 50))
        else:
            minutes_stability = 50
            
        # Role change penalty
        role_penalty = role_change.confidence_penalty * 100
        
        # Weighted combination
        confidence = (
            0.4 * sample_size_score +
            0.3 * consistency_score +
            0.3 * minutes_stability -
            role_penalty
        )
        
        return max(0, min(100, confidence))
    
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

