"""
Bet Enhancement System - Advanced Filtering & Display
=====================================================
Implements sophisticated filtering and tier classification for betting recommendations:

1. Quality Tier Classification (S/A/B/C/D)
2. Sample Size Weighting Penalty
3. Conflict Score for Correlated Bets
4. Line Difficulty Filter
5. Market Efficiency Check
6. Consistency Ranking
7. EV-to-Prob Ratio Filter
8. True Fair Odds Display
9. Projected Margin vs Line
10. Auto-Sorting

Usage:
    from bet_enhancement_system import BetEnhancementSystem

    enhancer = BetEnhancementSystem()
    enhanced_bets = enhancer.enhance_recommendations(recommendations)
    enhancer.display_enhanced_bets(enhanced_bets)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class QualityTier(Enum):
    """Quality tiers for betting recommendations"""
    S = "S-Tier (Elite Value)"
    A = "A-Tier (High Quality)"
    B = "B-Tier (Playable)"
    C = "C-Tier (Marginal)"
    D = "D-Tier (Avoid)"


class ConsistencyLevel(Enum):
    """Player consistency classification"""
    HIGH = "🔥 High Consistency"
    MEDIUM = "👍 Medium Consistency"
    LOW = "⚠️ Low Consistency"


@dataclass
class EnhancedBet:
    """Enhanced betting recommendation with all metrics"""
    # Original recommendation data
    original_rec: Dict

    # Core metrics
    player_name: Optional[str] = None
    market: str = ""
    selection: str = ""
    line: Optional[float] = None
    odds: float = 0.0

    # Probabilities & Value
    projected_probability: float = 0.0
    implied_probability: float = 0.0
    edge_percentage: float = 0.0
    expected_value: float = 0.0

    # Enhanced Metrics
    quality_tier: QualityTier = QualityTier.D
    tier_emoji: str = "❌"

    # Sample Size Analysis
    sample_size: int = 0
    sample_size_penalty: float = 0.0
    effective_confidence: float = 0.0

    # Correlation & Conflicts
    correlation_penalty: float = 0.0
    conflict_score: float = 0.0

    # Line Difficulty
    line_difficulty_penalty: float = 0.0

    # Market Efficiency
    market_efficiency_flag: bool = False
    passes_efficiency_check: bool = True

    # Consistency
    consistency_rank: Optional[ConsistencyLevel] = None
    consistency_score: float = 0.0

    # EV Ratio
    ev_to_prob_ratio: float = 0.0
    passes_ev_ratio: bool = True

    # Fair Odds
    fair_odds: float = 0.0
    odds_mispricing: float = 0.0

    # Projection Margin
    projected_value: Optional[float] = None
    projection_margin: float = 0.0

    # Final Scores
    adjusted_confidence: float = 0.0
    final_score: float = 0.0

    # Context
    game: str = ""
    opponent_team: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# BET ENHANCEMENT SYSTEM
# ============================================================================

class BetEnhancementSystem:
    """
    Comprehensive bet enhancement system with advanced filtering and classification
    """

    def __init__(self):
        # Quality tier thresholds
        self.tier_thresholds = {
            'S': {'ev_min': 20.0, 'edge_min': 12.0, 'prob_min': 0.68},
            'A': {'ev_min': 10.0, 'edge_min': 8.0},
            'B': {'ev_min': 5.0, 'edge_min': 4.0},
            'C': {'ev_min': 1.0, 'conf_min': 70.0},
        }

        # Sample size baseline
        self.sample_baseline = 5

        # Line difficulty thresholds
        self.high_line_threshold = 30.0
        self.extreme_line_threshold = 35.0

        # Market efficiency thresholds
        self.low_edge_threshold = 3.0
        self.sharp_prob_range = (0.55, 0.60)
        self.high_confidence_override = 85.0

        # EV ratio threshold
        self.min_ev_ratio = 0.08

        # Consistency thresholds
        self.high_consistency_threshold = 0.80
        self.medium_consistency_threshold = 0.60

    def enhance_recommendations(self, recommendations: List[Dict]) -> List[EnhancedBet]:
        """
        Apply all enhancements to betting recommendations

        Args:
            recommendations: List of betting recommendation dicts

        Returns:
            List of EnhancedBet objects with all metrics calculated
        """
        enhanced_bets = []

        # First pass: create enhanced bet objects
        for rec in recommendations:
            enhanced = self._create_enhanced_bet(rec)
            enhanced_bets.append(enhanced)

        # Second pass: calculate correlation penalties (requires all bets)
        self._calculate_correlation_penalties(enhanced_bets)

        # Third pass: recalculate final scores with all adjustments
        for bet in enhanced_bets:
            self._calculate_final_score(bet)

        # Sort by quality
        enhanced_bets = self._sort_bets(enhanced_bets)

        return enhanced_bets

    def _create_enhanced_bet(self, rec: Dict) -> EnhancedBet:
        """Create enhanced bet from recommendation dict"""
        # Extract core data
        player_name = rec.get('player_name')
        market = rec.get('market', '')
        selection = rec.get('selection', '')
        line = rec.get('line')
        odds = rec.get('odds', 0.0)

        # Extract metrics
        proj_prob = rec.get('projected_probability', 0.0)
        impl_prob = rec.get('implied_probability', 0.0)
        edge = rec.get('edge_percentage', 0.0)
        ev = rec.get('expected_value', 0.0)
        confidence = rec.get('confidence_score', 0.0)

        # Create base enhanced bet
        bet = EnhancedBet(
            original_rec=rec,
            player_name=player_name,
            market=market,
            selection=selection,
            line=line,
            odds=odds,
            projected_probability=proj_prob,
            implied_probability=impl_prob,
            edge_percentage=edge,
            expected_value=ev,
            game=rec.get('game', ''),
            opponent_team=rec.get('opponent_team'),
            sample_size=rec.get('sample_size', 0),
            projected_value=rec.get('projected_value')
        )

        # Apply enhancements
        self._classify_quality_tier(bet, confidence)
        self._calculate_sample_size_penalty(bet, confidence)
        self._calculate_line_difficulty_penalty(bet)
        self._check_market_efficiency(bet, confidence)
        self._calculate_consistency_rank(bet)
        self._calculate_ev_ratio(bet)
        self._calculate_fair_odds(bet)
        self._calculate_projection_margin(bet)

        return bet

    def _classify_quality_tier(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 1. Classify bet into quality tier (S/A/B/C/D)

        Tiers:
        - S-Tier: EV ≥ +20 AND Edge ≥ +12% AND Prob ≥ 68%
        - A-Tier: EV ≥ +10 AND Edge ≥ +8%
        - B-Tier: EV ≥ +5 AND Edge ≥ +4%
        - C-Tier: EV ≥ +1 OR Confidence ≥ 70
        - D-Tier: EV < 0 OR Prob < 50%
        """
        ev = bet.expected_value
        edge = bet.edge_percentage
        prob = bet.projected_probability

        # D-Tier (Avoid)
        if ev < 0 or prob < 0.50:
            bet.quality_tier = QualityTier.D
            bet.tier_emoji = "❌"
            return

        # S-Tier (Elite)
        if ev >= 20.0 and edge >= 12.0 and prob >= 0.68:
            bet.quality_tier = QualityTier.S
            bet.tier_emoji = "💎"
            bet.notes.append("ELITE VALUE: All metrics exceed premium thresholds")
            return

        # A-Tier (High Quality)
        if ev >= 10.0 and edge >= 8.0:
            bet.quality_tier = QualityTier.A
            bet.tier_emoji = "⭐"
            return

        # B-Tier (Playable)
        if ev >= 5.0 and edge >= 4.0:
            bet.quality_tier = QualityTier.B
            bet.tier_emoji = "✓"
            return

        # C-Tier (Marginal)
        if ev >= 1.0 or confidence >= 70.0:
            bet.quality_tier = QualityTier.C
            bet.tier_emoji = "~"
            return

        # Default to D-Tier
        bet.quality_tier = QualityTier.D
        bet.tier_emoji = "❌"

    def _calculate_sample_size_penalty(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 2. Calculate sample size weighting penalty

        Formula: effective_confidence = confidence - (5 - sample_size) * 4  if sample_size < 5

        Examples:
        - n=5 → zero penalty
        - n=3 → minus 8 confidence points
        - n=1 → minus 16 confidence points
        """
        n = bet.sample_size

        if n >= self.sample_baseline:
            bet.sample_size_penalty = 0.0
            bet.effective_confidence = confidence
        else:
            # Penalty: (5 - n) * 4
            penalty = (self.sample_baseline - n) * 4.0
            bet.sample_size_penalty = penalty
            bet.effective_confidence = max(0.0, confidence - penalty)

            if penalty > 0:
                bet.warnings.append(f"Small sample penalty: -{penalty:.0f} confidence points (n={n})")

    def _calculate_correlation_penalties(self, bets: List[EnhancedBet]):
        """
        ✅ 3. Calculate conflict score for correlated bets

        Penalties:
        - Same team AND same stat: -12 confidence
        - Same game AND same stat: -6 confidence
        - Otherwise: 0
        """
        for i, bet in enumerate(bets):
            max_penalty = 0.0
            conflicts = []

            for j, other in enumerate(bets):
                if i == j:
                    continue

                # Check correlation
                same_game = bet.game == other.game
                player_team = bet.original_rec.get('player_team')
                other_team = other.original_rec.get('player_team')

                # Only check team correlation if both teams are known
                same_team = (player_team == other_team and
                            player_team not in [None, 'Unknown', ''] and
                            other_team not in [None, 'Unknown', ''])

                same_stat = self._extract_stat_type(bet.market) == self._extract_stat_type(other.market)

                penalty = 0.0

                if same_team and same_stat and bet.player_name and other.player_name:
                    penalty = -12.0
                    conflicts.append(f"Same team ({player_team}) + stat ({self._extract_stat_type(bet.market)})")
                elif same_game and same_stat and bet.player_name and other.player_name:
                    penalty = -6.0
                    conflicts.append(f"Same game + stat ({self._extract_stat_type(bet.market)})")

                max_penalty = min(max_penalty, penalty)  # Most negative

            bet.correlation_penalty = max_penalty
            bet.conflict_score = abs(max_penalty)

            if conflicts:
                bet.warnings.append(f"Correlation detected: {conflicts[0]}")

    def _extract_stat_type(self, market: str) -> str:
        """Extract stat type from market string"""
        market_lower = market.lower()

        if 'point' in market_lower or 'pts' in market_lower:
            return 'points'
        elif 'assist' in market_lower or 'ast' in market_lower:
            return 'assists'
        elif 'rebound' in market_lower or 'reb' in market_lower:
            return 'rebounds'
        elif 'three' in market_lower or '3' in market_lower:
            return 'threes'
        elif 'steal' in market_lower or 'stl' in market_lower:
            return 'steals'
        elif 'block' in market_lower or 'blk' in market_lower:
            return 'blocks'

        return market_lower

    def _calculate_line_difficulty_penalty(self, bet: EnhancedBet):
        """
        ✅ 4. Calculate line difficulty penalty

        Harder lines (30+, 35+) get penalized:
        - Line ≥ 30: -5 penalty
        - Line ≥ 35: -10 penalty
        """
        if bet.line is None:
            bet.line_difficulty_penalty = 0.0
            return

        line = bet.line

        if line >= self.extreme_line_threshold:
            bet.line_difficulty_penalty = -10.0
            bet.warnings.append(f"Extreme line ({line}) - very volatile")
        elif line >= self.high_line_threshold:
            bet.line_difficulty_penalty = -5.0
            bet.warnings.append(f"High line ({line}) - increased volatility")
        else:
            bet.line_difficulty_penalty = 0.0

    def _check_market_efficiency(self, bet: EnhancedBet, confidence: float):
        """
        ✅ 5. Market efficiency check override

        If edge < 3% AND prob between 55-60%:
            hide unless confidence > 85
        """
        edge = bet.edge_percentage
        prob = bet.projected_probability

        # Check if in sharp market zone
        in_sharp_zone = (self.sharp_prob_range[0] <= prob <= self.sharp_prob_range[1])
        low_edge = edge < self.low_edge_threshold

        if in_sharp_zone and low_edge:
            bet.market_efficiency_flag = True

            if confidence <= self.high_confidence_override:
                bet.passes_efficiency_check = False
                bet.warnings.append(f"Sharp market: Edge {edge:.1f}% < {self.low_edge_threshold}% in efficient zone")
            else:
                bet.passes_efficiency_check = True
                bet.notes.append(f"Overrides efficiency check with {confidence:.0f}% confidence")
        else:
            bet.passes_efficiency_check = True

    def _calculate_consistency_rank(self, bet: EnhancedBet):
        """
        ✅ 6. Calculate consistency rank

        consistency = 1 - (standard_deviation / season_average)

        Levels:
        - High: 0.80+
        - Medium: 0.60-0.80
        - Low: <0.60
        """
        # Try to get stats from databallr_stats
        stats = bet.original_rec.get('databallr_stats', {})
        avg = stats.get('avg_value', 0)

        # Estimate std dev if not available (assume CV of 25%)
        std_dev = avg * 0.25 if avg > 0 else 0

        # Calculate consistency
        if avg > 0:
            consistency = 1.0 - (std_dev / avg)
            consistency = max(0.0, min(1.0, consistency))
            bet.consistency_score = consistency

            if consistency >= self.high_consistency_threshold:
                bet.consistency_rank = ConsistencyLevel.HIGH
            elif consistency >= self.medium_consistency_threshold:
                bet.consistency_rank = ConsistencyLevel.MEDIUM
            else:
                bet.consistency_rank = ConsistencyLevel.LOW
                bet.warnings.append(f"Low consistency ({consistency:.1%}) - volatile player")
        else:
            bet.consistency_rank = None
            bet.consistency_score = 0.0

    def _calculate_ev_ratio(self, bet: EnhancedBet):
        """
        ✅ 7. Calculate EV-to-Prob ratio

        EV_ratio = EV / probability

        Filter out: EV_ratio < 0.08
        """
        if bet.projected_probability > 0:
            bet.ev_to_prob_ratio = bet.expected_value / (bet.projected_probability * 100)
        else:
            bet.ev_to_prob_ratio = 0.0

        if bet.ev_to_prob_ratio < self.min_ev_ratio:
            bet.passes_ev_ratio = False
            bet.warnings.append(f"Low EV/Prob ratio ({bet.ev_to_prob_ratio:.3f} < {self.min_ev_ratio})")
        else:
            bet.passes_ev_ratio = True

    def _calculate_fair_odds(self, bet: EnhancedBet):
        """
        ✅ 8. Calculate true fair odds

        Fair Odds = 1 / Probability
        Mispricing = Market Odds - Fair Odds
        """
        if bet.projected_probability > 0:
            bet.fair_odds = 1.0 / bet.projected_probability
            bet.odds_mispricing = bet.odds - bet.fair_odds
        else:
            bet.fair_odds = 0.0
            bet.odds_mispricing = 0.0

    def _calculate_projection_margin(self, bet: EnhancedBet):
        """
        ✅ 9. Calculate projected margin vs line

        projection_margin = projected - line
        """
        if bet.projected_value is not None and bet.line is not None:
            bet.projection_margin = bet.projected_value - bet.line

            if bet.projection_margin > 0:
                bet.notes.append(f"Projected {bet.projection_margin:+.1f} vs line")
        else:
            bet.projection_margin = 0.0

    def _calculate_final_score(self, bet: EnhancedBet):
        """
        Calculate final adjusted confidence with all penalties applied
        """
        # Start with effective confidence (after sample size penalty)
        score = bet.effective_confidence

        # Apply correlation penalty
        score += bet.correlation_penalty

        # Apply line difficulty penalty
        score += bet.line_difficulty_penalty

        # Store final adjusted confidence
        bet.adjusted_confidence = max(0.0, min(100.0, score))

        # Calculate final score for sorting (weights different factors)
        bet.final_score = (
            bet.adjusted_confidence * 0.4 +
            bet.expected_value * 2.0 +
            bet.edge_percentage * 3.0 +
            bet.projected_probability * 50.0
        )

    def _sort_bets(self, bets: List[EnhancedBet]) -> List[EnhancedBet]:
        """
        ✅ 10. Auto-sorting rules

        Sort by:
        1. Tier (S > A > B > C > D)
        2. EV (descending)
        3. Edge (descending)
        4. Adjusted Confidence (descending)
        5. Projection Margin (descending)
        """
        tier_order = {
            QualityTier.S: 0,
            QualityTier.A: 1,
            QualityTier.B: 2,
            QualityTier.C: 3,
            QualityTier.D: 4
        }

        return sorted(bets, key=lambda b: (
            tier_order[b.quality_tier],
            -b.expected_value,
            -b.edge_percentage,
            -b.adjusted_confidence,
            -b.projection_margin
        ))

    def filter_bets(self, bets: List[EnhancedBet],
                   min_tier: QualityTier = QualityTier.C,
                   exclude_d_tier: bool = True) -> List[EnhancedBet]:
        """
        Filter bets based on quality tier and efficiency checks

        Args:
            bets: List of enhanced bets
            min_tier: Minimum tier to include
            exclude_d_tier: Exclude D-Tier bets

        Returns:
            Filtered list of bets
        """
        tier_order = {
            QualityTier.S: 0,
            QualityTier.A: 1,
            QualityTier.B: 2,
            QualityTier.C: 3,
            QualityTier.D: 4
        }

        min_tier_value = tier_order[min_tier]

        filtered = []
        for bet in bets:
            # Check tier
            if tier_order[bet.quality_tier] > min_tier_value:
                continue

            # Exclude D-Tier if requested
            if exclude_d_tier and bet.quality_tier == QualityTier.D:
                continue

            # Check efficiency
            if not bet.passes_efficiency_check:
                continue

            # Check EV ratio
            if not bet.passes_ev_ratio:
                continue

            filtered.append(bet)

        return filtered

    def display_enhanced_bets(self, bets: List[EnhancedBet], max_display: int = 20):
        """
        Display enhanced bets with all metrics in a readable format
        """
        print("=" * 100)
        print("ENHANCED BETTING RECOMMENDATIONS")
        print("=" * 100)
        print()

        # Group by tier
        tiers = {}
        for bet in bets:
            tier = bet.quality_tier
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(bet)

        # Display by tier
        for tier in [QualityTier.S, QualityTier.A, QualityTier.B, QualityTier.C, QualityTier.D]:
            if tier not in tiers:
                continue

            tier_bets = tiers[tier][:max_display]

            if not tier_bets:
                continue

            print(f"\n{'='*100}")
            print(f"{tier.value} ({len(tier_bets)} bets)")
            print(f"{'='*100}\n")

            for i, bet in enumerate(tier_bets, 1):
                self._display_single_bet(bet, i)
                print()

    def _display_single_bet(self, bet: EnhancedBet, index: int):
        """Display a single enhanced bet"""
        print(f"{index}. {bet.tier_emoji} {bet.player_name or 'TEAM'} - {bet.market} {bet.selection}")
        print(f"   Game: {bet.game}")

        if bet.opponent_team:
            print(f"   Matchup: vs {bet.opponent_team}")

        # Odds & Fair Value
        print(f"   Odds: {bet.odds:.2f} → Fair: {bet.fair_odds:.2f} (Mispricing: {bet.odds_mispricing:+.2f})")

        # Value Metrics
        print(f"   Edge: {bet.edge_percentage:+.1f}% | EV: {bet.expected_value:+.1f}% | EV/Prob: {bet.ev_to_prob_ratio:.3f}")

        # Probabilities
        print(f"   Projected: {bet.projected_probability:.1%} | Implied: {bet.implied_probability:.1%}")

        # Confidence
        print(f"   Confidence: {bet.adjusted_confidence:.0f}% (Base: {bet.effective_confidence:.0f}%, Sample: n={bet.sample_size})")

        # Projection Margin
        if bet.projected_value and bet.line:
            print(f"   Projection: {bet.projected_value:.1f} vs Line {bet.line:.1f} (Margin: {bet.projection_margin:+.1f})")

        # Consistency
        if bet.consistency_rank:
            print(f"   Consistency: {bet.consistency_rank.value} ({bet.consistency_score:.1%})")

        # Penalties
        if bet.sample_size_penalty != 0:
            print(f"   Sample Penalty: {bet.sample_size_penalty:.0f} points")
        if bet.correlation_penalty != 0:
            print(f"   Correlation Penalty: {bet.correlation_penalty:.0f} points")
        if bet.line_difficulty_penalty != 0:
            print(f"   Line Difficulty: {bet.line_difficulty_penalty:.0f} points")

        # Notes
        if bet.notes:
            print(f"   Notes:")
            for note in bet.notes:
                print(f"     ✓ {note}")

        # Warnings
        if bet.warnings:
            print(f"   Warnings:")
            for warning in bet.warnings:
                print(f"     ⚠ {warning}")


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == '__main__':
    import json

    # Load recommendations
    try:
        with open('betting_recommendations.json', 'r') as f:
            recommendations = json.load(f)
    except FileNotFoundError:
        print("No betting_recommendations.json found. Run nba_betting_system.py first.")
        exit(1)

    print(f"Loaded {len(recommendations)} recommendations")

    # Enhance
    enhancer = BetEnhancementSystem()
    enhanced_bets = enhancer.enhance_recommendations(recommendations)

    # Filter to quality bets only
    quality_bets = enhancer.filter_bets(enhanced_bets, min_tier=QualityTier.C, exclude_d_tier=True)

    print(f"After filtering: {len(quality_bets)} quality bets (C-Tier or better)\n")

    # Display
    enhancer.display_enhanced_bets(quality_bets, max_display=15)

    # Save enhanced bets
    enhanced_output = []
    for bet in quality_bets:
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

    with open('betting_recommendations_enhanced.json', 'w') as f:
        json.dump(enhanced_output, f, indent=2, default=str)

    print("\n✓ Saved enhanced recommendations to betting_recommendations_enhanced.json")
