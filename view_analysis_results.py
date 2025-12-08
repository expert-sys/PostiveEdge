"""
View Analysis Results
=====================
Display saved analysis results from unified_analysis_pipeline.py

Usage:
  python view_analysis_results.py              # Show most recent results
  python view_analysis_results.py --latest      # Show most recent results
  python view_analysis_results.py --all         # List all available results
  python view_analysis_results.py --file <name> # View specific file
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging for errors
logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def find_result_files() -> List[Path]:
    """Find all unified analysis result files"""
    output_dir = Path("data") / "outputs"
    if not output_dir.exists():
        return []
    
    # Find all unified_analysis_*.json files
    files = sorted(output_dir.glob("unified_analysis_*.json"), reverse=True)
    return files


def load_results(file_path: Path) -> Optional[Dict]:
    """Load results from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {file_path}: {e}")
        return None


def print_results_summary(data: Dict):
    """Print summary of analysis results"""
    print("\n" + "="*70)
    print("  ANALYSIS RESULTS SUMMARY")
    print("="*70)
    
    print(f"\nAnalysis Date: {data.get('analysis_date', 'N/A')}")
    print(f"Games Analyzed: {data.get('games_analyzed', 0)}")
    print(f"Total Bets Found: {data.get('total_bets', 0)}")
    print(f"  - Team Bets: {data.get('team_bets', 0)}")
    print(f"  - Player Props: {data.get('player_props', 0)}")
    print()


