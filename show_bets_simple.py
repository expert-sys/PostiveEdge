"""
Simple Bet Viewer - No Console Close
=====================================
This script displays enhanced bets and waits for user input before closing.
"""

import sys
import io
import os

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    try:
        print("=" * 100)
        print("ENHANCED BETTING RECOMMENDATIONS")
        print("=" * 100)
        print()

        # Check if file exists
        if not os.path.exists('betting_recommendations.json'):
            print("❌ ERROR: betting_recommendations.json not found")
            print()
            print("Please run nba_betting_system.py first:")
            print("  python nba_betting_system.py")
            print()
            input("Press Enter to exit...")
            return 1

        # Import and run
        print("Loading enhancement system...")
        from view_enhanced_bets import main as view_main

        # Run the viewer
        result = view_main()

        print()
        print("=" * 100)
        print("DONE")
        print("=" * 100)
        print()
        print("Enhanced recommendations saved to: betting_recommendations_enhanced.json")
        print()

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: Required file not found: {e}")
        print("\nMake sure you have betting_recommendations.json in this directory.")
        result = 1

    except ImportError as e:
        print(f"\n❌ ERROR: Missing module: {e}")
        print("\nMake sure bet_enhancement_system.py is in the same directory.")
        result = 1

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        result = 1

    # Always pause before exit
    print()
    input("Press Enter to exit...")
    return result


if __name__ == '__main__':
    sys.exit(main())
