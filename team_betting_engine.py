"""
Team Betting Engine - Moneyline, Totals, and Handicap Projections
==================================================================
Uses team-level historical data to project:
- Moneyline (win probability)
- Totals (over/under total points)
- Handicap/Spread (point differential)

Based on recent game results, offensive/defensive ratings, pace, and trends.

Usage:
    from team_betting_engine import TeamBettingEngine
    
    engine = TeamBettingEngine()
    projection = engine.project_game(
        home_team="Lakers",
        away_team="Celtics",
        home_recent_scores=[123, 120, 108, 119, 129],
        away_recent_scores=[125, 108, 121, 133, 119]
    )
"""

import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# NBA League Averages (2024-25 season)
LEAGUE_AVG_POINTS = 114.0
LEAGUE_AVG_MARGIN = 0.0
HOME_COURT_ADVANTAGE = 3.5  # Points


class MarketType(Enum):
    """Betting market types"""
    MONEYLINE = "moneyline"
    TOTAL = "total"
    SPREAD = "spread"


@dataclass
class TeamForm:
    """Team form analysis from recent games"""
    team_name: str
    
    # Scoring
    avg_points_scored: float
    avg_points_allowed: float
    
    # Trends
    win_pct: float
    recent_form: str  # "W-W-L-W-L" format
    streak: str  # "3W" or "2L"
    
    # Consistency
    scoring_std_dev: float
    defense_std_dev: float
    
    # Pace
    avg_total_points: float  # Combined team + opponent
    pace_rating: float  # vs league average
    
    # Recent results (last 5-10 games)
    recent_scores: List[Tuple[int, int]]  # [(team_score, opp_score), ...]
    
    # Trends
    scoring_trend: str  # "improving", "declining", "stable"
    defensive_trend: str  # "improving", "declining", "stable"


@dataclass
class GameProjection:
    """Complete game projection"""
    home_team: str
    away_team: str
    
    # Score projections
    projected_home_score: float
    projected_away_score: float
    projected_total: float
    projected_margin: float  # Positive = home wins
    
    # Win probabilities
    home_win_probability: float
    away_win_probability: float
    
    # Spread projections
    recommended_spread: float  # From home team perspective
    spread_confidence: float  # 0-100
    
    # Total projections
    recommended_total: float
    over_probability: float
    under_probability: float
    
    # Confidence metrics
    projection_confidence: float  # 0-100
    sample_size: int
    
    # Supporting data
    home_form: Optional[TeamForm] = None
    away_form: Optional[TeamForm] = None
    
    # Notes
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class BettingRecommendation:
    """Team-level betting recommendation"""
    game: str
    market_type: MarketType
    selection: str
    odds: float
    
    # Projections
    projected_probability: float
    implied_probability: float
    edge_percentage: float
    expected_value: float
    
    # Confidence
    confidence_score: float
    recommendation_strength: str  # "LOW", "MEDIUM", "HIGH", "VERY_HIGH"
    
    # Context
    reasoning: List[str]
    projection: GameProjection


