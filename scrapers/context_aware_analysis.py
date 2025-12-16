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

from typing import List, Dict, Optional, Tuple, Any
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

    # NEW: Clutch and situational factors
    clutch_factor: Optional[float] = None          # Differential: team clutch% - opponent clutch%
    reliability_factor: Optional[float] = None     # Team reliability% - opponent reliability%
    pace_advantage: Optional[float] = None         # Positive if team plays faster
    opponent_def_rating: Optional[float] = None    # Opponent points allowed per game

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

    def get_situational_adjustment(self) -> float:
        """
        Calculate probability adjustment from situational factors (±5-8% max).

        Returns a multiplier adjustment (e.g., 0.05 = +5% to probability)
        """
        adjustment = 0.0

        # Clutch situations (±3% for 20%+ differential)
        if self.clutch_factor and abs(self.clutch_factor) > 15:
            adjustment += (self.clutch_factor / 100) * 0.15

        # Halftime reliability (±2% for 20%+ differential)
        if self.reliability_factor and abs(self.reliability_factor) > 15:
            adjustment += (self.reliability_factor / 100) * 0.10

        # Pace advantage (±2% for 5+ possession difference)
        if self.pace_advantage and abs(self.pace_advantage) > 3:
            adjustment += (self.pace_advantage / 100) * 0.12

        # Defensive matchup (±2.5%)
        if self.opponent_def_rating:
            if self.opponent_def_rating > 115:   # Weak defense
                adjustment += 0.025
            elif self.opponent_def_rating < 105: # Strong defense
                adjustment -= 0.025

        # Cap total at ±8%
        return max(-0.08, min(0.08, adjustment))

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
    risk_adjusted_ev: float  # Properly risk-adjusted EV (Kelly/variance-based)
    implied_odds: float
    
    # NEW: Statistical improvements
    raw_historical_frequency: float  # Raw frequency (k/n) for display
    bayesian_probability: float  # Jeffreys prior: (k+0.5)/(n+1)
    blended_probability: float  # Blended with market probability (70/30 or 50/50)
    confidence_interval_lower: float  # Wilson/Jeffreys lower bound
    confidence_interval_upper: float  # Wilson/Jeffreys upper bound
    kelly_fraction: float  # Kelly fraction for stake sizing
    edge_category: str  # "Strong edge", "Moderate edge", "Weak edge", "No edge"

    # NEW: Final probability used for EV calculations (confidence-weighted blend)
    final_probability: float  # Actual probability used in EV calculation
    probability_source: str   # "market-heavy" | "balanced" | "model-heavy"

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
            'warnings': self.warnings,
            # NEW: Statistical improvements
            'raw_historical_frequency': getattr(self, 'raw_historical_frequency', self.historical_probability),
            'bayesian_probability': getattr(self, 'bayesian_probability', self.historical_probability),
            'blended_probability': getattr(self, 'blended_probability', self.adjusted_probability),
            'confidence_interval_lower': getattr(self, 'confidence_interval_lower', None),
            'confidence_interval_upper': getattr(self, 'confidence_interval_upper', None),
            'kelly_fraction': getattr(self, 'kelly_fraction', 0.0),
            'edge_category': getattr(self, 'edge_category', 'No edge')
        }


