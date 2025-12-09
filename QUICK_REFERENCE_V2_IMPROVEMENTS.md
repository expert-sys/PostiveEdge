# Enhancement System V2 - Quick Reference

## 🎯 What Changed?

### 1️⃣ Scaled Correlation Penalty

**Before**: All correlated bets → -6 penalty (flat)

**After**: Penalty scales by projection strength
```
Projection margin < 2.0  → -10 penalty (weak)
Projection margin 2-4    → -6 penalty (medium)
Projection margin > 4.0  → -4 penalty (strong)
```

**Impact**: Strong projections get rewarded, weak ones penalized harder

---

### 2️⃣ A-Tier Probability Gate

**Before**: `EV ≥ 10%` AND `Edge ≥ 8%`

**After**: `EV ≥ 10%` AND `Edge ≥ 8%` AND **`Prob ≥ 75%`**

**Impact**: A-tier bets must be true favorites (75%+ to hit)

---

### 3️⃣ Minutes Stability Score

**NEW**: Checks minutes volatility

```
If variance > 20% of average → -5 confidence penalty
If rotation unstable → -3 confidence penalty
```

**Impact**: Catches rotation risks, bench players, blowout candidates

**Example**:
```
Player: 32min average, ±12min variance (37.5%)
Penalty: -5 confidence points
Warning: "Minutes volatility: 12.0min variance (37% of avg)"
```

---

### 4️⃣ Line Shading Detection

**NEW**: Flags potentially shaded lines

**Shading indicators**:
- High points line (30+)
- Heavy juice (odds < 1.70)
- Moderate favorite (60-75% implied prob)

**Impact**: Know when books have adjusted for public action

**Example**:
```
⚠ Line potentially shaded by sportsbook
Warning: Heavy juice (odds < 1.70), Moderate favorite (potential public action)
```

---

### 5️⃣ C-Tier = "Do Not Bet"

**Before**: C-tier = "Marginal" (~)

**After**: C-tier = "Do Not Bet - Pass" (⛔)

**Auto C-Tier if ANY of**:
- Edge < 5%
- Confidence < 60%
- Mispricing < 0.10
- Sample size < 5
- **>2 props from same game**

**Impact**: Clear stop signal, no ambiguity

---

## 📊 Tier Requirements Comparison

### Before V2
| Tier | Requirements |
|------|--------------|
| S | EV≥20%, Edge≥12%, Prob≥68% |
| A | EV≥10%, Edge≥8% |
| B | EV≥5%, Edge≥4% |
| C | EV≥1% OR Conf≥70% |
| D | EV<0 OR Prob<50% |

### After V2
| Tier | Requirements |
|------|--------------|
| S | EV≥20%, Edge≥12%, Prob≥68% |
| A | EV≥10%, Edge≥8%, **Prob≥75%** ⬅ NEW |
| B | EV≥5%, Edge≥4% |
| C | **Fails ANY quality check** ⬅ CHANGED |
| D | EV<0 OR Prob<50% |

---

## 🔥 All Penalties Applied (Complete List)

1. **Sample Size**: -4 per game under n=5
2. **Correlation (SCALED)**:
   - Weak (<2 margin): -10
   - Medium (2-4): -6
   - Strong (>4): -4 ⬅ NEW SCALING
3. **Line Difficulty**: -5 for 30+, -10 for 35+
4. **Minutes Stability**: -5 if variance >20% ⬅ NEW
5. **Market Efficiency**: Hide if edge<3% in sharp zone
6. **EV/Prob Ratio**: Filter if <0.08
7. **Excessive Correlation**: Auto C-tier if >2 props/game ⬅ NEW

---

## 🎬 Example: How It Works

### Sample Bet Analysis

```
Player: Keldon Johnson
Market: Points Over 11.0
Projected: 13.5 (margin = +2.5)
Odds: 1.46
Projected Probability: 82.8%
Edge: 8.6%
EV: 12.5%
Sample: n=10
Minutes variance: 8.5min (25% of avg)
```

### V1 Scoring
```
✅ A-Tier (EV=12.5%, Edge=8.6%)
Confidence: 85.6%
Penalties:
  - Correlation: -6 (same game)
Final: 79.6% confidence
```

### V2 Scoring
```
❌ B-Tier (fails Prob≥75% gate for A-tier)
Confidence: 85.6%
Penalties:
  - Correlation: -6 (margin 2.5, medium penalty)
  - Minutes stability: -5 (25% variance)
Final: 74.6% confidence

Warnings:
  ⚠ Failed A-tier probability requirement (82.8% < 75%)
  ⚠ Minutes volatility: 8.5min variance (25% of avg)
```

**Result**: More conservative, catches minutes risk

---

## 💡 Quick Decision Guide

### ✅ BET (S/A/B-Tier)
- 💎 **S-Tier**: Max confidence plays
- ⭐ **A-Tier**: Standard units (now requires 75%+ prob!)
- ✓ **B-Tier**: Reduced units

