# Sports Value Engine - File Index

## 📚 Documentation Files (Read These First!)

### **STATUS.md** ⭐ START HERE
Project completion status, what was delivered, and how to get started.

### **QUICKSTART.md**
30-second quick start guide with examples and common use cases.

### **README.md**
Comprehensive documentation with full API reference, examples, and troubleshooting.

### **IMPLEMENTATION_SUMMARY.md**
Detailed summary of implementation, all features, and mathematical formulas.

## 💻 Application Files

### **main.py** (500 lines)
Interactive CLI application with 7 menu options:
- Manual market analysis
- CSV file analysis
- JSON file analysis
- Sample data demo
- Batch market analysis
- Help documentation
- Exit

**Usage**: `python main.py`

### **demo.py** (220 lines)
Demonstration script with 5 practical scenarios:
1. Simple player analysis
2. Over/under goals
3. CSV data analysis
4. Batch market evaluation
5. Odds comparison

**Usage**: `python demo.py`

## 🔧 Core Engine Files

### **value_engine.py** (380 lines)
Main calculation engine with:
- `ValueEngine` class - All calculations
- `HistoricalData` dataclass - Data model
- `MarketConfig` dataclass - Configuration
- `ValueAnalysis` dataclass - Results
- `analyze_simple_market()` - Quick API

**Usage**: Import and use in Python scripts

### **data_processor.py** (400 lines)
Data handling and processing with:
- `DataProcessor` class - CSV/JSON loading, filtering, adjustments
- `SampleDataGenerator` class - Generate test data

**Features**:
- CSV/JSON loading and saving
- Data extraction and validation
- Recency weighting
- Opponent strength adjustment
- Home/away split analysis
- Minutes adjustment

**Usage**: Import and use for data processing

## 🧪 Testing & Demo Files

### **test_engine.py** (440 lines)
Comprehensive test suite with 13 tests:

1. Basic binary outcome analysis
2. Continuous outcome with threshold
3. Small sample size (Bayesian shrinkage)
4. No value detection
5. Weighted outcomes (recency)
6. CSV data loading
7. JSON data loading
8. Opponent strength adjustment
9. Home/away split analysis
10. Minutes adjustment
11. Sample data generation
12. Batch analysis
13. EV calculation verification

**Status**: 13/13 passing ✓

**Usage**: `python test_engine.py`

## 🚀 Launcher Files

### **run.bat**
Windows batch file launcher - Automatically:
- Checks for Python installation
- Creates virtual environment
- Installs dependencies
- Launches application

**Usage**: Double-click or `run.bat` from Command Prompt

### **run.ps1**
Windows PowerShell launcher - Advanced version with:
- Color-coded output
- Execution policy handling
- Optional venv flag

**Usage**: `.\run.ps1` from PowerShell

## 📊 Data Files

### **sample_player_data.csv**
Example player performance data (20 games):
- Columns: date, opponent, location, minutes_played, goals, assists, shots, opponent_strength
- Real-looking data for testing
- Use in Option 2 (CSV analysis) of main menu

### **sample_markets.json**
5 pre-configured markets for batch analysis:
- Player to Score (Player A & B)
- Over 2.5 Goals
- Over 1.5 Assists
- Both Teams to Score
- Use in Option 5 (Batch) of main menu

## ⚙️ Configuration Files

### **.gitignore**
Properly configured for Python projects:
- Excludes __pycache__
- Excludes virtual environments
- Excludes IDE files
- Excludes test artifacts

### **requirements.txt**
Python dependencies - Currently empty (no external dependencies needed)

## 📁 File Organization

```
Core Components (Engine & Data)
├── value_engine.py           Main calculations
├── data_processor.py         Data handling
└── requirements.txt          Dependencies

User Interfaces
├── main.py                   Interactive CLI
├── demo.py                   Demonstrations
├── run.bat                   Windows launcher
└── run.ps1                   PowerShell launcher

Data Files
├── sample_player_data.csv    Player performance data
└── sample_markets.json       Market definitions

Testing
└── test_engine.py            Test suite (13 tests)

Documentation
├── STATUS.md                 Project status
├── QUICKSTART.md             Quick start guide
├── README.md                 Full documentation
├── IMPLEMENTATION_SUMMARY.md Detailed overview
└── INDEX.md                  This file

Configuration
└── .gitignore                Git configuration
```

## 🎯 Quick Navigation

### I want to...

**Get started quickly**
→ Read QUICKSTART.md (5 minutes)

**Understand the full system**
→ Read README.md (15 minutes)

**Use interactively**
→ Run `python main.py` or double-click `run.bat`

**See examples**
→ Run `python demo.py`

**Use programmatically**
→ Import from `value_engine.py`

**Process data**
→ Use `data_processor.py`

**Verify it works**
→ Run `python test_engine.py`

**Understand implementation**
→ Read IMPLEMENTATION_SUMMARY.md

**Check project status**
→ Read STATUS.md

## 📖 Reading Order

1. **STATUS.md** - Project overview (2 min)
2. **QUICKSTART.md** - Get started (5 min)
3. **README.md** - Full documentation (15 min)
4. Run `python demo.py` - See it in action (2 min)
5. Run `python main.py` - Try it yourself (5 min)
6. **IMPLEMENTATION_SUMMARY.md** - Deep dive (10 min)

## 🔗 Cross References

- **value_engine.py** implements algorithms described in README.md
- **data_processor.py** supports data loading described in README.md
- **main.py** uses both to provide the interface described in QUICKSTART.md
- **test_engine.py** validates algorithms from value_engine.py
- **demo.py** demonstrates usage examples from README.md

## 💡 Key Sections by Purpose

### For Users
- QUICKSTART.md - How to get started
- README.md - How to use features
- main.py - Interactive application
- demo.py - See examples

### For Developers
- value_engine.py - API reference
- data_processor.py - Data handling API
- README.md "Python API" section - Code examples
- test_engine.py - Usage examples in tests

### For Maintainers
- IMPLEMENTATION_SUMMARY.md - What was built
- STATUS.md - What works
- test_engine.py - What to test
- .gitignore - What to track

## ✅ Verification Checklist

Use this to verify the project is complete:

- [ ] All files present (14 items + .git directory)
- [ ] STATUS.md shows complete status
- [ ] `python test_engine.py` shows 13/13 passing
- [ ] `python demo.py` runs without errors
- [ ] `python main.py` launches interactive menu
- [ ] Windows: `run.bat` launches application
- [ ] Documentation is clear and helpful
- [ ] Sample data loads successfully
- [ ] .gitignore is properly configured

## 🎓 Learning Path

### Beginner
1. QUICKSTART.md
2. Run demo.py
3. Try main.py with sample data

### Intermediate
1. README.md sections on your use case
2. Load your own CSV data
3. Use batch analysis

### Advanced
1. Read value_engine.py source code
2. Read data_processor.py source code
3. Integrate into your own project
4. Review IMPLEMENTATION_SUMMARY.md for details

## 📞 Getting Help

### Issue: Can't get started
→ Read QUICKSTART.md

### Issue: Don't understand a concept
→ Check README.md "Concepts" section

### Issue: Found a bug
→ Check test_engine.py for examples
→ Read the docstring in the related function

### Issue: Want to integrate
→ Read README.md "Python API" section
→ Look at demo.py and test_engine.py for examples

---

**Total Files**: 14 (plus .git directory)
**Total Lines of Code**: ~2,500
**Total Documentation**: ~8,000 words
**Status**: ✅ Complete and tested
