# How to Use the V2 Enhanced Betting System

## 🎯 Quick Start (Recommended)

### Option 1: Generate Fresh Recommendations ⭐
**Best for:** Getting today's bets with latest odds

```bash
# Double-click this file:
GENERATE_FRESH_BETS.bat
```

**What it does:**
1. Scrapes ALL available NBA games from Sportsbet
2. Gets player stats from DataBallr
3. Runs model projections
4. Applies V2 enhancements
5. Shows only B-tier and better bets

**Time:** ~3-10 minutes depending on number of games

---

### Option 2: View Existing Recommendations
**Best for:** Reviewing previously generated bets

```bash
# Double-click this file:
show-bets.bat
```

**What it does:**
- Loads `betting_recommendations.json`
- Applies V2 enhancements
- Displays filtered bets with warnings

**Time:** <5 seconds

**Note:** Uses old data (check file timestamp: Dec 5)

---

## 📁 Understanding the Files

### Recommendation Files

| File | Contents | When Created |
|------|----------|--------------|
| `betting_recommendations.json` | Base recommendations from scraping | After `nba_betting_system.py` runs |
| `betting_recommendations_enhanced.json` | V2 enhanced with all filters applied | After enhancement system runs |
| `betting_recommendations_v2.json` | Old format (ignore) | Legacy |

### Batch Files

| File | Purpose |
|------|---------|
| `GENERATE_FRESH_BETS.bat` | ⭐ **Scrape + analyze new games** |
| `show-bets.bat` | View existing recommendations |
| `quick-start-comprehensive.bat` | Run full pipeline with V2 |
| `TEST_ENHANCEMENTS_V2.bat` | Test V2 filters on existing data |

---

## 🔄 Workflows

### Daily Betting Workflow

**1. Morning (Check Games)**
```bash
GENERATE_FRESH_BETS.bat
```
- Generates fresh recommendations for today's games
- Time: 2-5 minutes

**2. Review Results**
Results are displayed in terminal and saved to:
- `betting_recommendations_enhanced.json`

**3. Focus on Quality**
- ⭐ **S-Tier**: Elite value (rare)
- ⭐ **A-Tier**: High quality (75%+ prob)
- ✓ **B-Tier**: Playable (standard)
- ⛔ **C-Tier**: **DO NOT BET**
- ❌ **D-Tier**: Avoid

**4. Check Warnings**
Pay attention to:
- ⚠ Minutes volatility
- ⚠ Line shading
- ⚠ Correlation detected
- ⚠ Small sample size

---

### Testing/Demo Workflow

**1. Test V2 Enhancements**
```bash
TEST_ENHANCEMENTS_V2.bat
```
- Uses existing data (fast)
- Shows how V2 filters work

**2. Quick View**
```bash
show-bets.bat
```
- Instant display
- No scraping needed

---

## 🎮 Command Line Options

### Basic Usage
```bash
# All available games (recommended), enhanced, B-tier minimum
python nba_betting_system.py --enhanced --min-tier B

# Limit to first 5 games (faster for testing)
python nba_betting_system.py --games 5 --enhanced --min-tier B

# Higher confidence threshold
python nba_betting_system.py --enhanced --min-confidence 60

# Only A-tier and above
python nba_betting_system.py --enhanced --min-tier A
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--games N` | Analyze N games | All games |
| `--enhanced` | Apply V2 enhancements | Off |
| `--min-tier X` | Minimum tier (S/A/B/C) | C |
| `--min-confidence N` | Minimum confidence % | 55 |
| `--output FILE` | Output file name | betting_recommendations.json |

---

## 📊 Understanding V2 Output

### Sample Output

```
1. ✓ Jaden McDaniels - Rebounds Over 3.5
   Game: Minnesota Timberwolves @ New Orleans Pelicans
   Odds: 1.36 → Fair: 1.28 (Mispricing: +0.08)
   Edge: +4.7% | EV: +6.4% | EV/Prob: 0.082
   Projected: 78.2% | Implied: 73.5%
   Confidence: 64% (Base: 69%, Sample: n=20)
   Projection: 4.9 vs Line 3.5 (Margin: +1.4)
   Consistency: 👍 Medium Consistency (75.0%)
   Minutes Stability: -5 points (variance: 11.5min)
   ⚠ Line potentially shaded by sportsbook
   Notes:
     ✓ Projected +1.4 vs line
   Warnings:
     ⚠ Minutes volatility: 11.5min variance (36% of avg)
     ⚠ Potential line shading: Heavy juice, Moderate favorite
```

