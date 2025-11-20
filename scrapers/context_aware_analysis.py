"""
Context-Aware Value Analysis
=============================
Enhanced analysis that accounts for critical context factors:

1. Minutes projection (situational benching risk)
2. Recent form vs historical average (role changes)
3. Team composition changes
4. Pace and matchup factors
5. Context-specific trends (vs East, vs strong teams, etc.)

Usage:
  from context_aware_analysis import ContextAwareAnalyzer

  analyzer = ContextAwareAnalyzer()
  enhanced_analysis = analyzer.analyze_with_context(
      historical_outcomes=[1,1,0,1,1,0,1,1],
      recent_outcomes=[1,1,0],  # Last 3 games
      historical_minutes=[28,30,15,32,29,18,31,30],
      recent_minutes=[30,28,32],
      bookmaker_odds=1.85,
      player_name="Jonas Valanciunas",
      context_tags=["vs_east", "home"]
  )
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import math


@dataclass
class MinutesProjection:
    """Minutes projection and risk assessment"""
    historical_avg: float
    recent_avg: float  # Last 3-5 games
    min_threshold: float  # Minimum minutes needed for prop
    volatility: float  # Standard deviation of minutes
    benching_risk: str  # "LOW", "MEDIUM", "HIGH"
    risk_score: float  # 0-100, higher = more risk

    def to_dict(self):
        return asdict(self)


@dataclass
class RecencyAdjustment:
    """Recency-weighted probability adjustment"""
    historical_prob: float
    recent_form_prob: float  # Last 3-5 games
    adjusted_prob: float  # Weighted combination
    trend_direction: str  # "IMPROVING", "DECLINING", "STABLE"
    confidence: float  # 0-100, confidence in adjustment

    def to_dict(self):
        return asdict(self)


@dataclass
class ContextFactors:
    """External context affecting the bet"""
    opponent_strength: Optional[float] = None  # 0-100
    pace_differential: Optional[float] = None  # Team pace vs opponent pace
    days_rest: Optional[int] = None
    home_away: Optional[str] = None  # "HOME", "AWAY", "NEUTRAL"
    back_to_back: bool = False
    injury_impact: Optional[str] = None  # From lineup data

    def get_risk_multiplier(self) -> float:
        """Calculate risk multiplier based on context (0.5 to 1.5)"""
        multiplier = 1.0

        if self.back_to_back:
            multiplier *= 0.85  # Higher injury/rest risk

        if self.days_rest and self.days_rest < 1:
            multiplier *= 0.9

        if self.injury_impact in ["HIGH", "MODERATE"]:
            multiplier *= 0.85

        return max(0.5, min(1.5, multiplier))

    def to_dict(self):
        return asdict(self)


@dataclass
class MarketVariance:
    """Market-specific variance and confidence adjustments"""
    market_type: str  # "Match Winner", "Over/Under", "Handicap", "1H Winner", "Props"
    base_variance: float  # Base variance for this market type
    confidence_multiplier: float  # Multiplier for confidence (0.5 to 1.5)

    def to_dict(self):
        return asdict(self)


@dataclass
class ContextAwareAnalysis:
    """Complete context-aware analysis result with ALL enhancements"""
    # Core analysis
    historical_probability: float
    adjusted_probability: float  # After all context adjustments
    bookmaker_probability: float
    bookmaker_odds: float

    # Enhancements
    minutes_projection: MinutesProjection
    recency_adjustment: RecencyAdjustment
    context_factors: ContextFactors

    # NEW: Sample size and edge weighting
    sample_size: int
    sample_weight: float  # min(1, n/10) for edge weighting
    weighted_edge: float  # Edge * sample_weight
    raw_edge: float  # Original edge before weighting

    # NEW: Composite confidence scoring
    confidence_level: str  # "VERY_HIGH", "HIGH", "MEDIUM", "LOW"
    confidence_score: float  # 0-100 composite score
    edge_component: float  # Component from edge magnitude
    sample_component: float  # Component from sample size
    recency_component: float  # Component from recency

    # Risk assessment
    overall_risk: str  # "LOW", "MEDIUM", "HIGH", "VERY_HIGH"
    risk_score: float  # 0-100

    # NEW: Enhanced EV calculations
    has_value: bool
    value_percentage: float
    ev_per_100: float  # Standard EV
    risk_adjusted_ev: float  # EV * (Confidence / 100)
    implied_odds: float

    # Recommendations (must come before optional fields)
    recommendation: str  # "STRONG BET", "BET", "CONSIDER", "PASS", "AVOID"
    reasons: List[str]
    warnings: List[str]

    # NEW: Stake sizing guidance
    recommended_stake_pct: float  # Kelly Criterion stake % of bankroll

    # NEW: Market-specific adjustments (optional fields must come last)
    market_variance: Optional[MarketVariance] = None

    # NEW: Streak and variance info (optional fields)
    recent_streak: Optional[str] = None  # e.g., "5 of last 8 games were Over"
    historical_variance: Optional[float] = None  # Variance in outcomes

    def to_dict(self):
        return {
            'historical_probability': self.historical_probability,
            'adjusted_probability': self.adjusted_probability,
            'bookmaker_probability': self.bookmaker_probability,
            'bookmaker_odds': self.bookmaker_odds,
            'minutes_projection': self.minutes_projection.to_dict(),
            'recency_adjustment': self.recency_adjustment.to_dict(),
            'context_factors': self.context_factors.to_dict(),
            'sample_size': self.sample_size,
            'sample_weight': self.sample_weight,
            'weighted_edge': self.weighted_edge,
            'raw_edge': self.raw_edge,
            'confidence_level': self.confidence_level,
            'confidence_score': self.confidence_score,
            'edge_component': self.edge_component,
            'sample_component': self.sample_component,
            'recency_component': self.recency_component,
            'overall_risk': self.overall_risk,
            'risk_score': self.risk_score,
            'has_value': self.has_value,
            'value_percentage': self.value_percentage,
            'ev_per_100': self.ev_per_100,
            'risk_adjusted_ev': self.risk_adjusted_ev,
            'implied_odds': self.implied_odds,
            'recommended_stake_pct': self.recommended_stake_pct,
            'market_variance': self.market_variance.to_dict() if self.market_variance else None,
            'recent_streak': self.recent_streak,
            'historical_variance': self.historical_variance,
            'recommendation': self.recommendation,
            'reasons': self.reasons,
            'warnings': self.warnings
        }


class ContextAwareAnalyzer:
    """Enhanced analyzer with context awareness and ALL improvements"""

    def __init__(self):
        self.min_sample_size = 5
        self.recency_window = 5  # Last N games for recent form
        self.recency_weight = 0.3  # Weight for recent vs historical (0.3 = 30% recent, 70% historical)

        # Bayesian regression parameters
        self.regression_threshold = 30  # Sample size where we fully trust the data
        self.league_avg_probability = 0.50  # Default prior for most props

        # NEW: Sample size weighting threshold
        self.sample_weight_threshold = 10  # Sample size for full weight (n/10)

        # NEW: Market-specific variance profiles
        self.market_variances = {
            'Match Winner': {'variance': 0.25, 'confidence_mult': 1.0},
            'Over/Under': {'variance': 0.20, 'confidence_mult': 1.1},
            'Handicap': {'variance': 0.22, 'confidence_mult': 1.0},
            '1H Winner': {'variance': 0.35, 'confidence_mult': 0.7},  # Higher variance
            'Player Props': {'variance': 0.18, 'confidence_mult': 1.2},  # More predictable
            'Default': {'variance': 0.25, 'confidence_mult': 1.0}
        }

        # Trend quality weights (affects confidence and adjustments)
        self.trend_quality_weights = {
            'PLAYER_STATS_FLOOR': {'weight': 1.0, 'confidence_boost': 20, 'description': 'HIGH'},
            'PLAYER_USAGE_SPLIT': {'weight': 0.7, 'confidence_boost': 10, 'description': 'MEDIUM'},
            'TEAM_PACE_SPLIT': {'weight': 0.7, 'confidence_boost': 10, 'description': 'MEDIUM'},
            'H2H_TREND': {'weight': 0.3, 'confidence_boost': -10, 'description': 'LOW'},
            'STREAK': {'weight': 0.15, 'confidence_boost': -25, 'description': 'VERY_LOW'},
            'NARRATIVE_SPLIT': {'weight': 0.0, 'confidence_boost': -40, 'description': 'ZERO'}
        }

    def calculate_sample_weight(self, sample_size: int) -> float:
        """
        IMPROVEMENT 1: Sample Size Weighting

        Calculate weight based on sample size to prevent small sample flukes.
        Formula: min(1, n / threshold)

        Examples:
            n=4  -> weight=0.4
            n=10 -> weight=1.0
            n=20 -> weight=1.0
        """
        return min(1.0, sample_size / self.sample_weight_threshold)

    def calculate_composite_confidence(
        self,
        edge_pct: float,
        sample_size: int,
        recency_score: float,
        max_edge: float = 30.0,
        max_sample: int = 30
    ) -> Tuple[float, float, float, float]:
        """
        IMPROVEMENT 2: Composite Confidence Scoring

        Formula: Confidence = (Edge/MaxEdge)*0.4 + (sqrt(n)/sqrt(MaxN))*0.4 + Recency*0.2

        Returns:
            (total_confidence, edge_component, sample_component, recency_component)
        """
        # Edge component (0-40 points)
        edge_component = min(40.0, (abs(edge_pct) / max_edge) * 40.0)

        # Sample component (0-40 points) - using sqrt to avoid over-penalizing medium samples
        sample_component = min(40.0, (math.sqrt(sample_size) / math.sqrt(max_sample)) * 40.0)

        # Recency component (0-20 points)
        recency_component = recency_score * 20.0

        # Total confidence (0-100)
        total_confidence = edge_component + sample_component + recency_component

        return (total_confidence, edge_component, sample_component, recency_component)

    def adjust_edge_for_context(
        self,
        base_edge: float,
        context_factors: ContextFactors
    ) -> float:
        """
        IMPROVEMENT 3: Edge Calculation Enhancement

        Adjust edge based on:
        - Opponent strength (use team ratings if available)
        - Home/away factor
        - Fatigue/schedule effects (back-to-back, days rest)

        Returns:
            Adjusted edge percentage
        """
        adjusted_edge = base_edge

        # Opponent strength adjustment
        if context_factors.opponent_strength is not None:
            # If opponent is strong (>70), reduce edge slightly
            # If opponent is weak (<30), this might inflate edge
            strength_factor = 1.0 - ((context_factors.opponent_strength - 50) / 200.0)
            adjusted_edge *= strength_factor

        # Home/away adjustment
        if context_factors.home_away == "AWAY":
            adjusted_edge *= 0.95  # Slight penalty for away games
        elif context_factors.home_away == "HOME":
            adjusted_edge *= 1.03  # Slight boost for home games

        # Fatigue adjustment
        if context_factors.back_to_back:
            adjusted_edge *= 0.90  # Significant penalty for B2B
        elif context_factors.days_rest is not None and context_factors.days_rest < 1:
            adjusted_edge *= 0.93  # Moderate penalty for low rest
        elif context_factors.days_rest is not None and context_factors.days_rest > 3:
            adjusted_edge *= 1.02  # Small boost for well-rested

        return adjusted_edge

    def calculate_risk_adjusted_ev(
        self,
        standard_ev: float,
        confidence_score: float
    ) -> float:
        """
        IMPROVEMENT 4: Risk-Adjusted EV

        Formula: Risk-Adjusted EV = EV * (Confidence / 100)

        This accounts for uncertainty and prevents small-sample high-edge bets
        from looking overly attractive.
        """
        return standard_ev * (confidence_score / 100.0)

    def calculate_kelly_stake(
        self,
        edge_pct: float,
        bookmaker_odds: float,
        confidence_score: float,
        max_stake_pct: float = 5.0,
        fractional_kelly: float = 0.25
    ) -> float:
        """
        Calculate recommended stake using Kelly Criterion.

        Formula: Stake % = (Edge / Odds) × (Confidence / 100) × Fractional Kelly

        Args:
            edge_pct: Your edge percentage (e.g., 10.5 for 10.5%)
            bookmaker_odds: Decimal odds (e.g., 2.0)
            confidence_score: Confidence score (0-100)
            max_stake_pct: Maximum stake percentage (default 5%)
            fractional_kelly: Kelly fraction (0.25 = quarter Kelly for safety)

        Returns:
            Recommended stake as percentage of bankroll

        Example:
            Edge = 10%, Odds = 2.0, Confidence = 80%
            Stake = (0.10 / 2.0) × 0.80 × 0.25 = 0.01 = 1% of bankroll
        """
        if edge_pct <= 0 or bookmaker_odds <= 1.0:
            return 0.0

        # Convert edge to decimal
        edge_decimal = edge_pct / 100.0

        # Kelly formula: edge / (odds - 1)
        # But we use simplified: edge / odds for conservative estimate
        kelly_pct = (edge_decimal / bookmaker_odds) * (confidence_score / 100.0) * fractional_kelly

        # Convert to percentage and cap at max
        stake_pct = min(kelly_pct * 100, max_stake_pct)

        # Don't recommend stakes below 0.1%
        if stake_pct < 0.1:
            return 0.0

        return round(stake_pct, 2)

    def get_market_variance(self, market_type: str) -> MarketVariance:
        """
        IMPROVEMENT 5: Market-Specific Adjustments

        Different markets have different variances and predictability.
        Returns market-specific variance profile.
        """
        profile = self.market_variances.get(market_type, self.market_variances['Default'])

        return MarketVariance(
            market_type=market_type,
            base_variance=profile['variance'],
            confidence_multiplier=profile['confidence_mult']
        )

    def calculate_recent_streak(self, outcomes: List[int], window: int = 8) -> str:
        """
        IMPROVEMENT 7: Presentation Enhancement

        Calculate and format recent streak information.
        Example: "5 of last 8 games were Over"
        """
        if not outcomes or len(outcomes) < 3:
            return None

        recent = outcomes[-window:] if len(outcomes) >= window else outcomes
        hits = sum(recent)
        total = len(recent)

        return f"{hits} of last {total} games hit"

    def calculate_historical_variance(self, outcomes: List[int]) -> float:
        """
        Calculate variance in historical outcomes.
        Higher variance = less consistency
        """
        if len(outcomes) < 2:
            return 0.0

        try:
            return statistics.variance(outcomes)
        except:
            return 0.0

    def detect_duplicates(self, analyzed_bets: List[Dict]) -> List[Dict]:
        """
        IMPROVEMENT 6: Duplicate/Conflicting Bet Detection

        Detect duplicate games and resolve by selecting highest risk-adjusted EV.

        Args:
            analyzed_bets: List of bet analysis dicts

        Returns:
            Deduplicated list with best bet per game
        """
        # Group by game (extract teams from market/insight)
        games = {}

        for bet in analyzed_bets:
            # Try to extract game identifier
            market = bet.get('market', '')
            insight = bet.get('insight', {}).get('fact', '')

            # Simple team extraction (can be improved)
            game_key = self._extract_game_key(market, insight)

            if game_key not in games:
                games[game_key] = []

            games[game_key].append(bet)

        # For each game, keep only the bet with highest risk-adjusted EV
        deduplicated = []

        for game_key, bets in games.items():
            if len(bets) == 1:
                deduplicated.append(bets[0])
            else:
                # Sort by risk-adjusted EV
                best_bet = max(bets, key=lambda b: b.get('analysis', {}).get('risk_adjusted_ev', 0))
                deduplicated.append(best_bet)

        return deduplicated

    def _extract_game_key(self, market: str, insight: str) -> str:
        """
        Extract game identifier from market/insight text.
        Returns a key like "Lakers-Jazz" for grouping.
        """
        # Simple implementation - can be enhanced
        text = (market + " " + insight).lower()

        # List of common team names (expand as needed)
        teams = [
            'lakers', 'warriors', 'celtics', 'heat', 'bucks', 'nets',
            'suns', 'jazz', 'nuggets', 'clippers', 'mavericks', 'sixers',
            'hawks', 'knicks', 'bulls', 'raptors', 'cavaliers', 'pacers'
        ]

        found_teams = [team for team in teams if team in text]

        if len(found_teams) >= 2:
            return f"{found_teams[0]}-{found_teams[1]}"
        elif len(found_teams) == 1:
            return found_teams[0]
        else:
            return market or insight or "unknown"

    def classify_trend_type(self, insight_fact: str, market: str = "") -> str:
        """
        Classify the trend type to determine its predictive quality.

        Returns:
            Trend type key for quality weights
        """
        fact_lower = insight_fact.lower()
        market_lower = market.lower()

        # NARRATIVE_SPLIT (zero predictive value) - after OT, after leading at halftime, etc.
        narrative_indicators = ['after overtime', 'after leading', 'after trailing', 'when leading',
                               'when trailing', 'in overtime', 'following a win', 'following a loss']
        if any(ind in fact_lower for ind in narrative_indicators):
            return 'NARRATIVE_SPLIT'

        # STREAK (very low) - team/player win/loss streaks
        streak_indicators = ['won each of their last', 'lost each of their last', 'have won',
                           'have lost', 'winning streak', 'losing streak', 'team has won', 'team has lost']
        # Check if it's about wins/losses (not player stats)
        is_win_loss = any(ind in fact_lower for ind in streak_indicators)
        has_player_stats = any(stat in fact_lower for stat in ['scored', 'recorded', 'made', 'points', 'assists', 'rebounds'])
        if is_win_loss and not has_player_stats:
            return 'STREAK'

        # H2H_TREND (low) - head-to-head, opponent-specific
        h2h_indicators = ['against the', 'vs the', 'versus', 'matchup', 'all-time', 'in his career against']
        if any(ind in fact_lower for ind in h2h_indicators):
            return 'H2H_TREND'

        # TEAM_PACE_SPLIT (medium) - team pace, tempo, total points trends
        pace_indicators = ['total points', 'total match points', 'pace', 'tempo', 'gone over', 'gone under']
        if any(ind in fact_lower for ind in pace_indicators) or 'over/under' in market_lower:
            return 'TEAM_PACE_SPLIT'

        # PLAYER_USAGE_SPLIT (medium) - player stats with context (home/road, vs conference)
        usage_indicators = ['home', 'road', 'away', 'vs east', 'vs west', 'as underdog', 'as favorite']
        if any(ind in fact_lower for ind in usage_indicators) and ('scored' in fact_lower or 'recorded' in fact_lower or 'made' in fact_lower):
            return 'PLAYER_USAGE_SPLIT'

        # PLAYER_STATS_FLOOR (high) - player-specific outcome trends (points, assists, rebounds)
        player_indicators = ['scored', 'recorded', 'made', 'points', 'assists', 'rebounds', 'three', 'field goal']
        if any(ind in fact_lower for ind in player_indicators):
            return 'PLAYER_STATS_FLOOR'

        # Default to medium if unclear
        return 'PLAYER_USAGE_SPLIT'

    def apply_sample_size_regression(
        self,
        historical_prob: float,
        sample_size: int,
        league_avg: Optional[float] = None
    ) -> float:
        """
        Apply Bayesian sample size regression to prevent overweighting small samples.

        Formula: Adjusted_P = (Historical_P * (n / threshold)) + (League_Avg * (1 - n/threshold))

        This prevents 5/5 or 6/6 from being treated as "100% locked".

        Args:
            historical_prob: Raw historical win rate
            sample_size: Number of games in sample
            league_avg: League average for this prop type (defaults to 0.50)

        Returns:
            Regressed probability
        """
        if league_avg is None:
            league_avg = self.league_avg_probability

        # Calculate regression weight based on sample size
        regression_weight = min(1.0, sample_size / self.regression_threshold)

        # Apply Bayesian regression
        adjusted_prob = (historical_prob * regression_weight) + (league_avg * (1 - regression_weight))

        return adjusted_prob

    def analyze_with_context(
        self,
        historical_outcomes: List[int],
        bookmaker_odds: float,
        recent_outcomes: Optional[List[int]] = None,
        historical_minutes: Optional[List[float]] = None,
        recent_minutes: Optional[List[float]] = None,
        min_minutes_threshold: float = 15.0,
        context_factors: Optional[ContextFactors] = None,
        player_name: Optional[str] = None,
        insight_fact: Optional[str] = None,
        market: Optional[str] = None
    ) -> ContextAwareAnalysis:
        """
        Perform context-aware value analysis

        Args:
            historical_outcomes: Historical binary outcomes (1=success, 0=fail)
            bookmaker_odds: Current bookmaker odds (decimal)
            recent_outcomes: Recent outcomes (last 3-5 games)
            historical_minutes: Minutes played for each historical game
            recent_minutes: Minutes played in recent games
            min_minutes_threshold: Minimum minutes needed for prop to hit
            context_factors: External context (pace, rest, etc.)
            player_name: Player name for context
        """

        if context_factors is None:
            context_factors = ContextFactors()

        sample_size = len(historical_outcomes)

        # 1. Calculate raw historical probability
        raw_historical_prob = sum(historical_outcomes) / sample_size

        # 2. Apply sample size regression (prevents 5/5 = 100% problem)
        historical_prob = self.apply_sample_size_regression(
            raw_historical_prob,
            sample_size,
            self.league_avg_probability
        )

        # 3. Classify trend type for quality weighting
        trend_type = 'PLAYER_STATS_FLOOR'  # Default
        if insight_fact:
            trend_type = self.classify_trend_type(insight_fact, market or "")

        trend_quality = self.trend_quality_weights.get(trend_type, self.trend_quality_weights['PLAYER_USAGE_SPLIT'])

        # 4. Minutes projection and risk
        minutes_proj = self._analyze_minutes(
            historical_minutes,
            recent_minutes,
            min_minutes_threshold
        )

        # 5. Recency adjustment
        recency_adj = self._calculate_recency_adjustment(
            historical_outcomes,
            recent_outcomes or historical_outcomes[-self.recency_window:]
        )

        # 6. Apply context-based adjustments with trend quality weighting
        # Start with recency-adjusted probability
        adjusted_prob = recency_adj.adjusted_prob

        # Apply trend quality weight (lower quality = pull toward historical more)
        quality_weight = trend_quality['weight']
        adjusted_prob = (adjusted_prob * quality_weight) + (historical_prob * (1 - quality_weight))

        # Apply minutes risk adjustment
        if minutes_proj.benching_risk == "HIGH":
            adjusted_prob *= 0.75  # Reduce probability by 25%
        elif minutes_proj.benching_risk == "MEDIUM":
            adjusted_prob *= 0.90  # Reduce probability by 10%

        # Apply external context
        context_multiplier = context_factors.get_risk_multiplier()
        adjusted_prob *= context_multiplier

        # Ensure probability stays in valid range
        adjusted_prob = max(0.01, min(0.99, adjusted_prob))

        # 5. Calculate value metrics
        bookmaker_prob = 1 / bookmaker_odds
        implied_odds = 1 / adjusted_prob if adjusted_prob > 0 else 999
        raw_edge = (adjusted_prob - bookmaker_prob) * 100

        # IMPROVEMENT 1: Sample Size Weighting for Edge
        sample_weight = self.calculate_sample_weight(sample_size)
        weighted_edge = raw_edge * sample_weight

        # IMPROVEMENT 3: Context-Adjusted Edge
        context_adjusted_edge = self.adjust_edge_for_context(weighted_edge, context_factors)

        # Final value determination
        has_value = context_adjusted_edge > 0
        value_pct = context_adjusted_edge

        # Expected Value (standard formula)
        ev_per_100 = (adjusted_prob * (bookmaker_odds - 1) - (1 - adjusted_prob)) * 100

        # 6. Risk assessment
        risk_score, risk_level = self._calculate_risk(
            minutes_proj,
            recency_adj,
            context_factors,
            sample_size
        )

        # IMPROVEMENT 2: Composite Confidence Scoring
        # Get recency score (0-1) from recency adjustment
        recency_score = min(1.0, max(0.0, recency_adj.confidence / 100.0))

        (composite_confidence, edge_comp, sample_comp, recency_comp) = self.calculate_composite_confidence(
            abs(context_adjusted_edge),
            sample_size,
            recency_score,
            max_edge=30.0,
            max_sample=30
        )

        # IMPROVEMENT 5: Market-Specific Adjustments
        market_variance = self.get_market_variance(market or "Default")
        final_confidence = composite_confidence * market_variance.confidence_multiplier

        # Determine confidence level from score
        if final_confidence >= 75:
            confidence_level = "VERY_HIGH"
        elif final_confidence >= 60:
            confidence_level = "HIGH"
        elif final_confidence >= 40:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        # IMPROVEMENT 4: Risk-Adjusted EV
        risk_adjusted_ev = self.calculate_risk_adjusted_ev(ev_per_100, final_confidence)

        # IMPROVEMENT 7: Streak and Variance Info
        recent_streak = self.calculate_recent_streak(historical_outcomes, window=8)
        historical_variance = self.calculate_historical_variance(historical_outcomes)

        # Kelly Criterion Stake Sizing
        recommended_stake = self.calculate_kelly_stake(
            edge_pct=abs(value_pct),
            bookmaker_odds=bookmaker_odds,
            confidence_score=final_confidence,
            max_stake_pct=5.0,
            fractional_kelly=0.25  # Quarter Kelly for conservative approach
        )

        # 8. Generate recommendation (now includes all enhancements + contextual commentary)
        recommendation, reasons, warnings = self._generate_recommendation(
            has_value,
            value_pct,
            risk_adjusted_ev,  # Use risk-adjusted EV for recommendations
            risk_level,
            confidence_level,
            minutes_proj,
            recency_adj,
            trend_type,
            trend_quality,
            sample_size,
            context_factors=context_factors,
            recent_streak=recent_streak,
            historical_variance=historical_variance
        )

        return ContextAwareAnalysis(
            historical_probability=historical_prob,
            adjusted_probability=adjusted_prob,
            bookmaker_probability=bookmaker_prob,
            bookmaker_odds=bookmaker_odds,
            minutes_projection=minutes_proj,
            recency_adjustment=recency_adj,
            context_factors=context_factors,
            sample_size=sample_size,
            sample_weight=sample_weight,
            weighted_edge=weighted_edge,
            raw_edge=raw_edge,
            confidence_level=confidence_level,
            confidence_score=final_confidence,
            edge_component=edge_comp,
            sample_component=sample_comp,
            recency_component=recency_comp,
            overall_risk=risk_level,
            risk_score=risk_score,
            has_value=has_value,
            value_percentage=value_pct,
            ev_per_100=ev_per_100,
            risk_adjusted_ev=risk_adjusted_ev,
            implied_odds=implied_odds,
            recommended_stake_pct=recommended_stake,
            market_variance=market_variance,
            recent_streak=recent_streak,
            historical_variance=historical_variance,
            recommendation=recommendation,
            reasons=reasons,
            warnings=warnings
        )

    def _analyze_minutes(
        self,
        historical_minutes: Optional[List[float]],
        recent_minutes: Optional[List[float]],
        min_threshold: float
    ) -> MinutesProjection:
        """Analyze minutes projection and benching risk"""

        if not historical_minutes or len(historical_minutes) == 0:
            # No minutes data - assume moderate risk
            return MinutesProjection(
                historical_avg=20.0,
                recent_avg=20.0,
                min_threshold=min_threshold,
                volatility=0,
                benching_risk="MEDIUM",
                risk_score=50
            )

        hist_avg = statistics.mean(historical_minutes)
        recent_avg = statistics.mean(recent_minutes) if recent_minutes else hist_avg

        # Calculate volatility (standard deviation)
        if len(historical_minutes) > 1:
            volatility = statistics.stdev(historical_minutes)
        else:
            volatility = 0

        # Calculate benching risk
        # Count games below threshold
        games_below_threshold = sum(1 for m in historical_minutes if m < min_threshold)
        benching_rate = games_below_threshold / len(historical_minutes)

        # Recent trend
        recent_below = sum(1 for m in (recent_minutes or [])) if recent_minutes else 0
        recent_rate = recent_below / len(recent_minutes) if recent_minutes else 0

        # Risk assessment
        if recent_rate > 0.4 or benching_rate > 0.3 or recent_avg < min_threshold:
            benching_risk = "HIGH"
            risk_score = 75
        elif recent_rate > 0.2 or benching_rate > 0.15 or volatility > 8:
            benching_risk = "MEDIUM"
            risk_score = 50
        else:
            benching_risk = "LOW"
            risk_score = 25

        return MinutesProjection(
            historical_avg=hist_avg,
            recent_avg=recent_avg,
            min_threshold=min_threshold,
            volatility=volatility,
            benching_risk=benching_risk,
            risk_score=risk_score
        )

    def calculate_exponential_decay_weights(
        self,
        outcomes: List[int],
        decay_factor: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate weighted probability using exponential decay.

        Recent games are weighted more heavily than older games.

        Args:
            outcomes: List of outcomes (1=success, 0=fail), oldest to newest
            decay_factor: Decay factor (0.9-0.99). Higher = slower decay.
                         0.95 means each game back is worth 95% of the previous

        Returns:
            (weighted_probability, recency_score)

        Example:
            Last 5 games: [1, 0, 1, 1, 1] (oldest to newest)
            Weights:      [0.81, 0.86, 0.90, 0.95, 1.00]
            Most recent game has weight 1.00, game before 0.95, etc.
        """
        if not outcomes:
            return 0.0, 0.0

        n = len(outcomes)
        weights = []
        weighted_sum = 0.0
        total_weight = 0.0

        # Calculate weights (exponential decay from oldest to newest)
        for i, outcome in enumerate(outcomes):
            # i=0 is oldest, i=n-1 is newest
            games_back = n - 1 - i
            weight = decay_factor ** games_back
            weights.append(weight)

            weighted_sum += outcome * weight
            total_weight += weight

        # Weighted probability
        weighted_prob = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Recency score: how much more recent games contributed
        # Higher score means recent games align with the weighted result
        recent_3 = outcomes[-3:] if len(outcomes) >= 3 else outcomes
        recent_prob = sum(recent_3) / len(recent_3) if recent_3 else 0.5
        recency_score = min(1.0, abs(weighted_prob - recent_prob) / 0.5 + 0.5)

        return weighted_prob, recency_score

    def _calculate_recency_adjustment(
        self,
        historical_outcomes: List[int],
        recent_outcomes: List[int]
    ) -> RecencyAdjustment:
        """
        Calculate recency-weighted probability adjustment using exponential decay.

        Now uses exponential decay to weight recent games more heavily.
        """

        # Use exponential decay for weighted probability
        weighted_prob, recency_score = self.calculate_exponential_decay_weights(
            historical_outcomes,
            decay_factor=0.95
        )

        # Traditional probabilities for comparison
        historical_prob = sum(historical_outcomes) / len(historical_outcomes)
        recent_prob = sum(recent_outcomes) / len(recent_outcomes) if recent_outcomes else historical_prob

        # Use weighted probability as the adjusted probability
        adjusted_prob = weighted_prob

        # Determine trend
        diff = recent_prob - historical_prob
        if diff > 0.15:
            trend = "IMPROVING"
        elif diff < -0.15:
            trend = "DECLINING"
        else:
            trend = "STABLE"

        # Confidence in adjustment based on recent sample size and recency score
        base_confidence = 40
        if len(recent_outcomes) >= 5:
            base_confidence = 80
        elif len(recent_outcomes) >= 3:
            base_confidence = 60

        # Boost confidence if recency score is high (recent trend is strong)
        confidence = min(100, base_confidence + int(recency_score * 20))

        return RecencyAdjustment(
            historical_prob=historical_prob,
            recent_form_prob=recent_prob,
            adjusted_prob=adjusted_prob,
            trend_direction=trend,
            confidence=confidence
        )

    def _calculate_risk(
        self,
        minutes_proj: MinutesProjection,
        recency_adj: RecencyAdjustment,
        context_factors: ContextFactors,
        sample_size: int
    ) -> Tuple[float, str]:
        """Calculate overall risk score and level"""

        risk_score = 0

        # Minutes risk (0-30 points)
        risk_score += minutes_proj.risk_score * 0.3

        # Sample size risk (0-20 points)
        if sample_size < 5:
            risk_score += 20
        elif sample_size < 10:
            risk_score += 10

        # Trend instability (0-20 points)
        if recency_adj.trend_direction in ["IMPROVING", "DECLINING"]:
            risk_score += 15

        # Context risk (0-30 points)
        if context_factors.back_to_back:
            risk_score += 10
        if context_factors.injury_impact in ["HIGH", "MODERATE"]:
            risk_score += 15
        if context_factors.days_rest and context_factors.days_rest < 1:
            risk_score += 5

        # Determine risk level
        if risk_score >= 70:
            risk_level = "VERY_HIGH"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return risk_score, risk_level

    def _calculate_confidence(
        self,
        sample_size: int,
        minutes_proj: MinutesProjection,
        recency_adj: RecencyAdjustment,
        risk_level: str,
        trend_quality: Dict
    ) -> Tuple[float, str]:
        """Calculate confidence in the analysis"""

        confidence_score = 100

        # Sample size penalty (more severe for small samples)
        if sample_size < 5:
            confidence_score -= 50  # Increased from 40
        elif sample_size < 10:
            confidence_score -= 30  # Increased from 20
        elif sample_size < 15:
            confidence_score -= 15  # Increased from 10
        elif sample_size < 20:
            confidence_score -= 5   # New tier

        # Trend quality boost/penalty (critical addition)
        confidence_boost = trend_quality.get('confidence_boost', 0)
        confidence_score += confidence_boost

        # Minutes uncertainty penalty
        if minutes_proj.benching_risk == "HIGH":
            confidence_score -= 25
        elif minutes_proj.benching_risk == "MEDIUM":
            confidence_score -= 10

        # Trend instability penalty
        if recency_adj.trend_direction != "STABLE":
            confidence_score -= 10

        # Risk level penalty
        if risk_level == "VERY_HIGH":
            confidence_score -= 20
        elif risk_level == "HIGH":
            confidence_score -= 10

        confidence_score = max(0, min(100, confidence_score))

        # Determine confidence level
        if confidence_score >= 80:
            confidence_level = "VERY_HIGH"
        elif confidence_score >= 60:
            confidence_level = "HIGH"
        elif confidence_score >= 40:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        return confidence_score, confidence_level

    def _generate_recommendation(
        self,
        has_value: bool,
        value_pct: float,
        ev_per_100: float,
        risk_level: str,
        confidence_level: str,
        minutes_proj: MinutesProjection,
        recency_adj: RecencyAdjustment,
        trend_type: str,
        trend_quality: Dict,
        sample_size: int,
        context_factors: Optional[ContextFactors] = None,
        recent_streak: Optional[str] = None,
        historical_variance: Optional[float] = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        Generate betting recommendation with reasons and warnings.

        Enhanced with contextual commentary about fatigue, injuries, streaks, and variance.
        """

        reasons = []
        warnings = []

        # Trend type warnings/info (critical for user awareness)
        trend_desc = trend_quality.get('description', 'MEDIUM')
        if trend_type == 'NARRATIVE_SPLIT':
            warnings.append(f"NARRATIVE SPLIT trend (ZERO predictive value)")
        elif trend_type == 'STREAK':
            warnings.append(f"STREAK trend (VERY LOW predictive value)")
        elif trend_type == 'H2H_TREND':
            warnings.append(f"Head-to-head trend (LOW predictive value)")
        elif trend_type == 'PLAYER_STATS_FLOOR':
            reasons.append(f"Player stats floor prop (HIGH predictive value)")

        # NEW: Fatigue and rest warnings
        if context_factors:
            if context_factors.back_to_back:
                warnings.append("Back-to-back game - fatigue risk")
            elif context_factors.days_rest is not None:
                if context_factors.days_rest < 1:
                    warnings.append(f"<1 day rest - high fatigue risk")
                elif context_factors.days_rest >= 3:
                    reasons.append(f"{context_factors.days_rest} days rest - well-rested")

            # NEW: Injury impact warnings
            if context_factors.injury_impact == "HIGH":
                warnings.append("HIGH injury impact - key players out")
            elif context_factors.injury_impact == "MODERATE":
                warnings.append("Moderate injury impact - rotation affected")

        # NEW: Streak and consistency commentary
        if recent_streak:
            # Parse streak to determine if it's consistent
            if "of last" in recent_streak:
                parts = recent_streak.split()
                if len(parts) >= 4:
                    hits = int(parts[0])
                    total = int(parts[3])
                    hit_rate = hits / total
                    if hit_rate >= 0.75:
                        reasons.append(f"Strong recent trend: {recent_streak}")
                    elif hit_rate <= 0.25:
                        warnings.append(f"Weak recent trend: {recent_streak}")

        # NEW: Variance commentary (consistency indicator)
        if historical_variance is not None:
            if historical_variance < 0.15:
                reasons.append("Low variance - very consistent outcomes")
            elif historical_variance > 0.35:
                warnings.append("High variance - inconsistent outcomes")

        # Sample size warnings
        if sample_size < 10:
            warnings.append(f"Small sample size (n={sample_size}) - probability regressed to league avg")
        elif sample_size < 20:
            warnings.append(f"Moderate sample size (n={sample_size}) - some regression applied")

        # Analyze value
        if has_value:
            reasons.append(f"+{value_pct:.1f}% edge vs bookmaker")
            reasons.append(f"${ev_per_100:+.2f} EV per $100")
        else:
            warnings.append(f"No value: {value_pct:.1f}% edge")

        # Analyze trend
        if recency_adj.trend_direction == "IMPROVING":
            reasons.append("Recent form is improving")
        elif recency_adj.trend_direction == "DECLINING":
            warnings.append("Recent form is declining")

        # Analyze minutes
        if minutes_proj.benching_risk == "HIGH":
            warnings.append(f"HIGH benching risk (avg {minutes_proj.recent_avg:.1f} min)")
        elif minutes_proj.benching_risk == "MEDIUM":
            warnings.append(f"Moderate benching risk")
        else:
            reasons.append(f"Stable minutes ({minutes_proj.recent_avg:.1f} avg)")

        # Generate recommendation (with strict trend quality filtering)
        # Auto-avoid low-quality trends regardless of apparent "value"
        if trend_type == 'NARRATIVE_SPLIT':
            recommendation = "AVOID"
            warnings.append("Narrative splits have ZERO predictive power - avoiding")
        elif not has_value:
            recommendation = "AVOID"
        elif trend_type == 'STREAK' and confidence_level != "VERY_HIGH":
            recommendation = "AVOID"
            warnings.append("Streaks have very low predictive power - avoiding")
        elif risk_level == "VERY_HIGH":
            recommendation = "PASS"
            warnings.append("Very high risk - suggest avoiding")
        elif risk_level == "HIGH":
            if value_pct > 10 and confidence_level in ["HIGH", "VERY_HIGH"] and trend_type in ['PLAYER_STATS_FLOOR', 'PLAYER_USAGE_SPLIT']:
                recommendation = "CONSIDER"
                warnings.append("High risk but strong value - proceed with caution")
            else:
                recommendation = "PASS"
        elif confidence_level == "LOW":
            recommendation = "PASS"
            warnings.append("Low confidence in analysis")
        elif value_pct > 15 and confidence_level == "VERY_HIGH" and risk_level == "LOW" and trend_type in ['PLAYER_STATS_FLOOR', 'PLAYER_USAGE_SPLIT', 'TEAM_PACE_SPLIT']:
            recommendation = "STRONG BET"
        elif value_pct > 8 and confidence_level in ["HIGH", "VERY_HIGH"] and trend_type != 'H2H_TREND':
            recommendation = "BET"
        elif value_pct > 3 and trend_type in ['PLAYER_STATS_FLOOR', 'PLAYER_USAGE_SPLIT']:
            recommendation = "CONSIDER"
        else:
            recommendation = "PASS"

        return recommendation, reasons, warnings


def format_analysis_report(analysis: ContextAwareAnalysis, player_name: str = "Player") -> str:
    """Format analysis as readable report"""

    lines = []
    lines.append("=" * 70)
    lines.append(f"CONTEXT-AWARE VALUE ANALYSIS: {player_name}")
    lines.append("=" * 70)

    # Recommendation
    rec_emoji = {
        "STRONG BET": "✅",
        "BET": "✓",
        "CONSIDER": "⚠️",
        "PASS": "❌",
        "AVOID": "🛑"
    }

    lines.append(f"\n{rec_emoji.get(analysis.recommendation, '•')} RECOMMENDATION: {analysis.recommendation}")
    lines.append(f"   Confidence: {analysis.confidence_level} ({analysis.confidence_score}/100)")
    lines.append(f"   Risk Level: {analysis.overall_risk} ({analysis.risk_score}/100)")

    # Value metrics
    lines.append(f"\n📊 VALUE METRICS:")
    lines.append(f"   Historical Win Rate: {analysis.historical_probability*100:.1f}%")
    lines.append(f"   Adjusted Win Rate: {analysis.adjusted_probability*100:.1f}%")
    lines.append(f"   Bookmaker Implied: {analysis.bookmaker_probability*100:.1f}%")
    lines.append(f"   Edge: {analysis.value_percentage:+.1f}%")
    lines.append(f"   Expected Value: ${analysis.ev_per_100:+.2f} per $100")

    # Minutes projection
    lines.append(f"\n⏱️  MINUTES PROJECTION:")
    lines.append(f"   Recent Average: {analysis.minutes_projection.recent_avg:.1f} min")
    lines.append(f"   Historical Average: {analysis.minutes_projection.historical_avg:.1f} min")
    lines.append(f"   Volatility: {analysis.minutes_projection.volatility:.1f} min (σ)")
    lines.append(f"   Benching Risk: {analysis.minutes_projection.benching_risk}")

    # Recency adjustment
    lines.append(f"\n📈 RECENT FORM:")
    lines.append(f"   Trend: {analysis.recency_adjustment.trend_direction}")
    lines.append(f"   Recent Form: {analysis.recency_adjustment.recent_form_prob*100:.1f}%")
    lines.append(f"   Historical: {analysis.recency_adjustment.historical_prob*100:.1f}%")
    lines.append(f"   Adjustment Confidence: {analysis.recency_adjustment.confidence}/100")

    # Reasons
    if analysis.reasons:
        lines.append(f"\n✓ SUPPORTING FACTORS:")
        for reason in analysis.reasons:
            lines.append(f"   • {reason}")

    # Warnings
    if analysis.warnings:
        lines.append(f"\n⚠️  WARNINGS:")
        for warning in analysis.warnings:
            lines.append(f"   • {warning}")

    lines.append("\n" + "=" * 70)

    return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    analyzer = ContextAwareAnalyzer()

    # Example: Jonas Valanciunas O8.5 Rebounds vs East opponent
    analysis = analyzer.analyze_with_context(
        historical_outcomes=[1, 1, 0, 1, 1, 0, 1, 1, 1, 0],  # 7/10 = 70%
        recent_outcomes=[1, 0, 1],  # 2/3 = 67%
        historical_minutes=[28, 30, 15, 32, 29, 18, 31, 30, 28, 16],
        recent_minutes=[30, 28, 32],  # Recent avg: 30 min
        bookmaker_odds=1.85,  # Implies 54% probability
        min_minutes_threshold=15.0,
        context_factors=ContextFactors(
            opponent_strength=60,
            home_away="HOME",
            days_rest=1,
            back_to_back=False,
            injury_impact="LOW"
        ),
        player_name="Jonas Valanciunas O8.5 Rebounds"
    )

    print(format_analysis_report(analysis, "Jonas Valanciunas O8.5 Rebounds"))

    print("\n\nJSON Output:")
    import json
    print(json.dumps(analysis.to_dict(), indent=2))
