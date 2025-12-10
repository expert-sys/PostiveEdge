# Bet Enhancement System - Quick Reference

## 🚀 Quick Start

```bash
# Run demo
python demo_enhanced_filtering.py

# Use with NBA betting system
python nba_betting_system.py --enhanced

# Only A-Tier or better
python nba_betting_system.py --enhanced --min-tier A
```

---

## 🏆 Quality Tiers

| Tier | Emoji | Criteria | Use Case |
|------|-------|----------|----------|
| **S** | 💎 | EV≥20 & Edge≥12% & Prob≥68% | Elite value - max units |
| **A** | ⭐ | EV≥10 & Edge≥8% | High quality - standard bet |
| **B** | ✓ | EV≥5 & Edge≥4% | Playable - reduced units |
| **C** | ~ | EV≥1 OR Conf≥70 | Marginal - parlay filler |
| **D** | ❌ | EV<0 OR Prob<50% | Avoid - filtered out |

---

## ⚖️ Penalties

| Type | Trigger | Penalty |
|------|---------|---------|
| **Sample Size** | n < 5 | -(5-n)×4 confidence |
| **Correlation** | Same team + stat | -12 confidence |
| **Correlation** | Same game + stat | -6 confidence |
| **Line Difficulty** | Line ≥ 30 | -5 confidence |
| **Line Difficulty** | Line ≥ 35 | -10 confidence |

---

## 📊 Key Metrics

### Fair Odds
```
Fair Odds = 1 / Probability
Mispricing = Market Odds - Fair Odds
```

### EV/Prob Ratio
```
EV Ratio = EV / Probability
Filter if < 0.08
```

### Projection Margin
```
Margin = Projected Value - Line
```

### Consistency
```
Consistency = 1 - (StdDev / Average)
🔥 High: 0.80+
👍 Medium: 0.60-0.80
⚠️ Low: <0.60
```

---

## 🎯 Market Efficiency Check

**Rule:** If edge < 3% AND probability in [55%, 60%]:
- Hide bet UNLESS confidence > 85%

**Why:** Sharp markets have minimal value

---

## 📈 Auto-Sort Order

1. **Tier** (S > A > B > C > D)
2. **EV** (high to low)
3. **Edge** (high to low)
4. **Adjusted Confidence** (high to low)
5. **Projection Margin** (high to low)

---

## 💰 Bankroll Guidelines

| Tier | Unit Size | Risk Level |
|------|-----------|------------|
| S | 3-5% | Low |
| A | 2-3% | Low-Medium |
| B | 1-2% | Medium |
| C | 0.5-1% | High |
| D | 0% | Avoid |

---

## 🔧 Command Line Flags

```bash
--enhanced              # Enable enhancement system
--min-tier {S,A,B,C}   # Minimum tier (default: C)
--min-confidence N     # Min confidence (default: 55)
--games N              # Number of games to analyze
```

---

## 📱 Common Examples

### Elite Value (S-Tier)
```
💎 Luka Dončić Points Over 28.5 @ 1.90
Edge: +22.4% | EV: +21.3% | Prob: 75%
→ MAX UNITS
```

### Small Sample Warning
```
✓ Player X Over 5.5 @ 1.95
Sample: n=3 → -8 penalty
Confidence: 60% (was 68%)
→ REDUCE UNITS
```

### Correlation Detected
```
⚠️ Fox & Sabonis - Both Assists
Same team + stat → -12 penalty
→ PICK ONE, NOT BOTH
```

### Sharp Market Filtered
```
❌ LeBron Points Over 24.5
Edge: 0.8% in 55-60% zone
→ FILTERED OUT
```

---

## 📋 Output Explanation

```
1. 💎 Luka Dončić - Points Over
   Game: Mavericks @ Rockets
   Matchup: vs Houston Rockets

   Odds: 1.90 → Fair: 1.33 (Mispricing: +0.57)
   ↑ Market  ↑ True  ↑ Your edge

   Edge: +22.4% | EV: +21.3% | EV/Prob: 0.284
   ↑ Prob advantage  ↑ Dollar return  ↑ Risk-adjusted

   Projected: 75.0% | Implied: 52.6%
   ↑ Your model      ↑ Bookmaker

   Confidence: 82% (Base: 82%, Sample: n=18)
   ↑ After penalties  ↑ Before  ↑ Sample size

   Projection: 32.4 vs Line 28.5 (Margin: +3.9)
   ↑ Model says     ↑ Line     ↑ Expected beat

   Consistency: 🔥 High (84%)
   ↑ Volatility rating
```

---

## ⚠️ Warnings to Watch

| Warning | Meaning | Action |
|---------|---------|--------|
| Small sample | n < 5 | Reduce unit size |
| Correlation | Same team/game + stat | Don't parlay |
| High line | Line ≥ 30 | Expect volatility |
| Sharp market | Low edge in efficient zone | Skip bet |
| Low consistency | CV < 0.60 | Reduce confidence |

---

## 🎓 Pro Tips

1. **S/A-Tier bets** are your bread and butter
2. **Watch correlation penalties** in parlays
3. **Small samples (n<5)** need unit reduction
4. **High lines (30+)** are inherently risky
5. **Sharp markets** are usually not worth it
6. **Consistency matters** - avoid volatile players in multis

---

## 📊 Typical Session Results

```
Analyzed: 8 bets
├─ S-Tier: 1 (💎 Elite)
├─ A-Tier: 1 (⭐ High Quality)
├─ B-Tier: 3 (✓ Playable)
├─ C-Tier: 1 (~ Marginal)
└─ D-Tier: 2 (❌ Filtered)

Quality Bets: 6/8 (75%)
```

---

## 🔗 Files

- `bet_enhancement_system.py` - Core engine
- `demo_enhanced_filtering.py` - Demo script
- `BET_ENHANCEMENT_GUIDE.md` - Full documentation
- `ENHANCEMENT_SUMMARY.md` - Implementation summary

---

## 💡 Remember

✅ **TIER = VALUE** (not just confidence)
✅ **PENALTIES = REALITY** (accounts for risk)
✅ **CORRELATION = DANGER** (for parlays)
✅ **CONSISTENCY = RELIABILITY** (for multis)
✅ **FAIR ODDS = TRUTH** (true edge)

---

**Quick Ref v1.0 | All 10 Enhancements Active**
