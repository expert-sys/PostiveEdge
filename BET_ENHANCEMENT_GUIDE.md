# Bet Enhancement System - Complete Guide

## Overview

The **Bet Enhancement System** transforms raw betting recommendations into intelligently filtered, tier-classified opportunities with comprehensive risk assessment.

### What It Does

1. **Quality Tier Classification** - Categorizes every bet into S/A/B/C/D tiers
2. **Sample Size Penalties** - Penalizes low-sample predictions
3. **Correlation Detection** - Identifies and penalizes correlated bets
4. **Line Difficulty** - Adjusts for high-ceiling lines (30+, 35+)
5. **Market Efficiency** - Filters out sharp, low-value markets
6. **Consistency Ranking** - Rates player volatility
7. **EV/Prob Ratio** - Ensures value matches risk
8. **Fair Odds Display** - Shows true market mispricing
9. **Projection Margin** - Displays projected edge over line
10. **Auto-Sorting** - Organizes by tier, EV, edge, and confidence

---

## Quality Tiers

### 💎 S-Tier (Elite Value)
**Criteria:** EV ≥ +20 AND Edge ≥ +12% AND Probability ≥ 68%

Elite opportunities with exceptional value across all metrics.

**Example:**
- Luka Dončić Points Over 28.5 @ 1.90
- EV: +21.3% | Edge: +22.4% | Probability: 75%

### ⭐ A-Tier (High Quality)
**Criteria:** EV ≥ +10 AND Edge ≥ +8%

Strong value plays with significant edge.

**Example:**
- Jayson Tatum Rebounds Over 7.5 @ 1.85
- EV: +11.5% | Edge: +13.9%

### ✓ B-Tier (Playable)
**Criteria:** EV ≥ +5 AND Edge ≥ +4%

Solid value plays suitable for standard betting.

**Example:**
- De'Aaron Fox Assists Over 5.5 @ 1.95
- EV: +7.2% | Edge: +12.7%

### ~ C-Tier (Marginal)
**Criteria:** EV ≥ +1 OR Confidence ≥ 70%

Marginal value - use with caution or in parlays.

**Example:**
- Anthony Edwards Points Over 26.5 @ 1.92
- EV: +2.1% | Confidence: 74%

### ❌ D-Tier (Avoid)
**Criteria:** EV < 0 OR Probability < 50%

No value - filtered out automatically.

---

## Penalties & Adjustments

### 1. Sample Size Penalty

**Formula:**
```
effective_confidence = confidence - (5 - sample_size) × 4  (if n < 5)
```

**Examples:**
- n=5 → zero penalty
- n=3 → minus 8 confidence points
- n=1 → minus 16 confidence points

**Why:** Prevents overconfidence in small samples.

---

### 2. Correlation Penalty

**Rules:**
- Same team AND same stat: **-12 confidence**
- Same game AND same stat: **-6 confidence**
- Otherwise: **0**

**Example:**
- De'Aaron Fox Assists Over 5.5
- Domantas Sabonis Assists Over 6.5
- **Both Sacramento Kings, both assists → -12 penalty**

**Why:** Correlated bets amplify risk.

---

### 3. Line Difficulty Penalty

**Thresholds:**
- Line ≥ 30: **-5 penalty**
- Line ≥ 35: **-10 penalty**

**Example:**
- Stephen Curry Points Over 32.5
- **High line (32.5) → -5 confidence penalty**

**Why:** High lines are inherently more volatile.

---

### 4. Market Efficiency Check

**Rule:**
```
If edge < 3% AND probability in [55%, 60%]:
    hide unless confidence > 85%
```

**Example:**
- LeBron Points Over 24.5 @ 1.78
- Edge: 0.8% (low)
- Probability: 57% (efficient zone)
- Confidence: 72% (not high enough)
- **Result: FILTERED OUT**

**Why:** Sharp markets offer minimal value.

---

### 5. Consistency Ranking

**Formula:**
```
consistency = 1 - (std_dev / average)
```

**Levels:**
- 🔥 **High Consistency** (0.80+)
- 👍 **Medium Consistency** (0.60-0.80)
- ⚠️ **Low Consistency** (<0.60)

**Why:** Volatile players are riskier even with good projections.

---

### 6. EV-to-Prob Ratio

**Formula:**
```
EV_ratio = EV / probability
```

**Threshold:** Filter out if `EV_ratio < 0.08`

**Example:**
- EV: 5%
- Probability: 60%
- Ratio: 5 / 60 = 0.083 ✓ PASSES

**Why:** Ensures payoff justifies risk.

