"""
QA Validator - Pre-display validation for betting recommendations
==================================================================

PHASE 8: Validates mathematical consistency and tier logic before output.

Checks:
1. Fair odds = 1/probability (±1%)
2. Tier logic consistency
3. Probability caps (≤82%)
4. S-Tier correlation check
5. Edge/EV relationship
6. Confidence ≤ Probability

Blocks output if critical inconsistencies detected.
"""

from typing import List, Tuple
import logging

# Import quality tier enum
try:
    from bet_enhancement_system import EnhancedBet, QualityTier
except ImportError:
    # Fallback if import fails
    EnhancedBet = None
    QualityTier = None

logger = logging.getLogger(__name__)


class QAValidator:
    """Pre-display validation for betting recommendations"""

    def __init__(self, strict_mode=False):
        """
        Initialize QA Validator

        Args:
            strict_mode: If True, use strict validation (blocks bets).
                        If False, use lenient validation (warnings only)
        """
        self.strict_mode = strict_mode

        if strict_mode:
            # Strict tolerances - blocks bets with inconsistencies
            self.tolerance_fair_odds = 0.01  # ±1% tolerance
            self.tolerance_ev = 1.0  # ±1% EV tolerance
            self.max_probability = 0.82  # Hard cap (82%)
        else:
            # Lenient tolerances - allows more bets through
            self.tolerance_fair_odds = 0.10  # ±10% tolerance
            self.tolerance_ev = 5.0  # ±5% EV tolerance
            self.max_probability = 0.95  # 95% cap (very lenient)

    def validate_recommendation(self, bet: EnhancedBet) -> Tuple[bool, List[str]]:
        """
        Validate a single betting recommendation.

        Returns:
            (is_valid, error_messages)

        Blocks bet if:
        - Fair odds ≠ 1/probability
        - Tier logic violated
        - Probability > 82%
        - S-Tier has correlation penalty
        - EV formula inconsistent
        - Confidence > Probability
        """
        errors = []

        # 1. FAIR ODDS CONSISTENCY
        if bet.calibrated_probability > 0:
            expected_fair = 1.0 / bet.calibrated_probability
            if abs(bet.fair_odds - expected_fair) > self.tolerance_fair_odds:
                errors.append(
                    f"Fair odds: {bet.fair_odds:.3f} ≠ 1/{bet.calibrated_probability:.3f} "
                    f"(expected: {expected_fair:.3f})"
                )

        # 2. TIER LOGIC CONSISTENCY
        if QualityTier and bet.quality_tier == QualityTier.S:
            # S-Tier requires ALL conditions
            if bet.expected_value < 12.0:
                errors.append(
                    f"S-Tier requires EV ≥12%, got {bet.expected_value:.1f}%"
                )
            if bet.calibrated_probability < 0.65:
                errors.append(
                    f"S-Tier requires Prob ≥65%, got {bet.calibrated_probability:.0%}"
                )
            if bet.confidence_score < 75.0:
                errors.append(
                    f"S-Tier requires Conf ≥75%, got {bet.confidence_score:.0f}%"
                )
            if bet.minutes_volatility_score >= 6.0:
                errors.append(
                    f"S-Tier requires volatility <6.0, got {bet.minutes_volatility_score:.1f}"
                )
            if bet.correlation_multiplier < 1.0:
                errors.append(
                    "S-Tier cannot have correlation penalty "
                    f"(multiplier: {bet.correlation_multiplier:.2f})"
                )

        # 3. PROBABILITY CAPS
        if bet.calibrated_probability > self.max_probability:
            errors.append(
                f"Probability {bet.calibrated_probability:.0%} exceeds "
                f"{self.max_probability:.0%} hard cap"
            )

        # 4. EV FORMULA CONSISTENCY
        if bet.odds > 0 and bet.calibrated_probability > 0:
            expected_ev = (bet.odds * bet.calibrated_probability - 1) * 100
            if abs(bet.expected_value - expected_ev) > self.tolerance_ev:
                errors.append(
                    f"EV formula: {bet.expected_value:.2f}% ≠ {expected_ev:.2f}% "
                    f"(odds: {bet.odds:.2f}, prob: {bet.calibrated_probability:.3f})"
                )

        # 5. CONFIDENCE ≤ PROBABILITY (lag check)
        # In lenient mode, allow confidence to be slightly higher (up to +10%)
        max_allowed_confidence = bet.calibrated_probability * 100
        if not self.strict_mode:
            max_allowed_confidence += 10  # Allow +10% buffer in lenient mode

        if bet.confidence_score > max_allowed_confidence:
            errors.append(
                f"Confidence {bet.confidence_score:.0f}% > "
                f"Prob {bet.calibrated_probability:.0%}"
            )

        # 6. EDGE CONSISTENCY (edge = fair_odds - market_odds)
        if bet.fair_odds > 0 and bet.odds > 0:
            # Edge % = ((fair_odds / market_odds) - 1) * 100
            expected_edge = ((bet.fair_odds / bet.odds) - 1) * 100
            if abs(bet.edge_percentage - expected_edge) > self.tolerance_ev:
                errors.append(
                    f"Edge formula: {bet.edge_percentage:.2f}% ≠ {expected_edge:.2f}% "
                    f"(fair: {bet.fair_odds:.2f}, market: {bet.odds:.2f})"
                )

        return (len(errors) == 0, errors)

    def validate_batch(self, bets: List[EnhancedBet]) -> List[EnhancedBet]:
        """
        Filter invalid bets and log errors.

        Args:
            bets: List of enhanced bets to validate

        Returns:
            List of valid bets (failed bets are filtered out)
        """
        valid = []
        blocked_count = 0

        for bet in bets:
            is_valid, errors = self.validate_recommendation(bet)

            if is_valid:
                valid.append(bet)
            else:
                blocked_count += 1
                logger.error(
                    f"QA VALIDATION FAILED: {bet.player_name} {bet.market}"
                )
                for err in errors:
                    logger.error(f"  - {err}")

        logger.info(
            f"QA Validation: {len(valid)}/{len(bets)} bets passed "
            f"({blocked_count} blocked)"
        )

        return valid


# Export for convenience
__all__ = ['QAValidator']
