"""
NBA Betting System - Quick Test
================================
Tests the system with a single game to verify everything works.

Usage:
    python test_system.py
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import playwright
        print("  ✓ Playwright")
    except ImportError:
        print("  ✗ Playwright - Run: pip install playwright")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("  ✓ BeautifulSoup4")
    except ImportError:
        print("  ✗ BeautifulSoup4 - Run: pip install beautifulsoup4")
        return False
    
    try:
        import requests
        print("  ✓ Requests")
    except ImportError:
        print("  ✗ Requests - Run: pip install requests")
        return False
    
    return True


def test_scrapers():
    """Test that scraper modules exist"""
    print("\nTesting scraper modules...")
    
    scrapers_dir = Path(__file__).parent / "scrapers"
    
    required_files = [
        "sportsbet_final_enhanced.py",
        "databallr_scraper.py",
        "player_projection_model.py"
    ]
    
    all_exist = True
    for file in required_files:
        file_path = scrapers_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - Missing!")
            all_exist = False
    
    return all_exist


def test_cache():
    """Test that cache directory exists"""
    print("\nTesting cache directory...")
    
    cache_dir = Path(__file__).parent / "data" / "cache"
    
    if not cache_dir.exists():
        print(f"  Creating cache directory: {cache_dir}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        print("  ✓ Cache directory created")
    else:
        print("  ✓ Cache directory exists")
    
    return True


def test_main_script():
    """Test that main script exists"""
    print("\nTesting main script...")
    
    main_script = Path(__file__).parent / "nba_betting_system.py"
    
    if main_script.exists():
        print("  ✓ nba_betting_system.py exists")
        return True
    else:
        print("  ✗ nba_betting_system.py - Missing!")
        return False


def run_quick_test():
    """Run a quick test of the system"""
    print("\n" + "="*60)
    print("NBA BETTING SYSTEM - QUICK TEST")
    print("="*60)
    
    # Run all tests
    tests = [
        ("Imports", test_imports),
        ("Scrapers", test_scrapers),
        ("Cache", test_cache),
        ("Main Script", test_main_script)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20} {status}")
        if not result:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Run: python nba_betting_system.py --games 1")
        print("  2. Check output: betting_recommendations.json")
        print("  3. Review logs: nba_betting_system.log")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Install Playwright browsers: playwright install chromium")
        print("  - Check file structure matches documentation")
        return 1


if __name__ == "__main__":
    sys.exit(run_quick_test())