### Key Metrics Explained

**Odds Analysis:**
- `Odds: 1.36` - Bookmaker odds
- `Fair: 1.28` - True value odds based on probability
- `Mispricing: +0.08` - Edge in odds (positive = value)

**Value Metrics:**
- `Edge: +4.7%` - Probability edge over implied
- `EV: +6.4%` - Expected value percentage
- `EV/Prob: 0.082` - Payoff vs risk ratio

**Probabilities:**
- `Projected: 78.2%` - Model's win probability
- `Implied: 73.5%` - Bookmaker's implied probability

**Confidence:**
- `64%` - Final confidence after all penalties
- `Base: 69%` - Before penalties
- `Sample: n=20` - Games analyzed

**Projection:**
- `4.9 vs Line 3.5` - Projected value vs betting line
- `Margin: +1.4` - How much over the line

**NEW V2 Metrics:**
- `Minutes Stability: -5` - Penalty for volatile rotation
- `⚠ Line shading` - Bookmaker may have adjusted line
- `⚠ Minutes volatility` - Rotation risk warning

---

## ⚠️ Common Issues & Solutions

### Issue: "No recommendations found"
**Cause:** No bets met quality thresholds

**Solutions:**
1. Lower min-confidence: `--min-confidence 50`
2. Lower min-tier: `--min-tier C` (not recommended)
3. Analyze more games: `--games 10`

---

### Issue: "Old data (Dec 5)"
**Cause:** Using old `betting_recommendations.json`

**Solution:**
```bash
# Generate fresh data
GENERATE_FRESH_BETS.bat
```

---

### Issue: "Everything is C-tier"
**Cause:** Bets failing V2 quality checks

**This is CORRECT behavior!** C-tier = Do Not Bet

**What to do:**
- Skip these bets
- Wait for better opportunities
- Or lower filters (not recommended):
  ```bash
  python nba_betting_system.py --min-confidence 50
  ```

---

### Issue: "Script closes immediately"
**Cause:** Error in pipeline

**Solution:**
1. Check `output.log` for errors
2. Run verification:
   ```bash
   verify_modules.bat
   ```
3. Check internet connection (for scraping)

---

### Issue: "A-tier bets disappeared"
**Cause:** V2 requires 75%+ probability for A-tier

**This is CORRECT!** They're now B-tier (still playable)

**No action needed** - B-tier is fine to bet

---

## 🎯 Quality Tier Guide

### When to Bet

**S-Tier (💎)**: Elite value
- Requirements: EV≥20%, Edge≥12%, Prob≥68%
- Action: Max units
- Frequency: Rare (1-2 per week)

**A-Tier (⭐)**: High quality
- Requirements: EV≥10%, Edge≥8%, **Prob≥75%** ← V2
- Action: Standard units
- Frequency: Occasional (3-5 per week)

**B-Tier (✓)**: Playable
- Requirements: EV≥5%, Edge≥4%
- Action: Reduced units (50-75% of standard)
- Frequency: Common (10-15 per week)

### When NOT to Bet

**C-Tier (⛔)**: Do Not Bet
- Fails ANY quality check:
  - Edge < 5%
  - Confidence < 60%
  - Mispricing < 0.10
  - Sample < 5
  - >2 props from same game
- Action: **Skip entirely**

**D-Tier (❌)**: Avoid
- Requirements: EV<0 or Prob<50%
- Action: Never bet

---

## 🔧 Configuration

### Adjust Thresholds

Edit `bet_enhancement_system.py`:

