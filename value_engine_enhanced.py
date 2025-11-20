"""
Enhanced Value Engine - v2 with Team Stats Integration
=======================================================
Integrates team-level statistics from Sportsbet Stats & Insights:
- Records: avg points for/against, margins, total match points
- Performance: favorite/underdog records, night records
- Under Pressure: clutch win %, reliability %, comeback %, choke %

Features:
- Bayesian shrinkage for small samples
- Sample size weighting
- Recency weighting with exponential decay
- Regression to mean
- Volatility adjustment
- Team-form adjustments for match markets
- Projected totals from team scoring stats
- Favorite/underdog probability adjustments
- Clutch situation modifiers

Usage:
    from value_engine_enhanced import EnhancedValueEngine

    engine = EnhancedValueEngine()

    # With team stats
    analysis = engine.analyze_with_team_stats(
        historical_outcomes=[1, 1, 0, 1, 1, 0, 1],
        bookmaker_odds=1.85,
        team_a_stats=away_team_stats,  # From Sportsbet
        team_b_stats=home_team_stats,  # From Sportsbet
        market_type='match',
        is_favourite=True
    )
"""

import math
import numpy as np
from typing import List, Optional, Dict, Union
from dataclasses import dataclass, asdict
from enum import Enum


# -----------------------------
# Configuration / Constants
# -----------------------------

BAYESIAN_PRIOR_ALPHA = 1.0
BAYESIAN_PRIOR_BETA = 1.0
SAMPLE_WEIGHT_BASE = 20.0
LEAGUE_AVG = 0.5
VOLATILITY_SHRINK = 1.0
REGRESSION_SHRINK_N = 10.0


# -----------------------------
# Enums
# -----------------------------

class MarketType(Enum):
    MATCH = "match"           # Moneyline / match winner
    TOTAL = "total"           # Over/Under
    HANDICAP = "handicap"     # Point spread
    PROP = "prop"             # Player props


# -----------------------------
# Data Classes
# -----------------------------

