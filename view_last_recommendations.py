"""
View Last Analysis Recommendations (Enhanced)
============================================
Loads and displays the most recent unified analysis results using the enhanced betting system
with tier classifications, EV/Prob ratios, and advanced filtering.
"""

import json
import sys
import io
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Fix Windows encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bet_enhancement_system import BetEnhancementSystem, QualityTier


def find_latest_analysis_file(output_dir: Path) -> Optional[Path]:
    """
    Find the most recent unified_analysis JSON file.
    
    Args:
        output_dir: Directory containing analysis files
    
    Returns:
        Path to the most recent file, or None if none found
    """
    if not output_dir.exists():
        return None
    
    # Find all unified_analysis files
    analysis_files = list(output_dir.glob("unified_analysis_*.json"))
    
    if not analysis_files:
        return None
    
    # Sort by modification time (most recent first)
    analysis_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return analysis_files[0]


def load_analysis_results(file_path: Path) -> Optional[dict]:
    """
    Load analysis results from JSON file.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        Dictionary with analysis results, or None if loading fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None


def convert_bets_to_enhancement_format(bets: List[dict], games: List[dict] = None) -> List[dict]:
    """
    Convert bet dictionaries to the format expected by the enhancement system.
    
    Args:
        bets: List of bet dictionaries from unified_analysis
        games: Optional list of game dictionaries for context
    
    Returns:
        List of recommendation dictionaries in enhancement system format
    """
    recommendations = []
    
    # Create a game lookup by game string
    game_lookup = {}
    if games:
        for game in games:
            game_str = f"{game.get('away_team', 'Unknown')} @ {game.get('home_team', 'Unknown')}"
            game_lookup[game_str] = {
                'away_team': game.get('away_team', 'Unknown'),
                'home_team': game.get('home_team', 'Unknown'),
                'match_time': 'TBD'
            }
    
    for bet in bets:
        if not bet or not isinstance(bet, dict):
            continue
        
        # Extract game info
        game_str = bet.get('game', '')
        if game_str in game_lookup:
            game_info = game_lookup[game_str]
        elif game_str and ' @ ' in game_str:
            parts = game_str.split(' @ ')
            if len(parts) == 2:
                game_info = {
                    'away_team': parts[0].strip(),
                    'home_team': parts[1].strip(),
                    'match_time': bet.get('match_time', 'TBD')
                }
            else:
                game_info = None
        else:
            game_info = None
        
        bet_type = bet.get('type', 'unknown')
        
        # Build recommendation dict for enhancement system
        rec_dict = {
            'game': game_str,
            'match_time': bet.get('match_time', 'TBD'),
            'bet_type': bet_type,
            'odds': float(bet.get('odds', 0)),
            'confidence_score': float(bet.get('confidence', bet.get('confidence_score', 0))),
            'edge_percentage': float(bet.get('edge', bet.get('edge_percentage', 0))),
            'expected_value': float(bet.get('ev_per_100', bet.get('expected_value', 0))),
        }
        
        if bet_type == 'player_prop':
            # Player prop fields
            rec_dict.update({
                'player_name': bet.get('player', bet.get('player_name', 'Unknown')),
                'market': bet.get('stat', bet.get('stat_type', 'points')).replace('_', ' ').title(),
                'selection': f"{bet.get('prediction', 'OVER')} {bet.get('line', 0)}",
                'line': float(bet.get('line', 0)) if bet.get('line') else None,
                'player_team': bet.get('player_team'),
                'opponent_team': bet.get('opponent_team'),
                'stat_type': bet.get('stat', bet.get('stat_type', 'points')),
                'historical_hit_rate': bet.get('historical_prob', bet.get('historical_hit_rate', bet.get('historical_probability', 0))),
                'sample_size': bet.get('sample_size', 0),
                'projected_probability': bet.get('projected_prob', bet.get('projected_probability', bet.get('final_prob', 0))),
            })
            
            # Add projection details if available
            if 'projection_details' in bet:
                proj = bet['projection_details']
                if 'projected_value' in proj or 'projected_points' in proj or 'projected_total' in proj:
                    rec_dict['projected_value'] = proj.get('projected_value') or proj.get('projected_points') or proj.get('projected_total')
        else:
            # Team bet fields
            rec_dict.update({
                'market': bet.get('market', 'Unknown Market'),
                'selection': bet.get('result', bet.get('selection', 'Unknown')),
                'historical_hit_rate': bet.get('historical_probability', 0),
                'sample_size': bet.get('sample_size', 0),
                'projected_probability': bet.get('projected_prob', bet.get('projected_probability', bet.get('historical_probability', 0))),
            })
            
            # Add projection details from analysis if available
            analysis = bet.get('analysis', {})
            if analysis and 'projection_details' in analysis:
                proj = analysis['projection_details']
                if 'projected_total' in proj:
                    rec_dict['projected_value'] = proj['projected_total']
        
        # Ensure probabilities are in 0-1 range
        if rec_dict.get('projected_probability', 0) > 1:
            rec_dict['projected_probability'] = rec_dict['projected_probability'] / 100.0
        if rec_dict.get('historical_hit_rate', 0) > 1:
            rec_dict['historical_hit_rate'] = rec_dict['historical_hit_rate'] / 100.0
        
        # Calculate implied probability
        if rec_dict['odds'] > 0:
            rec_dict['implied_probability'] = 1.0 / rec_dict['odds']
        else:
            rec_dict['implied_probability'] = 0.0
        
        recommendations.append(rec_dict)
    
    return recommendations


def main():
    """Main function to load and display last analysis with enhancements"""
    
    try:
        # Find output directory
        output_dir = Path(__file__).parent / "data" / "outputs"
        
        print("=" * 76)
        print("ENHANCED BETTING RECOMMENDATIONS VIEWER")
        print("=" * 76)
        print()
        print("Checking requirements...")
        print()
        
        # Check for Python
        print("[OK] Python found")
        
        # Find latest file
        latest_file = find_latest_analysis_file(output_dir)
        
        if not latest_file:
            print("[FAIL] No analysis files found")
            print()
            print("No analysis files found in data/outputs/")
            print("Run the unified analysis pipeline first to generate results.")
            print()
            input("Press Enter to exit...")
            return
        
        print(f"[OK] Recommendations file found: {latest_file.name}")
        
        # Check for enhancement system
        try:
            from bet_enhancement_system import BetEnhancementSystem
            print("[OK] Enhancement system found")
        except ImportError:
            print("[FAIL] Enhancement system not found")
            print("Make sure bet_enhancement_system.py is in the project root.")
            print()
            input("Press Enter to exit...")
            return
        
        print("[OK] Viewer script found")
        print()
        print("All requirements met")
        print()
        print("Loading enhanced bets...")
        print()
        
        # Load results
        results = load_analysis_results(latest_file)
        
        if not results:
            print("❌ Failed to load analysis results.")
            print()
            input("Press Enter to exit...")
            return
        
        # Extract bets and games
        bets = results.get('bets', [])
        games = results.get('games', [])
        
        if not bets:
            print("No bets found in this analysis.")
            print(f"Analysis date: {results.get('analysis_date', 'Unknown')}")
            print(f"Games analyzed: {results.get('games_analyzed', 0)}")
            print()
            input("Press Enter to exit...")
            return
        
        print("=" * 76)
        print()
        print("=" * 100)
        print("ENHANCED BET VIEWER - ALL TIERS")
        print("=" * 100)
        print()
        print(f"Input: {latest_file.name}")
        print(f"Show D-Tier: No")
        print(f"Filters: Disabled")
        print()
        
        # Convert to enhancement format
        recommendations = convert_bets_to_enhancement_format(bets, games)
        
        if not recommendations:
            print("No valid recommendations could be converted from the bets.")
            print()
            input("Press Enter to exit...")
            return
        
        print(f"✓ Loaded {len(recommendations)} recommendations")
        print()
        
        # Enhance
        enhancer = BetEnhancementSystem()
        enhanced_bets = enhancer.enhance_recommendations(recommendations)
        
        print(f"✓ Enhanced {len(enhanced_bets)} bets")
        print()
        
        # Show tier distribution
        print("=" * 100)
        print("TIER DISTRIBUTION")
        print("=" * 100)
        print()
        
        tier_counts = {}
        for bet in enhanced_bets:
            tier = bet.quality_tier.name
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        for tier in ['S', 'A', 'B', 'C', 'D']:
            count = tier_counts.get(tier, 0)
            emoji = {'S': '💎', 'A': '⭐', 'B': '✓', 'C': '~', 'D': '❌'}[tier]
            desc = {
                'S': 'Elite Value',
                'A': 'High Quality',
                'B': 'Playable',
                'C': 'Marginal',
                'D': 'Avoid'
            }[tier]
            print(f"  {emoji} {tier}-Tier ({desc}): {count} bets")
        
        print()
        
        # Filter (exclude D-Tier, no other filters)
        display_bets = [b for b in enhanced_bets if b.quality_tier != QualityTier.D]
        print("Showing: ALL EXCEPT D-TIER (no filters)")
        print(f"Displaying: {len(display_bets)} bets")
        print()
        
        # Show filter statistics
        print("=" * 100)
        print("FILTER STATISTICS")
        print("=" * 100)
        print()
        
        failed_efficiency = sum(1 for b in enhanced_bets if not b.passes_efficiency_check)
        failed_ev_ratio = sum(1 for b in enhanced_bets if not b.passes_ev_ratio)
        d_tier = tier_counts.get('D', 0)
        
        print(f"Bets failing efficiency check: {failed_efficiency}")
        print(f"Bets failing EV/Prob ratio: {failed_ev_ratio}")
        print(f"D-Tier bets (auto-filtered): {d_tier}")
        print(f"Total filtered out: {len(enhanced_bets) - len(display_bets)}")
        print()
        
        # Display details about filtered bets
        if failed_ev_ratio > 0:
            print("\nEV/Prob Ratio Failures (< 0.08):")
            for bet in enhanced_bets:
                if not bet.passes_ev_ratio and bet.passes_efficiency_check:
                    player_name = bet.player_name or 'TEAM'
                    print(f"  • {player_name} - {bet.market}: "
                          f"Ratio {bet.ev_to_prob_ratio:.3f} (EV {bet.expected_value:.1f}%, Prob {bet.projected_probability:.1%})")
        
        # Display enhanced bets
        print()
        print("=" * 100)
        print("ENHANCED BETTING RECOMMENDATIONS")
        print("=" * 100)
        print()
        enhancer.display_enhanced_bets(display_bets, max_display=len(display_bets))
        
        # Summary
        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print()
        
        if tier_counts.get('S', 0) > 0:
            print(f"💎 {tier_counts['S']} ELITE VALUE bet(s) - Maximum unit size recommended")
        if tier_counts.get('A', 0) > 0:
            print(f"⭐ {tier_counts['A']} HIGH QUALITY bet(s) - Standard unit size")
        if tier_counts.get('B', 0) > 0:
            print(f"✓ {tier_counts['B']} PLAYABLE bet(s) - Reduced unit size")
        if tier_counts.get('C', 0) > 0:
            print(f"~ {tier_counts['C']} MARGINAL bet(s) - Minimal units or parlay only")
        if tier_counts.get('D', 0) > 0:
            print(f"❌ {tier_counts['D']} AVOID - No value")
        
        print()
        print("Recommendations:")
        if len(display_bets) == 0:
            print("  ⚠️ No quality bets found")
        else:
            print(f"  ✓ Focus on top {min(5, len(display_bets))} bets")
            if failed_ev_ratio > 0:
                print(f"  ⚠️ {failed_ev_ratio} bet(s) have low EV/Prob ratio (payoff doesn't justify risk)")
        
        # Save enhanced output
        print()
        print("=" * 100)
        print("SAVING OUTPUT")
        print("=" * 100)
        print()
        
        output_file = 'betting_recommendations_enhanced.json'
        enhanced_output = []
        for bet in display_bets:
            bet_dict = bet.original_rec.copy()
            bet_dict['enhanced_metrics'] = {
                'quality_tier': bet.quality_tier.name,
                'tier_emoji': bet.tier_emoji,
                'effective_confidence': bet.effective_confidence,
                'adjusted_confidence': bet.adjusted_confidence,
                'sample_size_penalty': bet.sample_size_penalty,
                'correlation_penalty': bet.correlation_penalty,
                'line_difficulty_penalty': bet.line_difficulty_penalty,
                'consistency_rank': bet.consistency_rank.value if bet.consistency_rank else None,
                'consistency_score': bet.consistency_score,
                'ev_to_prob_ratio': bet.ev_to_prob_ratio,
                'fair_odds': bet.fair_odds,
                'odds_mispricing': bet.odds_mispricing,
                'projection_margin': bet.projection_margin,
                'final_score': bet.final_score,
                'notes': bet.notes,
                'warnings': bet.warnings
            }
            enhanced_output.append(bet_dict)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_output, f, indent=2, default=str)
            print(f"✓ Saved {len(enhanced_output)} enhanced bets to {output_file}")
        except Exception as e:
            print(f"⚠️ Could not save output file: {e}")
        
        print()
        print("=" * 76)
        print("SUCCESS")
        print("=" * 76)
        print()
        print("Your enhanced recommendations are displayed above")
        print(f"Output saved to: {output_file}")
        print()
        print()
        print("=" * 76)
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Keep window open on Windows
    print("This window will stay open so you can read the results.")
    print("Press any key to close this window...")
    try:
        input()
    except:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()
        input("Press Enter to exit...")

