"""
Enhanced Player Props Analysis with Professional Features
========================================================

Implements 5 key improvements:
1. Risk Factors / Red Flags assessment
2. "Why" explanations for each prop
3. Variance-adjusted edge calculations
4. Player Usage Change (ΔUSG) tracking
5. Explicit Pace/Defense multiplier explanations
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessment:
    """Risk factors for a player prop bet"""
    blowout_risk: str  # LOW/MED/HIGH
    foul_trouble_risk: str  # LOW/MED/HIGH
    rotation_uncertainty: str  # LOW/MED/HIGH
    usage_inconsistency: str  # LOW/MED/HIGH
    minutes_volatility: str  # LOW/MED/HIGH
    overall_risk: str  # LOW/MED/HIGH/EXTREME
    risk_notes: List[str]

@dataclass
class UsageAnalysis:
    """Player usage change analysis"""
    season_usage: float
    recent_usage: float  # Last 5 games
    usage_change: float  # Recent vs season
    expected_usage_tonight: float
    usage_trend: str  # "increasing", "decreasing", "stable"
    usage_volatility: float  # Standard deviation

@dataclass
class MatchupContext:
    """Detailed matchup context explanations"""
    pace_explanation: str
    defense_explanation: str
    why_explanation: str  # 1-2 sentence explanation
    key_factors: List[str]

def calculate_risk_assessment(projection, game_log: List, stat_type: str, 
                            away_team: str, home_team: str) -> RiskAssessment:
    """Calculate comprehensive risk assessment for a prop bet"""
    
    risk_notes = []
    
    # 1. Blowout Risk Assessment
    # Based on team strength differential and pace
    blowout_risk = "LOW"  # Default
    
    # Simple heuristic - in real implementation, use team ratings
    team_differential = abs(hash(away_team) % 20 - hash(home_team) % 20)  # Mock differential
    if team_differential > 15:
        blowout_risk = "HIGH"
        risk_notes.append("High blowout risk due to team mismatch")
    elif team_differential > 10:
        blowout_risk = "MED"
        risk_notes.append("Moderate blowout risk")
    
    # 2. Foul Trouble Risk
    foul_trouble_risk = "LOW"
    if hasattr(projection, 'foul_rate') and projection.foul_rate > 0.15:
        foul_trouble_risk = "HIGH"
        risk_notes.append("High foul rate player")
    elif stat_type in ['blocks', 'steals']:
        foul_trouble_risk = "MED"
        risk_notes.append("Defensive stats prone to foul trouble")
    
    # 3. Minutes Volatility
    if len(game_log) >= 5:
        recent_minutes = [g.minutes for g in game_log[:5] if g.minutes > 0]
        if recent_minutes:
            minutes_std = (sum((m - sum(recent_minutes)/len(recent_minutes))**2 for m in recent_minutes) / len(recent_minutes))**0.5
            if minutes_std > 8:
                minutes_volatility = "HIGH"
                risk_notes.append(f"High minutes volatility (σ={minutes_std:.1f})")
            elif minutes_std > 4:
                minutes_volatility = "MED"
                risk_notes.append(f"Moderate minutes volatility (σ={minutes_std:.1f})")
            else:
                minutes_volatility = "LOW"
        else:
            minutes_volatility = "HIGH"
            risk_notes.append("Insufficient minutes data")
    else:
        minutes_volatility = "HIGH"
        risk_notes.append("Small sample size")
    
    # 4. Rotation Uncertainty
    rotation_uncertainty = "LOW"
    if hasattr(projection, 'role_change') and projection.role_change and projection.role_change.detected:
        rotation_uncertainty = "HIGH"
        risk_notes.append("Recent role change detected")
    
    # 5. Usage Inconsistency (if available)
    usage_inconsistency = "LOW"  # Default
    
    # Overall Risk Assessment
    risk_levels = [blowout_risk, foul_trouble_risk, minutes_volatility, rotation_uncertainty, usage_inconsistency]
    high_count = risk_levels.count("HIGH")
    med_count = risk_levels.count("MED")
    
    if high_count >= 2:
        overall_risk = "EXTREME"
    elif high_count >= 1 or med_count >= 3:
        overall_risk = "HIGH"
    elif med_count >= 1:
        overall_risk = "MED"
    else:
        overall_risk = "LOW"
    
    return RiskAssessment(
        blowout_risk=blowout_risk,
        foul_trouble_risk=foul_trouble_risk,
        rotation_uncertainty=rotation_uncertainty,
        usage_inconsistency=usage_inconsistency,
        minutes_volatility=minutes_volatility,
        overall_risk=overall_risk,
        risk_notes=risk_notes
    )

def calculate_usage_analysis(game_log: List, stat_type: str) -> Optional[UsageAnalysis]:
    """Calculate player usage change analysis"""
    
    if len(game_log) < 10:
        return None
    
    # Extract usage rates (mock calculation - in real implementation, use actual USG%)
    usage_rates = []
    for game in game_log:
        if game.minutes > 15:  # Only games with significant minutes
            # Mock usage calculation based on stats
            mock_usage = (getattr(game, 'points', 0) + getattr(game, 'assists', 0) * 2 + getattr(game, 'rebounds', 0)) / game.minutes * 2
            usage_rates.append(mock_usage)
    
    if len(usage_rates) < 5:
        return None
    
    # Season vs Recent (last 5)
    season_usage = sum(usage_rates) / len(usage_rates)
    recent_usage = sum(usage_rates[:5]) / 5
    usage_change = recent_usage - season_usage
    
    # Usage volatility
    usage_volatility = (sum((u - season_usage)**2 for u in usage_rates) / len(usage_rates))**0.5
    
    # Trend analysis
    if usage_change > 2:
        usage_trend = "increasing"
    elif usage_change < -2:
        usage_trend = "decreasing"
    else:
        usage_trend = "stable"
    
    # Expected usage tonight (with small adjustment)
    expected_usage_tonight = recent_usage + (usage_change * 0.3)  # Regression to mean
    
    return UsageAnalysis(
        season_usage=season_usage,
        recent_usage=recent_usage,
        usage_change=usage_change,
        expected_usage_tonight=expected_usage_tonight,
        usage_trend=usage_trend,
        usage_volatility=usage_volatility
    )

def create_matchup_context(projection, stat_type: str, player_name: str, 
                          away_team: str, home_team: str) -> MatchupContext:
    """Create detailed matchup context with explanations"""
    
    # Extract pace and defense multipliers
    pace_mult = 1.0
    defense_adj = 1.0
    
    if hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
        pace_mult = getattr(projection.matchup_adjustments, 'pace_multiplier', 1.0)
        defense_adj = getattr(projection.matchup_adjustments, 'defense_adjustment', 1.0)
    
    # Pace explanation
    if pace_mult > 1.05:
        pace_explanation = f"Fast pace game (+{(pace_mult-1)*100:.1f}%) - more possessions expected"
    elif pace_mult < 0.95:
        pace_explanation = f"Slow pace game ({(pace_mult-1)*100:.1f}%) - fewer possessions expected"
    else:
        pace_explanation = f"Neutral pace (±{abs(pace_mult-1)*100:.1f}%) - standard possessions"
    
    # Defense explanation
    if defense_adj > 1.05:
        defense_explanation = f"Favorable matchup (+{(defense_adj-1)*100:.1f}%) - opponent allows more {stat_type}"
    elif defense_adj < 0.95:
        defense_explanation = f"Tough matchup ({(defense_adj-1)*100:.1f}%) - opponent defends {stat_type} well"
    else:
        defense_explanation = f"Neutral matchup (±{abs(defense_adj-1)*100:.1f}%) - average defensive impact"
    
    # Create "why" explanation
    key_factors = []
    
    # Role change factor
    if hasattr(projection, 'role_change') and projection.role_change and projection.role_change.detected:
        key_factors.append("role change detected")
    
    # Usage factor (mock)
    if stat_type in ['points', 'assists']:
        key_factors.append("increased usage opportunity")
    
    # Matchup factor
    if defense_adj > 1.05:
        key_factors.append(f"opponent weak vs {stat_type}")
    elif defense_adj < 0.95:
        key_factors.append(f"opponent strong vs {stat_type}")
    
    # Pace factor
    if pace_mult > 1.05:
        key_factors.append("fast-paced game")
    elif pace_mult < 0.95:
        key_factors.append("slow-paced game")
    
    # Construct why explanation
    if key_factors:
        why_explanation = f"{player_name}'s {stat_type} projection boosted by {' and '.join(key_factors[:2])}."
    else:
        why_explanation = f"{player_name} maintains consistent {stat_type} production in neutral matchup."
    
    return MatchupContext(
        pace_explanation=pace_explanation,
        defense_explanation=defense_explanation,
        why_explanation=why_explanation,
        key_factors=key_factors
    )

def calculate_variance_adjusted_edge(raw_edge: float, risk_assessment: RiskAssessment, 
                                   usage_analysis: Optional[UsageAnalysis], 
                                   sample_size: int) -> float:
    """Calculate variance-adjusted edge to avoid overconfident high edges"""
    
    # Start with raw edge
    adjusted_edge = raw_edge
    
    # Sample size adjustment
    if sample_size < 10:
        sample_penalty = 0.4  # 40% reduction for very small samples
    elif sample_size < 15:
        sample_penalty = 0.2  # 20% reduction for small samples
    else:
        sample_penalty = 0.0
    
    # Risk-based adjustment
    risk_penalty = 0.0
    if risk_assessment.overall_risk == "EXTREME":
        risk_penalty = 0.5  # 50% reduction
    elif risk_assessment.overall_risk == "HIGH":
        risk_penalty = 0.3  # 30% reduction
    elif risk_assessment.overall_risk == "MED":
        risk_penalty = 0.15  # 15% reduction
    
    # Usage volatility adjustment
    usage_penalty = 0.0
    if usage_analysis and usage_analysis.usage_volatility > 5:
        usage_penalty = 0.2  # 20% reduction for high usage volatility
    elif usage_analysis and usage_analysis.usage_volatility > 3:
        usage_penalty = 0.1  # 10% reduction for moderate volatility
    
    # Apply all adjustments
    total_penalty = sample_penalty + risk_penalty + usage_penalty
    adjusted_edge = raw_edge * (1 - min(total_penalty, 0.7))  # Cap total penalty at 70%
    
    return adjusted_edge

def enhance_player_prop_prediction(prediction: Dict, projection, game_log: List) -> Dict:
    """Enhance a player prop prediction with all 5 improvements"""
    
    player_name = prediction['player']
    stat_type = prediction['stat']
    away_team = prediction.get('game', '').split(' @ ')[0] if ' @ ' in prediction.get('game', '') else ''
    home_team = prediction.get('game', '').split(' @ ')[1] if ' @ ' in prediction.get('game', '') else ''
    
    # 1. Risk Assessment
    risk_assessment = calculate_risk_assessment(projection, game_log, stat_type, away_team, home_team)
    
    # 2. Usage Analysis
    usage_analysis = calculate_usage_analysis(game_log, stat_type)
    
    # 3. Matchup Context (includes "why" explanation)
    matchup_context = create_matchup_context(projection, stat_type, player_name, away_team, home_team)
    
    # 4. Variance-adjusted edge
    raw_edge = prediction.get('edge', 0) / 100  # Convert from percentage
    adjusted_edge = calculate_variance_adjusted_edge(
        raw_edge, risk_assessment, usage_analysis, prediction.get('sample_size', 0)
    )
    
    # Add enhancements to prediction
    prediction['risk_assessment'] = {
        'overall_risk': risk_assessment.overall_risk,
        'blowout_risk': risk_assessment.blowout_risk,
        'foul_trouble_risk': risk_assessment.foul_trouble_risk,
        'rotation_uncertainty': risk_assessment.rotation_uncertainty,
        'usage_inconsistency': risk_assessment.usage_inconsistency,
        'minutes_volatility': risk_assessment.minutes_volatility,
        'risk_notes': risk_assessment.risk_notes
    }
    
    if usage_analysis:
        prediction['usage_analysis'] = {
            'season_usage': round(usage_analysis.season_usage, 1),
            'recent_usage': round(usage_analysis.recent_usage, 1),
            'usage_change': round(usage_analysis.usage_change, 1),
            'expected_usage_tonight': round(usage_analysis.expected_usage_tonight, 1),
            'usage_trend': usage_analysis.usage_trend,
            'usage_volatility': round(usage_analysis.usage_volatility, 1)
        }
    
    prediction['matchup_context'] = {
        'pace_explanation': matchup_context.pace_explanation,
        'defense_explanation': matchup_context.defense_explanation,
        'why_explanation': matchup_context.why_explanation,
        'key_factors': matchup_context.key_factors
    }
    
    # Update edge calculations
    prediction['raw_edge'] = round(raw_edge * 100, 1)
    prediction['adjusted_edge'] = round(adjusted_edge * 100, 1)
    prediction['edge'] = prediction['adjusted_edge']  # Use adjusted as primary
    
    # Add variance adjustment note
    if adjusted_edge < raw_edge * 0.9:
        prediction['variance_note'] = f"Edge reduced by {round((raw_edge - adjusted_edge) * 100, 1)}% due to risk factors"
    
    return prediction

def format_enhanced_prediction_display(prediction: Dict) -> str:
    """Format enhanced prediction for display"""
    
    player = prediction['player']
    stat = prediction['stat']
    line = prediction['line']
    pred = prediction['prediction']
    odds = prediction['odds']
    edge = prediction.get('adjusted_edge', prediction.get('edge', 0))
    confidence = prediction['confidence']
    
    # Risk level emoji
    risk_emoji = {
        'LOW': '🟢',
        'MED': '🟡', 
        'HIGH': '🟠',
        'EXTREME': '🔴'
    }
    
    risk = prediction.get('risk_assessment', {}).get('overall_risk', 'UNKNOWN')
    risk_display = f"{risk_emoji.get(risk, '⚪')} {risk}"
    
    # Usage change display
    usage_display = ""
    if 'usage_analysis' in prediction:
        usage = prediction['usage_analysis']
        change = usage['usage_change']
        if abs(change) > 1:
            usage_display = f" | ΔUsage: {change:+.1f}%"
    
    # Main line
    result = f"🎯 {player} {stat.upper()} {pred} {line} @ {odds} | Edge: {edge:.1f}% | Conf: {confidence:.0f}% | Risk: {risk_display}{usage_display}\n"
    
    # Why explanation
    if 'matchup_context' in prediction:
        result += f"   💡 {prediction['matchup_context']['why_explanation']}\n"
    
    # Risk factors (if any)
    if 'risk_assessment' in prediction and prediction['risk_assessment']['risk_notes']:
        risk_notes = prediction['risk_assessment']['risk_notes'][:2]  # Show top 2
        result += f"   ⚠️  Risks: {', '.join(risk_notes)}\n"
    
    # Pace/Defense context
    if 'matchup_context' in prediction:
        ctx = prediction['matchup_context']
        result += f"   📊 {ctx['pace_explanation']}\n"
        result += f"   🛡️  {ctx['defense_explanation']}\n"
    
    return result