### ⛔ DO NOT BET (C-Tier)
C-Tier bets fail critical quality checks:
- Low edge (<5%)
- Low confidence (<60%)
- Small sample (<5)
- Low mispricing (<0.10)
- Excessive correlation (>2 props/game)

**Action**: Skip entirely

### ❌ AVOID (D-Tier)
- Negative EV
- Probability <50%

**Action**: Never bet

---

## 🧪 Testing

### Run V2 Enhancements
```bash
python bet_enhancement_system.py
```

### Compare Results
```bash
# Old recommendations
cat betting_recommendations.json

# Enhanced V2
cat betting_recommendations_enhanced.json
```

### Quick Test
```bash
TEST_ENHANCEMENTS_V2.bat
```

---

## 📈 Expected Outcomes

### A-Tier Bets
- **Before**: Could have 68-74% probability
- **After**: Minimum 75% probability
- **Result**: Fewer but purer A-tier bets

### C-Tier Filtering
- **Before**: "Marginal" (maybe playable?)
- **After**: "Do Not Bet" (hard pass)
- **Result**: Clearer decision making

### Minutes Risk
- **Before**: Not tracked
- **After**: -5 penalty for volatile rotations
- **Result**: Catch rotation/blowout risks

### Line Shading
- **Before**: Not detected
- **After**: Flagged with warnings
- **Result**: Know when books have edge

### Correlation
- **Before**: Flat -6 penalty
- **After**: Scaled -4 to -10
- **Result**: Strong projections protected

---

## 🎯 Configuration

### Adjust Thresholds (bet_enhancement_system.py)

```python
# Line 128-133: Tier requirements
self.tier_thresholds = {
    'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
    'A': {'ev_min': 10.0, 'edge_min': 8.0, 'prob_min': 0.75},  # NEW
    'B': {'ev_min': 5.0, 'edge_min': 4.0},
}

# Line 147: EV ratio threshold
self.min_ev_ratio = 0.08

# Minutes stability threshold (NEW)
# Check variance_pct > 20.0 in _calculate_minutes_stability()

# Line shading thresholds (NEW)
# High points line: 30.0
# Heavy juice: 1.70
# Moderate favorite: (0.60, 0.75)
```

---

## 📚 Documentation

- **ENHANCEMENT_IMPROVEMENTS_V2.md** - Full detailed explanation
- **START_HERE.md** - Updated with V2 features
- **BET_ENHANCEMENT_GUIDE.md** - Complete system guide
- **This file** - Quick reference

---

## ✨ Version Info

- **V1.0**: Original 10 enhancements
- **V2.0**: 5 major improvements (current)
  - Scaled correlation penalties ✅
  - A-tier probability gate (≥75%) ✅
  - Minutes stability score ✅
  - Line shading detection ✅
  - C-tier as "Do Not Bet" ✅

---

## 🔄 Upgrade Path

### If using V1
1. Pull latest code
2. Test: `python bet_enhancement_system.py`
3. Review new C-tier classifications
4. Adjust min-tier filters if needed
5. Read ENHANCEMENT_IMPROVEMENTS_V2.md

### Breaking Changes
- **A-tier is stricter**: Requires 75% prob (some bets may drop to B)
- **C-tier means SKIP**: Not "marginal" anymore
- **More penalties**: Minutes stability adds -5 max

### Non-Breaking
- All existing functionality preserved
- Output format unchanged
- Can still filter by min-tier

---

## 🚨 Important Notes

### C-Tier Changed!
⛔ **C-tier now means "Do Not Bet"**

If you were betting C-tier bets before:
- Stop immediately
- Focus on B-tier and above
- Review why they're C-tier (quality issues)

### A-Tier Stricter
⭐ **A-tier now requires 75%+ win probability**

Some previous A-tier bets may become B-tier:
- This is correct behavior
- They didn't deserve A-tier status
- B-tier is still playable

### Minutes Matters
🕐 **Minutes volatility now penalized**

Bench players and rotation risks caught:
- Check warnings for "Minutes volatility"
- Consider reducing units on these
- Or skip if already in C-tier

---

## 📞 Quick Help

### My A-tier bets disappeared!
**Normal** - They likely had <75% probability and are now B-tier. This is correct.

### Everything is C-tier now!
**Working as designed** - Your bets are failing quality checks. Either:
1. Lower thresholds in config
2. Find better opportunities
3. Focus on B-tier (still playable)

### What's "line shading"?
Books adjust lines for public betting patterns. The flag warns you when odds might be shaded against your position.

### How do I disable minutes check?
In `_calculate_minutes_stability()`, comment out the penalty logic. But you shouldn't - it's protecting you!

---

**Pro Tip**: Focus on S/A/B-tier only. Ignore C/D entirely.