class TeamBettingEngine:
    """
    Team-level betting engine for moneyline, totals, and spreads.
    
    Uses recent game results to project team performance.
    """
    
    def __init__(self):
        self.min_games = 5  # Minimum games for analysis
    
    def analyze_team_form(
        self,
        team_name: str,
        recent_results: List[Tuple[int, int, str]]  # [(team_score, opp_score, result), ...]
    ) -> TeamForm:
        """
        Analyze team form from recent results.
        
        Args:
            team_name: Team name
            recent_results: List of (team_score, opp_score, "W"/"L") tuples
            
        Returns:
            TeamForm object
        """
        if len(recent_results) < self.min_games:
            raise ValueError(f"Need at least {self.min_games} games for analysis")
        
        # Extract scores
        team_scores = [r[0] for r in recent_results]
        opp_scores = [r[1] for r in recent_results]
        results = [r[2] for r in recent_results]
        
        # Calculate averages
        avg_scored = statistics.mean(team_scores)
        avg_allowed = statistics.mean(opp_scores)
        
        # Calculate standard deviations
        scoring_std = statistics.stdev(team_scores) if len(team_scores) > 1 else 0
        defense_std = statistics.stdev(opp_scores) if len(opp_scores) > 1 else 0
        
        # Win percentage
        wins = sum(1 for r in results if r == "W")
        win_pct = wins / len(results)
        
        # Recent form string
        form_str = "-".join(results[:5])  # Last 5 games
        
        # Streak
        streak_count = 1
        streak_type = results[0]
        for r in results[1:]:
            if r == streak_type:
                streak_count += 1
            else:
                break
        streak = f"{streak_count}{streak_type}"
        
        # Pace (total points per game)
        total_points = [team_scores[i] + opp_scores[i] for i in range(len(team_scores))]
        avg_total = statistics.mean(total_points)
        pace_rating = avg_total / (LEAGUE_AVG_POINTS * 2)
        
        # Trends (last 3 vs previous 3)
        if len(team_scores) >= 6:
            recent_scoring = statistics.mean(team_scores[:3])
            previous_scoring = statistics.mean(team_scores[3:6])
            
            if recent_scoring > previous_scoring * 1.05:
                scoring_trend = "improving"
            elif recent_scoring < previous_scoring * 0.95:
                scoring_trend = "declining"
            else:
                scoring_trend = "stable"
            
            recent_defense = statistics.mean(opp_scores[:3])
            previous_defense = statistics.mean(opp_scores[3:6])
            
            if recent_defense < previous_defense * 0.95:
                defensive_trend = "improving"
            elif recent_defense > previous_defense * 1.05:
                defensive_trend = "declining"
            else:
                defensive_trend = "stable"
        else:
            scoring_trend = "stable"
            defensive_trend = "stable"
        
        return TeamForm(
            team_name=team_name,
            avg_points_scored=avg_scored,
            avg_points_allowed=avg_allowed,
            win_pct=win_pct,
            recent_form=form_str,
            streak=streak,
            scoring_std_dev=scoring_std,
            defense_std_dev=defense_std,
            avg_total_points=avg_total,
            pace_rating=pace_rating,
            recent_scores=[(team_scores[i], opp_scores[i]) for i in range(len(team_scores))],
            scoring_trend=scoring_trend,
            defensive_trend=defensive_trend
        )
    
    def project_game(
        self,
        home_team: str,
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        neutral_site: bool = False
    ) -> GameProjection:
        """
        Project game outcome using team form.
        
        Method:
        1. Project scores using offensive/defensive ratings
        2. Apply home court advantage
        3. Calculate win probabilities
        4. Generate spread and total recommendations
        """
        notes = []
        
        # 1. Project scores using "Four Factors" approach
        # Home score = (Home offense + Away defense) / 2
        # Away score = (Away offense + Home defense) / 2
        
        home_offensive_rating = home_form.avg_points_scored
        home_defensive_rating = home_form.avg_points_allowed
        away_offensive_rating = away_form.avg_points_scored
        away_defensive_rating = away_form.avg_points_allowed
        
        # Base projections
        projected_home = (home_offensive_rating + away_defensive_rating) / 2
        projected_away = (away_offensive_rating + home_defensive_rating) / 2
        
        # Apply home court advantage
        if not neutral_site:
            projected_home += HOME_COURT_ADVANTAGE / 2
            projected_away -= HOME_COURT_ADVANTAGE / 2
            notes.append(f"Home court advantage: +{HOME_COURT_ADVANTAGE} points to {home_team}")
        
        # Adjust for pace
        # If both teams play fast/slow, adjust total
        avg_pace = (home_form.pace_rating + away_form.pace_rating) / 2
        if avg_pace > 1.05:
            pace_boost = (avg_pace - 1.0) * 10
            projected_home += pace_boost / 2
            projected_away += pace_boost / 2
            notes.append(f"Fast-paced matchup ({avg_pace:.2f}x) - expect higher scoring")
        elif avg_pace < 0.95:
            pace_reduction = (1.0 - avg_pace) * 10
            projected_home -= pace_reduction / 2
            projected_away -= pace_reduction / 2
            notes.append(f"Slow-paced matchup ({avg_pace:.2f}x) - expect lower scoring")
        
        # Calculate totals and margin
        projected_total = projected_home + projected_away
        projected_margin = projected_home - projected_away
        
        # 2. Calculate win probabilities
        # Use logistic function based on projected margin
        # P(home win) = 1 / (1 + e^(-margin/10))
        import math
        home_win_prob = 1 / (1 + math.exp(-projected_margin / 10))
        away_win_prob = 1 - home_win_prob
        
        # 3. Adjust probabilities based on form
        # Teams on winning streaks get slight boost
        if home_form.streak.endswith("W") and int(home_form.streak[0]) >= 3:
            home_win_prob += 0.03
            away_win_prob -= 0.03
            notes.append(f"{home_team} on {home_form.streak} streak - momentum boost")
        elif away_form.streak.endswith("W") and int(away_form.streak[0]) >= 3:
            away_win_prob += 0.03
            home_win_prob -= 0.03
            notes.append(f"{away_team} on {away_form.streak} streak - momentum boost")
        
        # Clamp probabilities
        home_win_prob = max(0.05, min(0.95, home_win_prob))
        away_win_prob = 1 - home_win_prob
        
        # 4. Generate spread recommendation
        recommended_spread = round(projected_margin * 2) / 2  # Round to nearest 0.5
        
        # Spread confidence based on consistency
        # More consistent teams = higher confidence
        home_consistency = 1 / (1 + home_form.scoring_std_dev / 10)
        away_consistency = 1 / (1 + away_form.scoring_std_dev / 10)
        avg_consistency = (home_consistency + away_consistency) / 2
        spread_confidence = avg_consistency * 100
        
        # 5. Generate total recommendation
        recommended_total = round(projected_total * 2) / 2  # Round to nearest 0.5
        
        # Over/under probabilities
        # Use combined standard deviation to estimate variance
        combined_std = math.sqrt(home_form.scoring_std_dev**2 + away_form.scoring_std_dev**2)
        
        # P(over) based on how far projected total is from recommended line
        # If projected = recommended, P(over) = 50%
        # For every 5 points difference, adjust by ~10%
        total_diff = projected_total - recommended_total
        over_prob = 0.5 + (total_diff / 50)
        over_prob = max(0.3, min(0.7, over_prob))
        under_prob = 1 - over_prob
        
        # 6. Calculate overall projection confidence
        # Based on sample size and consistency
        sample_size = min(len(home_form.recent_scores), len(away_form.recent_scores))
        sample_confidence = min(100, (sample_size / 10) * 100)
        consistency_confidence = avg_consistency * 100
        projection_confidence = (sample_confidence + consistency_confidence) / 2
        
        # Add form notes
        if home_form.scoring_trend == "improving":
            notes.append(f"{home_team} offense trending up")
        if away_form.defensive_trend == "improving":
            notes.append(f"{away_team} defense trending up")
        
        return GameProjection(
            home_team=home_team,
            away_team=away_team,
            projected_home_score=projected_home,
            projected_away_score=projected_away,
            projected_total=projected_total,
            projected_margin=projected_margin,
            home_win_probability=home_win_prob,
            away_win_probability=away_win_prob,
            recommended_spread=recommended_spread,
            spread_confidence=spread_confidence,
            recommended_total=recommended_total,
            over_probability=over_prob,
            under_probability=under_prob,
            projection_confidence=projection_confidence,
            sample_size=sample_size,
            home_form=home_form,
            away_form=away_form,
            notes=notes
        )
    
    def evaluate_bet(
        self,
        projection: GameProjection,
        market_type: MarketType,
        line: float,
        odds: float,
        selection: str
    ) -> Optional[BettingRecommendation]:
        """
        Evaluate if a bet has value.
        
        Args:
            projection: Game projection
            market_type: Type of bet (moneyline, total, spread)
            line: Betting line (spread or total)
            odds: Decimal odds
            selection: What you're betting on
            
        Returns:
            BettingRecommendation if bet has value, None otherwise
        """
        reasoning = []
        
        # Calculate projected probability based on market type
        if market_type == MarketType.MONEYLINE:
            if selection.lower() == projection.home_team.lower() or "home" in selection.lower():
                projected_prob = projection.home_win_probability
                reasoning.append(f"Projected {projection.home_team} win probability: {projected_prob:.1%}")
            else:
                projected_prob = projection.away_win_probability
                reasoning.append(f"Projected {projection.away_team} win probability: {projected_prob:.1%}")
        
        elif market_type == MarketType.TOTAL:
            if "over" in selection.lower():
                projected_prob = projection.over_probability
                reasoning.append(f"Projected total: {projection.projected_total:.1f} vs line {line}")
                reasoning.append(f"Over probability: {projected_prob:.1%}")
            else:
                projected_prob = projection.under_probability
                reasoning.append(f"Projected total: {projection.projected_total:.1f} vs line {line}")
                reasoning.append(f"Under probability: {projected_prob:.1%}")
        
        elif market_type == MarketType.SPREAD:
            # Calculate probability of covering spread
            # If home team favored by X, they need to win by > X
            import math
            
            if "home" in selection.lower() or projection.home_team.lower() in selection.lower():
                # Betting on home team to cover
                margin_needed = line  # Negative if home favored
                margin_diff = projection.projected_margin - margin_needed
                # P(cover) = P(margin > margin_needed)
                projected_prob = 1 / (1 + math.exp(-margin_diff / 8))
                reasoning.append(f"Projected margin: {projection.projected_margin:+.1f} vs spread {line:+.1f}")
            else:
                # Betting on away team to cover
                margin_needed = -line
                margin_diff = -projection.projected_margin - margin_needed
                projected_prob = 1 / (1 + math.exp(-margin_diff / 8))
                reasoning.append(f"Projected margin: {-projection.projected_margin:+.1f} vs spread {-line:+.1f}")
            
            reasoning.append(f"Cover probability: {projected_prob:.1%}")
        
        else:
            return None
        
        # Calculate value metrics
        implied_prob = 1.0 / odds
        edge = projected_prob - implied_prob
        ev = (projected_prob * (odds - 1)) - (1 - projected_prob)
        
        # Calculate confidence
        confidence = projection.projection_confidence * (projected_prob / 0.5)  # Boost for higher probability
        confidence = min(95, confidence)
        
        # Determine strength
        if confidence >= 75 and ev > 0.08:
            strength = "VERY_HIGH"
        elif confidence >= 65 and ev > 0.05:
            strength = "HIGH"
        elif confidence >= 55 and ev > 0.03:
            strength = "MEDIUM"
        else:
            strength = "LOW"
        
        # Add value analysis to reasoning
        reasoning.append(f"Implied probability: {implied_prob:.1%}")
        reasoning.append(f"Edge: {edge*100:+.1f}%")
        reasoning.append(f"Expected value: {ev*100:+.1f}%")
        
        # Only recommend if positive EV and sufficient confidence
        if ev > 0 and confidence >= 50:
            return BettingRecommendation(
                game=f"{projection.away_team} @ {projection.home_team}",
                market_type=market_type,
                selection=selection,
                odds=odds,
                projected_probability=projected_prob,
                implied_probability=implied_prob,
                edge_percentage=edge * 100,
                expected_value=ev * 100,
                confidence_score=confidence,
                recommendation_strength=strength,
                reasoning=reasoning,
                projection=projection
            )
        
        return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_game_results_from_insights(insights_data: List[Dict]) -> Dict[str, List[Tuple[int, int, str]]]:
    """
    Parse game results from Sportsbet insights data.
    
    Expected format from screenshot:
    - Team name
    - Date
    - Score (e.g., "123-120")
    - Result (W/L)
    
    Returns:
        Dict mapping team name to list of (team_score, opp_score, result) tuples
    """
    team_results = {}
    
    # This would parse the actual insights data structure
    # For now, placeholder implementation
    
    return team_results


