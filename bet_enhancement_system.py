"""
Bet Enhancement System - Advanced Filtering & Display
=====================================================
Implements sophisticated filtering and tier classification for betting recommendations:

1. Quality Tier Classification (S/A/B/C/D)
2. Sample Size Weighting Penalty
3. Conflict Score for Correlated Bets
4. Line Difficulty Filter
5. Market Efficiency Check
6. Consistency Ranking
7. EV-to-Prob Ratio Filter
8. True Fair Odds Display
9. Projected Margin vs Line
10. Auto-Sorting

Usage:
    from bet_enhancement_system import BetEnhancementSystem

    enhancer = BetEnhancementSystem()
    enhanced_bets = enhancer.enhance_recommendations(recommendations)
    enhancer.display_enhanced_bets(enhanced_bets)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class QualityTier(Enum):
    """Quality tiers for betting recommendations"""
    S = "S-Tier (Elite Value)"
    A = "A-Tier (High Quality)"
    B = "B-Tier (Playable)"
    C = "C-Tier (Do Not Bet - Pass)"
    D = "D-Tier (Avoid)"


class ConsistencyLevel(Enum):
    """Player consistency classification"""
    HIGH = "🔥 High Consistency"
    MEDIUM = "👍 Medium Consistency"
    LOW = "⚠️ Low Consistency"


@dataclass
class EnhancedBet:
    """Enhanced betting recommendation with all metrics"""
    # Original recommendation data
    original_rec: Dict

    # Core metrics
    player_name: Optional[str] = None
    market: str = ""
    selection: str = ""
    line: Optional[float] = None
    odds: float = 0.0

    # Probabilities & Value
    projected_probability: float = 0.0
    implied_probability: float = 0.0
    edge_percentage: float = 0.0
    expected_value: float = 0.0

    # Enhanced Metrics
    quality_tier: QualityTier = QualityTier.D
    tier_emoji: str = "❌"

    # Sample Size Analysis
    sample_size: int = 0
    sample_size_penalty: float = 0.0
    effective_confidence: float = 0.0

    # Correlation & Conflicts
    correlation_penalty: float = 0.0
    conflict_score: float = 0.0

    # Line Difficulty
    line_difficulty_penalty: float = 0.0

    # Market Efficiency
    market_efficiency_flag: bool = False
    passes_efficiency_check: bool = True

    # Consistency
    consistency_rank: Optional[ConsistencyLevel] = None
    consistency_score: float = 0.0

    # EV Ratio
    ev_to_prob_ratio: float = 0.0
    passes_ev_ratio: bool = True

    # Fair Odds
    fair_odds: float = 0.0
    odds_mispricing: float = 0.0

    # Projection Margin
    projected_value: Optional[float] = None
    projection_margin: float = 0.0

    # Minutes Stability
    minutes_stability_penalty: float = 0.0
    minutes_variance: float = 0.0
    minutes_volatility_score: float = 0.0  # NEW: 0-10 scale
    minutes_volatility_label: str = ""     # NEW: Very Stable, Stable, etc.

    # Injury / Role Change (NEW)
    role_change_detected: bool = False
    role_change_type: str = ""  # "increased_usage", "decreased_usage", "teammate_out"
    role_change_impact: float = 0.0  # % projection adjustment

    # Line Efficiency (shaded lines)
    line_shaded: bool = False
    line_movement: float = 0.0
    expected_line_movement: str = ""  # NEW: "OVER", "UNDER", "STABLE"
    line_movement_urgency: str = ""   # NEW: "BET_NOW", "MONITOR", "WAIT"

    # Sharp/Public Indicator (NEW)
    sharp_public_indicator: str = ""  # "SHARP_OVER", "PUBLIC_OVER", "BALANCED"
    betting_pressure: str = ""  # "Heavy Over", "Heavy Under", "Balanced"

    # Final Scores
    adjusted_confidence: float = 0.0
    final_score: float = 0.0

    # Context
    game: str = ""
    player_team: Optional[str] = None
    opponent_team: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# BET ENHANCEMENT SYSTEM
# ============================================================================

class BetEnhancementSystem:
    """
    Comprehensive bet enhancement system with advanced filtering and classification
    """

    def __init__(self):
        # Quality tier thresholds
        self.tier_thresholds = {
            'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
            'A': {'ev_min': 10.0, 'edge_min': 8.0},
            'B': {'ev_min': 5.0, 'edge_min': 4.0},
            'C': {'ev_min': 1.0, 'conf_min': 70.0},
        }

        # Sample size baseline
        self.sample_baseline = 5

        # Line difficulty thresholds
        self.high_line_threshold = 30.0
        self.extreme_line_threshold = 35.0

        # Market efficiency thresholds
        self.low_edge_threshold = 3.0
        self.sharp_prob_range = (0.55, 0.60)
        self.high_confidence_override = 85.0

        # EV ratio threshold
        self.min_ev_ratio = 0.08

        # Consistency thresholds
        self.high_consistency_threshold = 0.80
        self.medium_consistency_threshold = 0.60

    def enhance_recommendations(self, recommendations: List[Dict]) -> List[EnhancedBet]:
        """
        Apply all enhancements to betting recommendations

        Args:
            recommendations: List of betting recommendation dicts

        Returns:
            List of EnhancedBet objects with all metrics calculated
        """
        enhanced_bets = []

        # First pass: create enhanced bet objects
        for rec in recommendations:
            enhanced = self._create_enhanced_bet(rec)
            enhanced_bets.append(enhanced)

        # Second pass: calculate correlation penalties (requires all bets)
        self._calculate_correlation_penalties(enhanced_bets)

        # Third pass: check for excessive correlation and downgrade to C-tier if needed
        self._check_excessive_correlation(enhanced_bets)

        # Fourth pass: recalculate final scores with all adjustments
        for bet in enhanced_bets:
            self._calculate_final_score(bet)

        # Sort by quality
        enhanced_bets = self._sort_bets(enhanced_bets)

        return enhanced_bets

    def _create_enhanced_bet(self, rec: Dict) -> EnhancedBet:
        """Create enhanced bet from recommendation dict"""
        # Extract core data
        player_name = rec.get('player_name')
        market = rec.get('market', '')
        selection = rec.get('selection', '')
        line = rec.get('line')
        odds = rec.get('odds', 0.0)

        # Extract metrics
        proj_prob = rec.get('projected_probability', 0.0)
        impl_prob = rec.get('implied_probability', 0.0)
        edge = rec.get('edge_percentage', 0.0)
        ev = rec.get('expected_value', 0.0)
        confidence = rec.get('confidence_score', 0.0)

        # Create base enhanced bet
        bet = EnhancedBet(
            original_rec=rec,
            player_name=player_name,
            market=market,
            selection=selection,
            line=line,
            odds=odds,
            projected_probability=proj_prob,
            implied_probability=impl_prob,
            edge_percentage=edge,
            expected_value=ev,
            game=rec.get('game', ''),
            player_team=rec.get('player_team'),
            opponent_team=rec.get('opponent_team'),
            sample_size=rec.get('sample_size', 0),
            projected_value=rec.get('projected_value')
        )

        # Apply enhancements
        self._classify_quality_tier(bet, confidence)
        self._calculate_sample_size_penalty(bet, confidence)
        self._calculate_line_difficulty_penalty(bet)
        self._check_market_efficiency(bet, confidence)
        self._calculate_consistency_rank(bet)
        self._calculate_ev_ratio(bet)
        self._calculate_fair_odds(bet)
        self._calculate_projection_margin(bet)
        self._calculate_minutes_stability(bet)
        self._detect_role_changes(bet)
        self._check_line_efficiency(bet)
        self._predict_line_movement(bet)
        self._detect_sharp_public(bet)

        return bet

    def _classify_quality_tier(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 1. Classify bet into quality tier (S/A/B/C/D)

        Tiers:
        - S-Tier: EV ≥ +20 AND Edge ≥ +12% AND Prob ≥ 68%
        - A-Tier: EV ≥ +10 AND Edge ≥ +8% AND Prob ≥ 75%
        - B-Tier: EV ≥ +5 AND Edge ≥ +4%
        - C-Tier (Do Not Bet): Any of:
            * Edge < 5%
            * Confidence < 60%
            * Mispricing < 0.10
            * Sample < 5
            * Correlation > 2 props same game (checked later)
        - D-Tier: EV < 0 OR Prob < 50%
        """
        ev = bet.expected_value
        edge = bet.edge_percentage
        prob = bet.projected_probability

        # D-Tier (Avoid) - negative value
        if ev < 0 or prob < 0.50:
            bet.quality_tier = QualityTier.D
            bet.tier_emoji = "❌"
            return

        # S-Tier (Elite)
        if ev >= 20.0 and edge >= 12.0 and prob >= 0.68:
            bet.quality_tier = QualityTier.S
            bet.tier_emoji = "💎"
            bet.notes.append("ELITE VALUE: All metrics exceed premium thresholds")
            return

        # A-Tier (High Quality) - MUST have ≥75% projection probability
        if ev >= 10.0 and edge >= 8.0 and prob >= 0.75:
            bet.quality_tier = QualityTier.A
            bet.tier_emoji = "⭐"
            return

        # B-Tier (Playable) - Further relaxed criteria to allow more bets through
        # Original: EV >= 5.0 AND Edge >= 4.0
        # Relaxed: EV >= 1.0 AND Edge >= 1.5 (or any positive EV with Edge >= 2.0)
        if (ev >= 1.0 and edge >= 1.5) or (ev > 0 and edge >= 2.0):
            bet.quality_tier = QualityTier.B
            bet.tier_emoji = "✓"
            return

        # C-Tier (Do Not Bet) - fails quality checks
        # These have positive EV but fail one or more critical thresholds
        # Relaxed thresholds to allow more bets through
        c_tier_reasons = []

        if edge < 3.0:  # Relaxed from 5.0 to 3.0
            c_tier_reasons.append(f"Low edge ({edge:.1f}% < 3%)")

        if confidence < 55.0:  # Relaxed from 60.0 to 55.0
            c_tier_reasons.append(f"Low confidence ({confidence:.0f}% < 55%)")

        # Mispricing will be calculated later, but we can check if odds are available
        if bet.odds > 0:
            fair_odds_estimate = 1.0 / prob if prob > 0 else 0
            mispricing_estimate = bet.odds - fair_odds_estimate
            if mispricing_estimate < 0.10:
                c_tier_reasons.append(f"Low mispricing ({mispricing_estimate:.2f} < 0.10)")

        if bet.sample_size < 5:
            c_tier_reasons.append(f"Small sample (n={bet.sample_size} < 5)")

        # If any C-tier criteria met, mark as C-tier
        if c_tier_reasons:
            bet.quality_tier = QualityTier.C
            bet.tier_emoji = "⛔"
            bet.warnings.append(f"DO NOT BET - Quality issues: {'; '.join(c_tier_reasons)}")
            return

        # If positive EV but didn't meet B-tier, also mark as C-tier
        if ev >= 1.0:
            bet.quality_tier = QualityTier.C
            bet.tier_emoji = "⛔"
            bet.warnings.append("DO NOT BET - Marginal value, fails tier criteria")
            return

        # Default to D-Tier
        bet.quality_tier = QualityTier.D
        bet.tier_emoji = "❌"

    def _calculate_sample_size_penalty(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 2. Calculate sample size weighting penalty

        Formula: effective_confidence = confidence - (5 - sample_size) * 4  if sample_size < 5

        Examples:
        - n=5 → zero penalty
        - n=3 → minus 8 confidence points
        - n=1 → minus 16 confidence points
        """
        n = bet.sample_size

        if n >= self.sample_baseline:
            bet.sample_size_penalty = 0.0
            bet.effective_confidence = confidence
        else:
            # Penalty: (5 - n) * 4
            penalty = (self.sample_baseline - n) * 4.0
            bet.sample_size_penalty = penalty
            bet.effective_confidence = max(0.0, confidence - penalty)

            if penalty > 0:
                bet.warnings.append(f"Small sample penalty: -{penalty:.0f} confidence points (n={n})")

    def _calculate_correlation_penalties(self, bets: List[EnhancedBet]):
        """
        ✅ 3. Calculate conflict score for correlated bets (SCALED BY PROJECTION MARGIN)

        Penalties scaled by projection margin:
        - Same team AND same stat:
            * proj_margin < 2.0 → penalty -10
            * proj_margin 2-4 → penalty -6
            * proj_margin > 4 → penalty -4
        - Same game AND same stat:
            * proj_margin < 2.0 → penalty -10
            * proj_margin 2-4 → penalty -6
            * proj_margin > 4 → penalty -4
        """
        for i, bet in enumerate(bets):
            max_penalty = 0.0
            conflicts = []

            for j, other in enumerate(bets):
                if i == j:
                    continue

                # Check correlation
                same_game = bet.game == other.game
                player_team = bet.original_rec.get('player_team')
                other_team = other.original_rec.get('player_team')

                # Only check team correlation if both teams are known
                same_team = (player_team == other_team and
                            player_team not in [None, 'Unknown', ''] and
                            other_team not in [None, 'Unknown', ''])

                same_stat = self._extract_stat_type(bet.market) == self._extract_stat_type(other.market)

                penalty = 0.0

                if same_team and same_stat and bet.player_name and other.player_name:
                    # Scale penalty by projection distance between players
                    penalty = self._get_scaled_correlation_penalty(bet, other)
                    proj_dist = abs(bet.projected_value - other.projected_value) if bet.projected_value and other.projected_value else 0
                    conflicts.append(f"Same team ({player_team}) + stat ({self._extract_stat_type(bet.market)}, {proj_dist:.1f}pts apart)")
                elif same_game and same_stat and bet.player_name and other.player_name:
                    # Scale penalty by projection distance between players
                    penalty = self._get_scaled_correlation_penalty(bet, other)
                    proj_dist = abs(bet.projected_value - other.projected_value) if bet.projected_value and other.projected_value else 0
                    conflicts.append(f"Same game + stat ({self._extract_stat_type(bet.market)}, {proj_dist:.1f}pts apart)")

                max_penalty = min(max_penalty, penalty)  # Most negative

            bet.correlation_penalty = max_penalty
            bet.conflict_score = abs(max_penalty)

            if conflicts:
                bet.warnings.append(f"Correlation detected: {conflicts[0]}")

    def _check_excessive_correlation(self, bets: List[EnhancedBet]):
        """
        Check for >2 props in the same game and downgrade to C-tier (Do Not Bet).

        This prevents over-exposure to a single game.
        """
        # Count props per game
        game_prop_counts: Dict[str, List[EnhancedBet]] = {}

        for bet in bets:
            if bet.player_name:  # Only count player props
                game = bet.game
                if game not in game_prop_counts:
                    game_prop_counts[game] = []
                game_prop_counts[game].append(bet)

        # Check each game
        for game, game_bets in game_prop_counts.items():
            if len(game_bets) > 2:
                # More than 2 props in same game - downgrade excess to C-tier
                # Sort by final_score to keep the best 2
                sorted_bets = sorted(game_bets, key=lambda b: b.projected_probability, reverse=True)

                # Downgrade all but top 2
                for bet in sorted_bets[2:]:
                    # Only downgrade if currently better than C-tier
                    if bet.quality_tier in [QualityTier.S, QualityTier.A, QualityTier.B]:
                        bet.quality_tier = QualityTier.C
                        bet.tier_emoji = "⛔"
                        bet.warnings.append(f"DO NOT BET - Excessive correlation: >2 props in {game}")

    def _get_scaled_correlation_penalty(self, bet1: EnhancedBet, bet2: EnhancedBet) -> float:
        """
        ✅ ENHANCED: Calculate correlation penalty based on projection distance

        For same game + same stat, scale penalty by how far apart projections are:
        - If projections < 3 points apart → penalty -12 (direct competition)
        - If 3-6 apart → penalty -8 (some overlap)
        - If > 6 apart → penalty -5 (different tiers)

        This prevents over-penalizing when players don't compete for same volume.

        Args:
            bet1: First bet
            bet2: Second bet

        Returns:
            Penalty value (negative)
        """
        # Get projected values (use line if projection not available)
        proj1 = bet1.projected_value if bet1.projected_value else bet1.line if bet1.line else 0
        proj2 = bet2.projected_value if bet2.projected_value else bet2.line if bet2.line else 0

        # Calculate distance between projections
        if proj1 > 0 and proj2 > 0:
            proj_distance = abs(proj1 - proj2)

            # Scale penalty by projection distance
            if proj_distance < 3.0:
                return -12.0  # Close projections = direct competition
            elif proj_distance <= 6.0:
                return -8.0   # Moderate distance = some overlap
            else:
                return -5.0   # Large distance = different tiers
        else:
            # Fallback to original margin-based logic if projections not available
            proj_margin = bet1.projection_margin
            if proj_margin < 2.0:
                return -10.0
            elif proj_margin <= 4.0:
                return -6.0
            else:
                return -4.0

    def _extract_stat_type(self, market: str) -> str:
        """Extract stat type from market string"""
        market_lower = market.lower()

        if 'point' in market_lower or 'pts' in market_lower:
            return 'points'
        elif 'assist' in market_lower or 'ast' in market_lower:
            return 'assists'
        elif 'rebound' in market_lower or 'reb' in market_lower:
            return 'rebounds'
        elif 'three' in market_lower or '3' in market_lower:
            return 'threes'
        elif 'steal' in market_lower or 'stl' in market_lower:
            return 'steals'
        elif 'block' in market_lower or 'blk' in market_lower:
            return 'blocks'

        return market_lower

    def _calculate_line_difficulty_penalty(self, bet: EnhancedBet):
        """
        ✅ 4. Calculate line difficulty penalty

        Harder lines (30+, 35+) get penalized:
        - Line ≥ 30: -5 penalty
        - Line ≥ 35: -10 penalty
        """
        if bet.line is None:
            bet.line_difficulty_penalty = 0.0
            return

        line = bet.line

        if line >= self.extreme_line_threshold:
            bet.line_difficulty_penalty = -10.0
            bet.warnings.append(f"Extreme line ({line}) - very volatile")
        elif line >= self.high_line_threshold:
            bet.line_difficulty_penalty = -5.0
            bet.warnings.append(f"High line ({line}) - increased volatility")
        else:
            bet.line_difficulty_penalty = 0.0

    def _check_market_efficiency(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 5. Market efficiency check override

        If edge < 3% AND prob between 55-60%:
            hide unless confidence > 85
        """
        edge = bet.edge_percentage
        prob = bet.projected_probability

        # Check if in sharp market zone
        in_sharp_zone = (self.sharp_prob_range[0] <= prob <= self.sharp_prob_range[1])
        low_edge = edge < self.low_edge_threshold

        if in_sharp_zone and low_edge:
            bet.market_efficiency_flag = True

            if confidence <= self.high_confidence_override:
                bet.passes_efficiency_check = False
                bet.warnings.append(f"Sharp market: Edge {edge:.1f}% < {self.low_edge_threshold}% in efficient zone")
            else:
                bet.passes_efficiency_check = True
                bet.notes.append(f"Overrides efficiency check with {confidence:.0f}% confidence")
        else:
            bet.passes_efficiency_check = True

    def _calculate_consistency_rank(self, bet: EnhancedBet):
        """
        ✅ 6. Calculate consistency rank

        consistency = 1 - (standard_deviation / season_average)

        Levels:
        - High: 0.80+
        - Medium: 0.60-0.80
        - Low: <0.60
        """
        # Try to get stats from databallr_stats
        stats = bet.original_rec.get('databallr_stats', {})
        avg = stats.get('avg_value', 0)

        # Estimate std dev if not available (assume CV of 25%)
        std_dev = avg * 0.25 if avg > 0 else 0

        # Calculate consistency
        if avg > 0:
            consistency = 1.0 - (std_dev / avg)
            consistency = max(0.0, min(1.0, consistency))
            bet.consistency_score = consistency

            if consistency >= self.high_consistency_threshold:
                bet.consistency_rank = ConsistencyLevel.HIGH
            elif consistency >= self.medium_consistency_threshold:
                bet.consistency_rank = ConsistencyLevel.MEDIUM
            else:
                bet.consistency_rank = ConsistencyLevel.LOW
                bet.warnings.append(f"Low consistency ({consistency:.1%}) - volatile player")
        else:
            bet.consistency_rank = None
            bet.consistency_score = 0.0

    def _calculate_ev_ratio(self, bet: EnhancedBet):
        """
        ✅ 7. Calculate EV-to-Prob ratio

        EV_ratio = EV / probability

        Filter out: EV_ratio < 0.05 (relaxed from 0.08)
        """
        if bet.projected_probability > 0:
            bet.ev_to_prob_ratio = bet.expected_value / (bet.projected_probability * 100)
        else:
            bet.ev_to_prob_ratio = 0.0

        # Relaxed threshold: 0.05 instead of 0.08
        min_ev_ratio_relaxed = 0.05
        if bet.ev_to_prob_ratio < min_ev_ratio_relaxed:
            bet.passes_ev_ratio = False
            bet.warnings.append(f"Low EV/Prob ratio ({bet.ev_to_prob_ratio:.3f} < {min_ev_ratio_relaxed})")
        else:
            bet.passes_ev_ratio = True

    def _calculate_fair_odds(self, bet: EnhancedBet):
        """
        ✅ 8. Calculate true fair odds

        Fair Odds = 1 / Probability
        Mispricing = Market Odds - Fair Odds
        """
        if bet.projected_probability > 0:
            bet.fair_odds = 1.0 / bet.projected_probability
            bet.odds_mispricing = bet.odds - bet.fair_odds
        else:
            bet.fair_odds = 0.0
            bet.odds_mispricing = 0.0

    def _calculate_projection_margin(self, bet: EnhancedBet):
        """
        ✅ 9. Calculate projected margin vs line

        projection_margin = projected - line
        """
        if bet.projected_value is not None and bet.line is not None:
            bet.projection_margin = bet.projected_value - bet.line

            if bet.projection_margin > 0:
                bet.notes.append(f"Projected {bet.projection_margin:+.1f} vs line")
        else:
            bet.projection_margin = 0.0

    def _calculate_minutes_stability(self, bet: EnhancedBet):
        """
        ✅ ENHANCED: Calculate minutes volatility score (0-10 scale)

        Analyzes minutes variance from advanced context.

        Volatility Score (0-10):
        - 0-2: Very Stable
        - 3-4: Stable
        - 5-6: Moderate
        - 7-8: Volatile
        - 9-10: Very Volatile

        Formula: vol = std_dev(last_5) / avg(last_5), score = clamp(vol * 10, 0, 10)
        """
        # Try to get minutes analysis from advanced context
        advanced_ctx = bet.original_rec.get('advanced_context', {})
        minutes_analysis = advanced_ctx.get('minutes_analysis', {})

        if minutes_analysis:
            recent_avg = minutes_analysis.get('recent_avg', 0)
            variance = minutes_analysis.get('variance', 0)
            stable = minutes_analysis.get('stable', True)

            bet.minutes_variance = variance

            # Calculate variance percentage and volatility score
            if recent_avg > 0:
                variance_pct = (variance / recent_avg) * 100

                # Calculate volatility score (0-10 scale)
                # Standard deviation / average gives coefficient of variation
                # Multiply by 10 to get 0-10 scale
                volatility_score = min(10.0, max(0.0, (variance / recent_avg) * 10))
                bet.minutes_volatility_score = volatility_score

                # Assign label based on score
                if volatility_score <= 2.0:
                    bet.minutes_volatility_label = "Very Stable"
                    bet.minutes_stability_penalty = 0.0
                    bet.notes.append(f"✓ Minutes Volatility: {volatility_score:.1f}/10 (Very Stable)")
                elif volatility_score <= 4.0:
                    bet.minutes_volatility_label = "Stable"
                    bet.minutes_stability_penalty = 0.0
                    bet.notes.append(f"✓ Minutes Volatility: {volatility_score:.1f}/10 (Stable)")
                elif volatility_score <= 6.0:
                    bet.minutes_volatility_label = "Moderate"
                    bet.minutes_stability_penalty = -2.0
                    bet.warnings.append(f"Minutes Volatility: {volatility_score:.1f}/10 (Moderate) - {variance:.1f}min variance")
                elif volatility_score <= 8.0:
                    bet.minutes_volatility_label = "Volatile"
                    bet.minutes_stability_penalty = -5.0
                    bet.warnings.append(f"Minutes Volatility: {volatility_score:.1f}/10 (Volatile) - {variance:.1f}min variance")
                else:
                    bet.minutes_volatility_label = "Very Volatile"
                    bet.minutes_stability_penalty = -8.0
                    bet.warnings.append(f"⚠ Minutes Volatility: {volatility_score:.1f}/10 (VERY VOLATILE) - Unreliable minutes")
            else:
                bet.minutes_stability_penalty = 0.0
                bet.minutes_volatility_score = 0.0
                bet.minutes_volatility_label = "Unknown"
        else:
            # No minutes data available
            bet.minutes_stability_penalty = 0.0
            bet.minutes_volatility_score = 0.0
            bet.minutes_volatility_label = "Unknown"

    def _detect_role_changes(self, bet: EnhancedBet):
        """
        ✅ NEW: Detect injury/role change alerts

        Detects:
        - Increased usage last 3 games (role expansion)
        - Decreased usage (role reduction)
        - Teammate out (opportunity boost)

        Adds projection adjustments and alerts.
        """
        advanced_ctx = bet.original_rec.get('advanced_context', {})

        # Check for rebounding context (has recent_form for comparison)
        rebounding_ctx = advanced_ctx.get('rebounding_context', {})
        if rebounding_ctx:
            recent_form = rebounding_ctx.get('recent_form', 0)

            # Get databallr stats for season average comparison
            databallr_stats = bet.original_rec.get('databallr_stats', {})
            season_avg = databallr_stats.get('avg_value', 0)

            if recent_form > 0 and season_avg > 0:
                # Calculate % change in recent form vs season
                pct_change = ((recent_form - season_avg) / season_avg) * 100

                # Significant increase (>15%) = role expansion
                if pct_change > 15.0:
                    bet.role_change_detected = True
                    bet.role_change_type = "increased_usage"
                    bet.role_change_impact = pct_change
                    bet.notes.append(f"⬆ Role Shift: +{pct_change:.1f}% usage last 3 games")

                # Significant decrease (<-15%) = role reduction
                elif pct_change < -15.0:
                    bet.role_change_detected = True
                    bet.role_change_type = "decreased_usage"
                    bet.role_change_impact = pct_change
                    bet.warnings.append(f"⬇ Role Shift: {pct_change:.1f}% usage decline")

        # Check minutes for role changes
        minutes_analysis = advanced_ctx.get('minutes_analysis', {})
        if minutes_analysis:
            recent_avg = minutes_analysis.get('recent_avg', 0)
            season_avg = minutes_analysis.get('season_avg', 0)
            trending = minutes_analysis.get('trending', '')

            if recent_avg > 0 and season_avg > 0:
                minutes_change = ((recent_avg - season_avg) / season_avg) * 100

                # Significant minutes increase
                if minutes_change > 10.0:
                    bet.role_change_detected = True
                    if not bet.role_change_type:  # Don't overwrite if already set
                        bet.role_change_type = "increased_minutes"
                        bet.role_change_impact = minutes_change
                    bet.notes.append(f"⬆ Minutes Trend: +{minutes_change:.1f}% ({trending})")

                # Significant minutes decrease
                elif minutes_change < -10.0:
                    bet.role_change_detected = True
                    if not bet.role_change_type:
                        bet.role_change_type = "decreased_minutes"
                        bet.role_change_impact = minutes_change
                    bet.warnings.append(f"⬇ Minutes Trend: {minutes_change:.1f}% ({trending})")

        # Check for teammate impact (placeholder - would need injury data)
        # This would be populated if we had injury/lineup data
        matchup_factors = bet.original_rec.get('matchup_factors', {})
        if matchup_factors:
            # Future enhancement: Check for key teammate absences
            # For now, just note if matchup factors exist
            pass

    def _check_line_efficiency(self, bet: EnhancedBet):
        """
        ✅ NEW: Check for line efficiency / shaded lines

        Lines can be shaded by books on:
        - Star players
        - Highly bet overs
        - Back-to-backs
        - Blowout risk

        Currently marks potential shading based on:
        - High lines (30+) for points
        - High implied probability (books getting action)

        Future: Could integrate real-time line movement data
        """
        # Check for potential line shading indicators
        line = bet.line
        odds = bet.odds
        impl_prob = bet.implied_probability

        shading_indicators = []

        # High line on points (books often shade these)
        if line and line >= 30.0 and 'point' in bet.market.lower():
            shading_indicators.append("High points line (30+)")

        # Very low odds = heavy juice = potential shading
        if odds < 1.70:
            shading_indicators.append("Heavy juice (odds < 1.70)")

        # Implied probability > 60% but not a huge favorite
        if impl_prob > 0.60 and impl_prob < 0.75:
            shading_indicators.append("Moderate favorite (potential public action)")

        if shading_indicators:
            bet.line_shaded = True
            bet.warnings.append(f"Potential line shading: {', '.join(shading_indicators)}")
        else:
            bet.line_shaded = False

        # Note: Line movement would require historical data
        # For now, set to 0 (future enhancement)
        bet.line_movement = 0.0

    def _predict_line_movement(self, bet: EnhancedBet):
        """
        ✅ NEW: Predict expected line movement

        Logic:
        - If projection > fair > book → Line likely moves to OVER (bet now!)
        - If projection < fair < book → Line likely moves to UNDER (wait)
        - Otherwise → Stable

        Adds urgency flags:
        - BET_NOW: Line will move against you
        - MONITOR: Watch for movement
        - WAIT: Line may improve
        """
        proj_prob = bet.projected_probability
        fair_odds = bet.fair_odds
        book_odds = bet.odds

        # Convert odds to implied probabilities for comparison
        fair_prob = 1.0 / fair_odds if fair_odds > 0 else 0
        book_prob = bet.implied_probability

        # Determine if it's an over or under bet
        is_over = "over" in bet.selection.lower()

        if is_over:
            # For OVER bets: higher probability = more likely to hit
            if proj_prob > fair_prob > book_prob:
                # Our projection is better than fair, fair is better than book
                # Line will likely move UP (worse for us)
                bet.expected_line_movement = "OVER (Line moving up)"
                bet.line_movement_urgency = "BET_NOW"
                bet.notes.append("🔥 BET NOW: Line likely to move against you")
            elif proj_prob > book_prob and abs(proj_prob - book_prob) > 0.05:
                # Significant edge
                bet.expected_line_movement = "OVER (Moderate)"
                bet.line_movement_urgency = "MONITOR"
                bet.notes.append("📊 MONITOR: Line may tighten")
            elif proj_prob < book_prob:
                # Book favors over more than we do
                bet.expected_line_movement = "STABLE/DOWN"
                bet.line_movement_urgency = "WAIT"
                bet.warnings.append("⏳ WAIT: Line may improve (book overvaluing)")
            else:
                bet.expected_line_movement = "STABLE"
                bet.line_movement_urgency = "NORMAL"
        else:
            # For UNDER bets: logic is reversed
            if proj_prob > fair_prob > book_prob:
                bet.expected_line_movement = "UNDER (Line moving down)"
                bet.line_movement_urgency = "BET_NOW"
                bet.notes.append("🔥 BET NOW: Line likely to move in our favor")
            elif proj_prob > book_prob:
                bet.expected_line_movement = "UNDER (Moderate)"
                bet.line_movement_urgency = "MONITOR"
            else:
                bet.expected_line_movement = "STABLE"
                bet.line_movement_urgency = "NORMAL"

    def _detect_sharp_public(self, bet: EnhancedBet):
        """
        ✅ NEW: Detect sharp vs public money

        Without real line movement data, we infer from:
        1. Odds vs our projection (sharp agreement)
        2. Implied probability zones (public favorites)
        3. Odds value (heavy favorites = public)

        Indicators:
        - SHARP_OVER: Sharp money agrees with over
        - PUBLIC_OVER: Public betting over (fade)
        - SHARP_UNDER: Sharp money on under
        - PUBLIC_UNDER: Public on under
        - BALANCED: No clear bias
        """
        proj_prob = bet.projected_probability
        impl_prob = bet.implied_probability
        odds = bet.odds
        edge = bet.edge_percentage

        # Check if our projection aligns with a value line
        is_over = "over" in bet.selection.lower()

        # Sharp indicators:
        # 1. Positive edge (we agree with sharps)
        # 2. Odds in efficient range (1.70-2.20)
        # 3. Not heavily juiced

        has_sharp_agreement = edge > 3.0 and 1.70 <= odds <= 2.20
        has_public_pattern = (impl_prob > 0.65 and odds < 1.70) or (impl_prob < 0.45 and odds > 2.30)

        if is_over:
            if has_sharp_agreement:
                bet.sharp_public_indicator = "SHARP_OVER"
                bet.betting_pressure = "Sharp money on OVER"
                bet.notes.append("💰 Sharp Agreement: Professional money on OVER")
            elif has_public_pattern and impl_prob > 0.65:
                bet.sharp_public_indicator = "PUBLIC_OVER"
                bet.betting_pressure = "Public heavy on OVER"
                bet.warnings.append("⚠ Public Favorite: Heavy retail action (fade candidate)")
            elif edge < -5.0:
                bet.sharp_public_indicator = "SHARP_UNDER"
                bet.betting_pressure = "Sharp money on UNDER"
                bet.warnings.append("⚠ Sharp Disagreement: Pros favor UNDER")
            else:
                bet.sharp_public_indicator = "BALANCED"
                bet.betting_pressure = "Balanced"
        else:
            # UNDER bets - reverse logic
            if has_sharp_agreement:
                bet.sharp_public_indicator = "SHARP_UNDER"
                bet.betting_pressure = "Sharp money on UNDER"
                bet.notes.append("💰 Sharp Agreement: Professional money on UNDER")
            elif has_public_pattern:
                bet.sharp_public_indicator = "PUBLIC_UNDER"
                bet.betting_pressure = "Public heavy on UNDER"
                bet.warnings.append("⚠ Public Favorite: Heavy retail action")
            else:
                bet.sharp_public_indicator = "BALANCED"
                bet.betting_pressure = "Balanced"

    def _calculate_final_score(self, bet: EnhancedBet):
        """
        Calculate final adjusted confidence with all penalties applied
        """
        # Start with effective confidence (after sample size penalty)
        score = bet.effective_confidence

        # Apply correlation penalty
        score += bet.correlation_penalty

        # Apply line difficulty penalty
        score += bet.line_difficulty_penalty

        # Apply minutes stability penalty
        score += bet.minutes_stability_penalty

        # Store final adjusted confidence
        bet.adjusted_confidence = max(0.0, min(100.0, score))

        # Calculate final score for sorting (weights different factors)
        bet.final_score = (
            bet.adjusted_confidence * 0.4 +
            bet.expected_value * 2.0 +
            bet.edge_percentage * 3.0 +
            bet.projected_probability * 50.0
        )

    def _sort_bets(self, bets: List[EnhancedBet]) -> List[EnhancedBet]:
        """
        ✅ 10. Auto-sorting rules

        Sort by:
        1. Tier (S > A > B > C > D)
        2. EV (descending)
        3. Edge (descending)
        4. Adjusted Confidence (descending)
        5. Projection Margin (descending)
        """
        tier_order = {
            QualityTier.S: 0,
            QualityTier.A: 1,
            QualityTier.B: 2,
            QualityTier.C: 3,
            QualityTier.D: 4
        }

        return sorted(bets, key=lambda b: (
            tier_order[b.quality_tier],
            -b.expected_value,
            -b.edge_percentage,
            -b.adjusted_confidence,
            -b.projection_margin
        ))

    def filter_bets(self, bets: List[EnhancedBet],
                   min_tier: QualityTier = QualityTier.C,
                   exclude_d_tier: bool = True) -> List[EnhancedBet]:
        """
        Filter bets based on quality tier and efficiency checks

        Args:
            bets: List of enhanced bets
            min_tier: Minimum tier to include
            exclude_d_tier: Exclude D-Tier bets

        Returns:
            Filtered list of bets
        """
        tier_order = {
            QualityTier.S: 0,
            QualityTier.A: 1,
            QualityTier.B: 2,
            QualityTier.C: 3,
            QualityTier.D: 4
        }

        min_tier_value = tier_order[min_tier]

        filtered = []
        for bet in bets:
            # Check tier
            if tier_order[bet.quality_tier] > min_tier_value:
                continue

            # Exclude D-Tier if requested
            if exclude_d_tier and bet.quality_tier == QualityTier.D:
                continue

            # Check efficiency - RELAXED: Allow more bets through
            # Only reject if clearly inefficient (very low edge in efficient zone)
            if not bet.passes_efficiency_check:
                # Override: If it's B-Tier or better, allow it through anyway
                if bet.quality_tier in [QualityTier.S, QualityTier.A, QualityTier.B]:
                    pass  # Allow through despite efficiency check
                else:
                    continue

            # Check EV ratio - RELAXED: Lower threshold
            if not bet.passes_ev_ratio:
                # Override: If it's B-Tier or better, allow it through anyway
                if bet.quality_tier in [QualityTier.S, QualityTier.A, QualityTier.B]:
                    pass  # Allow through despite EV ratio check
                else:
                    continue

            filtered.append(bet)

        return filtered

    def display_enhanced_bets(self, bets: List[EnhancedBet], max_display: int = 20):
        """
        Display enhanced bets with all metrics in a readable format
        """
        print("=" * 100)
        print("ENHANCED BETTING RECOMMENDATIONS")
        print("=" * 100)
        print()

        # Group by tier
        tiers = {}
        for bet in bets:
            tier = bet.quality_tier
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(bet)

        # Display by tier
        for tier in [QualityTier.S, QualityTier.A, QualityTier.B, QualityTier.C, QualityTier.D]:
            if tier not in tiers:
                continue

            tier_bets = tiers[tier][:max_display]

            if not tier_bets:
                continue

            print(f"\n{'='*100}")
            print(f"{tier.value} ({len(tier_bets)} bets)")
            print(f"{'='*100}\n")

            for i, bet in enumerate(tier_bets, 1):
                self._display_single_bet(bet, i)
                print()

    def _display_single_bet(self, bet: EnhancedBet, index: int):
        """Display a single enhanced bet - CLEAN 5-SIGNAL MODEL"""
        # Header with team name
        team_info = ""
        if bet.player_team and bet.player_team != "Unknown":
            team_info = f" ({bet.player_team})"
        print(f"{index}. {bet.tier_emoji} {bet.player_name or 'TEAM'}{team_info} - {bet.market} {bet.selection}")

        # Signal 1: Odds & Mispricing (Market Inefficiency)
        print(f"   Odds {bet.odds:.2f} → Fair {bet.fair_odds:.2f} (Mispricing {bet.odds_mispricing:+.2f})")

        # Signal 2: EV + Edge + Projected Probability
        print(f"   Edge {bet.edge_percentage:+.1f}% | EV {bet.expected_value:+.1f}% | Projected {bet.projected_probability:.1%}")

        # Signal 3: Confidence (already includes all adjustments)
        print(f"   Confidence: {bet.adjusted_confidence:.0f}%")

        # Signal 4: Expected Line Movement (timing signal)
        movement_label = self._get_movement_label(bet)
        if movement_label:
            print(f"   Movement: {movement_label}")

        # Signal 5: ONE Warning Max (most important only)
        primary_warning = self._get_primary_warning(bet)
        if primary_warning:
            print(f"   Warning: {primary_warning}")

    def _get_movement_label(self, bet: EnhancedBet) -> str:
        """Get clean movement label (NOW • WAIT • MONITOR • STABLE)"""
        if bet.line_movement_urgency == "BET_NOW":
            return "NOW (line moving against you)"
        elif bet.line_movement_urgency == "WAIT":
            return "WAIT (line may improve)"
        elif bet.line_movement_urgency == "MONITOR":
            return "MONITOR (likely to tighten)"
        else:
            return "STABLE"

    def _get_primary_warning(self, bet: EnhancedBet) -> str:
        """
        Get ONLY the most important warning (priority order)

        Priority:
        1. Negative edge (bad bet)
        2. Small sample (unreliable)
        3. High correlation (parlay risk)
        4. Public heavy (fading opportunity)
        5. High volatility (unreliable minutes)
        6. Role decline (negative trend)
        """
        # Check for critical issues first
        if bet.edge_percentage < 0:
            return "Negative edge - avoid"

        if bet.sample_size < 5:
            return f"Small sample (n={bet.sample_size})"

        # Correlation (most impactful for parlays)
        if bet.correlation_penalty < -8:
            return "High correlation (same game)"
        elif bet.correlation_penalty < 0:
            return "Moderate correlation (same game)"

        # Public/Sharp signals
        if bet.sharp_public_indicator == "PUBLIC_OVER" or bet.sharp_public_indicator == "PUBLIC_UNDER":
            return "Public heavy (fade candidate)"

        if bet.sharp_public_indicator == "SHARP_UNDER" and "over" in bet.selection.lower():
            return "Sharp disagreement (pros on under)"

        # Volatility issues
        if bet.minutes_volatility_score >= 7.0:
            return f"High minutes volatility ({bet.minutes_volatility_score:.1f}/10)"

        # Role changes
        if bet.role_change_detected and bet.role_change_type == "decreased_usage":
            return f"Usage declining ({bet.role_change_impact:.1f}%)"

        # Line difficulty
        if bet.line_difficulty_penalty < -8:
            return f"Extreme line ({bet.line:.1f})"

        # Default: no major warning
        return ""


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == '__main__':
    import json
    import sys
    import io

    # Fix Windows encoding for Unicode characters
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Load recommendations
    try:
        with open('betting_recommendations.json', 'r') as f:
            recommendations = json.load(f)
    except FileNotFoundError:
        print("No betting_recommendations.json found. Run nba_betting_system.py first.")
        exit(1)

    print(f"Loaded {len(recommendations)} recommendations")

    # Enhance
    enhancer = BetEnhancementSystem()
    enhanced_bets = enhancer.enhance_recommendations(recommendations)

    # Filter to quality bets only
    quality_bets = enhancer.filter_bets(enhanced_bets, min_tier=QualityTier.C, exclude_d_tier=True)

    print(f"After filtering: {len(quality_bets)} quality bets (C-Tier or better)\n")

    # Display
    enhancer.display_enhanced_bets(quality_bets, max_display=15)

    # Save enhanced bets
    enhanced_output = []
    for bet in quality_bets:
        bet_dict = bet.original_rec.copy()
        bet_dict['enhanced_metrics'] = {
            'quality_tier': bet.quality_tier.name,
            'tier_emoji': bet.tier_emoji,
            'effective_confidence': bet.effective_confidence,
            'adjusted_confidence': bet.adjusted_confidence,
            'sample_size_penalty': bet.sample_size_penalty,
            'correlation_penalty': bet.correlation_penalty,
            'line_difficulty_penalty': bet.line_difficulty_penalty,
            'consistency_rank': bet.consistency_rank.value if bet.consistency_rank else None,
            'consistency_score': bet.consistency_score,
            'ev_to_prob_ratio': bet.ev_to_prob_ratio,
            'fair_odds': bet.fair_odds,
            'odds_mispricing': bet.odds_mispricing,
            'projection_margin': bet.projection_margin,
            'final_score': bet.final_score,
            'notes': bet.notes,
            'warnings': bet.warnings
        }
        enhanced_output.append(bet_dict)

    # Also save ALL enhancement metrics (V2 and V2.5)
    for i, bet in enumerate(quality_bets):
        if i < len(enhanced_output):
            enhanced_output[i]['enhanced_metrics'].update({
                # V2 features
                'minutes_stability_penalty': bet.minutes_stability_penalty,
                'minutes_variance': bet.minutes_variance,
                'line_shaded': bet.line_shaded,
                'line_movement': bet.line_movement,
                # V2.5 NEW features
                'minutes_volatility_score': bet.minutes_volatility_score,
                'minutes_volatility_label': bet.minutes_volatility_label,
                'role_change_detected': bet.role_change_detected,
                'role_change_type': bet.role_change_type,
                'role_change_impact': bet.role_change_impact,
                'expected_line_movement': bet.expected_line_movement,
                'line_movement_urgency': bet.line_movement_urgency,
                'sharp_public_indicator': bet.sharp_public_indicator,
                'betting_pressure': bet.betting_pressure
            })

    with open('betting_recommendations_enhanced.json', 'w') as f:
        json.dump(enhanced_output, f, indent=2, default=str)

    print("\n✓ Saved enhanced recommendations to betting_recommendations_enhanced.json")
