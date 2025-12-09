"""
Display Betting Recommendations
================================
Formatted display of BettingRecommendation objects with all analysis details.
"""

import logging
from typing import List
from models import BettingRecommendation

logger = logging.getLogger(__name__)


def display_recommendations(recommendations: List[BettingRecommendation], max_display: int = None, use_print: bool = False):
    """
    Display betting recommendations in a formatted, easy-to-read format.
    
    Args:
        recommendations: List of BettingRecommendation objects
        max_display: Maximum number of recommendations to display (None = all)
        use_print: If True, use print() instead of logger (for compatibility)
    """
    output = logger.info if not use_print else print
    
    if not recommendations:
        output("\n" + "=" * 80)
        output("  NO HIGH-CONFIDENCE BETS FOUND")
        output("=" * 80)
        output("\nNo bets met the minimum confidence threshold.")
        output("Consider analyzing more games or waiting for better opportunities.")
        return
    
    # Limit display if specified
    display_list = recommendations[:max_display] if max_display else recommendations
    
    output("\n" + "=" * 80)
    output(f"  FINAL RECOMMENDATIONS ({len(display_list)} of {len(recommendations)} total)")
    output("=" * 80)
    
    # Count by type
    team_count = sum(1 for r in display_list if r.bet_type.startswith('team_'))
    prop_count = sum(1 for r in display_list if r.bet_type == 'player_prop')
    
    output(f"\nTotal: {len(display_list)} bets ({team_count} team, {prop_count} player)")
    
    # Show confidence range
    if display_list:
        confidences = [r.confidence_score for r in display_list]
        min_conf = min(confidences)
        max_conf = max(confidences)
        output(f"Confidence Range: {min_conf:.0f}-{max_conf:.0f}/100")
    
    output("")
    
    # Display each recommendation
    for i, rec in enumerate(display_list, 1):
        try:
            _display_single_recommendation(rec, i, use_print)
        except Exception as e:
            if use_print:
                print(f"  Error displaying recommendation {i}: {e}")
            else:
                logger.warning(f"  Error displaying recommendation {i}: {e}")
            continue
    
    output("=" * 80)


