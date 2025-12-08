# NBA Betting System - Quick Reference

## One-Line Commands

```bash
# Quick start (Windows)
run_betting_system.bat

# Quick start (Linux/Mac)
./run_betting_system.sh

# Analyze 3 games (fast)
python nba_betting_system.py --games 3

# High confidence only (75%+)
python nba_betting_system.py --min-confidence 75

# Add new player to cache
echo "Player Name" >> PLAYERS_TO_ADD.txt && python build_databallr_player_cache.py
```

## Key Metrics Explained

| Metric | What It Means | Good Value |
|--------|---------------|------------|
| **Confidence** | Overall bet quality score | 70%+ |
| **Edge** | Your advantage over bookmaker | +3% or higher |
| **EV (Expected Value)** | Average profit per $100 bet | Positive |
| **Hit Rate** | Historical success rate | 55%+ for favorites |
| **Sample Size** | Games analyzed | 10+ ideal |

## Recommendation Strength

| Strength | Criteria | Action |
|----------|----------|--------|
| **VERY HIGH** | Confidence ≥80%, EV ≥5% | Strong bet |
| **HIGH** | Confidence ≥70%, EV ≥3% | Good bet |
| **MEDIUM** | Confidence ≥60%, EV ≥1% | Consider |
| **LOW** | Below thresholds | Skip |

## File Locations

```
nba-betting-system/
├── nba_betting_system.py              # Main script
├── betting_recommendations.json       # Output (your bets)
├── nba_betting_system.log            # Execution log
├── data/cache/
│   ├── databallr_player_cache.json   # Player IDs
│   └── player_stats_cache.json       # Recent stats (24h)
└── PLAYERS_TO_ADD.txt                # Add new players here
```

## Common Workflows

### Daily Analysis
```bash
# Morning: Run analysis
python nba_betting_system.py

# Review: Check recommendations
cat betting_recommendations.json

# Track: Record your bets
# (manual tracking recommended)
```

### Add New Player
```bash
# 1. Add to file
echo "Victor Wembanyama" >> PLAYERS_TO_ADD.txt

# 2. Rebuild cache
python build_databallr_player_cache.py

# 3. Re-run analysis
python nba_betting_system.py
```

### Troubleshooting
```bash
# Check logs
tail -20 nba_betting_system.log

# Clear cache
rm data/cache/player_stats_cache.json

# Reinstall dependencies
pip install -r requirements.txt
playwright install chromium
```

## Reading the Output

### Console Output
```
1. LeBron James - Points Over 25.5
   Game: Lakers @ Warriors (7:30 PM ET)
   Odds: 1.90 | Confidence: 78% | Strength: HIGH
   Edge: +5.2% | EV: +8.4%
   Historical: 65.0% (20 games)
   Projected: 70.3%
```

**Interpretation:**
- **Player**: LeBron James
- **Bet**: Over 25.5 points
- **Odds**: 1.90 (pays $90 profit on $100 bet)
- **Confidence**: 78% (high quality)
- **Edge**: +5.2% (you have 5.2% advantage)
- **EV**: +8.4% (expect $8.40 profit per $100 over time)
- **Historical**: Hit 65% of last 20 games
- **Projected**: Model predicts 70.3% chance

### JSON Output
```json
{
  "player_name": "LeBron James",
  "stat_type": "points",
  "line": 25.5,
  "odds": 1.90,
  "confidence_score": 78.0,
  "edge_percentage": 5.2,
  "expected_value": 8.4,
  "recommendation_strength": "HIGH"
}
```

## Betting Strategy Tips

### Bankroll Management
- **Unit Size**: 1-2% of bankroll per bet
- **Max Exposure**: 10-15% of bankroll per day
- **Never Chase**: Don't increase bets after losses

### Bet Selection
- **Focus on HIGH/VERY HIGH**: Skip MEDIUM unless you have additional insight
- **Minimum Edge**: +3% for props, +2% for sides/totals
- **Sample Size**: Prefer 15+ games over 5-10 games
- **Correlation**: Max 2 bets per game (system enforces this)

### Tracking Performance
Track these metrics:
- **ROI**: (Profit / Total Wagered) × 100
- **Win Rate**: Wins / Total Bets
- **Average Odds**: Sum of odds / Number of bets
- **Closing Line Value**: Your odds vs closing odds

### When to Bet
- ✅ **Early**: Lines often sharper closer to game time
- ✅ **Injury News**: Check for late scratches
- ✅ **Line Shopping**: Compare odds across books
- ❌ **Tilt**: Never bet emotionally
- ❌ **Chasing**: Don't try to recover losses

## Understanding Probability

