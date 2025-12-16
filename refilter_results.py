
import json
import glob
import os
import sys
from pathlib import Path
from bet_enhancement_system import BetEnhancementSystem
from utils.display_recommendations import display_recommendations
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def refilter_and_display():
    # Find latest results file
    output_dir = Path("data/outputs")
    json_files = list(output_dir.glob("betting_recommendations_*.json"))
    
    if not json_files:
        print("No recommendation files found.")
        return

    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading results from: {latest_file}\n")
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
            
        bets_data = data.get('bets', [])
        original_recs = []
        
        # Extract original recommendations
        for bet in bets_data:
            if 'original_rec' in bet:
                original_recs.append(bet['original_rec'])
            else:
                # Fallback: try to reconstruct if original_rec missing (shouldn't happen with recent files)
                original_recs.append(bet)
                
        print(f"Found {len(original_recs)} bets to process.")
        
        # enhance
        print("Re-running enhancement system...")
        enhancer = BetEnhancementSystem()
        enhanced_bets = enhancer.enhance_recommendations(original_recs)
        
        # display
        print("\n" + "="*80)
        print("RE-FILTERED RESULTS")
        print("="*80)
        display_recommendations(enhanced_bets, use_print=True)
        
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    refilter_and_display()
