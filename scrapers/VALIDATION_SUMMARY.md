# Bet Validation System - Implementation Summary

## Overview

Core invariants and validation hooks have been implemented to ensure mathematical consistency and tier requirements for all betting recommendations.

## Core Components

### 1. `bet_validation.py` Module

#### `BetEvaluation` Dataclass
- Standardized structure for bet validation
- Fields: `probability`, `odds`, `ev`, `confidence`, `tier`
- `from_bet_dict()` factory method to convert bet dictionaries

#### Validation Functions

**`assert_probability(probability)`**
- Ensures probability is in range [0.0, 1.0]
- Raises `ValueError` if invalid

**`assert_confidence(confidence)`**
- Ensures confidence is in range [0, 100]
- Raises `ValueError` if invalid

**`assert_ev(ev)`**
- Ensures EV is finite and in reasonable range [-10.0, 10.0]
- Raises `ValueError` if invalid

**`assert_ev_consistency(probability, odds, ev)`**
- **Core Invariant**: Validates `EV = (probability * odds) - 1`
- Tolerance: `0.001` (1 mill)
- Raises `ValueError` if mismatch detected

**`assert_tier(confidence, tier)`**
- Validates confidence meets tier threshold:
  - A-Tier: >= 65
  - B-Tier: >= 50
  - C-Tier: >= 40
  - WATCHLIST: No minimum
- Raises `ValueError` if threshold not met

**`validate_bet(bet, strict=True)`**
- **Master validation hook** - validates all invariants
- Checks probability, confidence, EV, EV consistency, tier requirements
- For non-watchlist bets: also validates `probability >= 0.50`
- If `strict=False`: logs warnings and returns `False` instead of raising

**`calculate_ev(probability, odds, stake=100.0)`**
- Calculates expected value: `EV = (probability * odds - 1) * stake`
- Returns EV for the given stake amount

#### Health Monitoring

**`health_snapshot(bets)`**
- Generates health metrics for a list of `BetEvaluation` objects
- Returns dictionary with:
  - `count`, `valid_count`
  - `mean_prob`, `mean_ev`, `mean_confidence`
  - `tiers`: counts by tier (A, B, C, WATCHLIST)
  - `validation_failures`: number of invalid bets
  - `ev_inconsistencies`: number of EV mismatches

**`health_snapshot_from_dicts(bets)`**
- Same as `health_snapshot()` but accepts bet dictionaries

**`validate_bet_list(bets, strict=False)`**
- Validates and filters a list of bets
- Removes invalid bets (if `strict=False`) or raises exception (if `strict=True`)
- Returns list of validated bet dictionaries

## Integration Points

### 1. Pre-Filter Validation (`unified_analysis_pipeline.py`)

After all bets are created (team + player props):
```python
from scrapers.bet_validation import validate_bet_list, health_snapshot_from_dicts

# Generate health snapshot
pre_filter_health = health_snapshot_from_dicts(all_bets)

# Validate all bets (filter invalid ones)
validated_bets = validate_bet_list(all_bets, strict=False)
```

### 2. EV Consistency Validation at Creation

**Team Bets:**
- After calculating `final_prob` and `ev_per_100`
- Recalculates EV if mismatch detected (1 cent tolerance)
- Logs warnings for mismatches

**Player Props:**
- Same validation applied
- Fixes EV if inconsistent

### 3. Post-EV-Filter Validation

After EV/probability filtering:
```python
from scrapers.bet_validation import BetEvaluation, validate_bet

# Validate EV consistency after filtering
ev_validated_bets = []
for bet in ev_filtered_bets:
    bet_eval = BetEvaluation.from_bet_dict(bet)
    if bet_eval:
        validate_bet(bet_eval, strict=False)  # Log warnings
        ev_validated_bets.append(bet)
```

### 4. Tier Assignment Validation

When assigning tiers:
```python
# Assign tier based on confidence
conf = bet.get('confidence', 0)
if conf >= A_TIER_CONFIDENCE:
    bet['tier'] = 'A'
elif conf >= B_TIER_CONFIDENCE:
    bet['tier'] = 'B'
elif conf >= C_TIER_CONFIDENCE:
    bet['tier'] = 'C'
else:
    bet['tier'] = 'WATCHLIST'

# Validate tier assignment
bet_eval = BetEvaluation.from_bet_dict(bet)
if bet_eval:
    validate_bet(bet_eval, strict=False)  # Log warnings
```

### 5. Final Health Snapshot

Before returning filtered bets:
```python
# Final health snapshot
final_health = health_snapshot_from_dicts(filtered_bets)
# Logs warnings if validation failures or EV inconsistencies
```

### 6. Pre-Display Validation

Before converting to `BettingRecommendation` objects:
```python
# Validate all bets before display
validated_final_bets = validate_bet_list(final_bets, strict=False)
# Filters invalid bets silently
```

## Tier Thresholds

Defined in `bet_validation.py`:
```python
TIER_THRESHOLDS = {
    "A": 65,    # Very high quality
    "B": 50,    # Standard quality
    "C": 40,    # Lower quality (max 1, capped stake)
    "WATCHLIST": 0  # No minimum
}
```

## EV Calculation Formula

Standard formula:
```python
EV = (probability * odds - 1) * stake
```

For per-$100 calculation:
```python
EV_per_100 = (probability * odds - 1) * 100
```

## Validation Tolerance

- **EV Consistency**: `0.001` (1 mill) for strict validation
- **EV Creation Check**: `0.01` (1 cent) for runtime fixes
- **Probability Range**: `[0.0, 1.0]`
- **Confidence Range**: `[0, 100]`
- **EV Range**: `[-10.0, 10.0]` (reasonable bounds)

## Usage Example

```python
from scrapers.bet_validation import BetEvaluation, validate_bet, health_snapshot

# Create bet evaluation
bet_eval = BetEvaluation(
    probability=0.55,
    odds=2.0,
    ev=0.10,  # (0.55 * 2.0 - 1) = 0.10
    confidence=65.0,
    tier="A"
)

# Validate
try:
    validate_bet(bet_eval, strict=True)
    print("✓ Bet is valid")
except ValueError as e:
    print(f"✗ Validation failed: {e}")

# Health snapshot
bets = [bet_eval]
health = health_snapshot(bets)
print(f"Valid: {health['valid_count']}/{health['count']}")
print(f"Mean EV: {health['mean_ev']}")
```

## Error Handling

- **Strict Mode** (`strict=True`): Raises `ValueError` on validation failure
- **Non-Strict Mode** (`strict=False`): Logs warnings and returns `False`
- Invalid bets are filtered out in non-strict mode
- Health snapshots report validation failures without raising

## Benefits

1. **Mathematical Consistency**: Ensures EV always matches probability and odds
2. **Tier Enforcement**: Guarantees tier assignments meet confidence thresholds
3. **Early Detection**: Catches inconsistencies at creation time
4. **Health Monitoring**: Provides visibility into validation health
5. **Graceful Degradation**: Non-strict mode filters invalid bets without crashing