### Odds to Probability
| Odds | Implied Probability | Break-Even Win Rate |
|------|---------------------|---------------------|
| 1.50 | 66.7% | 66.7% |
| 1.75 | 57.1% | 57.1% |
| 1.90 | 52.6% | 52.6% |
| 2.00 | 50.0% | 50.0% |
| 2.20 | 45.5% | 45.5% |
| 2.50 | 40.0% | 40.0% |

**Formula**: Probability = 1 / Odds

### Expected Value (EV)
```
EV = (Probability × (Odds - 1)) - (1 - Probability)
```

**Example:**
- Odds: 2.00
- Your Probability: 55%
- EV = (0.55 × 1.00) - 0.45 = +0.10 (+10%)

**Interpretation:**
- +10% EV = Expect $10 profit per $100 wagered over many bets
- Positive EV = Good bet
- Negative EV = Bad bet

## System Limitations

### What It Does Well
- ✅ Player props (points, rebounds, assists)
- ✅ Statistical projections
- ✅ Historical analysis
- ✅ Value detection

### What It Doesn't Do
- ❌ Live betting (pre-game only)
- ❌ Parlays/teasers
- ❌ Injury analysis (check manually)
- ❌ Lineup changes (check manually)
- ❌ Automatic bet placement

### Manual Checks Required
Before betting, always verify:
1. **Injury Report**: Check official injury reports
2. **Starting Lineup**: Confirm player is starting
3. **Minutes Projection**: Check recent playing time
4. **Matchup**: Consider defensive matchup
5. **Back-to-Back**: Check if team played yesterday

## Advanced Usage

### Custom Confidence Threshold
```bash
# Conservative (fewer bets, higher quality)
python nba_betting_system.py --min-confidence 80

# Aggressive (more bets, lower quality)
python nba_betting_system.py --min-confidence 65
```

### Analyze Specific Games
```bash
# Fast analysis (3 games)
python nba_betting_system.py --games 3

# Single game (fastest)
python nba_betting_system.py --games 1
```

### Custom Output
```bash
# Different filename
python nba_betting_system.py --output tonight_bets.json

# Pipe to other tools
python nba_betting_system.py | grep "VERY HIGH"
```

## Keyboard Shortcuts

### Windows Command Prompt
- `Ctrl+C`: Stop execution
- `Ctrl+V`: Paste
- `↑/↓`: Previous commands

### Linux/Mac Terminal
- `Ctrl+C`: Stop execution
- `Ctrl+D`: Exit
- `Ctrl+R`: Search command history
- `Tab`: Auto-complete

## Quick Diagnostics

### System Health Check
```bash
# Check Python
python --version

# Check dependencies
pip list | grep playwright

# Check cache
ls -lh data/cache/

# Check logs
tail -5 nba_betting_system.log
```

### Performance Metrics
- **1 game**: ~30-60 seconds
- **3 games**: ~2-3 minutes
- **All games**: ~5-10 minutes

Slower if:
- First run (installing browsers)
- Cache miss (fetching player stats)
- Many player props per game

## Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Python not found` | Python not installed | Install Python 3.8+ |
| `playwright: command not found` | Playwright not installed | `pip install playwright` |
| `Player not in cache` | Player ID missing | Add to PLAYERS_TO_ADD.txt |
| `Insufficient data (n=3)` | Not enough games | Expected, system skips |
| `No games found` | No NBA games today | Check NBA schedule |

## Resources

- **Setup Guide**: `SETUP_GUIDE.md` - Detailed installation
- **Architecture**: `SYSTEM_ARCHITECTURE.md` - Technical details
- **Main README**: `README.md` - Overview and examples

## Support Checklist

Before asking for help:
- [ ] Read error message carefully
- [ ] Check `nba_betting_system.log`
- [ ] Verify Python version (3.8+)
- [ ] Confirm dependencies installed
- [ ] Try with `--games 1` (simpler test)
- [ ] Check internet connection
- [ ] Review SETUP_GUIDE.md

## Responsible Betting Reminders

- 🎯 **Set Limits**: Decide max loss before betting
- 📊 **Track Results**: Keep detailed records
- 🧠 **Stay Disciplined**: Follow your strategy
- 💰 **Bet Small**: 1-2% of bankroll per bet
- 🚫 **Never Chase**: Don't try to recover losses
- ⏸️ **Take Breaks**: Step away if losing
- 📚 **Keep Learning**: Improve your edge over time

## Legal Disclaimer

This system is for educational and research purposes only. Sports betting involves risk and may not be legal in your jurisdiction. Always bet responsibly and within your means. Past performance does not guarantee future results.

---

**Last Updated**: December 2024
**Version**: 1.0.0
