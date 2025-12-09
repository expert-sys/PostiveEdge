# Bet Enhancement System - V2 Improvements

## Overview

Implemented 5 major improvements to the bet enhancement system to provide more intelligent filtering, better risk assessment, and stricter quality control.

---

## ✅ Improvement #1: Scaled Correlation Penalty

### Previous Implementation
- **Flat penalty**: -6 points for all correlated bets (same game + same stat)
- **Problem**: Penalized strong projections equally with weak ones

### New Implementation
**Penalty scales based on projection margin:**

```python
if proj_margin < 2.0:
    penalty = -10  # Weak projection, full penalty
elif proj_margin 2-4:
    penalty = -6   # Medium projection, moderate penalty
else:
    penalty = -4   # Strong projection, reduced penalty
```

### Why This Matters
- **Protects weak correlations**: Bets barely beating the line get harsher penalties
- **Rewards strong convictions**: Bets with large projection margins (4+) only get -4 penalty
- **Example**: Player projected for 28 points with 23.5 line (+4.5 margin) → only -4 penalty vs -6 previously

---

## ✅ Improvement #2: A-Tier Probability Gate (≥75%)

### Previous Implementation
- A-Tier required: `EV ≥ 10%` AND `Edge ≥ 8%`
- **Problem**: Could have 68% win probability with high variance

### New Implementation
**A-Tier MUST have ≥75% projected probability:**

```python
if ev >= 10.0 and edge >= 8.0 and prob >= 0.75:
    tier = A-Tier
```

### Why This Matters
- **Ensures elite quality**: A-Tier bets must be true favorites (75%+ to hit)
- **Prevents variance traps**: High EV/edge but low probability bets now fall to B-tier
- **Cleaner classifications**: S-tier = 68%+, A-tier = 75%+, creating true hierarchy

---

## ✅ Improvement #3: Minutes Stability Score

### What's New
**Analyzes minutes variance and penalizes volatility:**

```python
if minutes_variance > 20% of average:
    confidence -= 5 points
    warning: "Minutes volatility"
```

### Implementation Details
- Extracts `minutes_analysis` from `advanced_context`
- Calculates variance percentage: `(variance / recent_avg) * 100`
- **Thresholds**:
  - Variance > 20% of avg → -5 penalty
  - Unstable rotation → -3 penalty
  - Stable minutes → bonus note

### Why This Matters
- **Critical for player props**: Volatile minutes = unreliable stats
- **Example**: Player with 32min avg but ±12min variance (37.5%) → -5 penalty
- **Catches rotation risks**: Bench players, injury returns, blowout candidates

### Real Impact
From test output:
```
Jaden McDaniels - Rebounds Over 3.5
Minutes Stability: -5 points (variance: 11.5min)
Warning: Minutes volatility: 11.5min variance (36% of avg)
```

---

## ✅ Improvement #4: Line Efficiency Check (Shaded Lines)

### What's New
**Flags potentially shaded lines by sportsbooks:**

Indicators of line shading:
1. **High points lines** (30+) - books often shade star players
2. **Heavy juice** (odds < 1.70) - books taking vig on public action
3. **Moderate favorites** (60-75% implied prob) - potential public bet trap

### Implementation
```python
if line >= 30 and market == 'points':
    flag: "High points line (30+)"

if odds < 1.70:
    flag: "Heavy juice"

if 0.60 < implied_prob < 0.75:
    flag: "Moderate favorite (potential public action)"
```

### Why This Matters
- **Identifies value-shaded markets**: Where books adjust for public betting patterns
- **Risk awareness**: Warns when taking favorite side of public action
- **Future enhancement**: Can integrate real-time line movement data

### Real Impact
From test output:
```
⚠ Line potentially shaded by sportsbook
Warning: Heavy juice (odds < 1.70), Moderate favorite
```

---

## ✅ Improvement #5: C-Tier = "Do Not Bet"

### Previous Implementation
- C-Tier: `EV ≥ 1%` OR `Confidence ≥ 70%`
- **Label**: "Marginal"
- **Problem**: Still sounded playable

### New Implementation
**C-Tier is now "Do Not Bet - Pass"**

**Automatic C-Tier if ANY of:**
1. Edge < 5%
2. Confidence < 60%
3. Mispricing < 0.10
4. Sample size < 5
5. **>2 props from same game** (excessive correlation)

**New emoji**: ⛔ (stop sign)

### Implementation
```python
c_tier_reasons = []

if edge < 5.0:
    c_tier_reasons.append("Low edge")
if confidence < 60.0:
    c_tier_reasons.append("Low confidence")
if mispricing < 0.10:
    c_tier_reasons.append("Low mispricing")
if sample_size < 5:
    c_tier_reasons.append("Small sample")

if c_tier_reasons:
    tier = C-Tier
    warning = "DO NOT BET - Quality issues: ..."
```

### Excessive Correlation Check
**New feature**: Downgrades 3rd+ prop from same game to C-tier

```python
if props_in_game > 2:
    # Keep best 2 by projected probability
    # Downgrade rest to C-Tier
    warning = "DO NOT BET - Excessive correlation"
```

### Why This Matters
- **Clear signal**: ⛔ = Don't bet, simple as that
- **Prevents bad bets**: Catches low-quality bets that technically have positive EV
- **Risk management**: Automatically limits game exposure to 2 props max
- **Dashboard cleanup**: Makes filtering dead simple (exclude C/D)

