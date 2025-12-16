"""
QUICK START - One-Click NBA Betting Analysis
==============================================

Runs the full enhanced pipeline with all new features:
  [OK] Probability consistency fix
  [OK] Clutch stats integration
  [OK] Correlation penalties
  [OK] Full transparency

Just run: python quick_start.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "=" * 80)
print("QUICK START - ENHANCED NBA BETTING ANALYSIS")
print("=" * 80)
print("\nStarting full analysis with ALL new features...\n")

try:
    # Import and run the main analysis
    from run_betting_analysis import run_analysis, run_validation, print_pipeline_info

    print_pipeline_info()

    # Run analysis on all games (quick default)
    output_path = run_analysis(max_games=999)

    if output_path:
        print("\n" + "=" * 80)
        print("[OK] ANALYSIS COMPLETE!")
        print("=" * 80)
        print(f"\nResults saved to: {output_path}")

        # Ask if user wants validation
        print("\n" + "-" * 80)
        print("Would you like to run validation tests? (y/n): ", end='')
        choice = input().strip().lower()

        if choice == 'y':
            run_validation(str(output_path))

        print("\n" + "=" * 80)
        print("DONE!")
        print("=" * 80)
        print("\nYour recommendations now include:")
        print("  - [OK] Consistent probabilities (no more Paolo bug!)")
        print("  - Clutch stats (win%, reliability%, pace)")
        print("  - Smart blending (confidence-weighted)")
        print("  - Correlation penalties (proper diversification)")
        print("  - Full transparency (model vs market vs final)")
        print("\nCheck the JSON file for detailed probability breakdowns!")
    else:
        print("\n[WARNING] Analysis failed or no bets found.")

except KeyboardInterrupt:
    print("\n\n[WARNING] Interrupted by user")
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print()
