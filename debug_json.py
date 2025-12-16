
import json
from pathlib import Path

file_path = Path(r"c:\Users\nikor\Documents\GitHub\PostiveEdge\data\outputs\betting_recommendations_20251216_012037.json")

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    bets = data.get('bets', [])
    if bets:
        count_with_hist = 0
        count_insight = 0
        count_prop = 0
        
        for bet in bets:
            rec = bet.get('original_rec', {})
            if 'insight' in rec:
                count_insight += 1
            if rec.get('_bet_type') == 'player_prop':
                 count_prop += 1 # Note: Insight props might not set this or might set it differently
            
            if 'historical_prob' in rec or 'historical_hit_rate' in rec:
                count_with_hist += 1
                if count_with_hist < 3:
                     print(f"Found hit rate in: {bet.get('player_name')} - {rec.get('historical_prob') or rec.get('historical_hit_rate')}")
        
        print(f"Total Bets: {len(bets)}")
        print(f"Bets with Original Rec: {len([b for b in bets if 'original_rec' in b])}")
        print(f"Insight-based Bets: {count_insight}")
        print(f"Player Prop Bets (marked): {count_prop}")
        print(f"Bets with Historical Data: {count_with_hist}")
        
    else:
        print("No bets found")

except Exception as e:
    print(f"Error: {e}")
