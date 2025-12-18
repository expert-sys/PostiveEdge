"""
Display Betting Recommendations
================================
Formatted display of EnhancedBet objects with all analysis details.
"""

import logging
from typing import List, Union
try:
    from models import BettingRecommendation
except ImportError:
    BettingRecommendation = None
try:
    from bet_enhancement_system import EnhancedBet
except ImportError:
    EnhancedBet = None

logger = logging.getLogger(__name__)


def display_recommendations(recommendations: List[Union[BettingRecommendation, 'EnhancedBet']], max_display: int = None, use_print: bool = False):
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
    
    # Count by type (handle both EnhancedBet and BettingRecommendation)
    def is_team_bet(r):
        if hasattr(r, 'player_name'):  # EnhancedBet
            return not r.player_name
        elif hasattr(r, 'bet_type'):  # BettingRecommendation
            return r.bet_type.startswith('team_')
        return False

    def is_player_prop(r):
        if hasattr(r, 'player_name'):  # EnhancedBet
            return bool(r.player_name)
        elif hasattr(r, 'bet_type'):  # BettingRecommendation
            return r.bet_type == 'player_prop'
        return False

    team_count = sum(1 for r in display_list if is_team_bet(r))
    prop_count = sum(1 for r in display_list if is_player_prop(r))
    
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


