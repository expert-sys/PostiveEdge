"""
Enhanced Value Engine - Improved statistical analysis with Bayesian smoothing,
sample size filters, and context adjustments.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from value_engine import ValueEngine, HistoricalData, MarketConfig, ValueAnalysis, OutcomeType
import math


@dataclass
class ContextFactors:
    """Context adjustments for more accurate probability estimation."""
    expected_minutes: Optional[float] = None  # Player's expected minutes (0-48)
    opponent_rank: Optional[int] = None  # Opponent defensive ranking (1-30)
    pace: Optional[float] = None  # Team pace (possessions per game)
    is_home: Optional[bool] = None  # Home vs Away
    days_rest: Optional[int] = None  # Days since last game
    injuries: Optional[List[str]] = None  # Key injuries
    back_to_back: bool = False  # Playing on consecutive days


@dataclass
class EnhancedValueAnalysis(ValueAnalysis):
    """Extended analysis with confidence and context."""
    confidence_score: float = 0.0  # 0-100
    confidence_level: str = "LOW"  # LOW, MEDIUM, HIGH, VERY HIGH
    bayesian_adjusted: bool = False
    context_adjustment: float = 0.0  # Percentage adjustment from context
    effective_sample_size: float = 0.0  # After Bayesian adjustment


class EnhancedValueEngine(ValueEngine):
    """Enhanced engine with Bayesian smoothing and context adjustments."""

    def __init__(self):
        super().__init__()
        # Bayesian prior settings (league average for most props is ~50%)
        self.default_bayesian_prior = 0.5

        # Adaptive prior weight based on sample size
        # Smaller samples get more shrinkage toward prior
        self.base_prior_weight = 15

        # Minimum sample thresholds
        self.absolute_minimum = 4  # Don't show if n < 4
        self.baseline_sample_size = 6.5  # Baseline for predictions (6-7)
        self.confidence_threshold = 6  # Baseline confidence at 6-7

    def calculate_adaptive_prior_weight(self, sample_size: int) -> float:
        """
        Calculate adaptive prior weight based on sample size.
        6-7 is baseline with minimal shrinkage. Smaller samples get more shrinkage.

        Returns: prior weight (higher = more shrinkage toward prior)
        """
        if sample_size >= 6 and sample_size <= 7:
            return 2  # Baseline: minimal shrinkage (favor the data)
        elif sample_size >= 8:
            return 2  # Above baseline: minimal shrinkage
        elif sample_size >= 4:
            return 5  # Below baseline: moderate shrinkage
        else:
            return self.base_prior_weight  # Very small: maximum shrinkage

    def apply_adaptive_bayesian_smoothing(
        self,
        success_count: int,
        total_count: int,
        prior_probability: float = None
    ) -> tuple[float, float]:
        """
        Apply adaptive Bayesian smoothing with sample-size dependent weighting.

        Returns: (adjusted_probability, effective_sample_size)
        """
        if prior_probability is None:
            prior_probability = self.default_bayesian_prior

        # Calculate adaptive prior weight
        prior_weight = self.calculate_adaptive_prior_weight(total_count)

        # Bayesian adjustment
        adjusted_prob = (success_count + prior_weight * prior_probability) / (total_count + prior_weight)

        # Effective sample size
        effective_n = total_count + prior_weight

        return adjusted_prob, effective_n

    def calculate_confidence_score(
        self,
        sample_size: int,
        variance: Optional[float] = None
    ) -> tuple[float, str]:
        """
        Calculate confidence score (0-100) and level based on sample size.

        Confidence levels:
        - VERY HIGH: n >= 15, score 85-100
        - HIGH: n >= 10, score 70-84
        - MEDIUM: n >= 6, score 50-69
        - LOW: n >= 4, score 25-49
        - VERY LOW: n < 4, score 0-24

        Returns: (confidence_score, confidence_level)
        """
        # Base score from sample size (6-7 is baseline)
        if sample_size >= 6 and sample_size <= 7:
            base_score = 70  # Baseline: good confidence
        elif sample_size >= 8:
            base_score = 75  # Above baseline: slightly higher
        elif sample_size >= 10:
            base_score = 80
        elif sample_size >= 15:
            base_score = 85
        elif sample_size >= 20:
            base_score = 95
        elif sample_size >= 4:
            base_score = 50  # Below baseline: reduced but not penalized heavily
        else:
            base_score = 25

        # Adjust for variance if provided
        if variance is not None:
            # Lower variance = higher confidence
            variance_penalty = min(20, variance * 100)
            base_score -= variance_penalty

        # Ensure 0-100 range
        score = max(0, min(100, base_score))

        # Determine level
        if score >= 85:
            level = "VERY HIGH"
        elif score >= 70:
            level = "HIGH"
        elif score >= 50:
            level = "MEDIUM"
        elif score >= 25:
            level = "LOW"
        else:
            level = "VERY LOW"

        return score, level

    def apply_context_adjustments(
        self,
        base_probability: float,
        context: ContextFactors
    ) -> tuple[float, float]:
        """
        Apply context-based adjustments to probability.

        Returns: (adjusted_probability, total_adjustment_percentage)
        """
        adjustment = 0.0

        # Minutes adjustment (playing time matters)
        if context.expected_minutes is not None:
            if context.expected_minutes >= 32:
                adjustment += 0.03  # Starter, more opportunity
            elif context.expected_minutes < 20:
                adjustment -= 0.05  # Bench player, less opportunity

        # Opponent strength (for scoring props)
        if context.opponent_rank is not None:
            # Top 10 defense = harder to score
            if context.opponent_rank <= 10:
                adjustment -= 0.04
            # Bottom 10 defense = easier to score
            elif context.opponent_rank >= 21:
                adjustment += 0.04

        # Pace adjustment (faster pace = more opportunities)
        if context.pace is not None:
            league_avg_pace = 100.0
            if context.pace > league_avg_pace + 3:
                adjustment += 0.03  # Fast pace
            elif context.pace < league_avg_pace - 3:
                adjustment -= 0.03  # Slow pace

        # Home vs Away
        if context.is_home is not None:
            if context.is_home:
                adjustment += 0.02  # Home court advantage
            else:
                adjustment -= 0.02  # Road disadvantage

        # Rest/fatigue
        if context.back_to_back:
            adjustment -= 0.04  # Fatigue factor
        elif context.days_rest is not None and context.days_rest >= 3:
            adjustment += 0.02  # Well rested

        # Apply adjustment
        adjusted_prob = max(0.01, min(0.99, base_probability + adjustment))
        adjustment_pct = adjustment * 100

        return adjusted_prob, adjustment_pct

    def analyze_market_enhanced(
        self,
        historical_data: HistoricalData,
        config: MarketConfig,
        context: Optional[ContextFactors] = None
    ) -> EnhancedValueAnalysis:
        """
        Perform enhanced value analysis with Bayesian smoothing and context.
        """
        sample_size = len(historical_data.outcomes)

        # FILTER 1: Absolute minimum sample size
        if sample_size < self.absolute_minimum:
            # Don't analyze - insufficient data
            return None

        sufficient_sample = sample_size >= config.minimum_sample_size

        # Calculate raw historical probability
        raw_hist_probability = self.calculate_historical_probability(
            historical_data,
            config.outcome_type,
            config.threshold
        )

        # ENHANCEMENT 1: Apply Adaptive Bayesian Smoothing
        # Always apply to reduce overconfidence, but less for larger samples
        if config.outcome_type == OutcomeType.BINARY:
            success_count = sum(1 for o in historical_data.outcomes if o == 1)
            adjusted_prob, effective_n = self.apply_adaptive_bayesian_smoothing(
                success_count,
                sample_size,
                self.default_bayesian_prior
            )
            bayesian_adjusted = True
            notes = f"Bayesian smoothing applied (n={sample_size}, effective_n={effective_n:.1f})"
        else:
            adjusted_prob = raw_hist_probability
            effective_n = sample_size
            bayesian_adjusted = False
            notes = f"Analysis based on {sample_size} observations"

        # ENHANCEMENT 2: Calculate confidence
        # Calculate variance for confidence scoring
        if config.outcome_type == OutcomeType.BINARY:
            variance = adjusted_prob * (1 - adjusted_prob)
        else:
            variance = None

        confidence_score, confidence_level = self.calculate_confidence_score(
            sample_size,
            variance
        )

        # FILTER 2: Only reduce confidence for very small samples (below baseline)
        if sample_size < 6:
            confidence_score *= 0.85  # Slight reduction (15%) for below baseline
            if confidence_level == "HIGH":
                confidence_level = "MEDIUM"
            notes += f" | Below baseline sample size (n={sample_size}, baseline=6-7)"

        # ENHANCEMENT 3: Apply context adjustments
        context_adjustment = 0.0
        if context is not None:
            final_prob, context_adjustment = self.apply_context_adjustments(
                adjusted_prob,
                context
            )
            notes += f" | Context adjustment: {context_adjustment:+.1f}%"
        else:
            final_prob = adjusted_prob

        # Convert to odds
        implied_odds = self.convert_probability_to_odds(final_prob)
        if implied_odds is None:
            implied_odds = self.convert_probability_to_odds(config.fallback_probability)
            notes += " | Invalid probability, using fallback"
            final_prob = config.fallback_probability

        # Calculate bookmaker probability
        bookmaker_prob = self.convert_odds_to_probability(config.bookmaker_odds)

        # Calculate edge and value
        edge = config.bookmaker_odds - implied_odds
        value_pct = self.calculate_value_percentage(final_prob, bookmaker_prob)

        # Calculate EV
        ev = self.calculate_ev(final_prob, config.bookmaker_odds, stake=1.0)
        ev_per_100 = self.calculate_ev(final_prob, config.bookmaker_odds, stake=100)

        # Determine if has value
        has_value = final_prob > bookmaker_prob

        return EnhancedValueAnalysis(
            event_type=config.event_type,
            sample_size=sample_size,
            historical_probability=final_prob,
            implied_odds=implied_odds,
            bookmaker_odds=config.bookmaker_odds,
            bookmaker_probability=bookmaker_prob,
            edge_in_odds=edge,
            value_percentage=value_pct,
            ev_per_unit=ev,
            expected_return_per_100=ev_per_100,
            has_value=has_value,
            sufficient_sample=sufficient_sample,
            analysis_notes=notes,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            bayesian_adjusted=bayesian_adjusted,
            context_adjustment=context_adjustment,
            effective_sample_size=effective_n
        )


# Convenience function for simple analysis
def analyze_simple_market_enhanced(
    event_type: str,
    historical_outcomes: List[int],
    bookmaker_odds: float,
    outcome_type: str = "binary",
    minimum_sample_size: int = 4,
    context: Optional[ContextFactors] = None
) -> Optional[EnhancedValueAnalysis]:
    """
    Simple interface for market analysis with enhancements.

    Returns None if sample size < 4 (absolute minimum)
    """
    engine = EnhancedValueEngine()

    hist_data = HistoricalData(outcomes=historical_outcomes)

    config = MarketConfig(
        event_type=event_type,
        outcome_type=OutcomeType.BINARY if outcome_type == "binary" else OutcomeType.CONTINUOUS,
        bookmaker_odds=bookmaker_odds,
        minimum_sample_size=minimum_sample_size
    )

    return engine.analyze_market_enhanced(hist_data, config, context)
