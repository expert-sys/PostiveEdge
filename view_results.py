"""
View Analysis Results
====================
Displays previously saved analysis results from the unified analysis pipeline.
Automatically finds and displays the most recent results file.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Fix Windows console encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.convert_recommendations import convert_dict_to_recommendation
from utils.display_recommendations import display_recommendations


def find_latest_results_file() -> Optional[Path]:
    """Find the most recent unified_analysis_*.json file"""
    output_dir = Path(__file__).parent / "data" / "outputs"
    
    if not output_dir.exists():
        return None
    
    # Find all unified_analysis_*.json files
    pattern = "unified_analysis_*.json"
    result_files = list(output_dir.glob(pattern))
    
    if not result_files:
        return None
    
    # Sort by modification time (newest first)
    result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return result_files[0]


def load_results_file(filepath: Path) -> Optional[dict]:
    """Load results from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load results file: {e}")
        return None


def display_results_summary(data: dict):
    """Display summary information about the analysis"""
    print("\n" + "=" * 80)
    print("  ANALYSIS RESULTS SUMMARY")
    print("=" * 80)
    
    analysis_date = data.get('analysis_date', 'Unknown')
    if isinstance(analysis_date, str):
        try:
            # Parse ISO format and format nicely
            dt = datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_date = analysis_date
    else:
        formatted_date = str(analysis_date)
    
    print(f"\nAnalysis Date: {formatted_date}")
    print(f"Games Analyzed: {data.get('games_analyzed', 0)}")
    print(f"Total Bets Found: {data.get('total_bets', 0)}")
    print(f"  - Team Bets: {data.get('team_bets', 0)}")
    print(f"  - Player Props: {data.get('player_props', 0)}")
    
    # Show games info
    games = data.get('games', [])
    if games:
        print(f"\nGames:")
        for game in games:
            away = game.get('away_team', 'Unknown')
            home = game.get('home_team', 'Unknown')
            markets = game.get('total_markets', 0)
            props = game.get('total_props', 0)
            print(f"  {away} @ {home} ({markets} markets, {props} props)")
    
    print("=" * 80)


def main():
    """Main function to view results"""
    print("\n" + "=" * 80)
    print("  VIEW ANALYSIS RESULTS")
    print("=" * 80)
    print("\nSearching for latest analysis results...")
    
    # Find latest results file
    results_file = find_latest_results_file()
    
    if not results_file:
        print("\n[ERROR] No results file found!")
        print(f"Expected location: data/outputs/unified_analysis_*.json")
        print("\nPlease run the analysis first using:")
        print("  python scrapers/unified_analysis_pipeline.py")
        print("  or")
        print("  run_analysis.bat")
        return
    
    print(f"\n[OK] Found results file: {results_file.name}")
    print(f"     Created: {datetime.fromtimestamp(results_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load results
    data = load_results_file(results_file)
    if not data:
        return
    
    # Display summary
    display_results_summary(data)
    
    # Convert bets to recommendations
    bets = data.get('bets', [])
    if not bets:
        print("\n[INFO] No bets found in results file.")
        return
    
    print("\nConverting bets to recommendations...")
    recommendations = []
    
    # Create game info lookup for better game context
    games = data.get('games', [])
    game_lookup = {}
    for game in games:
        key = f"{game.get('away_team', '')} @ {game.get('home_team', '')}"
        game_lookup[key] = game
    
    for bet in bets:
        # Try to find game info
        game_str = bet.get('game', '')
        game_info = game_lookup.get(game_str)
        
        rec = convert_dict_to_recommendation(bet, game_info)
        if rec:
            recommendations.append(rec)
    
    if not recommendations:
        print("\n[WARNING] Could not convert any bets to recommendations.")
        print("Raw bet data:")
        for i, bet in enumerate(bets[:5], 1):
            print(f"  {i}. {bet}")
        if len(bets) > 5:
            print(f"  ... and {len(bets) - 5} more")
        return
    
    # Display recommendations using the same format as the pipeline
    print(f"\n[OK] Converted {len(recommendations)} bet(s) to recommendations\n")
    display_recommendations(recommendations, use_print=True)
    
    print("\n" + "=" * 80)
    print("  END OF RESULTS")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error viewing results: {e}")
        import traceback
        traceback.print_exc()
