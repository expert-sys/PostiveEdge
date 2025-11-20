# PositiveEdge - Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Launch the Platform

**Windows:**
```bash
launch.bat
```

**Linux/Mac:**
```bash
python launcher.py
```

### Step 2: Try Demo Mode

Select option **2** from the menu to run the demo with sample data.

### Step 3: Run a Full Analysis

1. Select option **5** (Sportsbet Scraper) to collect data
2. Select option **8** (Complete Analysis) to analyze
3. Select option **3** (View Results) to see your findings

## 📁 New Directory Structure

Your project is now cleanly organized:

```
PositiveEdge/
│
├── 🚀 LAUNCHERS
│   ├── launcher.py          # Main Python launcher
│   ├── launch.bat           # Windows quick launcher
│   └── launch.ps1           # PowerShell launcher
│
├── 🎯 CORE ENGINES
│   ├── main.py              # Value Engine Interactive CLI
│   ├── value_engine.py      # Core probability/EV calculator
│   ├── data_processor.py    # Data processing utilities
│   └── demo.py              # Demo mode
│
├── 🌐 SCRAPERS (scrapers/)
│   ├── universal_scraper.py              # Multi-site scraper
│   ├── sportsbet_final_enhanced.py      # Sportsbet scraper
│   ├── data_consolidator.py             # Data consolidation
│   ├── auto_analysis_pipeline.py        # Automated pipeline
│   ├── sportsbet_complete_analysis.py   # Full workflow
│   └── historical_data_helper.py        # Historical data tools
│
├── 📊 DATA (data/)
│   ├── outputs/             # Analysis results (JSON)
│   ├── scraped/             # Raw scraped data
│   ├── samples/             # Sample data files
│   └── historical/          # Historical performance data
│
├── 🧪 TESTS (tests/)
│   ├── test_engine.py
│   └── test_sportsbet_scraper.py
│
├── 📚 DOCUMENTATION (docs/)
│   ├── SPORTSBET_SCRAPER_GUIDE.md
│   ├── PIPELINE_GUIDE.md
│   ├── LAUNCHER_GUIDE.md
│   └── ... (10 guide files)
│
├── 🐛 DEBUG (debug/)
│   └── HTML files, logs, debug output
│
└── 📦 ARCHIVE (archive/)
    └── Old/deprecated scripts
```

## 🎯 What Each Component Does

### Value Analysis
- **Value Engine (Option 1)**: Calculate implied probability and expected value
- **Demo Mode (Option 2)**: See the engine in action with sample data
- **View Results (Option 3)**: Browse your previous analyses

### Data Collection
- **Universal Scraper (Option 4)**: Scrape multiple sportsbooks
- **Sportsbet Scraper (Option 5)**: Specialized Sportsbet scraper
- **Data Consolidator (Option 6)**: Merge data from multiple sources

### Automated Workflows
- **Auto Pipeline (Option 7)**: Automated scrape → analyze workflow
- **Complete Analysis (Option 8)**: Full Sportsbet workflow with insights
- **Pipeline Integration (Option 9)**: Integrated Sportsbet pipeline

### Utilities
- **Run Tests (Option 10)**: Execute test suite
- **Historical Data (Option 11)**: Access historical data tools
- **Documentation (Option 12)**: View all guides
- **System Status (Option 13)**: Check setup and dependencies

## 🔧 Common Commands

### Direct Launch (Skip Menu)
```bash
# Value Engine
python launcher.py --mode value

# Demo
python launcher.py --mode demo

# Scraper
python launcher.py --mode scraper

# Sportsbet
python launcher.py --mode sportsbet

# Pipeline
python launcher.py --mode pipeline
```

### Individual Components
```bash
# Value Engine directly
python main.py

# Demo directly
python demo.py

# Sportsbet scraper
python scrapers/sportsbet_final_enhanced.py

# Full pipeline
python scrapers/auto_analysis_pipeline.py
```

## 📖 Documentation

All documentation is now organized in the `docs/` folder:

- **LAUNCHER_README.md** - Launcher usage guide
- **SPORTSBET_SCRAPER_GUIDE.md** - Sportsbet scraper details
- **PIPELINE_GUIDE.md** - Automated pipeline guide
- **DATA_CONSOLIDATOR_README.md** - Data consolidation guide
- **QUICKSTART.md** - Original quick start
- And more...

View all docs from the launcher menu (option 12).

## 🎓 Example Workflow

Here's a complete workflow from scratch:

1. **Launch**: `launch.bat`
2. **Check Status**: Select option 13
3. **Try Demo**: Select option 2
4. **Collect Data**: Select option 5 (Sportsbet)
5. **Run Analysis**: Select option 8 (Complete Analysis)
6. **View Results**: Select option 3
7. **Review Findings**: Look for positive EV opportunities

## 💡 Tips

- Start with **Demo Mode (option 2)** to understand the engine
- Use **System Status (option 13)** to verify setup
- Check **Documentation (option 12)** for detailed guides
- **Direct mode** is great for automation: `python launcher.py --mode value`
- All output is saved in `data/outputs/` for later review

## 🆘 Troubleshooting

### Python not found
```bash
# Install Python from python.org
# Make sure "Add to PATH" is checked during installation
# Restart terminal after installation
```

### Missing dependencies
```bash
pip install -r requirements.txt
playwright install
```

### No data appearing
1. Run a scraper first (options 4-6)
2. Then run analysis (options 7-9)
3. Results appear in `data/outputs/`

### Need help?
- Option 12: View all documentation
- Option 13: Check system status
- README.md: Full project documentation

## 🎉 What's New

### Clean Organization
- All temporary files moved to appropriate folders
- Duplicate scripts consolidated
- Clear separation of concerns

### Unified Launcher
- Single entry point for all tools
- Interactive menu system
- Direct launch mode for automation

### Better Structure
- Scrapers in `scrapers/`
- Tests in `tests/`
- Docs in `docs/`
- Output in `data/outputs/`
- Debug files in `debug/`

### Easy Navigation
- Quick launch with `launch.bat`
- Browse results from menu
- System status checker
- Documentation viewer

---

**Ready to find value bets? Launch now with `launch.bat`! 🎯**
