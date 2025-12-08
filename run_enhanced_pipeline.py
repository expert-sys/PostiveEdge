"""
Run Enhanced Unified Analysis Pipeline
=====================================

Runs the full pipeline with enhanced analysis features
and shows professional betting recommendations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.unified_analysis_pipeline import main

print("=" * 80)
print("🚀 ENHANCED NBA BETTING ANALYSIS PIPELINE")
print("=" * 80)
print("\nThis will run the full analysis with enhanced features:")
print("  ✅ Risk Assessment (blowout, foul trouble, volatility)")
print("  ✅ Why Explanations (clear reasoning)")
print("  ✅ Variance-Adjusted Edges (prevents overconfidence)")
print("  ✅ Usage Change Tracking (recent vs season)")
print("  ✅ Pace/Defense Context (explicit explanations)")
print("\n" + "=" * 80)

# Set command line argument to analyze 3 games for faster testing
sys.argv = ['run_enhanced_pipeline.py', '3']

try:
    main()
except KeyboardInterrupt:
    print("\n\n⚠️  Analysis interrupted by user")
except Exception as e:
    print(f"\n❌ Error running pipeline: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("🎯 ENHANCED ANALYSIS COMPLETE")
print("=" * 80)
print("\nYour recommendations now include:")
print("  • Professional risk assessment")
print("  • Clear explanations for each bet")
print("  • Variance-adjusted edges")
print("  • Usage change insights")
print("  • Detailed pace/defense context")
print("\nThis creates trustworthy, actionable betting intelligence!")