# Value Engine Fix: Sample Size Regression & Trend Quality

## Problem Statement

The original value engine heavily overweighted small samples with 100% success rates:
- **5/5 (100%) was treated as a "locked" bet**
- **6/6 (100%) had the same confidence as 60/60 (100%)**
- **All trend types were treated equally** (streaks = player props)
- **No penalties for narrative splits** (e.g., "after overtime", "following a win")

This led to false confidence in statistically unreliable trends.

## Solution Implemented

### ✅ 1. Sample Size Regression (Bayesian Adjustment)

**Formula**: `Adjusted_P = (Historical_P × (n / 30)) + (League_Avg × (1 - n/30))`

**Results**:
- 5/5 (100% raw) → **58.3% regressed** (41.7 point correction)
- 6/6 (100% raw) → **60.0% regressed** (40 point correction)
- 10/10 (100% raw) → **66.7% regressed** (33.3 point correction)
- 30/30 (100% raw) → **100% regressed** (no correction, sample is large)

**Impact**: Small samples are now properly regressed toward league average (50%), preventing overconfidence.

### ✅ 2. Trend Quality Scoring

Different trend types now receive different predictive weights and confidence adjustments:

| Trend Type | Weight | Confidence Boost | Description |
|------------|--------|------------------|-------------|
| **Player Stats Floor** | 1.0 | +20 | HIGH - Most predictive (e.g., "Player scored 20+ in 9/10 games") |
| **Player Usage Split** | 0.7 | +10 | MEDIUM - Context matters (e.g., "home vs road splits") |
| **Team Pace Split** | 0.7 | +10 | MEDIUM - Pace and totals trends |
| **H2H Trend** | 0.3 | -10 | LOW - Opponent-specific history |
| **Streak** | 0.15 | -25 | VERY LOW - Win/loss streaks |
| **Narrative Split** | 0.0 | -40 | ZERO - "After OT", "following a win", etc. |

**Test Results**:
- Player stats floor: **95/100 confidence** → BET
- Streak: **50/100 confidence** → AVOID (was 85/100 before)
- H2H trend: **65/100 confidence** → AVOID
- Narrative split: **35/100 confidence** → AVOID

### ✅ 3. Context Engine (Penalties & Boosts)

**Automatic Penalties**:
- ❌ **Narrative splits**: Auto-AVOID regardless of apparent "value"
- ❌ **Streaks**: Auto-AVOID unless confidence is VERY HIGH
- ❌ **Small samples (n<10)**: Heavy confidence penalty + regression warning
- ❌ **Moderate samples (n<20)**: Moderate confidence penalty + regression warning
- ❌ **H2H trends**: Reduced to 30% weight, -10 confidence

**Boosts**:
- ✅ **Player stats floor props**: Full weight, +20 confidence
- ✅ **Large samples (n≥30)**: No regression applied
- ✅ **High-quality trends**: Preferred in recommendations

## Code Changes

### Files Modified:
1. **`scrapers/context_aware_analysis.py`**:
   - Added `classify_trend_type()` method
   - Added `apply_sample_size_regression()` method
   - Updated `analyze_with_context()` to use both
   - Enhanced `_calculate_confidence()` with trend quality
   - Updated `_generate_recommendation()` with strict filtering

2. **`scrapers/insights_to_value_analysis.py`**:
   - Updated to pass `insight_fact` and `market` to analyzer

3. **`scrapers/sportsbet_complete_analysis.py`**:
   - Changed sorting from `historical_probability` to `confidence_score`

## Testing

Run `python test_regression_fix.py` to verify:
- Sample size regression works correctly
- Trend quality scoring differentiates trend types
- Context penalties auto-avoid low-quality trends

## Impact on Recommendations

**Before**:
- 5/5 streak → "STRONG BET" (100% confidence)
- Narrative split → "BET" (treated same as player props)
- All 100% records treated equally

**After**:
- 5/5 streak → "AVOID" (50% confidence, VERY LOW predictive value)
- Narrative split → "AVOID" (35% confidence, ZERO predictive value)
- 5/5 player prop → "STRONG BET" (80% confidence, 58.3% regressed probability)
- 30/30 player prop → "STRONG BET" (100% confidence, no regression needed)

## Key Takeaways

1. **Small samples ≠ certainty**: 5/5 is NOT a lock. It's regressed to ~58%.
2. **Trend type matters**: Player props >> Team streaks
3. **Narrative splits are noise**: Auto-avoided regardless of "value"
4. **Confidence reflects reliability**: High confidence only for large samples + quality trends

## Next Steps (Optional Enhancements)

- [ ] Add sport-specific league averages (NBA ≠ NFL ≠ NHL)
- [ ] Add prop-specific priors (Over/Under ≠ Player Props)
- [ ] Add recency-weighted regression (more recent = more weight)
- [ ] Add Bayesian credible intervals for uncertainty quantification
