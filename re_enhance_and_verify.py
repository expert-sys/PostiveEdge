
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bet_enhancement_system import BetEnhancementSystem

def re_enhance_and_verify():
    file_path = Path(r"c:\Users\nikor\Documents\GitHub\PostiveEdge\data\outputs\betting_recommendations_20251216_012037.json")
    
    print(f"Loading data from {file_path}")
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    bets = data.get('bets', [])
    print(f"Loaded {len(bets)} bets.")

    # Extract original recommendations
    recommendations = []
    skipped = 0
    for bet in bets:
        if 'original_rec' in bet:
            recommendations.append(bet['original_rec'])
        else:
            skipped += 1
            
    if skipped > 0:
        print(f"Warning: {skipped} bets missing 'original_rec'.")

    if not recommendations:
        print("No recommendations found to re-enhance.")
        return

    print(f"Re-enhancing {len(recommendations)} recommendations...")
    
    try:
        enhancer = BetEnhancementSystem()
        enhanced_bets = enhancer.enhance_recommendations(recommendations)
        print(f"Successfully re-enhanced {len(enhanced_bets)} bets.")
        
        # Verify and Display
        print("\nTOP BETS (Re-enhanced):")
        print("-" * 60)
        
        # Display top 10
        for i, bet in enumerate(enhanced_bets[:10], 1):
            player = bet.player_name or bet.market or 'Unknown'
            # Check for Kevin Durant specifically
            is_target = 'Durant' in str(player)
            
            hist_rate = bet.historical_hit_rate
            
            print(f"{i}. {player} - {bet.market}")
            print(f"   Historical Hit Rate: {hist_rate:.1%}")
            
            if is_target:
                print(f"   *** TARGET FOUND: {player} ***")
            
            if hist_rate > 0:
                 print(f"   [PASS] Non-zero historical rate")
            else:
                 print(f"   [FAIL] Zero historical rate (unless legitimately 0)")
            print("-" * 30)

    except Exception as e:
        print(f"Error during enhancement: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    re_enhance_and_verify()
