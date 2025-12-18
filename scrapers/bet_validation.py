"""
Bet Validation Module
=====================
Core invariants and validation hooks for betting recommendations.

Ensures mathematical consistency and tier requirements are met.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Market-specific tier confidence thresholds
MARKET_TIER_THRESHOLDS = {
    "player_prop": {"A": 65, "B": 50, "C": 35},
    "team_sides": {"A": 65, "B": 50, "C": 40},
    "totals": {"A": 65, "B": 50, "C": 45}
}

# Legacy tier thresholds (for backward compatibility, uses team_sides)
TIER_THRESHOLDS = {
    "A": 65,
    "B": 50,
    "C": 40,
    "WATCHLIST": 0  # No minimum for watchlist
}

# Market weights for soft floor (allows borderline props)
MARKET_WEIGHTS = {
    "player_prop": 0.92,  # Soft floor (allows borderline props)
    "team_sides": 1.0,    # No adjustment
    "totals": 1.05        # Slight boost
}

# Market-specific minimum probability floors (expert-level tolerance)
# Player props have higher variance, so lower floor is acceptable
MIN_PROBABILITY = {
    "player_prop": 0.47,  # 47% - allows Ja Morant (49.1%) to survive
    "team_sides": 0.50,   # 50% - standard floor
    "totals": 0.52        # 52% - higher floor for totals
}

# Legacy constant for backward compatibility
MIN_PROBABILITY_LEGACY = 0.50

# Insight weighting by market type (for blending model vs insight probabilities)
INSIGHT_WEIGHT = {
    "player_prop": 0.7,  # Model 70%, Insight 30% (model is primary for player props)
    "team_sides": 1.0,   # Insight 100% (no model for team sides, rely on insight analysis)
    "totals": 0.9        # Insight 90%, Model 10% (insight is primary for totals)
}

# EV calculation tolerance
EV_TOLERANCE = 0.001


@dataclass
class BetEvaluation:
    """Standardized bet evaluation for validation"""
    probability: float  # 0.0 to 1.0
    odds: float  # e.g., 2.0 for even money
    ev: float  # Expected value: (probability * odds) - 1
    confidence: float  # 0 to 100
    tier: str  # "A", "B", "C", or "WATCHLIST"
    
    @classmethod
    def from_bet_dict(cls, bet: Dict[str, Any]) -> Optional['BetEvaluation']:
        """Create BetEvaluation from a bet dictionary"""
        try:
            # Extract probability
            prob = bet.get('final_prob') or bet.get('historical_probability') or bet.get('projected_prob', 0)
            if prob == 0:
                prob = bet.get('historical_prob', 0)
            
            # Extract odds
            odds = bet.get('odds', 0)
            if odds <= 0:
                return None
            
            # Extract EV (normalized to per-unit)
            ev_per_100 = bet.get('ev_per_100', 0)
            ev = ev_per_100 / 100.0 if ev_per_100 != 0 else bet.get('expected_value', 0)
            
            # If EV is missing, calculate it
            if ev == 0:
                ev = (prob * odds) - 1
            
            # Extract confidence
            conf = float(bet.get('confidence', 0))
            
            # Extract tier
            tier = bet.get('tier', 'WATCHLIST')
            if not tier or tier not in ["A", "B", "C", "WATCHLIST"]:
                # Infer tier from confidence
                if conf >= TIER_THRESHOLDS["A"]:
                    tier = "A"
                elif conf >= TIER_THRESHOLDS["B"]:
                    tier = "B"
                elif conf >= TIER_THRESHOLDS["C"]:
                    tier = "C"
                else:
                    tier = "WATCHLIST"
            
            return cls(
                probability=float(prob),
                odds=float(odds),
                ev=float(ev),
                confidence=float(conf),
                tier=tier
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Failed to create BetEvaluation from bet dict: {e}")
            return None


def assert_probability(probability: float):
    """Assert probability is in valid range [0.0, 1.0]"""
    if not (0.0 <= probability <= 1.0):
        raise ValueError(
            f"Probability must be between 0.0 and 1.0, got {probability:.4f}"
        )


def assert_confidence(confidence: float):
    """Assert confidence is in valid range [0, 100]"""
    if not (0.0 <= confidence <= 100.0):
        raise ValueError(
            f"Confidence must be between 0 and 100, got {confidence:.2f}"
        )


def assert_ev(ev: float):
    """Assert EV is finite and reasonable"""
    if not isinstance(ev, (int, float)) or not (-10.0 <= ev <= 10.0):
        # Allow wide range but catch invalid values
        if not (-10.0 <= ev <= 10.0):
            raise ValueError(
                f"EV out of reasonable range [-10.0, 10.0], got {ev:.4f}"
            )


def assert_ev_consistency(probability: float, odds: float, ev: float):
    """Assert EV matches probability and odds: EV = (prob * odds) - 1"""
    expected_ev = (probability * odds) - 1
    if abs(expected_ev - ev) >= EV_TOLERANCE:
        raise ValueError(
            f"EV mismatch: expected {expected_ev:.4f}, got {ev:.4f} "
            f"(prob={probability:.4f}, odds={odds:.2f}, diff={abs(expected_ev - ev):.4f})"
        )


def assert_tier(confidence: float, tier: str, market_type: str, promoted_from: Optional[str] = None):
    """
    Assert confidence meets tier requirement for market type.
    
    Args:
        confidence: Confidence score (0-100)
        tier: Tier level ('A', 'B', 'C', 'WATCHLIST', or 'A*' for promoted)
        market_type: Market type (REQUIRED - must be 'player_prop', 'team_sides', or 'totals')
        promoted_from: If tier is 'A' and this is 'B', use lower validation floor (48) instead of A threshold
    
    Raises:
        ValueError: If market_type is None, invalid, or confidence doesn't meet tier requirement
    """
    # Handle promoted tier (A* or A with promoted_from='B')
    if tier == "A" and promoted_from == "B":
        tier = "A*"  # Use synthetic tier for promoted bets
    
    if tier not in ["A", "A*", "B", "C", "WATCHLIST"]:
        raise ValueError(f"Invalid tier: {tier} (must be A, A*, B, C, or WATCHLIST)")
    
    if tier == "WATCHLIST":
        return  # No minimum for watchlist
    
    # CRITICAL FIX: Require market_type, fail loudly if missing or invalid
    if market_type is None:
        raise ValueError("market_type is REQUIRED for tier validation (cannot be None)")
    
    assert market_type in MARKET_TIER_THRESHOLDS, (
        f"Invalid market_type: '{market_type}' (must be one of: {list(MARKET_TIER_THRESHOLDS.keys())})"
    )
    
    # Use market-specific thresholds
    thresholds = get_tier_thresholds(market_type)
    
    # For promoted bets (A*), use B-tier threshold as floor (validation only, display still shows A)
    if tier == "A*":
        threshold = thresholds.get("B", 48)  # Use B-tier threshold (48-50) as validation floor for promoted A
    else:
        threshold = thresholds.get(tier)
    
    if threshold is None:
        raise ValueError(f"Invalid tier '{tier}' for market_type '{market_type}'")
    
    if confidence < threshold:
        raise ValueError(
            f"Tier {tier} requires confidence >= {threshold} "
            f"(market={market_type}), got {confidence:.2f}"
        )


def validate_bet(bet: BetEvaluation, strict: bool = True, market_type: str = None) -> bool:
    """
    Master validation hook - call this BEFORE a bet enters filtering or display.
    
    Args:
        bet: BetEvaluation to validate
        strict: If False, log warnings instead of raising exceptions
        market_type: Market type (REQUIRED for non-watchlist bets) - must be 'player_prop', 'team_sides', or 'totals'
    
    Returns:
        True if valid, False if invalid (only when strict=False)
    
    Raises:
        ValueError: If validation fails and strict=True, or if market_type is None/invalid for non-watchlist bets
    """
    try:
        # Core value assertions
        assert_probability(bet.probability)
        assert_confidence(bet.confidence)
        assert_ev(bet.ev)
        assert_ev_consistency(bet.probability, bet.odds, bet.ev)
        
        # Tier and probability requirements (skip for watchlist)
        if bet.tier != "WATCHLIST":
            # CRITICAL FIX: Require market_type for non-watchlist bets
            if market_type is None:
                if strict:
                    raise ValueError("market_type is REQUIRED for non-watchlist bet validation (cannot be None)")
                logger.warning("[VALIDATION] market_type is REQUIRED for non-watchlist bet validation")
                return False
            
            # Validate market_type is valid
            assert market_type in MARKET_TIER_THRESHOLDS, (
                f"Invalid market_type: '{market_type}' (must be one of: {list(MARKET_TIER_THRESHOLDS.keys())})"
            )
            
            # Use market-specific probability floor
            min_prob = MIN_PROBABILITY.get(market_type, MIN_PROBABILITY_LEGACY)
            
            if bet.probability < min_prob:
                msg = f"Probability below minimum for {market_type}: {bet.probability:.4f} < {min_prob}"
                if strict:
                    raise ValueError(msg)
                logger.warning(f"[VALIDATION] {msg}")
                return False
            
            # Pass promoted_from for promoted bets (A-tier promoted from B)
            promoted_from = getattr(bet, 'promoted_from', None)
            assert_tier(bet.confidence, bet.tier, market_type=market_type, promoted_from=promoted_from)
        
        return True
        
    except (ValueError, TypeError, AssertionError) as e:
        if strict:
            raise
        logger.warning(f"[VALIDATION] Bet validation failed: {e}")
        return False


def validate_bet_dict(bet: Dict[str, Any], strict: bool = True) -> bool:
    """
    Validate a bet dictionary by converting to BetEvaluation first.
    
    Args:
        bet: Bet dictionary
        strict: If False, return False on validation failure instead of raising
    
    Returns:
        True if valid, False if invalid
    """
    bet_eval = BetEvaluation.from_bet_dict(bet)
    if bet_eval is None:
        if strict:
            raise ValueError("Failed to create BetEvaluation from bet dict")
        return False
    
    # Extract market_type from bet dict for validation
    market_type = bet.get('market_type') or get_market_type(bet)
    
    # Extract promoted_from for promoted bets
    promoted_from = bet.get('promoted_from')
    if promoted_from and bet_eval.tier == "A":
        # Pass promoted_from to assert_tier through a custom bet_eval
        # We'll handle this in validate_bet by checking the dict
        setattr(bet_eval, 'promoted_from', promoted_from)
    
    return validate_bet(bet_eval, strict=strict, market_type=market_type)


def health_snapshot(bets: List[BetEvaluation], market_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate health metrics for a list of bets.
    
    Args:
        bets: List of BetEvaluation objects
        market_types: Optional list of market types corresponding to bets (if None, watchlist bets are skipped)
    
    Returns:
        Dictionary with health metrics
    """
    if not bets:
        return {
            "count": 0,
            "mean_prob": None,
            "mean_ev": None,
            "mean_confidence": None,
            "tiers": {},
            "validation_failures": 0,
            "ev_inconsistencies": 0
        }
    
    valid_bets = []
    validation_failures = 0
    ev_inconsistencies = 0
    
    for i, bet in enumerate(bets):
        try:
            # Extract market_type if provided, or skip validation for watchlist bets without market_type
            market_type = market_types[i] if market_types and i < len(market_types) else None
            # Only validate non-watchlist bets (watchlist doesn't require market_type)
            if bet.tier != "WATCHLIST" and market_type is None:
                logger.warning(f"[VALIDATION] Skipping validation for non-watchlist bet (no market_type provided)")
                validation_failures += 1
                continue
            
            validate_bet(bet, strict=False, market_type=market_type)
            valid_bets.append(bet)
        except (ValueError, AssertionError) as e:
            validation_failures += 1
            if "EV mismatch" in str(e):
                ev_inconsistencies += 1
    
    tier_counts = {
        tier: sum(1 for b in valid_bets if b.tier == tier)
        for tier in ["A", "B", "C", "WATCHLIST"]
    }
    
    return {
        "count": len(bets),
        "valid_count": len(valid_bets),
        "mean_prob": round(sum(b.probability for b in valid_bets) / len(valid_bets), 3) if valid_bets else None,
        "mean_ev": round(sum(b.ev for b in valid_bets) / len(valid_bets), 3) if valid_bets else None,
        "mean_confidence": round(sum(b.confidence for b in valid_bets) / len(valid_bets), 2) if valid_bets else None,
        "tiers": tier_counts,
        "validation_failures": validation_failures,
        "ev_inconsistencies": ev_inconsistencies
    }


