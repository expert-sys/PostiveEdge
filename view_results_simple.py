"""
Simple, crash-proof version to view analysis results
"""
import json
import sys
from pathlib import Path

def main():
    try:
        # Find results
        output_dir = Path("data") / "outputs"
        if not output_dir.exists():
            print("No results directory found. Run the analysis first.")
            return
        
        files = sorted(output_dir.glob("unified_analysis_*.json"), reverse=True)
        if not files:
            print("No results found. Run the analysis first.")
            return
        
        # Load most recent
        try:
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading file: {e}")
            return
        
        # Show summary
        print(f"\nFile: {files[0].name}")
        print(f"Date: {data.get('analysis_date', 'N/A')}")
        print(f"Games: {data.get('games_analyzed', 0)}")
        print(f"Bets: {data.get('total_bets', 0)}")
        print()
        
        # Show bets
        bets = data.get('bets', [])
        if not bets:
            print("No bets found.")
            return
        
        print(f"Top {len(bets)} Bets:\n")
        for i, bet in enumerate(bets, 1):
            if not isinstance(bet, dict):
                continue
            
            bet_type = bet.get('type', 'unknown')
            
            if bet_type == 'player_prop':
                player = bet.get('player', 'Unknown')
                stat = bet.get('stat', 'points')
                line = bet.get('line', 0)
                print(f"{i}. {player} - {stat} OVER {line}")
            else:
                market = bet.get('market', 'Unknown')
                result = bet.get('result', '')
                print(f"{i}. {result} - {market}")
            
            # Basic info
            try:
                odds = bet.get('odds', 0)
                conf = bet.get('confidence', 0)
                ev = bet.get('ev_per_100', 0)
                edge = bet.get('edge', 0)
                print(f"   Odds: {odds} | Conf: {conf} | EV: ${ev}/100 | Edge: {edge}%")
            except:
                pass
            
            print()
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