if __name__ == '__main__':
    # Example usage
    print("="*70)
    print("TEAM BETTING ENGINE - TEST")
    print("="*70)
    print()
    
    engine = TeamBettingEngine()
    
    # Example: Lakers vs Celtics
    # Lakers recent results (from screenshot format)
    lakers_results = [
        (123, 120, "W"),  # Most recent
        (125, 108, "W"),
        (121, 133, "L"),
        (119, 129, "L"),
        (118, 135, "L"),
        (108, 106, "W"),
        (126, 140, "L"),
        (119, 95, "W"),
    ]
    
    celtics_results = [
        (120, 130, "L"),
        (123, 115, "W"),
        (122, 108, "W"),
        (127, 120, "W"),
        (116, 118, "L"),
        (116, 115, "W"),
        (122, 108, "W"),
        (123, 115, "W"),
    ]
    
    # Analyze form
    lakers_form = engine.analyze_team_form("Lakers", lakers_results)
    celtics_form = engine.analyze_team_form("Celtics", celtics_results)
    
    print(f"Lakers Form:")
    print(f"  Avg Scored: {lakers_form.avg_points_scored:.1f}")
    print(f"  Avg Allowed: {lakers_form.avg_points_allowed:.1f}")
    print(f"  Win%: {lakers_form.win_pct:.1%}")
    print(f"  Streak: {lakers_form.streak}")
    print(f"  Form: {lakers_form.recent_form}")
    print()
    
    print(f"Celtics Form:")
    print(f"  Avg Scored: {celtics_form.avg_points_scored:.1f}")
    print(f"  Avg Allowed: {celtics_form.avg_points_allowed:.1f}")
    print(f"  Win%: {celtics_form.win_pct:.1%}")
    print(f"  Streak: {celtics_form.streak}")
    print(f"  Form: {celtics_form.recent_form}")
    print()
    
    # Project game
    projection = engine.project_game(
        home_team="Lakers",
        away_team="Celtics",
        home_form=lakers_form,
        away_form=celtics_form
    )
    
    print("Game Projection:")
    print(f"  {projection.away_team} @ {projection.home_team}")
    print(f"  Projected Score: {projection.projected_away_score:.1f} - {projection.projected_home_score:.1f}")
    print(f"  Projected Total: {projection.projected_total:.1f}")
    print(f"  Projected Margin: {projection.projected_margin:+.1f} (home)")
    print()
    print(f"  Win Probabilities:")
    print(f"    {projection.home_team}: {projection.home_win_probability:.1%}")
    print(f"    {projection.away_team}: {projection.away_win_probability:.1%}")
    print()
    print(f"  Recommended Spread: {projection.recommended_spread:+.1f} (home)")
    print(f"  Recommended Total: {projection.recommended_total:.1f}")
    print()
    print(f"  Confidence: {projection.projection_confidence:.0f}%")
    print()
    
    if projection.notes:
        print("  Notes:")
        for note in projection.notes:
            print(f"    • {note}")
    print()
    
    # Evaluate sample bets
    print("="*70)
    print("BET EVALUATION")
    print("="*70)
    print()
    
    # Moneyline
    bet1 = engine.evaluate_bet(
        projection=projection,
        market_type=MarketType.MONEYLINE,
        line=0,
        odds=1.90,
        selection="Lakers"
    )
    
    if bet1:
        print(f"✓ MONEYLINE: {bet1.selection} @ {bet1.odds}")
        print(f"  Confidence: {bet1.confidence_score:.0f}% | Strength: {bet1.recommendation_strength}")
        print(f"  Edge: {bet1.edge_percentage:+.1f}% | EV: {bet1.expected_value:+.1f}%")
        print()
    
    # Total
    bet2 = engine.evaluate_bet(
        projection=projection,
        market_type=MarketType.TOTAL,
        line=223.5,
        odds=1.90,
        selection="Over"
    )
    
    if bet2:
        print(f"✓ TOTAL: {bet2.selection} {223.5} @ {bet2.odds}")
        print(f"  Confidence: {bet2.confidence_score:.0f}% | Strength: {bet2.recommendation_strength}")
        print(f"  Edge: {bet2.edge_percentage:+.1f}% | EV: {bet2.expected_value:+.1f}%")
        print()
    
    # Spread
    bet3 = engine.evaluate_bet(
        projection=projection,
        market_type=MarketType.SPREAD,
        line=-3.5,
        odds=1.90,
        selection="Lakers -3.5"
    )
    
    if bet3:
        print(f"✓ SPREAD: {bet3.selection} @ {bet3.odds}")
        print(f"  Confidence: {bet3.confidence_score:.0f}% | Strength: {bet3.recommendation_strength}")
        print(f"  Edge: {bet3.edge_percentage:+.1f}% | EV: {bet3.expected_value:+.1f}%")