def health_snapshot_from_dicts(bets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate health snapshot from bet dictionaries.
    
    Args:
        bets: List of bet dictionaries
    
    Returns:
        Dictionary with health metrics
    """
    bet_evals = []
    market_types = []
    for bet in bets:
        bet_eval = BetEvaluation.from_bet_dict(bet)
        if bet_eval:
            bet_evals.append(bet_eval)
            # Extract market_type from bet dict
            market_type = bet.get('market_type') or get_market_type(bet)
            market_types.append(market_type)
    
    return health_snapshot(bet_evals, market_types=market_types)


def get_market_type(bet: Dict[str, Any]) -> str:
    """
    Determine market type from bet dictionary.
    
    Args:
        bet: Bet dictionary
    
    Returns:
        Market type: 'player_prop', 'team_sides', or 'totals'
    """
    bet_type = bet.get('type', '').lower()
    
    # Player props
    if bet_type == 'player_prop' or 'player' in bet_type:
        return 'player_prop'
    
    # Check market category for team bets
    market = bet.get('market', '').lower()
    result = bet.get('result', '').lower()
    
    # Totals (over/under markets)
    if 'total' in market or 'over' in result or 'under' in result:
        return 'totals'
    
    # Default to team sides (moneylines, spreads, etc.)
    return 'team_sides'


def calculate_effective_confidence(bet: Dict[str, Any]) -> float:
    """
    Apply market weight to confidence (soft floor).
    
    This allows borderline props (e.g., confidence 38 for player props)
    to pass through by effectively treating them as confidence 35.
    
    Args:
        bet: Bet dictionary
    
    Returns:
        Effective confidence after market weight adjustment
    """
    market_type = get_market_type(bet)
    raw_conf = float(bet.get('confidence', 0))
    weight = MARKET_WEIGHTS.get(market_type, 1.0)
    return raw_conf * weight


def get_tier_thresholds(market_type: str) -> Dict[str, int]:
    """
    Get tier thresholds for a specific market type.
    
    Args:
        market_type: 'player_prop', 'team_sides', or 'totals'
    
    Returns:
        Dictionary with 'A', 'B', 'C' thresholds
    """
    return MARKET_TIER_THRESHOLDS.get(market_type, MARKET_TIER_THRESHOLDS["team_sides"])


def calculate_ev(probability: float, odds: float, stake: float = 100.0) -> float:
    """
    Calculate expected value: EV = (probability * odds - 1) * stake
    
    Args:
        probability: Win probability (0.0 to 1.0)
        odds: Decimal odds (e.g., 2.0 for even money)
        stake: Stake amount (default 100.0 for per-100 calculation)
    
    Returns:
        Expected value for the stake amount
    """
    return (probability * odds - 1) * stake


def validate_bet_list(bets: List[Dict[str, Any]], strict: bool = False) -> List[Dict[str, Any]]:
    """
    Validate and filter a list of bets, removing invalid ones.
    
    Args:
        bets: List of bet dictionaries
        strict: If True, raise exception on invalid bet; if False, filter it out
    
    Returns:
        List of validated bet dictionaries
    """
    validated = []
    invalid_count = 0
    
    for bet in bets:
        try:
            if validate_bet_dict(bet, strict=False):
                validated.append(bet)
            else:
                invalid_count += 1
                if strict:
                    bet_eval = BetEvaluation.from_bet_dict(bet)
                    if bet_eval:
                        validate_bet(bet_eval, strict=True)  # Will raise
        except (ValueError, TypeError) as e:
            invalid_count += 1
            logger.debug(f"Filtered invalid bet: {e}")
            if strict:
                raise
    
    if invalid_count > 0:
        logger.info(f"[VALIDATION] Filtered {invalid_count} invalid bet(s) from {len(bets)} total")
    
    return validated


def apply_sample_size_confidence_dampener(confidence: float, sample_size: int) -> float:
    """
    Apply soft confidence dampener based on sample size ranges.
    
    Small sample sizes are penalized to prevent overconfidence:
    - <8 games → -8% confidence
    - 8-12 games → -4% confidence
    - 13-20 games → neutral (no change)
    - >20 games → neutral (no change)
    
    Args:
        confidence: Base confidence score (0-100)
        sample_size: Number of games in sample
    
    Returns:
        Dampened confidence score (0-100)
    """
    if sample_size < 8:
        dampening = -8.0
    elif sample_size < 13:
        dampening = -4.0
    else:
        dampening = 0.0
    
    dampened = max(0.0, min(100.0, confidence + dampening))
    return dampened


def apply_confidence_stack_cap(
    confidence: float,
    base_confidence: float,
    max_total_dampening: Optional[float] = None,
    large_edge_threshold: float = 8.0,
    probability: Optional[float] = None,
    bookmaker_probability: Optional[float] = None
) -> float:
    """
    Cap total confidence dampening and allow large edges to reclaim tier.
    
    Uses RELATIVE cap: min(30.0, base_confidence * 0.4) to prevent catastrophic
    drops for low-confidence bets (e.g., 40 → 10) while allowing reasonable
    drops for high-confidence bets (e.g., 75 → 45).
    
    Args:
        confidence: Current confidence after all penalties
        base_confidence: Original confidence before penalties
        max_total_dampening: Maximum absolute % reduction (None = auto-calculate relative cap)
        large_edge_threshold: Edge % to trigger tier reclaim (default: +8%)
        probability: Final probability (for edge calculation)
        bookmaker_probability: Bookmaker probability (for edge calculation)
    
    Returns:
        Adjusted confidence (capped relative to base, with edge boost)
    
    Examples:
        High-conf bet (75% base, 30% after penalties):
            Cap: min(30.0, 75*0.4) = 30 → Capped at 45, then boost for large edge
        
        Low-conf bet (40% base, 5% after penalties):
            Cap: min(30.0, 40*0.4) = 16 → Capped at 24 (prevents 40 → 10 catastrophe)
    """
    # Calculate relative cap: max 30% absolute OR 40% of base (whichever is lower)
    if max_total_dampening is None:
        max_total_dampening = min(30.0, base_confidence * 0.4)
    
    # Calculate current dampening
    current_dampening = base_confidence - confidence
    
    # Apply cap
    if current_dampening > max_total_dampening:
        confidence = base_confidence - max_total_dampening
    
    # Large edge tier reclaim: boost confidence for very strong edges
    if probability is not None and bookmaker_probability is not None:
        edge_pct = (probability - bookmaker_probability) * 100
        if edge_pct >= large_edge_threshold and probability >= 0.55:
            # Boost: +5-10% depending on edge magnitude
            edge_boost = min(10.0, 5.0 + (edge_pct - large_edge_threshold) * 0.5)
            confidence = min(100.0, confidence + edge_boost)
    
    return max(0.0, min(100.0, confidence))