def _display_single_recommendation(rec: BettingRecommendation, index: int, use_print: bool = False):
    """Display a single betting recommendation with all details"""
    output = logger.info if not use_print else print
    
    # Check if this is a team market or player prop
    is_team_market = rec.bet_type.startswith('team_')
    
    if is_team_market:
        output(f"\n{index}. TEAM MARKET: {rec.market} - {rec.selection}")
        output(f"   Game: {rec.game} ({rec.match_time})")
        output(f"   Odds: {rec.odds:.2f} | Confidence: {rec.confidence_score:.0f}% | Strength: {rec.recommendation_strength}")
        output(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")
        output(f"   Projected Probability: {rec.projected_probability:.1%}")
        
        # Show projection details
        if rec.advanced_context and 'projection' in rec.advanced_context:
            proj = rec.advanced_context['projection']
            away_score = proj.get('away_score', 'N/A')
            home_score = proj.get('home_score', 'N/A')
            total = proj.get('total', 'N/A')
            margin = proj.get('margin', 'N/A')
            
            output(f"   Projected Score: {away_score} - {home_score}")
            if isinstance(margin, (int, float)):
                output(f"   Projected Total: {total} | Margin: {margin:+.1f}")
            else:
                output(f"   Projected Total: {total} | Margin: {margin}")
        
        # Show reasoning
        if rec.sportsbet_insight:
            output(f"   Reasoning:")
            for line in rec.sportsbet_insight.split('\n')[:3]:  # Show first 3 reasons
                if line.strip():
                    output(f"     • {line.strip()}")
    else:
        # Player prop
        output(f"\n{index}. PLAYER PROP: {rec.player_name} - {rec.market} {rec.selection}")
        if rec.player_team:
            output(f"   Player Team: {rec.player_team}")
        if rec.opponent_team:
            output(f"   Matchup: vs {rec.opponent_team}")
        output(f"   Game: {rec.game} ({rec.match_time})")
        output(f"   Odds: {rec.odds:.2f} | Confidence: {rec.confidence_score:.0f}% | Strength: {rec.recommendation_strength}")
        output(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")
        output(f"   Historical: {rec.historical_hit_rate:.1%} ({rec.sample_size} games)")
        output(f"   Projected: {rec.projected_probability:.1%}")
        
        # Show stat details
        if rec.stat_type and rec.line:
            output(f"   Stat: {rec.stat_type.replace('_', ' ').title()} Over {rec.line}")
        
        # Show DataBallr stats if available
        if rec.databallr_stats:
            db_stats = rec.databallr_stats
            if 'avg_value' in db_stats:
                output(f"   Season Avg: {db_stats['avg_value']:.1f}")
            if 'recent_avg' in db_stats:
                output(f"   Recent Avg: {db_stats['recent_avg']:.1f} (last 5)")
            if 'trend' in db_stats:
                output(f"   Trend: {db_stats['trend'].upper()}")
    
    # Show advanced context if available
    if rec.advanced_context:
        ctx = rec.advanced_context
        
        # Minutes analysis
        if 'minutes_analysis' in ctx:
            mins = ctx['minutes_analysis']
            stability = "STABLE" if mins.get('stable') else "VARIABLE"
            output(f"   Minutes: {mins.get('recent_avg', 'N/A')}min avg (last 5), {stability} rotation")
        
        # Stat-specific context
        if 'assist_context' in ctx:
            ast = ctx['assist_context']
            output(f"   Assist Rate: {ast.get('per_36_rate', 'N/A')}/36min | Consistency: {ast.get('consistency', 0):.0f}%")
        
        if 'scoring_context' in ctx:
            pts = ctx['scoring_context']
            output(f"   Scoring: {pts.get('recent_form', 'N/A')} ppg (last 5) | Consistency: {pts.get('consistency', 0):.0f}%")
        
        if 'rebounding_context' in ctx:
            reb = ctx['rebounding_context']
            output(f"   Rebounding: {reb.get('recent_form', 'N/A')} rpg (last 5)")
    
    # Show matchup factors if available
    if rec.matchup_factors:
        mf = rec.matchup_factors
        if mf.get('total_multiplier'):
            output(f"   Matchup: {mf['total_multiplier']:.2f}x multiplier", end="")
            if mf.get('favorable_matchup'):
                output(" (FAVORABLE)", end="")
            output("")
            
            if mf.get('pace_multiplier') and abs(mf['pace_multiplier'] - 1.0) > 0.03:
                pace_desc = "Fast" if mf['pace_multiplier'] > 1.0 else "Slow"
                output(f"   Pace: {pace_desc} ({mf['pace_multiplier']:.2f}x)")
            
            if mf.get('defense_multiplier') and abs(mf['defense_multiplier'] - 1.0) > 0.03:
                def_desc = "Favorable" if mf['defense_multiplier'] > 1.0 else "Tough"
                output(f"   Defense: {def_desc} ({mf['defense_multiplier']:.2f}x)")


def display_recommendations_summary(recommendations: List[BettingRecommendation]):
    """
    Display a summary of recommendations (counts and statistics).
    
    Args:
        recommendations: List of BettingRecommendation objects
    """
    if not recommendations:
        return
    
    team_bets = [r for r in recommendations if r.bet_type.startswith('team_')]
    player_props = [r for r in recommendations if r.bet_type == 'player_prop']
    
    logger.info("\n" + "=" * 80)
    logger.info("  RECOMMENDATIONS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"\nTotal Recommendations: {len(recommendations)}")
    logger.info(f"  Team Markets: {len(team_bets)}")
    logger.info(f"  Player Props: {len(player_props)}")
    
    if recommendations:
        confidences = [r.confidence_score for r in recommendations]
        evs = [r.expected_value for r in recommendations]
        edges = [r.edge_percentage for r in recommendations]
        
        logger.info(f"\nAverage Metrics:")
        logger.info(f"  Confidence: {sum(confidences)/len(confidences):.1f}%")
        logger.info(f"  Expected Value: {sum(evs)/len(evs):+.1f}%")
        logger.info(f"  Edge: {sum(edges)/len(edges):+.1f}%")
        
        logger.info(f"\nBest Metrics:")
        logger.info(f"  Highest Confidence: {max(confidences):.0f}%")
        logger.info(f"  Best EV: {max(evs):+.1f}%")
        logger.info(f"  Best Edge: {max(edges):+.1f}%")
    
    logger.info("=" * 80)

