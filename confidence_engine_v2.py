"""
Confidence Engine V2 - Fixes Overconfidence Bias
================================================
Implements realistic confidence scoring with:
1. Sample size-based confidence caps
2. Matchup & role weighting
3. Bayesian shrinkage for small samples
4. Volatility scoring
5. Injury context adjustments
6. Risk classifications

Usage:
    from confidence_engine_v2 import ConfidenceEngineV2
    
    engine = ConfidenceEngineV2()
    result = engine.calculate_confidence(
        sample_size=18,
        historical_hit_rate=0.75,
        projected_probability=0.87,
        stat_volatility=0.25,
        minutes_stable=False,
        role_change_detected=False,
        matchup_factors=matchup_data
    )
"""

import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Risk classification for bets"""
    LOW = "LOW"  # High sample, stable role, low volatility
    MEDIUM = "MEDIUM"  # One source of risk
    HIGH = "HIGH"  # Role change, low sample, or high volatility
    EXTREME = "EXTREME"  # Multiple risk factors - avoid in multis


@dataclass
class ConfidenceResult:
    """Complete confidence analysis result"""
    # Final scores
    final_confidence: float  # 0-100, capped by sample size
    adjusted_probability: float  # Probability after all adjustments
    risk_level: RiskLevel
    
    # Component scores
    base_confidence: float
    sample_size_cap: float  # Maximum allowed confidence
    volatility_penalty: float
    matchup_adjustment: float
    role_change_penalty: float
    
    # Bayesian adjustments
    bayesian_hit_rate: float  # Shrunk historical hit rate
    bayesian_probability: float  # Shrunk projected probability
    
    # Flags
    sufficient_sample: bool
    minutes_stable: bool
    role_stable: bool
    favorable_matchup: bool
    
    # Recommendations
    bet_recommendation: str  # "BET", "CONSIDER", "WATCH", "SKIP"
    multi_safe: bool  # Safe to include in multi-bets
    notes: list


class ConfidenceEngineV2:
    """
    Enhanced confidence engine that fixes overconfidence bias.
    """
    
    def __init__(self):
        # League averages for Bayesian priors
        self.league_avg_hit_rate = 0.50
        self.league_avg_probability = 0.50
        
        # Sample size thresholds
        self.sample_thresholds = {
            15: 0.75,  # n < 15: max 75% confidence
            30: 0.85,  # n < 30: max 85% confidence
            50: 0.90,  # n < 50: max 90% confidence
            80: 0.93,  # n < 80: max 93% confidence
            # n >= 80: max 95% confidence
        }
        
        # Volatility thresholds (coefficient of variation)
        self.low_volatility_threshold = 0.20  # CV < 20% = low volatility
        self.high_volatility_threshold = 0.40  # CV > 40% = high volatility
        
    def calculate_confidence(
        self,
        sample_size: int,
        historical_hit_rate: float,
        projected_probability: float,
        stat_mean: float,
        stat_std_dev: float,
        minutes_stable: bool,
        role_change_detected: bool,
        matchup_factors: Optional[Dict] = None,
        injury_context: Optional[Dict] = None
    ) -> ConfidenceResult:
        """
        Calculate realistic confidence score with all adjustments.
        
        Args:
            sample_size: Number of games in sample
            historical_hit_rate: Raw hit rate (0-1)
            projected_probability: Model's projected probability (0-1)
            stat_mean: Average stat value
            stat_std_dev: Standard deviation of stat
            minutes_stable: Whether minutes are stable (variance < 8)
            role_change_detected: Whether role change detected
            matchup_factors: Dict with pace, defense, opponent data
            injury_context: Dict with teammate injury impacts
            
        Returns:
            ConfidenceResult with complete analysis
        """
        notes = []
        
        # 1. APPLY SAMPLE SIZE CAP (Fix #1: Overconfidence)
        sample_size_cap = self._get_sample_size_cap(sample_size)
        sufficient_sample = sample_size >= 30
        
        if sample_size < 15:
            notes.append(f"Very small sample (n={sample_size}) - max confidence capped at 75%")
        elif sample_size < 30:
            notes.append(f"Small sample (n={sample_size}) - max confidence capped at 85%")
        
        # 2. BAYESIAN SHRINKAGE (Fix #3: Overweighting short samples)
        bayesian_hit_rate = self._apply_bayesian_shrinkage(
            observed_rate=historical_hit_rate,
            sample_size=sample_size,
            prior=self.league_avg_hit_rate
        )
        
        bayesian_probability = self._apply_bayesian_shrinkage(
            observed_rate=projected_probability,
            sample_size=sample_size,
            prior=self.league_avg_probability
        )
        
        shrinkage_amount = abs(historical_hit_rate - bayesian_hit_rate)
        if shrinkage_amount > 0.05:
            notes.append(f"Bayesian shrinkage applied: {shrinkage_amount:.1%} adjustment")
        
        # 3. CALCULATE VOLATILITY SCORE (Fix #4: Floor/ceiling volatility)
        volatility_score, volatility_penalty = self._calculate_volatility_penalty(
            stat_mean=stat_mean,
            stat_std_dev=stat_std_dev
        )
        
        if volatility_score > self.high_volatility_threshold:
            notes.append(f"High volatility detected (CV={volatility_score:.1%}) - confidence reduced")
        
        # 4. MATCHUP ADJUSTMENTS (Fix #2: Matchup & role weighting)
        matchup_adjustment, favorable_matchup = self._calculate_matchup_adjustment(
            matchup_factors=matchup_factors
        )
        
        if matchup_factors:
            notes.append(f"Matchup adjustment: {matchup_adjustment:+.1%}")
        
        # 5. ROLE CHANGE PENALTY
        role_change_penalty = 0.0
        if role_change_detected:
            role_change_penalty = 0.15  # 15% penalty
            notes.append("Role change detected - confidence reduced by 15%")
        
        # 6. MINUTES STABILITY
        if not minutes_stable:
            volatility_penalty += 0.05  # Additional 5% penalty
            notes.append("Minutes unstable - additional 5% penalty")
        
        # 7. INJURY CONTEXT (Fix #5: Injury adjustments)
        injury_adjustment = 0.0
        if injury_context:
            injury_adjustment = self._calculate_injury_adjustment(injury_context)
            if abs(injury_adjustment) > 0.02:
                notes.append(f"Injury context: {injury_adjustment:+.1%} adjustment")
        
        # 8. CALCULATE BASE CONFIDENCE
        # Start with blend of historical and projected (weighted by sample size)
        sample_weight = min(1.0, sample_size / 30.0)  # Full weight at 30+ games
        base_prob = (
            sample_weight * bayesian_hit_rate +
            (1 - sample_weight) * bayesian_probability
        )
        
        # Base confidence from probability (higher prob = higher confidence)
        # But not linear - use sigmoid-like curve
        base_confidence = self._probability_to_confidence(base_prob)
        
        # 9. APPLY ALL ADJUSTMENTS
        adjusted_confidence = base_confidence
        
        # Apply volatility penalty (multiplicative)
        adjusted_confidence *= (1.0 - volatility_penalty)
        
        # Apply role change penalty (multiplicative)
        adjusted_confidence *= (1.0 - role_change_penalty)
        
        # Apply matchup adjustment (additive, small)
        adjusted_confidence += matchup_adjustment * 10  # Scale to 0-10 points
        
        # Apply injury adjustment (additive)
        adjusted_confidence += injury_adjustment * 10
        
        # 10. APPLY SAMPLE SIZE CAP (Hard cap)
        final_confidence = min(adjusted_confidence, sample_size_cap * 100)
        
        # 11. CALCULATE ADJUSTED PROBABILITY
        # Adjust the probability based on matchup and injury factors
        adjusted_probability = base_prob + matchup_adjustment + injury_adjustment
        adjusted_probability = max(0.0, min(1.0, adjusted_probability))
        
        # 12. DETERMINE RISK LEVEL (Fix #6: Risk classifications)
        risk_level = self._determine_risk_level(
            sample_size=sample_size,
            volatility_score=volatility_score,
            minutes_stable=minutes_stable,
            role_change_detected=role_change_detected,
            sufficient_sample=sufficient_sample
        )
        
        # 13. BET RECOMMENDATION
        bet_recommendation, multi_safe = self._get_bet_recommendation(
            final_confidence=final_confidence,
            risk_level=risk_level,
            sample_size=sample_size
        )
        
        return ConfidenceResult(
            final_confidence=final_confidence,
            adjusted_probability=adjusted_probability,
            risk_level=risk_level,
            base_confidence=base_confidence,
            sample_size_cap=sample_size_cap,
            volatility_penalty=volatility_penalty,
            matchup_adjustment=matchup_adjustment,
            role_change_penalty=role_change_penalty,
            bayesian_hit_rate=bayesian_hit_rate,
            bayesian_probability=bayesian_probability,
            sufficient_sample=sufficient_sample,
            minutes_stable=minutes_stable,
            role_stable=not role_change_detected,
            favorable_matchup=favorable_matchup,
            bet_recommendation=bet_recommendation,
            multi_safe=multi_safe,
            notes=notes
        )
    
    def _get_sample_size_cap(self, n: int) -> float:
        """Get maximum confidence based on sample size"""
        if n < 15:
            return 0.75
        elif n < 30:
            return 0.85
        elif n < 50:
            return 0.90
        elif n < 80:
            return 0.93
        else:
            return 0.95
    
    def _apply_bayesian_shrinkage(
        self,
        observed_rate: float,
        sample_size: int,
        prior: float
    ) -> float:
        """
        Apply Bayesian shrinkage to prevent small sample flukes.
        
        Formula: (observed * n + prior * prior_weight) / (n + prior_weight)
        
        Prior weight decreases as sample size increases.
        """
        # Prior weight: strong for small samples, weak for large samples
        if sample_size < 10:
            prior_weight = 20  # Strong shrinkage
        elif sample_size < 20:
            prior_weight = 10  # Moderate shrinkage
        elif sample_size < 40:
            prior_weight = 5   # Light shrinkage
        else:
            prior_weight = 2   # Minimal shrinkage
        
        adjusted_rate = (
            (observed_rate * sample_size + prior * prior_weight) /
            (sample_size + prior_weight)
        )
        
        return adjusted_rate
    
    def _calculate_volatility_penalty(
        self,
        stat_mean: float,
        stat_std_dev: float
    ) -> Tuple[float, float]:
        """
        Calculate volatility score and confidence penalty.
        
        Returns:
            (volatility_score, penalty)
            volatility_score: Coefficient of variation (std_dev / mean)
            penalty: Confidence reduction (0.0 to 0.30)
        """
        if stat_mean <= 0:
            return 0.0, 0.0
        
        # Coefficient of variation
        cv = stat_std_dev / stat_mean
        
        # Calculate penalty based on CV
        if cv < self.low_volatility_threshold:
            # Low volatility: minimal penalty
            penalty = 0.0
        elif cv < self.high_volatility_threshold:
            # Medium volatility: moderate penalty (0-15%)
            penalty = (cv - self.low_volatility_threshold) / (
                self.high_volatility_threshold - self.low_volatility_threshold
            ) * 0.15
        else:
            # High volatility: heavy penalty (15-30%)
            penalty = 0.15 + min(0.15, (cv - self.high_volatility_threshold) * 0.5)
        
        return cv, penalty
    
    def _calculate_matchup_adjustment(
        self,
        matchup_factors: Optional[Dict]
    ) -> Tuple[float, bool]:
        """
        Calculate matchup-based probability adjustment.
        
        Returns:
            (adjustment, favorable)
            adjustment: Probability adjustment (-0.10 to +0.10)
            favorable: Whether matchup is favorable
        """
        if not matchup_factors:
            return 0.0, False
        
        adjustment = 0.0
        
        # Pace multiplier (faster pace = more opportunities)
        pace_mult = matchup_factors.get('pace_multiplier', 1.0)
        if pace_mult != 1.0:
            # Each 10% pace difference = 3% probability adjustment
            pace_adj = (pace_mult - 1.0) * 0.3
            adjustment += pace_adj
        
        # Defense adjustment (weaker defense = higher probability)
        defense_mult = matchup_factors.get('defense_adjustment', 1.0)
        if defense_mult != 1.0:
            # Each 10% defense difference = 5% probability adjustment
            defense_adj = (defense_mult - 1.0) * 0.5
            adjustment += defense_adj
        
        # Opponent ranking (if available)
        opp_rank = matchup_factors.get('opponent_defensive_rank')
        if opp_rank:
            # Top 10 defense: -3% adjustment
            # Bottom 10 defense: +3% adjustment
            if opp_rank <= 10:
                adjustment -= 0.03
            elif opp_rank >= 20:
                adjustment += 0.03
        
        # Cap adjustment at ±10%
        adjustment = max(-0.10, min(0.10, adjustment))
        
        favorable = adjustment > 0.02
        
        return adjustment, favorable
    
    def _calculate_injury_adjustment(self, injury_context: Dict) -> float:
        """
        Calculate probability adjustment based on teammate injuries.
        
        Args:
            injury_context: Dict with:
                - key_player_out: bool
                - usage_increase_expected: float (0-1)
                - assist_opportunities_impact: float (-1 to +1)
        
        Returns:
            Probability adjustment (-0.08 to +0.08)
        """
        adjustment = 0.0
        
        # Key player out increases usage
        if injury_context.get('key_player_out'):
            usage_increase = injury_context.get('usage_increase_expected', 0.0)
            adjustment += usage_increase * 0.08  # Up to 8% boost
        
        # Assist opportunities (e.g., if primary ball handler is out)
        assist_impact = injury_context.get('assist_opportunities_impact', 0.0)
        adjustment += assist_impact * 0.05  # Up to ±5% adjustment
        
        # Cap at ±8%
        return max(-0.08, min(0.08, adjustment))
    
    def _probability_to_confidence(self, probability: float) -> float:
        """
        Convert probability to confidence score (0-100).
        
        Uses sigmoid-like curve:
        - 50% probability → 50 confidence
        - 70% probability → 70 confidence
        - 85% probability → 85 confidence
        - 95% probability → 90 confidence (diminishing returns)
        """
        # Simple mapping with diminishing returns at extremes
        if probability < 0.5:
            # Below 50%: scale 0-50
            return probability * 100
        else:
            # Above 50%: diminishing returns
            # Use log curve: 50 + 40 * log((p-0.5)/0.5 + 1) / log(2)
            excess = probability - 0.5
            confidence = 50 + 40 * math.log(excess / 0.5 + 1) / math.log(2)
            return min(95, confidence)
    
    def _determine_risk_level(
        self,
        sample_size: int,
        volatility_score: float,
        minutes_stable: bool,
        role_change_detected: bool,
        sufficient_sample: bool
    ) -> RiskLevel:
        """Determine risk classification"""
        risk_factors = 0
        
        # Count risk factors
        if not sufficient_sample:
            risk_factors += 1
        if volatility_score > self.high_volatility_threshold:
            risk_factors += 1
        if not minutes_stable:
            risk_factors += 1
        if role_change_detected:
            risk_factors += 1
        
        # Classify
        if risk_factors == 0:
            return RiskLevel.LOW
        elif risk_factors == 1:
            return RiskLevel.MEDIUM
        elif risk_factors == 2:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME
    
    def _get_bet_recommendation(
        self,
        final_confidence: float,
        risk_level: RiskLevel,
        sample_size: int
    ) -> Tuple[str, bool]:
        """
        Get betting recommendation and multi-bet safety.
        
        Returns:
            (recommendation, multi_safe)
        """
        # Multi-bet safety: only LOW and MEDIUM risk
        multi_safe = risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        
        # Recommendation based on confidence and risk
        if risk_level == RiskLevel.EXTREME:
            return "SKIP", False
        
        if final_confidence >= 80 and risk_level == RiskLevel.LOW:
            return "BET", True
        elif final_confidence >= 75 and risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]:
            return "BET", multi_safe
        elif final_confidence >= 70:
            return "CONSIDER", multi_safe
        elif final_confidence >= 60:
            return "WATCH", False
        else:
            return "SKIP", False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def rate_todays_bets_with_improved_logic(recommendations: list) -> list:
    """
    Re-rate today's bets using improved confidence logic.
    
    Takes existing recommendations and applies V2 confidence engine.
    """
    engine = ConfidenceEngineV2()
    
    rerated_bets = []
    
    for rec in recommendations:
        # Extract data from recommendation
        sample_size = rec.get('sample_size', 0)
        historical_hit_rate = rec.get('historical_hit_rate', 0.5)
        projected_probability = rec.get('projected_probability', 0.5)
        
        # Get stat volatility from databallr_stats
        databallr_stats = rec.get('databallr_stats', {})
        avg_value = databallr_stats.get('avg_value', 0)
        
        # Estimate std dev (assume CV of 0.25 if not available)
        stat_std_dev = avg_value * 0.25 if avg_value > 0 else 0
        
        # Get advanced context
        advanced_context = rec.get('advanced_context', {})
        minutes_analysis = advanced_context.get('minutes_analysis', {})
        minutes_stable = minutes_analysis.get('stable', True)
        
        # Check for role change (if minutes trending significantly)
        role_change_detected = False
        if minutes_analysis:
            trending = minutes_analysis.get('trending', 'stable')
            variance = minutes_analysis.get('variance', 0)
            if trending != 'stable' and variance > 10:
                role_change_detected = True
        
        # Matchup factors (if available)
        matchup_factors = rec.get('matchup_factors')
        
        # Calculate new confidence
        confidence_result = engine.calculate_confidence(
            sample_size=sample_size,
            historical_hit_rate=historical_hit_rate,
            projected_probability=projected_probability,
            stat_mean=avg_value,
            stat_std_dev=stat_std_dev,
            minutes_stable=minutes_stable,
            role_change_detected=role_change_detected,
            matchup_factors=matchup_factors,
            injury_context=None
        )
        
        # Update recommendation
        rec['confidence_score_v2'] = confidence_result.final_confidence
        rec['adjusted_probability_v2'] = confidence_result.adjusted_probability
        rec['risk_level'] = confidence_result.risk_level.value
        rec['bet_recommendation'] = confidence_result.bet_recommendation
        rec['multi_safe'] = confidence_result.multi_safe
        rec['confidence_notes'] = confidence_result.notes
        
        # Update original confidence for comparison
        rec['confidence_score_v1'] = rec.get('confidence_score', 0)
        rec['confidence_score'] = confidence_result.final_confidence
        
        rerated_bets.append(rec)
    
    return rerated_bets


if __name__ == '__main__':
    # Example usage
    engine = ConfidenceEngineV2()
    
    # Test case: Jaden McDaniels Rebounds Over 3.5
    result = engine.calculate_confidence(
        sample_size=20,
        historical_hit_rate=0.85,
        projected_probability=0.86,
        stat_mean=4.75,
        stat_std_dev=1.5,
        minutes_stable=False,  # 11.5 variance
        role_change_detected=False,
        matchup_factors={
            'pace_multiplier': 1.02,
            'defense_adjustment': 1.0
        }
    )
    
    print("="*70)
    print("CONFIDENCE ENGINE V2 - TEST")
    print("="*70)
    print(f"Final Confidence: {result.final_confidence:.1f}%")
    print(f"Adjusted Probability: {result.adjusted_probability:.1%}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Recommendation: {result.bet_recommendation}")
    print(f"Multi-Safe: {result.multi_safe}")
    print(f"\nSample Size Cap: {result.sample_size_cap:.0%}")
    print(f"Volatility Penalty: {result.volatility_penalty:.1%}")
    print(f"Matchup Adjustment: {result.matchup_adjustment:+.1%}")
    print(f"\nNotes:")
    for note in result.notes:
        print(f"  - {note}")