---

### 7. Fair Odds & Mispricing

**Formulas:**
```
fair_odds = 1 / probability
mispricing = market_odds - fair_odds
```

**Display:**
```
Odds: 1.88 → Fair: 1.46 (Mispricing: +0.42)
```

**Why:** Shows true value in intuitive format.

---

### 8. Projection Margin

**Formula:**
```
projection_margin = projected_value - line
```

**Example:**
- Projected: 32.4 points
- Line: 28.5
- **Margin: +3.9**

**Why:** Shows how much player is expected to beat the line.

---

## Auto-Sorting

Bets are sorted by:
1. **Tier** (S > A > B > C > D)
2. **Expected Value** (descending)
3. **Edge Percentage** (descending)
4. **Adjusted Confidence** (descending)
5. **Projection Margin** (descending)

This ensures the best opportunities appear first.

---

## Usage

### Basic Usage

```python
from bet_enhancement_system import BetEnhancementSystem

# Load recommendations
with open('betting_recommendations.json', 'r') as f:
    recommendations = json.load(f)

# Enhance
enhancer = BetEnhancementSystem()
enhanced_bets = enhancer.enhance_recommendations(recommendations)

# Filter to quality bets
quality_bets = enhancer.filter_bets(
    enhanced_bets,
    min_tier=QualityTier.C,
    exclude_d_tier=True
)

# Display
enhancer.display_enhanced_bets(quality_bets)
```

### Command Line

```bash
# Standard run
python nba_betting_system.py

# With enhanced filtering (recommended)
python nba_betting_system.py --enhanced

# Enhanced with higher tier threshold
python nba_betting_system.py --enhanced --min-tier A

# Demo with sample data
python demo_enhanced_filtering.py
```

### Integration with NBA Betting System

```bash
# Run full pipeline with enhancements
python nba_betting_system.py --enhanced --min-tier B --games 3

# Output files:
# - betting_recommendations.json (raw)
# - betting_recommendations_enhanced.json (filtered & enhanced)
```

---

## Output Format

### Enhanced Bet Display

```
1. 💎 Luka Dončić - Points Over
   Game: Dallas Mavericks @ Houston Rockets
   Matchup: vs Houston Rockets
   Odds: 1.90 → Fair: 1.33 (Mispricing: +0.57)
   Edge: +22.4% | EV: +21.3% | EV/Prob: 0.284
   Projected: 75.0% | Implied: 52.6%
   Confidence: 82% (Base: 82%, Sample: n=18)
   Projection: 32.4 vs Line 28.5 (Margin: +3.9)
   Consistency: 🔥 High Consistency (84%)
   Notes:
     ✓ ELITE VALUE: All metrics exceed premium thresholds
     ✓ Projected +3.9 vs line
```

### JSON Output

```json
{
  "player_name": "Luka Dončić",
  "market": "Points",
  "selection": "Over",
  "line": 28.5,
  "odds": 1.90,
  "enhanced_metrics": {
    "quality_tier": "S",
    "tier_emoji": "💎",
    "effective_confidence": 82.0,
    "adjusted_confidence": 82.0,
    "sample_size_penalty": 0.0,
    "correlation_penalty": 0.0,
    "line_difficulty_penalty": 0.0,
    "consistency_rank": "🔥 High Consistency",
    "consistency_score": 0.84,
    "ev_to_prob_ratio": 0.284,
    "fair_odds": 1.33,
    "odds_mispricing": 0.57,
    "projection_margin": 3.9,
    "final_score": 185.6,
    "notes": [
      "ELITE VALUE: All metrics exceed premium thresholds",
      "Projected +3.9 vs line"
    ],
    "warnings": []
  }
}
```

---

## Configuration

All thresholds are configurable in `bet_enhancement_system.py`:

```python
# Quality tier thresholds
self.tier_thresholds = {
    'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
    'A': {'ev_min': 10.0, 'edge_min': 8.0},
    'B': {'ev_min': 5.0, 'edge_min': 4.0},
    'C': {'ev_min': 1.0, 'conf_min': 70.0},
}

# Sample size baseline
self.sample_baseline = 5

# Line difficulty thresholds
self.high_line_threshold = 30.0
self.extreme_line_threshold = 35.0

# Market efficiency thresholds
self.low_edge_threshold = 3.0
self.sharp_prob_range = (0.55, 0.60)
self.high_confidence_override = 85.0

# EV ratio threshold
self.min_ev_ratio = 0.08

# Consistency thresholds
self.high_consistency_threshold = 0.80
self.medium_consistency_threshold = 0.60
```

