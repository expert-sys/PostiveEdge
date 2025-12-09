# Batch Files Updated for Refactored Structure

## Summary

All batch files have been updated to work with the new modular structure. The refactored code is now organized into separate modules:

- `nba_betting/collectors/` - Data collection modules
- `nba_betting/engines/` - Analysis and projection engines
- `models/` - Data models
- `config/` - Configuration management
- `utils/` - Utility functions

## Updated Files

### 1. `quick-start-comprehensive.bat`
- ✅ Added PYTHONPATH setup
- ✅ Added module verification before running
- ✅ Works with refactored structure

### 2. `quick-start-comprehensive.ps1`
- ✅ Added PYTHONPATH setup (PowerShell format)
- ✅ Added module verification before running
- ✅ Works with refactored structure

### 3. `run_betting_system.bat`
- ✅ Added PYTHONPATH setup
- ✅ Ensures modules can be found

### 4. `verify_modules.bat` (NEW)
- ✅ Standalone verification script
- ✅ Tests all module imports
- ✅ Useful for troubleshooting

## What Changed

### PYTHONPATH Setup
All batch files now set the PYTHONPATH to include the current directory, ensuring Python can find all modules:

**Batch files:**
```batch
set PYTHONPATH=%CD%;%PYTHONPATH%
```

**PowerShell:**
```powershell
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
```

### Module Verification
The comprehensive launcher now verifies modules can be imported before running:

```batch
python -c "from nba_betting.collectors import SportsbetCollector, DataBallrValidator; from nba_betting.engines import ValueProjector; from models import BettingRecommendation; print('✓ All modules found')"
```

## Testing

All modules have been tested and verified:
- ✅ Collectors module imports correctly
- ✅ Engines module imports correctly
- ✅ Models module imports correctly
- ✅ Config module imports correctly
- ✅ Utils modules import correctly
- ✅ All classes can be instantiated

## Usage

### Quick Start (Comprehensive)
```batch
quick-start-comprehensive.bat
```

This will:
1. Activate virtual environment (if exists)
2. Set PYTHONPATH
3. Verify modules
4. Run the comprehensive launcher

### Direct System Run
```batch
run_betting_system.bat
```

This will:
1. Set up environment
2. Install dependencies if needed
3. Run `nba_betting_system.py` directly

### Module Verification
```batch
verify_modules.bat
```

This will:
1. Test all module imports
2. Report any issues
3. Verify the refactored structure is working

## Troubleshooting

If you encounter import errors:

1. **Run verification:**
   ```batch
   verify_modules.bat
   ```

2. **Check PYTHONPATH:**
   - Ensure batch files are run from the project root
   - PYTHONPATH should include the current directory

3. **Verify module structure:**
   - Check that `nba_betting/` directory exists
   - Check that `models/` directory exists
   - Check that `config/` directory exists
   - Check that `utils/` directory exists

4. **Check Python version:**
   - Requires Python 3.8+
   - Run `python --version` to verify

## Notes

- All batch files maintain backward compatibility
- The main `nba_betting_system.py` file still works as before
- Module imports are transparent to the end user
- No changes needed to how you run the system

## Next Steps

1. Test the system using `quick-start-comprehensive.bat`
2. If everything works, you're good to go!
3. If there are issues, run `verify_modules.bat` to diagnose

---

*Last Updated: After refactoring to modular structure*

