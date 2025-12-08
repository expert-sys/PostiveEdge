"""
View Analysis Results - Ultra-Robust Version
============================================
This version handles all edge cases and works when double-clicked or run from command line.
"""
import json
import sys
import os
from pathlib import Path

def safe_get(data, *keys, default=None):
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
    except:
        return default

def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default

def safe_int(value, default=0):
    """Safely convert to int"""
    try:
        if value is None:
            return default
        return int(value)
    except:
        return default

def safe_str(value, default='Unknown'):
    """Safely convert to string"""
    try:
        if value is None:
            return default
        return str(value)
    except:
        return default

def find_results():
    """Find result files"""
    try:
        output_dir = Path("data") / "outputs"
        if not output_dir.exists():
            return []
        files = sorted(output_dir.glob("unified_analysis_*.json"), reverse=True)
        return files
    except:
        return []

def load_file(file_path):
    """Load JSON file safely"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path.name}: {e}")
        return None

def print_bet(bet, index):
    """Print a single bet safely with all projection details"""
    if not isinstance(bet, dict):
        return
    
    try:
        bet_type = safe_str(bet.get('type'), 'unknown')
        
        if bet_type == 'player_prop':
            player = safe_str(bet.get('player'), 'Unknown')
            stat = safe_str(bet.get('stat'), 'points')
            line = safe_float(bet.get('line'), 0)
            prediction = safe_str(bet.get('prediction'), 'OVER')
            print(f"{index}. {player} - {stat.title()} {prediction} {line}")
            
            # Get projection details
            proj_details = bet.get('projection_details', {})
            if isinstance(proj_details, dict) and proj_details:
                # Projected value
                projected_ev = safe_float(bet.get('expected_value') or bet.get('projected_expected_value'), 0)
                projected_prob = safe_float(bet.get('projected_prob'), 0)
                final_prob = safe_float(bet.get('final_prob') or bet.get('historical_probability'), 0)
                original_hist_prob = safe_float(bet.get('historical_prob') or bet.get('original_historical_probability') or final_prob, final_prob)
                
                print(f"   Projected: {projected_ev:.1f} | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                
                # Minutes and adjustments
                minutes_proj = safe_get(proj_details, 'minutes_projected')
                if minutes_proj is not None:
                    minutes = safe_float(minutes_proj, 0)
                    pace_mult = safe_float(safe_get(proj_details, 'pace_multiplier'), 1.0)
                    def_adj = safe_float(safe_get(proj_details, 'defense_adjustment'), 1.0)
                    print(f"   Minutes: {minutes:.1f} | Pace: {pace_mult:.3f}x | Defense: {def_adj:.3f}x")
                
                # Role change warning
                if safe_get(proj_details, 'role_change_detected'):
                    print(f"   ⚠ WARNING: Role change detected")
            else:
                print(f"   ⚠ WARNING: Missing projection details")
            
        else:
            # Team bet
            market = safe_str(bet.get('market'), 'Unknown')
            result = safe_str(bet.get('result'), '')
            print(f"{index}. {result} - {market}")
            
            # Show fact/insight if available
            fact = safe_str(bet.get('fact'), '')
            if fact and fact != 'N/A':
                print(f"   {fact[:80]}{'...' if len(fact) > 80 else ''}")
            
            # Get projection details from analysis
            analysis = bet.get('analysis', {})
            if not isinstance(analysis, dict):
                analysis = {}
            
            proj_details = safe_get(analysis, 'projection_details')
            projected_ev = safe_get(analysis, 'projected_expected_value')
            projected_prob = safe_get(analysis, 'projected_prob')
            historical_prob = safe_float(safe_get(analysis, 'historical_probability'), 0)
            original_hist_prob = safe_float(safe_get(analysis, 'original_historical_probability'), historical_prob)
            
            # Check if this bet has model projections
            has_model = bet.get('has_model_projection', False)
            
            # Display projections based on what's available
            if proj_details and isinstance(proj_details, dict):
                # Team bet with projection details
                projected_total = safe_get(proj_details, 'projected_total')
                projected_spread = safe_get(proj_details, 'projected_spread')
                
                if projected_total is not None:
                    print(f"   Projected Total: {safe_float(projected_total, 0):.1f} | Prob: {historical_prob:.1%}", end="")
                    if projected_prob is not None:
                        print(f" (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})")
                    else:
                        print()
                    # Show pace factor if available
                    pace_factor = safe_float(safe_get(proj_details, 'pace_factor'), 1.0)
                    if abs(pace_factor - 1.0) > 0.001:
                        print(f"   Pace Factor: {pace_factor:.3f}x")
                elif projected_spread is not None:
                    print(f"   Projected Spread: {safe_float(projected_spread, 0):.1f} | Prob: {historical_prob:.1%}", end="")
                    if projected_prob is not None:
                        print(f" (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})")
                    else:
                        print()
                elif projected_prob is not None:
                    # Have projected probability but no total/spread
                    print(f"   Projected Prob: {safe_float(projected_prob, 0):.1%} | Final Prob: {historical_prob:.1%} (Hist: {original_hist_prob:.1%})")
                else:
                    # Have projection_details but no specific projections - show what we have
                    pace_factor = safe_float(safe_get(proj_details, 'pace_factor'), 1.0)
                    form_diff = safe_float(safe_get(proj_details, 'form_differential'), 0)
                    away_form = safe_float(safe_get(proj_details, 'away_form_score'), 0)
                    home_form = safe_float(safe_get(proj_details, 'home_form_score'), 0)
                    
                    # Show probability with available projection data
                    print(f"   Prob: {historical_prob:.1%}", end="")
                    if projected_prob is not None:
                        print(f" (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})", end="")
                    elif abs(original_hist_prob - historical_prob) > 0.001:
                        print(f" (Hist: {original_hist_prob:.1%})", end="")
                    
                    # Show available projection factors
                    has_factors = False
                    if abs(pace_factor - 1.0) > 0.001:
                        print(f" | Pace: {pace_factor:.3f}x", end="")
                        has_factors = True
                    if form_diff != 0 or (away_form != 0 and home_form != 0):
                        print(f" | Form: {form_diff:+.1f}", end="")
                        has_factors = True
                    
                    if not has_factors and not projected_prob:
                        print(" (Trend-only: No model projections)")
                    elif not projected_prob:
                        print(" (Model factors available, no probability calculated)")
                    print()
            elif projected_prob is not None:
                # Have projected probability from model
                print(f"   Projected Prob: {safe_float(projected_prob, 0):.1%} | Final Prob: {historical_prob:.1%} (Hist: {original_hist_prob:.1%})")
            elif projected_ev is not None:
                # Have projected EV
                if projected_prob is not None:
                    print(f"   Projected EV: ${safe_float(projected_ev, 0):.2f}/100 | Prob: {historical_prob:.1%} (Proj: {safe_float(projected_prob, 0):.1%}, Hist: {original_hist_prob:.1%})")
                else:
                    print(f"   Projected EV: ${safe_float(projected_ev, 0):.2f}/100 | Prob: {historical_prob:.1%}")
            elif has_model:
                # Has model but no specific projections shown
                print(f"   Prob: {historical_prob:.1%} (Model projections available)")
            else:
                # Trend-only bet
                print(f"   Prob: {historical_prob:.1%}")
                print(f"   ⚠ WARNING: TREND-ONLY (No Model Projections)")
                original_conf = safe_float(bet.get('original_confidence') or bet.get('confidence'), 0)
                current_conf = safe_float(bet.get('confidence'), 0)
                if abs(original_conf - current_conf) > 0.1:
                    print(f"   Confidence Penalty: {original_conf:.0f} -> {current_conf:.0f} (-20 for trend-only)")
        
        # Basic metrics (always show)
        odds = safe_float(bet.get('odds'), 0)
        conf = safe_float(bet.get('confidence'), 0)
        ev = safe_float(bet.get('ev_per_100'), 0)
        edge = safe_float(bet.get('edge'), 0)
        sample = safe_int(bet.get('sample_size'), 0)
        
        print(f"   Odds: {odds:.2f} | Confidence: {conf:.0f}/100")
        print(f"   EV: ${ev:+.2f}/100 | Edge: {edge:+.1f}% | Sample: n={sample}")
        
        # Show weighted confidence components if available
        trend_score = bet.get('trend_score')
        if trend_score is not None:
            print(f"   Trend Score: {safe_float(trend_score, 0):.2f}")
        if bet.get('has_matchup_alignment'):
            print(f"   ✓ Matchup Alignment: Defense/Pace factors aligned")
        correlation_penalty = bet.get('correlation_penalty')
        if correlation_penalty is not None:
            print(f"   Correlation Penalty: {safe_float(correlation_penalty, 0):.0f}")
        
        # Game info
        game = safe_str(bet.get('game'), 'Unknown')
        print(f"   Game: {game}")
        print()
    except Exception as e:
        print(f"{index}. [ERROR displaying bet: {e}]")
        import traceback
        traceback.print_exc()
        print()

def main():
    """Main function"""
    try:
        print("\n" + "="*70)
        print("  ANALYSIS RESULTS VIEWER")
        print("="*70 + "\n")
        
        # Find files
        files = find_results()
        if not files:
            print("No analysis results found.")
            print("Run the analysis first: python launcher.py -> Option 1")
            input("\nPress Enter to exit...")
            return
        
        # Load most recent
        data = load_file(files[0])
        if not data:
            print("Failed to load results file.")
            input("\nPress Enter to exit...")
            return
        
        # Summary
        print(f"File: {files[0].name}")
        print(f"Date: {safe_str(data.get('analysis_date'), 'N/A')}")
        print(f"Games Analyzed: {safe_int(data.get('games_analyzed'), 0)}")
        print(f"Total Bets: {safe_int(data.get('total_bets'), 0)}")
        print(f"  - Team Bets: {safe_int(data.get('team_bets'), 0)}")
        print(f"  - Player Props: {safe_int(data.get('player_props'), 0)}")
        print()
        
        # Show bets
        bets = data.get('bets', [])
        if not bets:
            print("No bets found in results.")
        else:
            print("="*70)
            print(f"  TOP {len(bets)} BETS")
            print("="*70 + "\n")
            
            for i, bet in enumerate(bets, 1):
                print_bet(bet, i)
        
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Keep window open if double-clicked
    if len(sys.argv) == 1:  # No command line args = likely double-clicked
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()