class ContextAwareAnalyzer:
    """Enhanced analyzer with context awareness and ALL improvements"""

    def __init__(self):
        self.min_sample_size = 5
        self.recency_window = 5  # Last N games for recent form
        self.recency_weight = 0.3  # Weight for recent vs historical (0.3 = 30% recent, 70% historical)

        # Bayesian regression parameters
        self.regression_threshold = 6.5  # Baseline sample size (6-7) for minimal regression
        self.league_avg_probability = 0.50  # Default prior for most props

        # NEW: Sample size weighting threshold (6-7 is baseline)
        self.sample_weight_threshold = 6.5  # Baseline sample size for full weight

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
            'TEAM_NARRATIVE_TREND': {'weight': 0.3, 'confidence_boost': -20, 'description': 'LOW', 'min_confidence': 60},  # Relaxed: requires 60+ confidence (was 75)
            'H2H_TREND': {'weight': 0.3, 'confidence_boost': -10, 'description': 'LOW'},
            'STREAK': {'weight': 0.15, 'confidence_boost': -25, 'description': 'VERY_LOW'},
            'NARRATIVE_SPLIT': {'weight': 0.0, 'confidence_boost': -40, 'description': 'ZERO'}
        }

    def calculate_sample_weight(self, sample_size: int) -> float:
        """
        IMPROVEMENT 1: Sample Size Weighting

        Calculate weight based on sample size with 6-7 as baseline.
        6-7 gets full weight, larger samples maintain full weight.

        Examples:
            n=4  -> weight=0.6 (below baseline)
            n=6  -> weight=1.0 (baseline)
            n=7  -> weight=1.0 (baseline)
            n=10 -> weight=1.0 (above baseline, full weight)
        """
        if sample_size >= 6:
            return 1.0  # Baseline and above: full weight
        else:
            # Below baseline: scale from 0.5 at n=1 to 1.0 at n=6
            return 0.5 + (sample_size - 1) * (0.5 / 5.0)

    def calculate_confidence_interval(
        self,
        successes: int,
        total: int,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """
        IMPROVEMENT: Fix #2 - Calculate Wilson confidence interval
        
        Uses Wilson score interval which works well for all sample sizes.
        More appropriate than normal approximation for small samples.
        """
        if total == 0:
            return (0.0, 1.0)
        
        k = successes
        n = total
        
        # Wilson score interval
        z = 1.96 if confidence_level == 0.95 else 2.576 if confidence_level == 0.99 else 1.645
        p_hat = k / n
        
        # Wilson score interval formula
        denominator = 1 + (z**2 / n)
        center = (p_hat + (z**2 / (2 * n))) / denominator
        margin = (z / denominator) * math.sqrt((p_hat * (1 - p_hat) / n) + (z**2 / (4 * n**2)))
        
        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)
        
        return (lower, upper)

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

        # Sample component (0-40 points) - penalize below-baseline more aggressively
        if sample_size >= 6:
            # Baseline and above: normal scaling
            sample_component = min(40.0, (math.sqrt(sample_size) / math.sqrt(max_sample)) * 40.0)
        else:
            # Below baseline: heavily penalize
            # n=1: 3, n=2: 6, n=3: 9, n=4: 12, n=5: 18 (vs 30+ for baseline)
            if sample_size <= 3:
                sample_component = sample_size * 3.0
            else:
                # Extra penalty for n=4,5
                sample_component = 9.0 + (sample_size - 3) * 4.5  # n=4: 13.5, n=5: 18
        
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
        adjusted_prob: float,
        bookmaker_odds: float,
        sample_size: int,
        variance: Optional[float] = None,
        confidence_score: float = 50.0
    ) -> float:
        """
        FIX #5: Risk-Adjusted EV must reflect risk
        
        If confidence is 40-50%, EV should be reduced heavily or possibly negative.
        Low confidence = high risk = heavily reduced EV.
        """
        # FIX #5: Confidence-based risk adjustment
        # Low confidence (40-50%) should heavily reduce or make EV negative
        if confidence_score < 40:
            # Very low confidence: Make EV negative or zero
            return min(0.0, standard_ev * 0.1)  # 90% reduction, can go negative
        elif confidence_score < 50:
            # Low confidence: Heavy reduction (70-80% reduction)
            confidence_multiplier = confidence_score / 100.0  # 0.4 to 0.5
            return standard_ev * confidence_multiplier * 0.5  # Additional 50% penalty
        elif confidence_score < 60:
            # Moderate confidence: Moderate reduction
            confidence_multiplier = 0.5 + ((confidence_score - 50) / 10.0) * 0.3  # 0.5 to 0.8
            return standard_ev * confidence_multiplier
        elif confidence_score < 80:
            # Good confidence: Light reduction
            confidence_multiplier = 0.8 + ((confidence_score - 60) / 20.0) * 0.15  # 0.8 to 0.95
            return standard_ev * confidence_multiplier
        else:
            # High confidence: Minimal reduction
            confidence_multiplier = 0.95 + ((confidence_score - 80) / 20.0) * 0.05  # 0.95 to 1.0
            return standard_ev * confidence_multiplier
        
        # Old method (kept as fallback, but confidence-based is primary)
        # Calculate variance if not provided
        if variance is None:
            variance = adjusted_prob * (1 - adjusted_prob)
        
        # Variance penalty
        std_dev = math.sqrt(variance) if variance > 0 else 0.1
        variance_penalty = 1.0 / (1.0 + std_dev * 2.0)
        
        # Sample size penalty
        if sample_size < 20:
            sample_penalty = 0.3  # Heavy penalty for very small samples
        elif sample_size < 30:
            sample_penalty = 0.6  # Moderate penalty
        else:
            sample_penalty = 1.0  # No penalty
        
        # Combine penalties
        risk_adjusted_ev = standard_ev * variance_penalty * sample_penalty
        
        return risk_adjusted_ev
    
    def _calculate_kelly_fraction(
        self,
        probability: float,
        odds: float,
        sample_size: int,
        fractional_kelly: float = 0.25  # Use quarter Kelly for safety
    ) -> float:
        """
        Calculate Kelly fraction: f* = (p*odds - 1) / (odds - 1)
        Then apply fractional Kelly and sample size adjustment
        """
        if odds <= 1.0:
            return 0.0
        
        # Full Kelly fraction
        kelly = (probability * odds - 1.0) / (odds - 1.0)
        
        # Only bet if positive edge
        if kelly <= 0:
            return 0.0
        
        # Apply fractional Kelly (quarter Kelly for safety)
        kelly = kelly * fractional_kelly
        
        # Reduce Kelly for small samples
        if sample_size < 30:
            sample_adjustment = min(1.0, sample_size / 30.0)
            kelly = kelly * sample_adjustment
        
        # Cap at reasonable maximum (5% of bankroll)
        return min(0.05, max(0.0, kelly))

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

    def analyze_correlation(self, analyzed_bets: List[Dict]) -> Dict[str, Any]:
        """
        IMPROVEMENT: Fix #7 - Correlation Analysis for Multiple Bets on Same Game
        
        Identifies games with multiple bets and calculates correlation risk.
        High correlation means if the game goes wrong, all bets fail together.
        
        Returns:
            Dict with correlation warnings and recommendations
        """
        # Group bets by game
        games = {}
        for bet in analyzed_bets:
            game_key = self._extract_game_key(
                bet.get('market', ''),
                bet.get('insight', {}).get('fact', '')
            )
            if game_key not in games:
                games[game_key] = []
            games[game_key].append(bet)
        
        # Find games with multiple bets
        correlated_games = {k: v for k, v in games.items() if len(v) > 1}
        
        warnings = []
        recommendations = []
        
        for game_key, bets in correlated_games.items():
            num_bets = len(bets)
            total_risk_adj_ev = sum(b.get('analysis', {}).get('risk_adjusted_ev', 0) for b in bets)
            
            # High correlation risk if 3+ bets on same game
            if num_bets >= 3:
                warnings.append(
                    f"Game '{game_key}': {num_bets} correlated bets "
                    f"(Total Risk-Adj EV: ${total_risk_adj_ev:.2f}). "
                    f"If game outcome is unexpected, all bets may fail together."
                )
                recommendations.append(
                    f"Consider diversifying: Keep max 2 bets per game, "
                    f"or reduce stake sizes by {min(50, num_bets * 15)}% for correlation risk."
                )
            elif num_bets == 2:
                # Moderate correlation - just note it
                warnings.append(
                    f"Game '{game_key}': 2 bets detected. "
                    f"Consider diversifying across different games/markets."
                )
        
        return {
            'correlated_games': len(correlated_games),
            'total_bets': len(analyzed_bets),
            'warnings': warnings,
            'recommendations': recommendations,
            'correlation_risk': 'HIGH' if len(correlated_games) > 0 and any(len(bets) >= 3 for bets in correlated_games.values()) else 'LOW'
        }

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

        # Check for narrative indicators (after OT, after leading, etc.)
        narrative_indicators = ['after overtime', 'after leading', 'after trailing', 'when leading',
                               'when trailing', 'in overtime', 'following a win', 'following a loss',
                               'after winning', 'after losing']
        has_narrative = any(ind in fact_lower for ind in narrative_indicators)
        
        if has_narrative:
            # Distinguish between team and player narrative trends
            # Team indicators: "they", "their", team names, team outcomes (won/lost games, totals)
            # Player indicators: player names, "he", "his", individual stats (scored, recorded, made)
            is_team_trend = False
            is_player_trend = False
            
            # Check for player indicators (individual stats)
            player_stat_indicators = ['scored', 'recorded', 'made', 'points', 'assists', 'rebounds', 
                                     'steals', 'blocks', 'threes', 'field goals', 'free throws']
            has_player_stats = any(stat in fact_lower for stat in player_stat_indicators)
            
            # Check for team indicators
            team_indicators = ['they', 'their', 'team', 'games', 'won', 'lost', 'total', 'over', 'under']
            has_team_indicators = any(ind in fact_lower for ind in team_indicators)
            
            # If it has player stats, it's a player trend
            if has_player_stats:
                is_player_trend = True
            # If it has team indicators and no player stats, it's likely a team trend
            elif has_team_indicators and not has_player_stats:
                is_team_trend = True
            # Default: if unclear, check for "his" vs "their" pronouns
            elif ' his ' in fact_lower or 'his last' in fact_lower:
                is_player_trend = True
            elif ' their ' in fact_lower or 'their last' in fact_lower:
                is_team_trend = True
            
            # Return appropriate type
            if is_player_trend:
                return 'NARRATIVE_SPLIT'  # Still reject player narrative trends
            elif is_team_trend:
                return 'TEAM_NARRATIVE_TREND'  # Allow team narrative trends with strict confidence
            else:
                # Default to rejecting if unclear
                return 'NARRATIVE_SPLIT'

        # STREAK (very low) - team/player win/loss streaks
        streak_indicators = ['won each of their last', 'lost each of their last', 'have won',
                           'have lost', 'winning streak', 'losing streak', 'team has won', 'team has lost']
        # Check if it's about wins/losses (not player stats)
        is_win_loss = any(ind in fact_lower for ind in streak_indicators)
        has_player_stats = any(stat in fact_lower for stat in ['scored', 'recorded', 'made', 'points', 'assists', 'rebounds'])
        if is_win_loss and not has_player_stats:
            return 'STREAK'

        # H2H_TREND (low) - head-to-head, opponent-specific, not causally meaningful
        h2h_indicators = ['against the', 'vs the', 'versus', 'matchup', 'all-time', 'in his career against']
        if any(ind in fact_lower for ind in h2h_indicators):
            return 'H2H_TREND'

        # Check for conference filters (low-medium predictive value)
        # These should ideally be validated against opponent's actual conference
        # For now, treat as low quality (better than zero)
        conference_indicators = [
            'vs eastern conference', 'vs western conference', 'vs east', 'vs west',
            'eastern conference', 'western conference',
            'against eastern', 'against western', 'east teams', 'west teams'
        ]
        if any(ind in fact_lower for ind in conference_indicators):
            # Conference filters have some predictive value if opponent is from that conference
            # TODO: Validate opponent's actual conference for better accuracy
            return 'TEAM_PACE_SPLIT'  # Medium weight (0.7)

        # Non-predictive indicators (favorites/favourites splits)
        non_predictive_indicators = [
            'as home favorite', 'as home favourites', 'as away favorite',
            'as away favourites', 'as favorite', 'as favourite'
        ]
        if any(ind in fact_lower for ind in non_predictive_indicators):
            # Favorite/underdog splits have zero predictive value
            return 'NARRATIVE_SPLIT'  # Zero weight

        # TEAM_PACE_SPLIT (medium) - team pace, tempo, total points trends
        pace_indicators = ['total points', 'total match points', 'pace', 'tempo', 'gone over', 'gone under']
        if any(ind in fact_lower for ind in pace_indicators) or 'over/under' in market_lower:
            return 'TEAM_PACE_SPLIT'

        # PLAYER_USAGE_SPLIT (medium) - player stats with context (home/road, vs conference)
        # But only if it's about actual performance metrics, not role-based
        usage_indicators = ['home', 'road', 'away']
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

        # Calculate regression weight based on sample size (6-7 is baseline)
        # More aggressive regression for below-baseline samples
        if sample_size >= 6:
            # Baseline and above: minimal regression (90%+ weight on observed)
            regression_weight = 0.9 + min(0.1, (sample_size - 6) * 0.01)
        else:
            # Below baseline: very aggressive regression (only n=5 should reach here)
            # n=5: 0.70 (since n<5 is filtered out)
            regression_weight = 0.25 + (sample_size - 1) * (0.45 / 4.0)
        regression_weight = min(1.0, regression_weight)

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
    ) -> Optional[ContextAwareAnalysis]:
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
        
        # Safety filter: Don't analyze if sample size is below minimum (5)
        if sample_size < self.min_sample_size:
            return None

        # 1. Calculate Bayesian probability using Jeffreys prior (SPECIFICATION)
        # Formula: P_bayesian = (k + 0.5) / (n + 1) where k = successes, n = total
        # This prevents inflated estimates from small sample sizes
        successes = sum(historical_outcomes)
        bayesian_prob = (successes + 0.5) / (sample_size + 1)

        # Store raw frequency for display
        raw_historical_frequency = successes / sample_size if sample_size > 0 else 0.5

        # AGGRESSIVE REGRESSION TO MEAN for extreme probabilities and small samples
        # League average is 50% - extreme probabilities (>75% or <25%) with small samples are unreliable
        LEAGUE_AVERAGE = 0.50

        # Calculate how much to regress based on sample size and extremeness
        if sample_size < 15:
            # Small samples: regress heavily toward 50%
            if bayesian_prob > 0.75 or bayesian_prob < 0.25:
                # Extreme probability with small sample - very unreliable
                regression_weight = 0.70  # 70% toward league average
            elif bayesian_prob > 0.65 or bayesian_prob < 0.35:
                # Moderately extreme
                regression_weight = 0.50  # 50% toward league average
            else:
                # More reasonable
                regression_weight = 0.30  # 30% toward league average
        elif sample_size < 25:
            # Medium samples: moderate regression
            if bayesian_prob > 0.75 or bayesian_prob < 0.25:
                regression_weight = 0.50
            elif bayesian_prob > 0.65 or bayesian_prob < 0.35:
                regression_weight = 0.35
            else:
                regression_weight = 0.20
        else:
            # Large samples: light regression
            if bayesian_prob > 0.80 or bayesian_prob < 0.20:
                regression_weight = 0.30
            elif bayesian_prob > 0.70 or bayesian_prob < 0.30:
                regression_weight = 0.20
            else:
                regression_weight = 0.10

        # Apply regression to mean
        bayesian_prob = (bayesian_prob * (1 - regression_weight)) + (LEAGUE_AVERAGE * regression_weight)
        historical_prob = bayesian_prob

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

        # 4.5. Calculate confidence score early (needed for probability blending later)
        # Calculate variance of outcomes
        outcome_variance = statistics.variance(historical_outcomes) if len(historical_outcomes) > 1 else 0.0

        # Sample size component (0-40 points) - MORE CONSERVATIVE
        if sample_size >= 30:
            sample_score = 40.0  # Large sample
        elif sample_size >= 20:
            sample_score = 30.0  # Good sample
        elif sample_size >= 15:
            sample_score = 22.0  # Moderate sample (reduced from 30)
        elif sample_size >= 10:
            sample_score = 15.0  # Small sample (reduced from 20)
        else:
            sample_score = 8.0  # Very small sample (reduced from 10)

        # Variance component (0-20 points) - lower variance = higher confidence
        variance_score = max(0.0, 20.0 - (outcome_variance * 40.0))

        # Predictive strength of trend (0-20 points) - REDUCED MAX
        # Cap trend score contribution
        trend_score = min(15.0, trend_quality['confidence_boost'] + 10.0)  # Reduced max from 20 to 15

        # Market efficiency (0-10 points) - assume moderate efficiency
        market_efficiency_score = 7.0

        # Team/player stability (0-10 points) - based on minutes consistency
        if minutes_proj.benching_risk == "LOW":
            stability_score = 8.0  # Reduced from 10
        elif minutes_proj.benching_risk == "MEDIUM":
            stability_score = 5.0  # Reduced from 6
        else:
            stability_score = 2.0  # Reduced from 3

        # Calculate base confidence (0-100)
        base_confidence = sample_score + variance_score + trend_score + market_efficiency_score + stability_score

        # AGGRESSIVE CAPS for small samples (fix overconfidence issue)
        if sample_size < 10:
            max_confidence = 60.0  # Very small samples capped at 60
        elif sample_size < 15:
            max_confidence = 70.0  # Small samples capped at 70
        elif sample_size < 20:
            max_confidence = 80.0  # Moderate samples capped at 80
        elif sample_size < 30:
            max_confidence = 90.0  # Good samples capped at 90
        else:
            max_confidence = 100.0  # Large samples can reach 100

        # Apply cap
        final_confidence = min(base_confidence, max_confidence)
        final_confidence = max(0.0, min(100.0, final_confidence))

        # Enforce minimum confidence for TEAM_NARRATIVE_TREND (relaxed requirement)
        if trend_type == 'TEAM_NARRATIVE_TREND':
            min_confidence = trend_quality.get('min_confidence', 60)  # Relaxed from 75
            if final_confidence < min_confidence:
                # Confidence too low for team narrative trends - reject
                final_confidence = 0.0  # Set to 0 to trigger rejection

        # Categorize confidence
        if final_confidence >= 80:
            confidence_level = "VERY_HIGH"  # Large sample, consistent context, low variance
        elif final_confidence >= 60:
            confidence_level = "HIGH"  # Moderate sample or moderate variance
        elif final_confidence >= 40:
            confidence_level = "MEDIUM"  # Small sample or high variance
        else:
            confidence_level = "LOW"  # Unreliable trend; not recommended

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

        # NEW: Apply situational adjustments (clutch, pace, defense)
        situational_adj = context_factors.get_situational_adjustment()
        adjusted_prob = adjusted_prob * (1.0 + situational_adj)

        # Ensure probability stays in valid range
        adjusted_prob = max(0.01, min(0.99, adjusted_prob))

        # 5. Calculate value metrics
        bookmaker_prob = 1 / bookmaker_odds
        implied_odds = 1 / adjusted_prob if adjusted_prob > 0 else 999
        
        # FIX #1 & #2: Start from market odds, adjust slightly
        # UPDATED: Even more conservative blending to prevent inflated probabilities
        # For n < 10: Treat trends as very weak clues (95% market, 5% Bayesian)
        # For n < 15: Still mostly market (92% market, 8% Bayesian)
        # For n < 25: Heavily weight market (85% market, 15% Bayesian)
        # For n < 40: More balanced (70% market, 30% Bayesian)
        # For n >= 40: Trust the data more (50% market, 50% Bayesian)
        # IMPORTANT: Always blend - final prob can NEVER equal raw trend

        if sample_size < 10:
            # Very small sample: 95% market, 5% Bayesian (extremely weak clue)
            w_market = 0.95
            w_bayesian = 0.05
        elif sample_size < 15:
            # Small sample: 92% market, 8% Bayesian
            w_market = 0.92
            w_bayesian = 0.08
        elif sample_size < 25:
            # Below average: 85% market, 15% Bayesian
            w_market = 0.85
            w_bayesian = 0.15
        elif sample_size < 40:
            # Average: 70% market, 30% Bayesian
            w_market = 0.70
            w_bayesian = 0.30
        else:
            # Large sample: 50% market, 50% Bayesian
            w_market = 0.50
            w_bayesian = 0.50
        
        # Calculate adjustment from Bayesian probability
        # Start from market, adjust slightly based on trend
        bayesian_adjustment = bayesian_prob - bookmaker_prob

        # For small samples, make adjustment extremely small
        if sample_size < 10:
            adjustment_multiplier = 0.05  # Only 5% of the difference
        elif sample_size < 15:
            adjustment_multiplier = 0.08  # 8% of the difference
        elif sample_size < 25:
            adjustment_multiplier = 0.15  # 15% of the difference
        elif sample_size < 40:
            adjustment_multiplier = 0.30  # 30% of the difference
        else:
            adjustment_multiplier = 0.50  # 50% of the difference
        
        # Apply small adjustment to market probability
        adjusted_from_market = bookmaker_prob + (bayesian_adjustment * adjustment_multiplier)
        
        # Ensure we always have a blend (never equals raw trend)
        blended_prob = (w_market * bookmaker_prob) + (w_bayesian * bayesian_prob)
        
        # Use the more conservative of the two (the one closer to market)
        blended_prob = min(blended_prob, adjusted_from_market) if bayesian_prob > bookmaker_prob else max(blended_prob, adjusted_from_market)
        
        # Ensure blended_prob is never equal to raw trend (always different)
        if abs(blended_prob - bayesian_prob) < 0.001:
            # Force a blend by moving slightly toward market
            blended_prob = bookmaker_prob * 0.95 + bayesian_prob * 0.05


        # NEW PROBABILITY BLEND: 60% Model + 30% Historical + 10% Market
        # This is the PRIMARY probability calculation - model-driven, not market-heavy
        # Formula: final_prob = (0.6 × adjusted_prob) + (0.3 × historical_prob) + (0.1 × bookmaker_prob)
        # 
        # Rationale:
        # - 60% Model (adjusted_prob): Trust our statistical analysis with adjustments
        # - 30% Historical (historical_prob): Real performance data counts
        # - 10% Market (bookmaker_prob): Slight nod to betting market wisdom
        #
        # NOTE: Archetype caps are applied in the projection model, not here
        
        final_probability = (0.6 * adjusted_prob) + (0.3 * historical_prob) + (0.1 * bookmaker_prob)
        
        # Since we're now model-driven (60%), label as model-heavy
        probability_source = "model-heavy"

        # FIX #3: Cap edges based on sample size (stricter for small samples)
        # NOTE: Use final_probability for edge calculation instead of blended_prob
        raw_edge = (final_probability - bookmaker_prob) * 100

        # Stricter caps based on sample size (updated for better accuracy)
        if sample_size < 10:
            max_edge = 2.5  # Very small samples: max 2.5% edge
        elif sample_size < 15:
            max_edge = 3.5  # Small samples: max 3.5% edge
        elif sample_size < 20:
            max_edge = 4.0  # Below baseline: max 4% edge
        elif sample_size < 30:
            max_edge = 5.0  # Moderate samples: max 5% edge
        else:
            max_edge = 6.0  # Large samples: max 6% edge

        # Apply cap
        capped_edge = max(-max_edge, min(max_edge, raw_edge))
        
        # Categorize edge (for reporting)
        if capped_edge > 6.0:
            edge_category = "Strong edge"
        elif capped_edge > 3.0:
            edge_category = "Moderate edge"
        elif capped_edge > 0.0:
            edge_category = "Weak edge"
        else:
            edge_category = "No edge"

        # IMPROVEMENT 1: Sample Size Weighting for Edge
        sample_weight = self.calculate_sample_weight(sample_size)
        weighted_edge = capped_edge * sample_weight

        # IMPROVEMENT 3: Context-Adjusted Edge
        context_adjusted_edge = self.adjust_edge_for_context(weighted_edge, context_factors)

        # Expected Value (IMPROVEMENT: Fix #4 - Proper EV formula)
        # EV = (p · (odds - 1) - (1 - p)) per unit
        # Use final_probability for EV calculation (confidence-weighted blend)
        ev_per_unit = (final_probability * (bookmaker_odds - 1)) - (1 - final_probability)
        ev_per_100 = ev_per_unit * 100
        
        # Final value determination: Use EV > 0 instead of edge > 0
        # This is more appropriate when using blended probabilities
        # The blended probability already accounts for market efficiency,
        # so if EV is positive, there's value even if edge is small
        has_value = ev_per_100 > 0  # Use EV instead of edge for value detection
        value_pct = context_adjusted_edge  # Still report edge for display

        # 6. Risk assessment
        risk_score, risk_level = self._calculate_risk(
            minutes_proj,
            recency_adj,
            context_factors,
            sample_size
        )

        # Store confidence components for reporting (confidence already calculated earlier)
        edge_comp = 0.0  # Not used in confidence calculation per spec
        sample_comp = sample_score
        recency_comp = 0.0  # Not used per spec

        # Get market variance profile (for reporting)
        market_variance = self.get_market_variance(market or "Default")

        # Calculate confidence intervals
        ci_lower, ci_upper = self.calculate_confidence_interval(successes, sample_size, 0.95)
        
        # FIX #5: Risk-Adjusted EV must reflect risk (use confidence score)
        variance = blended_prob * (1 - blended_prob)
        risk_adjusted_ev = self.calculate_risk_adjusted_ev(
            ev_per_100, 
            blended_prob, 
            bookmaker_odds, 
            sample_size,
            variance,
            final_confidence  # Pass confidence score for proper risk adjustment
        )
        
        # Calculate Kelly fraction for stake sizing
        kelly_frac = self._calculate_kelly_fraction(blended_prob, bookmaker_odds, sample_size)

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
            final_confidence,
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
            warnings=warnings,
            # NEW: Statistical improvements
            raw_historical_frequency=raw_historical_frequency,
            bayesian_probability=bayesian_prob,  # This is the Bayesian probability (k+0.5)/(n+1)
            blended_probability=blended_prob,
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
            kelly_fraction=kelly_frac,
            edge_category=edge_category,
            # NEW: Final probability used for EV calculations
            final_probability=final_probability,
            probability_source=probability_source
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
        final_confidence: float,
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
        elif trend_type == 'TEAM_NARRATIVE_TREND':
            warnings.append(f"TEAM NARRATIVE trend (VERY LOW predictive value - requires 75+ confidence)")
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

        # Sample size warnings (6-7 is baseline)
        if sample_size < 6:
            warnings.append(f"Below baseline sample size (n={sample_size}, baseline=6-7) - reduced confidence")
        elif sample_size < 10:
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
        # Also penalize below-baseline sample sizes (n < 6)
        if trend_type == 'NARRATIVE_SPLIT':
            recommendation = "AVOID"
            warnings.append("Narrative splits have ZERO predictive power - avoiding")
        elif trend_type == 'TEAM_NARRATIVE_TREND' and final_confidence < trend_quality.get('min_confidence', 60):
            recommendation = "AVOID"
            warnings.append(f"Team narrative trend requires minimum {trend_quality.get('min_confidence', 60)} confidence - current: {final_confidence:.0f}")
        elif not has_value:
            recommendation = "AVOID"
        elif sample_size < 6:
            # Below baseline: downgrade recommendation
            if has_value and value_pct > 10 and confidence_level in ["HIGH", "VERY_HIGH"]:
                recommendation = "CONSIDER"  # Can only be CONSIDER at best
                warnings.append(f"Below baseline sample size (n={sample_size}) - downgraded from BET")
            else:
                recommendation = "PASS"
                warnings.append(f"Below baseline sample size (n={sample_size}, baseline=6-7) - insufficient data")
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
        elif value_pct > 10 and confidence_level == "VERY_HIGH" and trend_type == 'TEAM_NARRATIVE_TREND':
            # Team narrative trends need very high confidence and good value
            recommendation = "CONSIDER"
            warnings.append("Team narrative trend - proceed with caution, early value opportunity")
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
