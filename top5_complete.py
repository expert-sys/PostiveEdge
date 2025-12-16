import json

with open('data/outputs/betting_recommendations_20251216_034325.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

bets = data.get('bets', [])

print("\n" + "="*80)
print("  TOP 5 BETTING RECOMMENDATIONS - COMPLETE DATA")
print("="*80 + "\n")

for i, bet in enumerate(bets[:5], 1):
    orig = bet.get('original_rec', {})
    analysis = orig.get('analysis', {})
    
    selection = bet.get('selection', orig.get('selection', 'N/A'))
    market = bet.get('market', orig.get('market', 'N/A'))
    
    # Historical rate
    hist_prob = analysis.get('historical_probability', 0)
    hist_rate = bet.get('historical_hit_rate', hist_prob)
    
    # Other metrics
    edge = bet.get('edge_percentage', 0)
    conf = bet.get('confidence_score', 0)
    ev = bet.get('expected_value', 0)
    odds = bet.get('odds', 0)
    
    # Model/market probs
    model_prob = analysis.get('model_probability', 0)
    market_prob = analysis.get('market_probability', 0)
    final_prob = analysis.get('final_probability', 0)
    sample_size = analysis.get('sample_size', 0)
    
    print(f"{i}. {selection}")
    print(f"   Market: {market}")
    print(f"   ")
    print(f"   Historical Hit Rate: {hist_rate*100:.1f}%  (Sample: {sample_size} games)")
    print(f"   Model Probability: {model_prob*100:.1f}%")
    print(f"   Market Probability: {market_prob*100:.1f}%")
    print(f"   Final Probability: {final_prob*100:.1f}%")
    print(f"   ")
    print(f"   Edge: {edge:.1f}%")
    print(f"   Expected Value: {ev:.1f}%")
    print(f"   Confidence: {conf:.0f}%")
    print(f"   Odds: {odds:.2f}")
    print("-"*80 + "\n")

print(f"Total bets available: {len(bets)}")
print(f"Full results: data/outputs/betting_recommendations_20251216_034325.json\n")