```python
# Line 128-133: Tier requirements
self.tier_thresholds = {
    'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
    'A': {'ev_min': 10.0, 'edge_min': 8.0, 'prob_min': 0.75},  # V2
    'B': {'ev_min': 5.0, 'edge_min': 4.0},
}

# Line 560: Minutes variance threshold
if variance_pct > 20.0:  # Change to adjust sensitivity

# Line 599-607: Line shading thresholds
if line >= 30.0:  # High points line
if odds < 1.70:   # Heavy juice
```

**Warning:** Lowering thresholds reduces bet quality

---

## 📚 Documentation Reference

### V2 Improvements
- **ENHANCEMENT_IMPROVEMENTS_V2.md** - Full details on V2
- **QUICK_REFERENCE_V2_IMPROVEMENTS.md** - Quick lookup
- **V2_IMPROVEMENTS_COMPLETE.md** - Implementation summary

### General Guides
- **START_HERE.md** - Main getting started guide
- **BET_ENHANCEMENT_GUIDE.md** - Complete enhancement docs
- **HOW_TO_USE_ENHANCEMENTS.md** - Usage guide

### This Guide
- **HOW_TO_USE_V2_SYSTEM.md** - You are here!

---

## 🚀 Quick Commands Cheat Sheet

```bash
# Generate fresh bets - ALL games (recommended)
GENERATE_FRESH_BETS.bat

# View existing bets
show-bets.bat

# Test V2 enhancements
TEST_ENHANCEMENTS_V2.bat

# Full pipeline - ALL games
quick-start-comprehensive.bat

# Command line - ALL games (recommended)
python nba_betting_system.py --enhanced --min-tier B

# Command line - Limit to 5 games (faster testing)
python nba_betting_system.py --games 5 --enhanced --min-tier B

# View specific tier
python view_enhanced_bets.py --min-tier A

# Show all (including C/D)
python view_enhanced_bets.py --show-all
```

---

## ✅ Best Practices

### 1. Daily Routine
- Morning: Run `GENERATE_FRESH_BETS.bat`
- Review: Focus on S/A/B tiers only
- Ignore: All C/D tier bets
- Check: Warnings for each bet

### 2. Unit Sizing
- S-Tier: 3-5 units
- A-Tier: 2-3 units
- B-Tier: 1-2 units
- C/D-Tier: 0 units (don't bet)

### 3. Risk Management
- Max 2 props per game (system enforces)
- Watch correlation warnings
- Avoid minutes volatility warnings
- Check line shading flags

### 4. Quality Over Quantity
- Better to have 1 A-tier than 5 C-tier bets
- V2 filters protect you from bad bets
- Trust the system - if it's C-tier, skip it

---

## 🎓 Example Session

```bash
# 1. Generate fresh recommendations
C:\PositiveEdge> GENERATE_FRESH_BETS.bat

Running betting system with V2 enhancements...
Configuration:
  - Games to analyze: 5
  - Min confidence: 55%
  - Enhanced filtering: ON
  - Min tier: B

[... scraping and analysis ...]

B-Tier (Playable) (2 bets)
────────────────────────────

1. ✓ Player A - Points Over 25.5
   Confidence: 72%
   Edge: +5.2% | EV: +8.1%
   ⚠ Minutes volatility warning

2. ✓ Player B - Rebounds Over 8.5
   Confidence: 68%
   Edge: +4.7% | EV: +6.4%
   ⚠ Line potentially shaded

SUCCESS - Fresh recommendations generated!

# 2. Review results
Files created:
  - betting_recommendations_enhanced.json

# 3. Decision
✅ Bet on Player B (no major warnings)
⚠ Monitor Player A (minutes volatility)
```

---

## 📞 Support

### File Issues
- Check file timestamps with `ls -lh *.json`
- Delete old files if needed
- Regenerate with `GENERATE_FRESH_BETS.bat`

### Output Issues
- Check `output.log`
- Run `verify_modules.bat`
- Check internet connection

### Enhancement Issues
- Read V2 documentation
- Test with `TEST_ENHANCEMENTS_V2.bat`
- Check configuration in `bet_enhancement_system.py`

---

**Pro Tip:** Save time by creating a desktop shortcut to `GENERATE_FRESH_BETS.bat` for one-click daily bet generation!
