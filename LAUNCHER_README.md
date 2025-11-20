# PositiveEdge Launcher Guide

The comprehensive launcher provides a unified interface to all PositiveEdge platform components.

## Quick Start

### Windows

**Batch File (Recommended):**
```bash
launch.bat
```

**PowerShell:**
```powershell
.\launch.ps1
```

### Linux/Mac

```bash
python launcher.py
```

## Direct Mode

Launch specific components directly:

```bash
# Value Engine
python launcher.py --mode value

# Demo Mode
python launcher.py --mode demo

# Universal Scraper
python launcher.py --mode scraper

# Sportsbet Scraper
python launcher.py --mode sportsbet

# Auto Pipeline
python launcher.py --mode pipeline
```

## Menu Overview

### 📊 Value Analysis
- **Value Engine**: Interactive CLI for calculating implied probability and EV
- **Demo Mode**: Run with sample data to see how it works
- **View Results**: Browse and view previous analysis outputs

### 🌐 Data Collection
- **Universal Scraper**: Multi-site scraper for various sportsbooks
- **Sportsbet Scraper**: Specialized scraper for Sportsbet.com.au
- **Data Consolidator**: Merge data from multiple sources

### 🔄 Automated Pipelines
- **Auto Analysis Pipeline**: Automated scrape → consolidate → analyze workflow
- **Sportsbet Complete Analysis**: Full Sportsbet workflow with insights
- **Sportsbet Pipeline Integration**: Integrated pipeline for Sportsbet

### 🔧 Utilities
- **Run Tests**: Execute all test files
- **View Historical Data**: Access historical data helper
- **Open Documentation**: View all documentation files
- **Check System Status**: Verify installation and dependencies

## Features

- **Interactive Menu**: Easy-to-navigate menu system
- **Direct Launch**: Launch specific tools without menus
- **Status Checking**: Verify system setup and dependencies
- **Result Viewing**: Browse previous analysis results
- **Documentation Access**: Quick access to all guides

## Project Structure

After cleanup, your directory structure is:

```
PositiveEdge/
├── launcher.py              # Main launcher script
├── launch.bat              # Windows batch launcher
├── launch.ps1              # PowerShell launcher
├── main.py                 # Value Engine CLI
├── value_engine.py         # Core calculation engine
├── data_processor.py       # Data processing utilities
├── demo.py                 # Demo mode
├── README.md               # Main project documentation
├── LAUNCHER_README.md      # This file
│
├── scrapers/               # All scraper scripts
│   ├── universal_scraper.py
│   ├── sportsbet_final_enhanced.py
│   ├── sportsbet_scraper.py
│   ├── data_consolidator.py
│   ├── auto_analysis_pipeline.py
│   ├── sportsbet_complete_analysis.py
│   ├── sportsbet_pipeline_integration.py
│   └── historical_data_helper.py
│
├── data/                   # All data files
│   ├── outputs/           # Analysis results (JSON)
│   ├── scraped/           # Raw scraped data
│   └── historical/        # Historical performance data
│
├── tests/                  # Test files
│   ├── test_engine.py
│   └── test_sportsbet_scraper.py
│
├── docs/                   # Documentation
│   ├── SPORTSBET_SCRAPER_GUIDE.md
│   ├── PIPELINE_GUIDE.md
│   ├── LAUNCHER_GUIDE.md
│   └── ...
│
├── debug/                  # Debug files (HTML, logs)
│   ├── sportsbet_homepage.html
│   └── ...
│
└── archive/                # Old/deprecated scripts
    ├── sportsbet_scraper_v2.py
    └── ...
```

## Dependencies

The launcher automatically checks for required dependencies:

- Python 3.7+
- playwright (for web scraping)
- beautifulsoup4 (for HTML parsing)
- requests (for HTTP requests)

Install dependencies:
```bash
pip install -r requirements.txt
```

For Playwright browser automation:
```bash
playwright install
```

## Troubleshooting

### "Python is not installed or not in PATH"
- Install Python from [python.org](https://www.python.org/)
- During installation, check "Add Python to PATH"
- Restart your terminal/computer after installation

### "Module not found" errors
- Run: `pip install -r requirements.txt`
- For Playwright: `playwright install`

### Scripts not running
- Use the launcher menu (option 13) to check system status
- Verify all directories exist
- Check that scripts are in the correct folders

### No analysis results
- Run a scraper first (options 4-6)
- Then run a pipeline (options 7-9)
- Results will appear in `data/outputs/`

## Tips

1. **Start with Demo Mode** (option 2) to understand how the value engine works
2. **Run System Status** (option 13) after initial setup
3. **Use Direct Mode** for automation/scripting: `python launcher.py --mode value`
4. **Check Documentation** (option 12) for detailed guides on each component
5. **View Recent Results** (option 3) to see your latest analysis

## Example Workflow

1. Launch the platform: `launch.bat`
2. Run Sportsbet scraper (option 5)
3. Run Complete Analysis pipeline (option 8)
4. View analysis results (option 3)
5. Review findings and identify value bets

## Need Help?

- Check the main README.md for project overview
- Browse docs/ folder for detailed guides
- Run option 13 (System Status) to verify setup
- Check option 12 (Documentation) for all available guides

---

**Happy Value Hunting! 🎯**