### Tier Summary
| Tier | Emoji | Action | Criteria |
|------|-------|--------|----------|
| S | 💎 | Max units | EV≥20, Edge≥12, Prob≥68% |
| A | ⭐ | Standard units | EV≥10, Edge≥8, **Prob≥75%** |
| B | ✓ | Reduced units | EV≥5, Edge≥4 |
| C | ⛔ | **DO NOT BET** | Fails quality checks |
| D | ❌ | Avoid | EV<0 or Prob<50% |

---

## Summary of All Penalties Now Applied

1. **Sample Size Penalty**: -4 per game under n=5
2. **Correlation Penalty (SCALED)**:
   - Weak projection (<2 margin): -10
   - Medium (2-4 margin): -6
   - Strong (>4 margin): -4
3. **Line Difficulty**: -5 for 30+ lines, -10 for 35+
4. **Minutes Stability**: -5 if variance >20%, -3 if unstable
5. **Market Efficiency**: Hide if edge<3% in sharp zone (55-60%)
6. **EV/Prob Ratio**: Filter if <0.08
7. **Excessive Correlation**: Auto-downgrade to C-tier

---

## Test Results

### Before Improvements
```
4 recommendations total
→ 1 A-Tier (Keldon Johnson)
→ 2 B-Tier
→ 1 C-Tier
```

### After Improvements
```
4 recommendations total
→ 0 A-Tier (Keldon Johnson failed prob≥75% gate)
→ 1 B-Tier (Jaden McDaniels)
→ 3 C-Tier (failed quality checks)

B-Tier bet now shows:
✓ Minutes volatility warning (-5 penalty)
✓ Line shading detection
✓ Scaled correlation penalty
```

---

## How to Use

### Run Enhanced System
```bash
python bet_enhancement_system.py
```

### View in Main Pipeline
```bash
python nba_betting_system.py --enhanced --min-tier B
```

### Quick View
```bash
show-bets.bat
```

---

## Configuration

All thresholds are in `BetEnhancementSystem.__init__()`:

```python
# Tier thresholds
self.tier_thresholds = {
    'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
    'A': {'ev_min': 10.0, 'edge_min': 8.0, 'prob_min': 0.75},  # NEW
    'B': {'ev_min': 5.0, 'edge_min': 4.0},
}

# Minutes stability
self.minutes_variance_threshold = 20.0  # % of average

# Line shading
self.high_points_line = 30.0
self.heavy_juice_threshold = 1.70
self.moderate_fav_range = (0.60, 0.75)
```

---

## Files Modified

1. **bet_enhancement_system.py**
   - Added `_get_scaled_correlation_penalty()` method
   - Added `_calculate_minutes_stability()` method
   - Added `_check_line_efficiency()` method
   - Added `_check_excessive_correlation()` method
   - Updated `_classify_quality_tier()` with stricter C-tier
   - Updated `_calculate_final_score()` to include minutes penalty
   - Added Unicode encoding fix for Windows

2. **EnhancedBet dataclass**
   - Added `minutes_stability_penalty: float`
   - Added `minutes_variance: float`
   - Added `line_shaded: bool`
   - Added `line_movement: float`

---

## Future Enhancements

### Line Movement Integration
Currently `line_movement = 0.0` (placeholder). Future versions could:
- Track historical line movements
- Flag if line moved >0.5 in past hour
- Identify reverse line movement (sharp money indicators)

### Minute Projections
Could integrate with rotation analysis to:
- Predict minutes based on game script
- Adjust for back-to-backs
- Factor in blowout probability

### Advanced Shading Detection
- Star player detection (compare to league average usage)
- Back-to-back game flags
- Injury return detection
- Public betting percentage data

---

## Impact Assessment

### Improvement Quality Metrics
- **Better A-tier purity**: 75% prob gate ensures true elite bets
- **Smarter correlation handling**: Strong projections protected
- **Minutes risk captured**: -5 penalty for volatile rotations
- **Line shading awareness**: Users know when books have edge
- **Clean filtering**: C-tier = hard pass, no confusion

### Expected Outcomes
1. **Fewer but better A-tier bets**: Only true elite recommendations
2. **Better risk management**: Minutes + correlation awareness
3. **Cleaner dashboards**: C/D tier = auto-skip
4. **User confidence**: Clear signals on what to bet/skip

---

## Testing Checklist

✅ Scaled correlation penalty works (projection margin-based)
✅ A-tier requires ≥75% probability
✅ Minutes stability penalty applied
✅ Line shading detection flags bets
✅ C-tier auto-filters low quality
✅ Excessive correlation (>2 props) caught
✅ All penalties combine in final score
✅ Unicode display works on Windows

---

## Quick Reference Card

### When to Bet
- **S/A-Tier**: High confidence plays
- **B-Tier**: Standard plays with reduced risk
- **C-Tier**: ⛔ **DO NOT BET**
- **D-Tier**: ❌ Avoid entirely

### Red Flags
- ⛔ C-Tier designation
- ⚠ Minutes volatility warning
- ⚠ Line potentially shaded
- ⚠ Excessive correlation
- ⚠ Small sample (n<5)

### Green Flags
- 💎 S-Tier or ⭐ A-Tier
- ✓ Projected margin >2.0
- ✓ Stable minutes
- ✓ Sample size ≥10
- ✓ Fair odds mispricing >0.15

---

## Version History

- **V1.0**: Original 10 enhancements
- **V2.0**: 5 major improvements (this update)
  - Scaled correlation penalties
  - A-tier probability gate (75%)
  - Minutes stability score
  - Line shading detection
  - C-tier as "Do Not Bet"
