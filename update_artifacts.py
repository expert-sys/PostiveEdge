"""
Update Artifacts from Analysis
==============================
Reads the latest betting recommendations JSON and updates:
1. top5_results.md
2. projections_detail.md

FORMATTING: Matches user preference EXACTLY.
"""
import json
import os
import glob
from datetime import datetime

OUTPUT_DIR = 'data/outputs'
ARTIFACT_DIR = r'C:\Users\nikor\.gemini\antigravity\brain\fbf72528-17df-4fb6-9021-b67a06b51b39'

def get_latest_output_file():
    search_pattern = os.path.join(OUTPUT_DIR, 'betting_recommendations_*.json')
    files = glob.glob(search_pattern)
    if not files: return None
    return sorted(files, key=os.path.getmtime, reverse=True)[0]

def update_top5(bets, filename):
    md_path = os.path.join(ARTIFACT_DIR, 'top5_results.md')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    content = [
        f"# 🏀 BETTING RECOMMENDATIONS - {date_str}",
        ""
    ]
    
    for i, bet in enumerate(bets[:10], 1):  # Show top 10
        # Extract data
        orig = bet.get('original_rec', {})
        analysis = orig.get('analysis', {})
        selection = bet.get('selection', orig.get('selection', 'N/A'))
        market = bet.get('market', orig.get('market', 'N/A'))
        player = bet.get('player_name', 'Player')
        
        # Game Info
        game_info = bet.get('game_info', 'N/A')
        if game_info == 'N/A':
            # Try to construct from team names if available
            team = bet.get('team', '')
            opponent = bet.get('opponent', '')
            if team and opponent:
                game_info = f"{team} @ {opponent}"
        
        # Probabilities
        model_prob = analysis.get('adjusted_probability', 0) * 100
        if model_prob == 0: model_prob = analysis.get('model_probability', 0) * 100
        
        final_prob = analysis.get('final_probability', 0) * 100
        
        # Historical
        hist_rate = bet.get('historical_hit_rate', analysis.get('historical_probability', 0)) * 100
        sample = bet.get('sample_size', 0)
        
        # Metrics
        edge = bet.get('edge_percentage', 0)
        ev = bet.get('expected_value', 0)
        conf = bet.get('confidence_score', 0)
        odds = bet.get('odds', 0)
        tier = bet.get('quality_tier', 'N/A')
        
        # Formatting block
        content.append(f"TEAM MARKET: {selection} - {player}")
        content.append(f"   Game: {game_info}")
        content.append(f"   Odds: {odds:.2f} | Confidence: {conf:.1f}% | Strength: {tier}")
        content.append(f"   Edge: {edge:.1f}% | EV: {ev:.1f}%")
        content.append(f"   Sample Size: {sample} games | Historical: {hist_rate:.1f}%")
        content.append(f"   Projected Probability: {model_prob:.1f}%")
        content.append(f"   Final %: {final_prob:.1f}%")
        content.append("")
        content.append("---")
        content.append("")
        
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    print(f"Updated {md_path}")

def update_details(bets):
    md_path = os.path.join(ARTIFACT_DIR, 'projections_detail.md')
    content = ["# Full Projection Details", "", "## All Recommendations", ""]
    
    for i, bet in enumerate(bets, 1):
        sel = bet.get('selection', 'N/A')
        ev = bet.get('expected_value', 0)
        edge = bet.get('edge_percentage', 0)
        content.append(f"{i}. **{sel}** | EV: {ev:.1f}% | Edge: {edge:.1f}%")
        
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    print(f"Updated {md_path}")

if __name__ == "__main__":
    latest = get_latest_output_file()
    if latest:
        print(f"Reading {latest}...")
        with open(latest, 'r', encoding='utf-8') as f:
            data = json.load(f)
            bets = data.get('bets', [])
            update_top5(bets, latest)
            update_details(bets)
    else:
        print("No file found")
