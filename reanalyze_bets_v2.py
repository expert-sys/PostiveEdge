"""
Re-analyze Today's Bets with Improved Confidence Logic
======================================================
Applies the V2 confidence engine to existing recommendations
to show realistic confidence scores.
"""

import json
from pathlib import Path
from confidence_engine_v2 import ConfidenceEngineV2, rate_todays_bets_with_improved_logic


def load_recommendations(filepath: str = 'betting_recommendations.json'):
    """Load existing recommendations"""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_rerated_recommendations(recommendations: list, filepath: str = 'betting_recommendations_v2.json'):
    """Save re-rated recommendations"""
    with open(filepath, 'w') as f:
        json.dump(recommendations, f, indent=2, default=str)


def print_comparison(recommendations: list):
    """Print before/after comparison"""
    print("="*80)
    print("CONFIDENCE ENGINE V2 - REANALYSIS OF TODAY'S BETS")
    print("="*80)
    print()
    
    for i, rec in enumerate(recommendations, 1):
        player = rec.get('player_name', 'Unknown')
        market = rec.get('market', '')
        selection = rec.get('selection', '')
        odds = rec.get('odds', 0)
        
        # Old vs new confidence
        old_conf = rec.get('confidence_score_v1', 0)
        new_conf = rec.get('confidence_score_v2', 0)
        diff = new_conf - old_conf
        
        # Old vs new probability
        old_prob = rec.get('projected_probability', 0)
        new_prob = rec.get('adjusted_probability_v2', 0)
        
        # Risk and recommendation
        risk = rec.get('risk_level', 'UNKNOWN')
        recommendation = rec.get('bet_recommendation', 'UNKNOWN')
        multi_safe = rec.get('multi_safe', False)
        
        print(f"{i}. {player} - {market} {selection} @ {odds}")
        print(f"   {'='*70}")
        print(f"   OLD Confidence: {old_conf:.1f}%  →  NEW Confidence: {new_conf:.1f}%  ({diff:+.1f}%)")
        print(f"   OLD Probability: {old_prob:.1%}  →  NEW Probability: {new_prob:.1%}")
        print(f"   Risk Level: {risk}")
        print(f"   Recommendation: {recommendation}")
        print(f"   Multi-Bet Safe: {'YES' if multi_safe else 'NO'}")
        
        # Show notes
        notes = rec.get('confidence_notes', [])
        if notes:
            print(f"   Notes:")
            for note in notes:
                print(f"     • {note}")
        
        print()


def main():
    # Load existing recommendations
    print("Loading existing recommendations...")
    recommendations = load_recommendations()
    
    print(f"Found {len(recommendations)} recommendations\n")
    
    # Re-rate with V2 engine
    print("Applying V2 confidence engine...\n")
    rerated = rate_todays_bets_with_improved_logic(recommendations)
    
    # Print comparison
    print_comparison(rerated)
    
    # Save results
    save_rerated_recommendations(rerated)
    print("="*80)
    print(f"✓ Saved re-rated recommendations to betting_recommendations_v2.json")
    print("="*80)
    
    # Summary statistics
    print("\nSUMMARY:")
    print("-"*80)
    
    avg_old_conf = sum(r.get('confidence_score_v1', 0) for r in rerated) / len(rerated)
    avg_new_conf = sum(r.get('confidence_score_v2', 0) for r in rerated) / len(rerated)
    
    print(f"Average Confidence (Old): {avg_old_conf:.1f}%")
    print(f"Average Confidence (New): {avg_new_conf:.1f}%")
    print(f"Average Change: {avg_new_conf - avg_old_conf:+.1f}%")
    print()
    
    # Risk distribution
    risk_counts = {}
    for r in rerated:
        risk = r.get('risk_level', 'UNKNOWN')
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    print("Risk Distribution:")
    for risk, count in sorted(risk_counts.items()):
        print(f"  {risk}: {count} bets")
    print()
    
    # Recommendation distribution
    rec_counts = {}
    for r in rerated:
        recommendation = r.get('bet_recommendation', 'UNKNOWN')
        rec_counts[recommendation] = rec_counts.get(recommendation, 0) + 1
    
    print("Recommendations:")
    for rec, count in sorted(rec_counts.items()):
        print(f"  {rec}: {count} bets")
    print()
    
    # Multi-bet safe count
    multi_safe_count = sum(1 for r in rerated if r.get('multi_safe', False))
    print(f"Multi-Bet Safe: {multi_safe_count}/{len(rerated)} bets")


if __name__ == '__main__':
    main()
