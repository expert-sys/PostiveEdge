# Confidence Engine V2 - Quick Start Guide

## What Changed?

The system now uses **realistic confidence scores** instead of inflated ones. This means:
- 95% confidence is **extremely rare** (requires 80+ games, perfect conditions)
- 60-70% confidence is **normal** for good bets
- Sample size **strictly limits** maximum confidence

## Quick Commands

### Run Analysis with V2 Engine
```bash
# Analyze all games with V2 confidence
python nba_betting_system.py

# Analyze 3 games only
python nba_betting_system.py --games 3

# Higher confidence threshold (more selective)
python nba_betting_system.py --min-confidence 65
```

### Re-analyze Existing Bets
```bash
# Apply V2 logic to today's recommendations
python reanalyze_bets_v2.py
```

## Understanding V2 Confidence Scores

### Confidence Ranges
```
75-95%: VERY HIGH - Rare, requires perfect conditions
65-74%: HIGH      - Good bet, solid edge
55-64%: MEDIUM    - Acceptable, monitor closely
45-54%: LOW       - Risky, avoid or small stake
<45%:   SKIP      - Too unreliable
```

### Risk Levels
```
LOW:     Safe for multis, stable conditions
MEDIUM:  Single bet or small multi
HIGH:    Single bet only, one risk factor
EXTREME: SKIP - multiple risk factors
```

## Reading V2 Output

### Example Output
```
1. Jaden McDaniels - Rebounds Over 3.5 @ 1.43
   Confidence: 59% (was 95%)  ← V2 is more realistic
   Risk: EXTREME               ← Multiple risk factors
   Recommendation: SKIP        ← Don't bet this
   
   Why confidence dropped:
   • Small sample (n=20) - max capped at 85%
   • Minutes unstable - 5% penalty
   • Role change detected - 15% penalty
   • Bayesian shrinkage - 7% adjustment
```

### What to Look For
✅ **Good Bet Indicators:**
- Confidence ≥ 65%
- Risk: LOW or MEDIUM
- Recommendation: BET or CONSIDER
- Sample size ≥ 30
- Minutes stable
- No role changes

❌ **Red Flags:**
- Confidence < 55%
- Risk: HIGH or EXTREME
- Recommendation: SKIP or WATCH
- Sample size < 20
- Minutes unstable
- Role change detected

## Betting Strategy with V2

### Single Bets
```
Confidence ≥ 65%: Standard stake (1-2 units)
Confidence 55-64%: Reduced stake (0.5-1 unit)
Confidence < 55%:  Skip or track only
```

### Multi-Bets (Parlays)
```
Only use bets with:
- Risk: LOW or MEDIUM
- Confidence ≥ 60%
- Multi-Safe: YES
- Maximum 2 bets per game
```

### Bankroll Management
```
VERY HIGH (75%+): 2% of bankroll
HIGH (65-74%):    1.5% of bankroll
MEDIUM (55-64%):  1% of bankroll
LOW (<55%):       Skip or 0.5% (tracking)
```

## Common Questions

### Q: Why did my 95% confidence bet drop to 60%?
**A:** The old system was overconfident. V2 applies:
- Sample size caps (n=20 → max 85%)
- Volatility penalties (high variance → -15-30%)
- Role change penalties (unstable minutes → -15%)
- Bayesian shrinkage (small samples → -5-10%)

### Q: Should I still bet on 60% confidence bets?
**A:** Yes! 60% confidence in V2 = good bet. The old 95% was unrealistic. A 60% confidence bet with positive EV is profitable long-term.

### Q: What sample size do I need for 85%+ confidence?
**A:** Minimum 30 games, plus:
- Low volatility (CV < 25%)
- Stable minutes (variance < 8)
- No role changes
- Favorable matchup

### Q: Can I use EXTREME risk bets?
**A:** Not recommended. EXTREME = 3+ risk factors. These are too volatile for consistent profit.

### Q: How do I get more bets?
**A:** Lower the minimum confidence threshold:
```bash
python nba_betting_system.py --min-confidence 50
```
But be aware: lower confidence = higher risk.

## Interpreting Notes

### Sample Size Notes
```
"Very small sample (n=15)" → Need 15 more games
"Small sample (n=25)"      → Need 5 more games
"Adequate sample (n=35)"   → Good to bet
```

### Volatility Notes
```
"High volatility (CV=45%)" → Player inconsistent
"Low volatility (CV=18%)"  → Player consistent
```

### Role Change Notes
```
"Role change detected"     → Minutes changed 20%+
"Minutes unstable"         → Variance > 8 minutes
"Minutes trending up"      → Increasing role
```

### Matchup Notes
```
"Favorable matchup"        → Weak defense, fast pace
"Unfavorable matchup"      → Strong defense, slow pace
"Matchup adjustment: +5%"  → Probability boost
```

## Example Workflow

### 1. Run Analysis
```bash
python nba_betting_system.py --games 5
```

### 2. Review Output
Look for:
- Confidence ≥ 65%
- Risk: LOW or MEDIUM
- Positive EV ≥ 5%

### 3. Check Notes
Verify:
- Sample size ≥ 30
- No major red flags
- Favorable or neutral matchup

### 4. Place Bets
```
Single bets: Confidence ≥ 65%
Multis:      Risk LOW/MEDIUM, Confidence ≥ 60%
```

### 5. Track Results
```bash
# Re-analyze after games complete
python reanalyze_bets_v2.py
```

## Tips for Success

1. **Be Patient** - Wait for 30+ game samples
2. **Trust the System** - 60% confidence is good in V2
3. **Avoid EXTREME Risk** - No matter how tempting
4. **Use Proper Stakes** - Don't overbet on any single prop
5. **Track Everything** - Build your own database of results

## Getting Help

### Check Diagnostics
```bash
# Test V2 engine
python confidence_engine_v2.py

# View detailed analysis
python reanalyze_bets_v2.py
```

### Common Issues

**Issue:** No bets found
**Solution:** Lower min-confidence or wait for more games

**Issue:** All bets are EXTREME risk
**Solution:** Early season - need more data

**Issue:** Confidence seems too low
**Solution:** V2 is realistic - trust the math

## Summary

✅ **V2 is more accurate** - Lower confidence = more realistic
✅ **Better risk management** - Clear risk classifications
✅ **Profitable long-term** - Avoid overconfident bets
✅ **Trust the system** - 60% confidence is a good bet

**Remember:** The goal is long-term profitability, not high confidence scores. V2 helps you avoid the overconfidence trap that kills bankrolls.
