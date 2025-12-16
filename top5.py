import json

with open('data/outputs/betting_recommendations_20251216_034325.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

bets = data.get('bets', [])

print("\n" + "="*70)
print(f"  TOP 5 BETTING RECOMMENDATIONS")
print("="*70 + "\n")

for i, bet in enumerate(bets[:5], 1):
    orig = bet.get('original_rec', {})
    
    selection = bet.get('selection', orig.get('selection', 'N/A'))
    market = bet.get('market', orig.get('market', 'N/A'))
    
    # Get historical from multiple possible locations
    hist_prob = orig.get('analysis', {}).get('historical_probability', 0)
    hist_rate = bet.get('historical_hit_rate', hist_prob)
    
    edge = bet.get('edge_percentage', 0)
    conf = bet.get('confidence_score', 0)
    ev = bet.get('expected_value', 0)
    odds = bet.get('odds', 0)
    
    print(f"{i}. {selection}")
    print(f"   {market}")
    print(f"   Historical Hit Rate: {hist_rate*100:.1f}%")
    print(f"   Edge: {edge:.1f}% | EV: {ev:.1f}% | Confidence: {conf:.0f}%")
    print(f"   Odds: {odds:.2f}")
    print("-"*70 + "\n")

print(f"Full results: data/outputs/betting_recommendations_20251216_034325.json")
print(f"Total bets available: {len(bets)}\n")