def _display_single_recommendation(rec: Union[BettingRecommendation, 'EnhancedBet'], index: int, use_print: bool = False):
    """Display a single betting recommendation with all details"""
    output = logger.info if not use_print else print

    # Check if this is a team market or player prop (handle both EnhancedBet and BettingRecommendation)
    if hasattr(rec, 'player_name'):  # EnhancedBet
        is_team_market = not rec.player_name
    elif hasattr(rec, 'bet_type'):  # BettingRecommendation
        is_team_market = rec.bet_type.startswith('team_')
    else:
        is_team_market = False
    
    if is_team_market:
        output(f"\nTEAM MARKET: {rec.market} - {rec.selection}")
        match_time = getattr(rec, 'match_time', 'TBD')
        output(f"   Game: {rec.game} ({match_time})")

        recommendation_strength = getattr(rec, 'recommendation_strength', 'N/A')
        # Show tier if available
        tier = getattr(rec, 'tier', None)
        promoted_from = getattr(rec, 'promoted_from', None)
        confidence = getattr(rec, 'confidence_score', 0)
        
        # Fix #1: For promoted bets, show confidence-aligned tier with validation flag
        if tier and promoted_from:
            # Determine actual tier based on confidence (use team_sides thresholds for team bets)
            from scrapers.bet_validation import MARKET_TIER_THRESHOLDS
            market_type = getattr(rec, 'market_type', 'team_sides')
            if market_type not in MARKET_TIER_THRESHOLDS:
                market_type = 'team_sides'
            thresholds = MARKET_TIER_THRESHOLDS[market_type]
            
            # Determine actual tier from confidence
            if confidence >= thresholds["A"]:
                actual_tier = "A"
            elif confidence >= thresholds["B"]:
                actual_tier = "B"
            elif confidence >= thresholds["C"]:
                actual_tier = "C"
            else:
                actual_tier = "WATCHLIST"
            
            # Show confidence-aligned tier with validation flag
            tier_display = f" | Tier: {actual_tier} (CLV-validated)"
        elif tier:
            tier_display = f" | Tier: {tier}"
        else:
            tier_display = ""
        stake_cap = getattr(rec, 'stake_cap_pct', None)
        stake_display = f" (Stake: {stake_cap*100:.0f}%)" if stake_cap else ""
        output(f"   Odds: {rec.odds:.2f} | Confidence: {rec.confidence_score:.0f}% | Strength: {recommendation_strength}{tier_display}{stake_display}")
        output(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")

        historical_hit_rate = getattr(rec, 'historical_hit_rate', 0.0)
        output(f"   Sample Size: {rec.sample_size} games | Historical: {historical_hit_rate:.1%}")
        # Fix #3: Show final blended probability (what's used for EV calculation)
        output(f"   Final Probability: {rec.projected_probability:.1%}")
        
        # Fix #3: Show raw model probability if available and significantly different
        raw_model_prob = getattr(rec, 'raw_model_probability', None)
        if raw_model_prob is not None:
            diff_from_raw = abs(rec.projected_probability - raw_model_prob) * 100
            if diff_from_raw > 5.0:  # Show if difference > 5%
                output(f"   Raw Model Probability: {raw_model_prob:.1%} (before blending)")
        
        # FIX #6: WHY THIS BET section
        output("\n   WHY:")
        model_prob = getattr(rec, 'projected_probability', rec.projected_probability)
        market_prob = getattr(rec, 'implied_probability', 1.0 / rec.odds if rec.odds > 0 else 0.5)
        diff_pct = (model_prob - market_prob) * 100
        output(f"   - Model > Market by +{diff_pct:.1f}%")
        insight_boost = getattr(rec, 'insight_boost', None)
        if insight_boost and insight_boost > 0:
            output(f"   - Insight boost: +{insight_boost*100:.1f}%")
    else:
        # Player prop
        output(f"\nPLAYER PROP: {rec.player_name} - {rec.market} {rec.selection}")
        match_time = getattr(rec, 'match_time', 'TBD')
        output(f"   Game: {rec.game} ({match_time})")

        recommendation_strength = getattr(rec, 'recommendation_strength', 'N/A')
        # Show tier if available
        tier = getattr(rec, 'tier', None)
        promoted_from = getattr(rec, 'promoted_from', None)
        confidence = getattr(rec, 'confidence_score', 0)
        
        # Fix #1: For promoted bets, show confidence-aligned tier with validation flag
        if tier and promoted_from:
            # Determine actual tier based on confidence (use player_prop thresholds for player props)
            from scrapers.bet_validation import MARKET_TIER_THRESHOLDS
            thresholds = MARKET_TIER_THRESHOLDS["player_prop"]
            
            # Determine actual tier from confidence
            if confidence >= thresholds["A"]:
                actual_tier = "A"
            elif confidence >= thresholds["B"]:
                actual_tier = "B"
            elif confidence >= thresholds["C"]:
                actual_tier = "C"
            else:
                actual_tier = "WATCHLIST"
            
            # Show confidence-aligned tier with validation flag
            tier_display = f" | Tier: {actual_tier} (CLV-validated)"
        elif tier:
            tier_display = f" | Tier: {tier}"
        else:
            tier_display = ""
        stake_cap = getattr(rec, 'stake_cap_pct', None)
        stake_display = f" (Stake: {stake_cap*100:.0f}%)" if stake_cap else ""
        output(f"   Odds: {rec.odds:.2f} | Confidence: {rec.confidence_score:.0f}% | Strength: {recommendation_strength}{tier_display}{stake_display}")
        output(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")

        historical_hit_rate = getattr(rec, 'historical_hit_rate', 0.0)
        output(f"   Sample Size: {rec.sample_size} games | Historical: {historical_hit_rate:.1%}")
        # Fix #3: Show final blended probability (what's used for EV calculation)
        output(f"   Final Probability: {rec.projected_probability:.1%}")
        
        # Fix #3: Show raw model probability if available and significantly different
        raw_model_prob = getattr(rec, 'raw_model_probability', None)
        if raw_model_prob is not None:
            diff_from_raw = abs(rec.projected_probability - raw_model_prob) * 100
            if diff_from_raw > 5.0:  # Show if difference > 5%
                output(f"   Raw Model Probability: {raw_model_prob:.1%} (before blending)")
        
        # FIX #6: WHY THIS BET section
        output("\n   WHY:")
        model_prob = getattr(rec, 'projected_probability', rec.projected_probability)
        market_prob = getattr(rec, 'implied_probability', 1.0 / rec.odds if rec.odds > 0 else 0.5)
        diff_pct = (model_prob - market_prob) * 100
        output(f"   - Model > Market by +{diff_pct:.1f}%")
        player_role = getattr(rec, 'player_role', None)
        if player_role:
            output(f"   - Role: {player_role.replace('_', ' ').title()}")
        # Show matchup advantages
        advanced_context = getattr(rec, 'advanced_context', None)
        if advanced_context and isinstance(advanced_context, dict):
            proj_details = advanced_context.get('projection_details', {})
            if isinstance(proj_details, dict):
                pace_mult = proj_details.get('pace_multiplier', 1.0)
                def_adj = proj_details.get('defense_adjustment', 1.0)
                if abs(pace_mult - 1.0) > 0.05:
                    output(f"   - Pace advantage: {pace_mult:.3f}x")
                if abs(def_adj - 1.0) > 0.05:
                    output(f"   - Defense adjustment: {def_adj:.3f}x")
        
        # Show fade alert if this is a fade opposite bet
        if getattr(rec, 'fade_opposite', False):
            original_fade_score = getattr(rec, 'original_fade_score', 0)
            output(f"   - 🔴 FADE OPPOSITE: Original bet had fade score {original_fade_score}/100")


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