def safe_get(data: Dict, *keys, default=None):
    """Safely get nested dictionary values"""
    try:
        result = data
        for key in keys:
            if not isinstance(result, dict):
                return default
            result = result.get(key)
            if result is None:
                return default
        return result
    except (KeyError, TypeError, AttributeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Safely convert to int"""
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def print_bet_details(bet: Dict, index: int):
    """Print detailed information for a single bet"""
    if not bet or not isinstance(bet, dict):
        print(f"{index}. [ERROR] Invalid bet data")
        return
    
    try:
        bet_type = bet.get('type', 'UNKNOWN') or 'UNKNOWN'
        print(f"{index}. [{bet_type.upper().replace('_', ' ')}] ", end="")
        
        if bet_type == 'team_bet':
            print(f"{bet.get('result', 'N/A')} - {bet.get('market', 'N/A')}")
            print(f"   {bet.get('fact', 'N/A')}")
            
            # Check if model projections are available
            has_model = bet.get('has_model_projection', False) or False
            analysis = bet.get('analysis', {}) or {}
            if not isinstance(analysis, dict):
                analysis = {}
            proj_details = safe_get(analysis, 'projection_details')
            projected_ev = safe_get(analysis, 'projected_expected_value')
            projected_prob = safe_get(analysis, 'projected_prob')
            historical_prob = safe_float(safe_get(analysis, 'historical_probability'), 0.0)
            
            if proj_details and isinstance(proj_details, dict):
                # Team bet with projection details
                projected_total = safe_get(proj_details, 'projected_total')
                if projected_total is not None:
                    try:
                        print(f"   Projected Total: {safe_float(projected_total, 0):.1f} | Prob: {historical_prob:.1%}", end="")
                        if projected_prob is not None:
                            original_hist_prob = safe_float(safe_get(analysis, 'original_historical_probability'), historical_prob)
                            print(f" (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})")
                        else:
                            print()
                        # Show pace factor if available
                        pace_factor = safe_float(safe_get(proj_details, 'pace_factor'), 1.0)
                        if abs(pace_factor - 1.0) > 0.001:
                            print(f"   Pace Factor: {pace_factor:.3f}x")
                    except Exception as e:
                        logger.debug(f"Error displaying projected total: {e}")
                        print(f"   Prob: {historical_prob:.1%}")
                else:
                    try:
                        if projected_prob is not None:
                            original_hist_prob = safe_float(safe_get(analysis, 'original_historical_probability'), historical_prob)
                            print(f"   Projected Prob: {safe_float(projected_prob, 0):.1%} | Final Prob: {historical_prob:.1%} (Hist: {original_hist_prob:.1%})")
                        else:
                            print(f"   Prob: {historical_prob:.1%}")
                    except Exception:
                        print(f"   Prob: {historical_prob:.1%}")
            elif projected_ev is not None:
                try:
                    original_hist_prob = safe_float(safe_get(analysis, 'original_historical_probability'), historical_prob)
                    if projected_prob is not None:
                        print(f"   Projected EV: ${safe_float(projected_ev, 0):.2f}/100 | Prob: {historical_prob:.1%} (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})")
                    else:
                        print(f"   Projected EV: ${safe_float(projected_ev, 0):.2f}/100 | Prob: {historical_prob:.1%}")
                except Exception:
                    print(f"   Prob: {historical_prob:.1%}")
            else:
                # TREND-ONLY BET
                if not has_model:
                    try:
                        original_conf = safe_float(bet.get('original_confidence') or bet.get('confidence'), 0)
                        current_conf = safe_float(bet.get('confidence'), 0)
                        print(f"   WARNING: TREND-ONLY (No Model Projections)")
                        if abs(original_conf - current_conf) > 0.1:
                            print(f"   Confidence Penalty: {original_conf:.0f} -> {current_conf:.0f} (-20 for trend-only)")
                    except Exception:
                        pass
            
            # Print standard metrics
            try:
                odds = safe_float(bet.get('odds'), 0)
                confidence = safe_float(bet.get('confidence'), 0)
                ev = safe_float(bet.get('ev_per_100'), 0)
                edge = safe_float(bet.get('edge'), 0)
                sample = safe_int(bet.get('sample_size'), 0)
                game = str(bet.get('game', 'Unknown') or 'Unknown')
                
                print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100")
                print(f"   EV: ${ev:+.2f}/100 | Edge: {edge:+.1f}% | Sample: n={sample}")
                print(f"   Game: {game}")
                
                # Show weighted confidence components if available
                trend_score = bet.get('trend_score')
                if trend_score is not None:
                    try:
                        print(f"   Trend Score: {safe_float(trend_score, 0):.2f}")
                    except Exception:
                        pass
                if bet.get('has_matchup_alignment'):
                    print(f"   ✓ Matchup Alignment: Defense/Pace factors aligned")
                correlation_penalty = bet.get('correlation_penalty')
                if correlation_penalty is not None:
                    try:
                        print(f"   Correlation Penalty: {safe_float(correlation_penalty, 0):.0f}")
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Error displaying standard metrics: {e}")
                print(f"   [ERROR] Could not display all metrics")
        
        elif bet_type == 'player_prop':
            try:
                player = str(bet.get('player', 'Unknown') or 'Unknown')
                stat = str(bet.get('stat', 'points') or 'points')
                prediction = str(bet.get('prediction', 'OVER') or 'OVER')
                line = safe_float(bet.get('line'), 0)
                print(f"{player} - {stat.title()} {prediction} {line}")
            except Exception as e:
                logger.debug(f"Error displaying player prop header: {e}")
                print("Unknown Player Prop")
            
            # Show projection model details
            proj_details = bet.get('projection_details')
            if not proj_details or not isinstance(proj_details, dict):
                print(f"   WARNING: Missing projection details")
                # Still show basic info even without projections
                try:
                    odds = safe_float(bet.get('odds'), 0)
                    confidence = safe_float(bet.get('confidence'), 0)
                    ev = safe_float(bet.get('ev_per_100'), 0)
                    edge = safe_float(bet.get('edge'), 0)
                    sample = safe_int(bet.get('sample_size'), 0)
                    game = str(bet.get('game', 'Unknown') or 'Unknown')
                    
                    print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100")
                    print(f"   EV: ${ev:+.2f}/100 | Edge: {edge:+.1f}% | Sample: n={sample}")
                    print(f"   Game: {game}")
                except Exception:
                    print(f"   [ERROR] Could not display basic info")
                print()
                return
            
            try:
                proj = proj_details
                projected_ev = safe_float(bet.get('expected_value') or bet.get('projected_expected_value'), 0)
                projected_prob = safe_float(bet.get('projected_prob'), 0)
                final_prob = safe_float(bet.get('final_prob') or bet.get('historical_probability'), 0)
                original_hist_prob = safe_float(
                    bet.get('historical_prob') or bet.get('original_historical_probability') or final_prob,
                    final_prob
                )
                
                print(f"   Projected: {projected_ev:.1f} | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                
                minutes_proj = safe_get(proj, 'minutes_projected')
                if minutes_proj is not None:
                    try:
                        pace_mult = safe_float(safe_get(proj, 'pace_multiplier'), 1.0)
                        def_adj = safe_float(safe_get(proj, 'defense_adjustment'), 1.0)
                        minutes = safe_float(minutes_proj, 0)
                        print(f"   Minutes: {minutes:.1f} | Pace: {pace_mult:.3f}x | Defense: {def_adj:.3f}x")
                    except Exception as e:
                        logger.debug(f"Error displaying projection details: {e}")
                
                if safe_get(proj, 'role_change_detected'):
                    print(f"   WARNING: Role change detected")
                
                odds = safe_float(bet.get('odds'), 0)
                confidence = safe_float(bet.get('confidence'), 0)
                ev = safe_float(bet.get('ev_per_100'), 0)
                edge = safe_float(bet.get('edge'), 0)
                sample = safe_int(bet.get('sample_size'), 0)
                game = str(bet.get('game', 'Unknown') or 'Unknown')
                
                print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100")
                
                original_conf = bet.get('original_confidence')
                if original_conf is not None:
                    try:
                        orig_conf_val = safe_float(original_conf, 0)
                        if abs(orig_conf_val - confidence) > 0.1:
                            print(f"   Original Confidence: {orig_conf_val:.0f} (weighted: {confidence:.0f})")
                    except Exception:
                        pass
                
                print(f"   EV: ${ev:+.2f}/100 | Edge: {edge:+.1f}% | Sample: n={sample}")
                print(f"   Game: {game}")
                
                # Show weighted confidence components if available
                if bet.get('has_matchup_alignment'):
                    print(f"   ✓ Matchup Alignment: Defense/Pace factors aligned")
                correlation_penalty = bet.get('correlation_penalty')
                if correlation_penalty is not None:
                    try:
                        print(f"   Correlation Penalty: {safe_float(correlation_penalty, 0):.0f}")
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Error displaying player prop details: {e}")
                print(f"   [ERROR] Could not display all details")
        
        print()
    except Exception as e:
        print(f"   [ERROR] Error displaying bet {index}: {e}")
        import traceback
        print(f"   Details: {traceback.format_exc()}")
        print()


def print_full_results(data: Dict):
    """Print full results in formatted manner"""
    print_results_summary(data)
    
    bets = data.get('bets', [])
    if not bets:
        print("  NO BETS FOUND")
        print("\nNo bets met the minimum criteria.")
        return
    
    print("="*70)
    print(f"  TOP {len(bets)} HIGH-CONFIDENCE BETS")
    print("="*70)
    
    # Calculate confidence range
    confidences = [bet.get('confidence', 0) for bet in bets if bet and isinstance(bet, dict)]
    if confidences:
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        print(f"\nConfidence Range: {min_confidence:.0f}-{max_confidence:.0f}/100")
    
    team_count = sum(1 for b in bets if b and isinstance(b, dict) and b.get('type') == 'team_bet')
    prop_count = sum(1 for b in bets if b and isinstance(b, dict) and b.get('type') == 'player_prop')
    print(f"Total: {len(bets)} bets ({team_count} team, {prop_count} player)\n")
    
    for i, bet in enumerate(bets, 1):
        print_bet_details(bet, i)
    
    print("="*70)
    
    # Show games analyzed
    games = data.get('games', [])
    if games:
        print(f"\nGames Analyzed ({len(games)}):")
        for game in games:
            away = game.get('away_team', 'Unknown')
            home = game.get('home_team', 'Unknown')
            markets = game.get('total_markets', 0)
            insights = game.get('total_insights', 0)
            props = game.get('total_props', 0)
            print(f"  - {away} @ {home} (Markets: {markets}, Insights: {insights}, Props: {props})")
        print()


def list_all_results():
    """List all available result files"""
    files = find_result_files()
    
    if not files:
        print("\n[INFO] No analysis results found")
        print("Run the unified analysis pipeline first:")
        print("  python launcher.py -> Option 1")
        return
    
    print("\n" + "="*70)
    print("  AVAILABLE ANALYSIS RESULTS")
    print("="*70 + "\n")
    
    for i, file in enumerate(files, 1):
        try:
            data = load_results(file)
            if data:
                date_str = data.get('analysis_date', 'Unknown')
                total_bets = data.get('total_bets', 0)
                games = data.get('games_analyzed', 0)
                size_kb = file.stat().st_size / 1024
                print(f"  {i:2d}. {file.name}")
                print(f"      Date: {date_str} | Games: {games} | Bets: {total_bets} | Size: {size_kb:.1f} KB")
        except Exception as e:
            print(f"  {i:2d}. {file.name} (Error: {e})")
    
    print("\n" + "="*70)
    print("\nTo view a specific result, run:")
    print("  python view_analysis_results.py --file <filename>")


def main():
    """Main entry point"""
    import argparse
    import traceback
    
    try:
        parser = argparse.ArgumentParser(description="View saved analysis results")
        parser.add_argument('--latest', action='store_true', help='Show most recent results (default)')
        parser.add_argument('--all', action='store_true', help='List all available results')
        parser.add_argument('--file', type=str, help='View specific result file (filename or number)')
        
        args = parser.parse_args()
        
        files = find_result_files()
        
        if not files:
            print("\n[INFO] No analysis results found")
            print("Run the unified analysis pipeline first:")
            print("  python launcher.py -> Option 1")
            print("  OR")
            print("  python scrapers/unified_analysis_pipeline.py")
            return
        
        if args.all:
            list_all_results()
            return
        
        # Determine which file to show
        target_file = None
        
        if args.file:
            # Try to parse as number
            try:
                file_num = int(args.file)
                if 1 <= file_num <= len(files):
                    target_file = files[file_num - 1]
                else:
                    print(f"[ERROR] Invalid file number. Available: 1-{len(files)}")
                    return
            except ValueError:
                # Try to find by filename
                for f in files:
                    if args.file in f.name:
                        target_file = f
                        break
                if not target_file:
                    print(f"[ERROR] File not found: {args.file}")
                    print(f"\nAvailable files:")
                    for i, f in enumerate(files[:10], 1):
                        print(f"  {i}. {f.name}")
                    return
        else:
            # Default: show most recent
            target_file = files[0]
        
        # Load and display results
        data = load_results(target_file)
        if data:
            print(f"\n[VIEWING] {target_file.name}")
            print_full_results(data)
        else:
            print(f"[ERROR] Failed to load results from {target_file}")
    
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Script crashed: {e}")
        print("\nFull error details:")
        traceback.print_exc()
        print("\nIf this persists, please report the error above.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

