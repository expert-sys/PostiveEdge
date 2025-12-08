"""
Quick test script to diagnose view_analysis_results.py issues
"""
import sys
from pathlib import Path

print("Testing view_analysis_results.py...")
print("="*70)

# Test 1: Check if script exists
script_path = Path("view_analysis_results.py")
if not script_path.exists():
    print("[ERROR] view_analysis_results.py not found!")
    sys.exit(1)
print("[OK] Script file exists")

# Test 2: Check if data/outputs directory exists
output_dir = Path("data") / "outputs"
if not output_dir.exists():
    print(f"[WARNING] Output directory not found: {output_dir}")
    print("         This is OK if you haven't run the analysis yet")
else:
    print(f"[OK] Output directory exists: {output_dir}")

# Test 3: Check for result files
if output_dir.exists():
    files = list(output_dir.glob("unified_analysis_*.json"))
    print(f"[OK] Found {len(files)} result file(s)")
    if files:
        print(f"      Most recent: {files[0].name}")
else:
    print("[INFO] No output directory - no results to view yet")

# Test 4: Try importing required modules
print("\nTesting imports...")
try:
    import json
    print("[OK] json module")
except ImportError as e:
    print(f"[ERROR] json module: {e}")

try:
    from pathlib import Path
    print("[OK] pathlib module")
except ImportError as e:
    print(f"[ERROR] pathlib module: {e}")

try:
    import argparse
    print("[OK] argparse module")
except ImportError as e:
    print(f"[ERROR] argparse module: {e}")

# Test 5: Try running the script
print("\n" + "="*70)
print("Attempting to run view_analysis_results.py...")
print("="*70)

try:
    import subprocess
    result = subprocess.run(
        [sys.executable, "view_analysis_results.py", "--all"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print("[OK] Script executed successfully!")
        if result.stdout:
            print("\nOutput:")
            print(result.stdout[:500])  # First 500 chars
    else:
        print(f"[ERROR] Script exited with code {result.returncode}")
        if result.stderr:
            print("\nError output:")
            print(result.stderr)
        if result.stdout:
            print("\nStandard output:")
            print(result.stdout)
            
except subprocess.TimeoutExpired:
    print("[ERROR] Script timed out (took > 10 seconds)")
except Exception as e:
    print(f"[ERROR] Failed to run script: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Test complete!")
print("="*70)