---

## Examples

### Example 1: S-Tier Elite Value

```
💎 Luka Dončić - Points Over 28.5
- Odds: 1.90 → Fair: 1.33 (Mispricing: +0.57)
- Edge: +22.4% | EV: +21.3%
- Projected: 75.0% | Sample: n=18
- Projection: 32.4 vs Line 28.5 (+3.9)
✓ ELITE VALUE: All metrics exceed premium thresholds
```

**Why S-Tier:**
- EV (21.3%) > 20% ✓
- Edge (22.4%) > 12% ✓
- Probability (75%) > 68% ✓

---

### Example 2: Sample Size Penalty

```
✓ De'Aaron Fox - Assists Over 5.5
- Confidence: 60% (Base: 68%, Sample: n=3)
- Sample Penalty: -8 points
⚠ Small sample penalty: -8 confidence points (n=3)
```

**Penalty Calculation:**
- Formula: (5 - 3) × 4 = 8
- Effective Confidence: 68 - 8 = 60%

---

### Example 3: Correlation Detection

```
✓ Domantas Sabonis - Assists Over 6.5
- Confidence: 59% (Base: 71%, Sample: n=15)
- Correlation Penalty: -12 points
⚠ Correlation detected: Same team (Sacramento Kings) + stat (assists)
```

**Why Penalized:**
- Same team as De'Aaron Fox ✓
- Same stat (assists) ✓
- Penalty: -12 confidence points

---

### Example 4: Market Efficiency Filter

```
❌ LeBron James - Points Over 24.5 (FILTERED OUT)
- Edge: 0.8% (< 3%)
- Probability: 57% (in 55-60% zone)
- Confidence: 72% (< 85% override threshold)
⚠ Sharp market: Edge 0.8% < 3.0% in efficient zone
```

**Why Filtered:**
- Low edge in efficient probability zone
- Confidence not high enough to override

---

## Best Practices

### For Single Bets
- Focus on **A-Tier or better**
- Minimum confidence: **70%**
- Prefer high consistency players

### For Parlays
- Use **B-Tier or better**
- Avoid correlated bets (watch penalties)
- Maximum 3-4 legs
- Ensure no same-game, same-stat combinations

### For Bankroll Management
- S-Tier: 3-5% of bankroll
- A-Tier: 2-3% of bankroll
- B-Tier: 1-2% of bankroll
- C-Tier: 0.5-1% of bankroll

---

## Troubleshooting

### Issue: Too many bets filtered out

**Solution:** Lower the minimum tier
```bash
python nba_betting_system.py --enhanced --min-tier C
```

### Issue: No S-Tier or A-Tier bets

**Possible causes:**
- Market is efficient (bookmakers are sharp)
- Small samples (increase `--games` parameter)
- Low value day (not every day has elite opportunities)

### Issue: Correlation penalties too aggressive

**Solution:** Adjust thresholds in `bet_enhancement_system.py`:
```python
# Reduce penalties
if same_team and same_stat:
    penalty = -8.0  # Instead of -12.0
elif same_game and same_stat:
    penalty = -4.0  # Instead of -6.0
```

---

## Files

- `bet_enhancement_system.py` - Core enhancement logic
- `demo_enhanced_filtering.py` - Demonstration with sample data
- `nba_betting_system.py` - Main pipeline (updated with --enhanced flag)
- `BET_ENHANCEMENT_GUIDE.md` - This guide

---

## FAQ

**Q: What's the difference between EV and Edge?**

A:
- **Edge** = (Projected Prob - Implied Prob) × 100
- **EV** = Expected value per $100 wagered

Edge shows the probability advantage, EV shows the dollar return.

**Q: Why are some high-confidence bets rated C-Tier?**

A: Tier classification prioritizes **value** (EV + Edge), not just confidence. A 90% confidence bet with 2% edge is C-Tier, while a 70% confidence bet with 15% edge is A-Tier.

**Q: How do I adjust for my own risk tolerance?**

A: Modify the tier thresholds in `bet_enhancement_system.py`. Conservative bettors should raise the thresholds; aggressive bettors can lower them.

**Q: Can I use this for sports other than NBA?**

A: Yes, the system is sport-agnostic. It works with any betting recommendations that have EV, edge, probability, and confidence metrics.

---

## Support

For issues or questions:
1. Check this guide first
2. Review the demo: `python demo_enhanced_filtering.py`
3. Examine sample output in `demo_enhanced_bets.json`

---

## License

Part of the PositiveEdge NBA Betting System.