@dataclass
class TeamStats:
    """Team statistics from Sportsbet Stats & Insights"""
    team_name: str

    # Records
    avg_points_for: Optional[float] = None
    avg_points_against: Optional[float] = None
    avg_winning_margin: Optional[float] = None
    avg_losing_margin: Optional[float] = None
    avg_total_points: Optional[float] = None

    # Performance
    favorite_win_pct: Optional[float] = None
    underdog_win_pct: Optional[float] = None
    night_win_pct: Optional[float] = None

    # Under Pressure
    clutch_win_pct: Optional[float] = None
    reliability_pct: Optional[float] = None
    comeback_pct: Optional[float] = None
    choke_pct: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EnhancedValueAnalysis:
    """Enhanced analysis result with team stats integration"""
    # Core metrics
    sample_size: int
    historical_probability: float
    adjusted_probability: float
    bookmaker_probability: float
    bookmaker_odds: float

    # Probabilities breakdown
    raw_probability: float
    bayesian_probability: float
    recency_probability: float
    regressed_probability: float

    # Adjustments
    team_form_adjustment: float = 0.0
    favorite_underdog_adjustment: float = 0.0
    total_projection_adjustment: float = 0.0
    volatility_multiplier: float = 1.0

    # Value metrics
    has_value: bool = False
    value_percentage: float = 0.0
    edge_in_odds: float = 0.0
    ev_per_unit: float = 0.0
    ev_per_100: float = 0.0

    # Confidence
    confidence_score: float = 0.0
    sample_weight: float = 0.0
    market_agreement: float = 0.5

    # Context
    market_type: Optional[str] = None
    projected_total: Optional[float] = None
    market_line: Optional[float] = None

    # Notes
    analysis_notes: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.analysis_notes is None:
            self.analysis_notes = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self) -> str:
        lines = [
            f"Sample Size: {self.sample_size}",
            f"",
            f"PROBABILITIES:",
            f"  Raw Historical: {self.raw_probability*100:.1f}%",
            f"  Bayesian Adjusted: {self.bayesian_probability*100:.1f}%",
            f"  Recency Weighted: {self.recency_probability*100:.1f}%",
            f"  Regressed to Mean: {self.regressed_probability*100:.1f}%",
            f"  Final Adjusted: {self.adjusted_probability*100:.1f}%",
            f"  Bookmaker Implied: {self.bookmaker_probability*100:.1f}%",
            f"",
            f"ADJUSTMENTS:",
            f"  Team Form: {self.team_form_adjustment:+.3f}",
            f"  Fav/Underdog: {self.favorite_underdog_adjustment:+.3f}",
            f"  Volatility: {self.volatility_multiplier:.3f}x",
        ]

        if self.projected_total:
            lines.append(f"  Projected Total: {self.projected_total:.1f} (line: {self.market_line:.1f})")

        lines.extend([
            f"",
            f"VALUE:",
            f"  Edge: {self.value_percentage:+.1f}%",
            f"  EV per $100: ${self.ev_per_100:+.2f}",
            f"  Has Value: {self.has_value}",
            f"",
            f"CONFIDENCE: {self.confidence_score:.1f}/100",
        ])

        if self.warnings:
            lines.append(f"\nWARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.analysis_notes:
            lines.append(f"\nNOTES:")
            for note in self.analysis_notes:
                lines.append(f"  - {note}")

        return "\n".join(lines)


# -----------------------------
# Helper Functions
# -----------------------------

def bayesian_shrinkage(wins: int, n: int,
                       prior_alpha: float = BAYESIAN_PRIOR_ALPHA,
                       prior_beta: float = BAYESIAN_PRIOR_BETA) -> float:
    """
    Apply Bayesian shrinkage using Beta distribution.
    Prevents overconfidence in small samples.
    """
    return (wins + prior_alpha) / (n + prior_alpha + prior_beta)


def sample_size_weight(n: int, base: float = SAMPLE_WEIGHT_BASE) -> float:
    """
    Calculate weight based on sample size using logarithmic scaling.
    Returns value between 0 and 1.
    """
    if n <= 0:
        return 0.0
    return min(1.0, math.log(n + 1) / math.log(base + 1))


def regression_to_mean(observed_p: float, n: int,
                       league_avg: float = LEAGUE_AVG,
                       shrink_n: float = REGRESSION_SHRINK_N) -> float:
    """
    Regress observed probability toward league average based on sample size.
    Larger samples = less regression.
    """
    w = min(1.0, n / (shrink_n + 1e-9))
    return observed_p * w + league_avg * (1 - w)


def recency_weighted_prob(values: np.ndarray,
                         days_ago: Optional[np.ndarray] = None,
                         decay_rate: float = 0.9) -> float:
    """
    Calculate probability with exponential decay for recency.
    More recent outcomes get higher weight.
    """
    if len(values) == 0:
        return LEAGUE_AVG

    values = np.asarray(values)

    if days_ago is None:
        # Exponential decay: most recent = highest weight
        weights = np.array([decay_rate ** i for i in range(len(values)-1, -1, -1)])
    else:
        # Weight by inverse of days ago
        days_ago = np.asarray(days_ago)
        weights = 1.0 / (days_ago + 1.0)

    weights = weights / weights.sum()
    return float((values * weights).sum())


def volatility_adjustment(p: float) -> float:
    """
    Adjust confidence based on probability volatility.
    Probabilities near 0.5 have highest variance -> lower confidence.
    """
    variance = p * (1 - p)
    multiplier = 1.0 - (variance / 0.25) * 0.5
    return max(0.5, min(1.0, multiplier))


def odds_to_prob(odds: float) -> float:
    """Convert decimal odds to probability"""
    if odds <= 0:
        return 0.0
    return 1.0 / odds


def prob_to_odds(prob: float) -> Optional[float]:
    """Convert probability to decimal odds"""
    if prob <= 0 or prob >= 1:
        return None
    return 1.0 / prob


def compute_ev(perceived_p: float, odds: float, stake: float = 100.0) -> float:
    """Calculate expected value"""
    return stake * (perceived_p * (odds - 1.0) - (1.0 - perceived_p))


# -----------------------------
# Team Stats Integration
# -----------------------------

def calculate_form_score(team_stats: TeamStats) -> float:
    """
    Calculate a team form score from their stats.
    Higher = better recent form.
    """
    if not team_stats:
        return 0.0

    pf = team_stats.avg_points_for or 0.0
    pa = team_stats.avg_points_against or 0.0

    # Net points = offensive - defensive
    return pf - pa


def form_adjustment(team_a_stats: TeamStats, team_b_stats: TeamStats) -> float:
    """
    Calculate probability adjustment based on team form differential.
    Returns adjustment to add to base probability (-0.1 to +0.1).
    """
    if not team_a_stats or not team_b_stats:
        return 0.0

    a_form = calculate_form_score(team_a_stats)
    b_form = calculate_form_score(team_b_stats)

    # Form differential
    diff = a_form - b_form

    # Each 1 point advantage -> 0.6% probability increase
    # Cap at ±10% adjustment
    adjustment = diff * 0.006
    return float(max(-0.10, min(0.10, adjustment)))


def favorite_underdog_adjustment(team_stats: TeamStats, is_favourite: bool) -> float:
    """
    Adjust probability based on team's historical favorite/underdog performance.
    Returns adjustment to add to base probability.
    """
    if not team_stats:
        return 0.0

    if is_favourite:
        record = team_stats.favorite_win_pct
    else:
        record = team_stats.underdog_win_pct

    if record is None:
        return 0.0

    # Convert percentage to decimal if needed
    if record > 1.0:
        record = record / 100.0

    # Map record (0..1) to adjustment (-0.08 to +0.08)
    # 50% record = no adjustment
    # 70% record = +3.2% adjustment
    # 30% record = -3.2% adjustment
    adjustment = (record - 0.5) * 0.16
    return float(max(-0.08, min(0.08, adjustment)))


def clutch_adjustment(team_stats: TeamStats, is_close_game: bool) -> float:
    """
    Adjust for clutch performance in close games.
    """
    if not is_close_game or not team_stats or team_stats.clutch_win_pct is None:
        return 0.0

    clutch_pct = team_stats.clutch_win_pct
    if clutch_pct > 1.0:
        clutch_pct = clutch_pct / 100.0

    # Strong clutch teams get boost in close games
    adjustment = (clutch_pct - 0.5) * 0.12
    return float(max(-0.06, min(0.06, adjustment)))


def project_total_from_team_stats(team_a_stats: TeamStats,
                                   team_b_stats: TeamStats) -> Optional[float]:
    """
    Project total points for the matchup using team stats.
    """
    if not team_a_stats or not team_b_stats:
        return None

    # Method 1: Use avg_total_points if available
    if team_a_stats.avg_total_points is not None and team_b_stats.avg_total_points is not None:
        return (team_a_stats.avg_total_points + team_b_stats.avg_total_points) / 2.0

    # Method 2: Project from points for/against
    a_pf = team_a_stats.avg_points_for
    a_pa = team_a_stats.avg_points_against
    b_pf = team_b_stats.avg_points_for
    b_pa = team_b_stats.avg_points_against

    if any(x is None for x in [a_pf, a_pa, b_pf, b_pa]):
        return None

    # Weighted projection: what A scores vs B's defense, plus what B scores vs A's defense
    a_projected_score = (a_pf * 0.6) + (b_pa * 0.4)
    b_projected_score = (b_pf * 0.6) + (a_pa * 0.4)

    return a_projected_score + b_projected_score


def total_market_adjustment(projected_total: float, market_line: float) -> float:
    """
    Adjust over/under probability based on projected total vs market line.
    """
    diff = projected_total - market_line

    # Each point difference -> 1.5% probability shift
    # E.g., projected 220, line 215 -> +7.5% to OVER
    adjustment = diff * 0.015
    return float(max(-0.15, min(0.15, adjustment)))


# -----------------------------
# Enhanced Value Engine
# -----------------------------

class EnhancedValueEngine:
    """
    Enhanced value engine with team stats integration.
    """

    def __init__(self):
        self.league_avg = LEAGUE_AVG
        self.sample_weight_base = SAMPLE_WEIGHT_BASE
        self.regression_shrink_n = REGRESSION_SHRINK_N

    def analyze_with_team_stats(
        self,
        historical_outcomes: List[int],
        bookmaker_odds: float,
        team_a_stats: Optional[TeamStats] = None,
        team_b_stats: Optional[TeamStats] = None,
        market_type: str = "match",
        is_favourite: bool = False,
        market_line: Optional[float] = None,
        is_close_game: bool = False,
        days_ago: Optional[List[int]] = None,
        context: Optional[Dict] = None
    ) -> EnhancedValueAnalysis:
        """
        Perform enhanced value analysis with team stats integration.

        Args:
            historical_outcomes: List of binary outcomes (1=success, 0=fail)
            bookmaker_odds: Current bookmaker decimal odds
            team_a_stats: TeamStats for team A (usually the team you're betting on)
            team_b_stats: TeamStats for opponent
            market_type: "match", "total", "handicap", or "prop"
            is_favourite: Whether team A is favored
            market_line: For totals/handicap markets (e.g., 237.5 for O/U)
            is_close_game: Whether this is expected to be close (for clutch adjustment)
            days_ago: Days since each outcome (for recency weighting)
            context: Additional context dict

        Returns:
            EnhancedValueAnalysis with complete breakdown
        """
        if context is None:
            context = {}

        n = len(historical_outcomes)
        wins = sum(historical_outcomes)

        notes = []
        warnings = []

        # 1. Raw probability
        raw_p = wins / n if n > 0 else self.league_avg

        # 2. Bayesian shrinkage (prevents 5/5 = 100% problem)
        bayes_p = bayesian_shrinkage(wins, n)

        # 3. Recency weighting
        outcomes_array = np.array(historical_outcomes)
        days_array = np.array(days_ago) if days_ago else None
        recency_p = recency_weighted_prob(outcomes_array, days_array)

        # 4. Combine with sample size weighting
        w = sample_size_weight(n, self.sample_weight_base)
        observed_p = w * recency_p + (1 - w) * bayes_p

        # 5. Regression to mean
        regressed_p = regression_to_mean(observed_p, n, self.league_avg, self.regression_shrink_n)

        # 6. Start with regressed probability
        adjusted_p = regressed_p

        # Track adjustments
        team_form_adj = 0.0
        fav_dog_adj = 0.0
        total_proj_adj = 0.0
        projected_total = None

        # 7. Apply team-specific adjustments based on market type
        if market_type.lower() == "match" or market_type.lower() == "moneyline":
            # Match market: use form and favorite/underdog adjustments
            if team_a_stats and team_b_stats:
                team_form_adj = form_adjustment(team_a_stats, team_b_stats)
                adjusted_p = max(0.0, min(1.0, adjusted_p + team_form_adj))
                notes.append(f"Form adjustment: {team_form_adj:+.3f}")

            # Favorite/underdog adjustment
            if team_a_stats:
                fav_dog_adj = favorite_underdog_adjustment(team_a_stats, is_favourite)
                adjusted_p = max(0.0, min(1.0, adjusted_p + fav_dog_adj))
                notes.append(f"Fav/Dog adjustment: {fav_dog_adj:+.3f}")

            # Clutch adjustment if close game
            if team_a_stats and is_close_game:
                clutch_adj = clutch_adjustment(team_a_stats, is_close_game)
                adjusted_p = max(0.0, min(1.0, adjusted_p + clutch_adj))
                notes.append(f"Clutch adjustment: {clutch_adj:+.3f}")

        elif market_type.lower() == "total" and market_line is not None:
            # Total market: compare projected total to line
            if team_a_stats and team_b_stats:
                projected_total = project_total_from_team_stats(team_a_stats, team_b_stats)

                if projected_total is not None:
                    total_proj_adj = total_market_adjustment(projected_total, market_line)
                    adjusted_p = max(0.0, min(1.0, adjusted_p + total_proj_adj))
                    notes.append(f"Projected total: {projected_total:.1f} vs line {market_line:.1f}")
                    notes.append(f"Total adjustment: {total_proj_adj:+.3f}")

        # 8. Calculate volatility multiplier
        vol_mult = volatility_adjustment(adjusted_p)

        # 9. Calculate bookmaker probability and value
        bookmaker_p = odds_to_prob(bookmaker_odds)
        value_pct = (adjusted_p - bookmaker_p) * 100
        has_value = adjusted_p > bookmaker_p

        # 10. Calculate EV
        ev_per_unit = compute_ev(adjusted_p, bookmaker_odds, stake=1.0)
        ev_per_100 = compute_ev(adjusted_p, bookmaker_odds, stake=100.0)

        # Apply volatility to EV
        ev_per_unit *= vol_mult
        ev_per_100 *= vol_mult

        # 11. Calculate confidence
        market_agreement = context.get('market_agreement', 0.5)
        confidence = self._compute_confidence(n, adjusted_p, recency_p, market_agreement)

        # 12. Add warnings for risky situations
        if n < 5:
            warnings.append(f"Very small sample size (n={n})")
        if n < 10:
            warnings.append(f"Small sample - probability heavily regressed")
        if team_a_stats and team_a_stats.choke_pct and team_a_stats.choke_pct > 25:
            warnings.append(f"Team has {team_a_stats.choke_pct:.1f}% choke rate")
        if abs(value_pct) > 20:
            warnings.append(f"Extreme value detected - verify data quality")

        return EnhancedValueAnalysis(
            sample_size=n,
            historical_probability=raw_p,
            adjusted_probability=adjusted_p,
            bookmaker_probability=bookmaker_p,
            bookmaker_odds=bookmaker_odds,
            raw_probability=raw_p,
            bayesian_probability=bayes_p,
            recency_probability=recency_p,
            regressed_probability=regressed_p,
            team_form_adjustment=team_form_adj,
            favorite_underdog_adjustment=fav_dog_adj,
            total_projection_adjustment=total_proj_adj,
            volatility_multiplier=vol_mult,
            has_value=has_value,
            value_percentage=value_pct,
            edge_in_odds=bookmaker_odds - prob_to_odds(adjusted_p) if prob_to_odds(adjusted_p) else 0,
            ev_per_unit=ev_per_unit,
            ev_per_100=ev_per_100,
            confidence_score=confidence,
            sample_weight=w,
            market_agreement=market_agreement,
            market_type=market_type,
            projected_total=projected_total,
            market_line=market_line,
            analysis_notes=notes,
            warnings=warnings
        )

    def _compute_confidence(
        self,
        n: int,
        perceived_p: float,
        recency_score: float,
        market_agreement: float
    ) -> float:
        """Calculate confidence score (0-100)"""
        w_n = sample_size_weight(n, self.sample_weight_base)
        volatility = 1.0 - volatility_adjustment(perceived_p)

        # Weighted combination
        base = 0.6 * w_n + 0.3 * recency_score + 0.1 * market_agreement

        # Penalize high volatility
        confidence = base * (1.0 - 0.4 * volatility)

        return float(max(0.0, min(100.0, confidence * 100.0)))


# -----------------------------
# Example Usage
# -----------------------------

if __name__ == '__main__':
    print("="*70)
    print("  ENHANCED VALUE ENGINE - DEMO")
    print("="*70)
    print()

    # Create engine
    engine = EnhancedValueEngine()

    # Example team stats (from Sportsbet)
    lakers_stats = TeamStats(
        team_name="Lakers",
        avg_points_for=113.1,
        avg_points_against=113.4,
        avg_total_points=226.5,
        avg_winning_margin=13.2,
        avg_losing_margin=13.8,
        favorite_win_pct=60.0,
        underdog_win_pct=40.0,
        clutch_win_pct=50.0
    )

    warriors_stats = TeamStats(
        team_name="Warriors",
        avg_points_for=116.3,
        avg_points_against=111.8,
        avg_total_points=228.1,
        avg_winning_margin=14.5,
        avg_losing_margin=10.5,
        favorite_win_pct=62.5,
        underdog_win_pct=50.0,
        clutch_win_pct=33.3
    )

    # Test 1: Match market
    print("TEST 1: Match Market (Lakers vs Warriors)")
    print("-"*70)
    analysis = engine.analyze_with_team_stats(
        historical_outcomes=[1, 1, 0, 1, 1, 0, 1, 1],  # 6/8 = 75%
        bookmaker_odds=1.85,  # Implies 54%
        team_a_stats=lakers_stats,
        team_b_stats=warriors_stats,
        market_type="match",
        is_favourite=True
    )
    print(analysis)
    print()

    # Test 2: Total market
    print("\nTEST 2: Total Market (Over 237.5)")
    print("-"*70)
    analysis2 = engine.analyze_with_team_stats(
        historical_outcomes=[1, 1, 1, 1, 1],  # 5/5 = 100% raw
        bookmaker_odds=1.9,
        team_a_stats=lakers_stats,
        team_b_stats=warriors_stats,
        market_type="total",
        market_line=237.5
    )
    print(analysis2)
    print()

    print("="*70)
    print("  Demonstrates:")
    print("  [+] Sample size regression (5/5 not treated as 100%)")
    print("  [+] Team form adjustments from stats")
    print("  [+] Projected totals from team scoring")
    print("  [+] Favorite/underdog historical records")
    print("  [+] Comprehensive probability breakdown")
    print("="*70)
