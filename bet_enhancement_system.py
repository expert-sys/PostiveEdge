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

import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from enum import Enum

# PHASE 8: Import QA Validator for pre-display validation
try:
    from scrapers.qa_validator import QAValidator
except ImportError:
    logger.warning("QA Validator not available - validation will be limited")
    QAValidator = None
import math
from scrapers.nba_stats_api_scraper import get_player_game_log, GameLogEntry
from scrapers.player_projection_model import PlayerProjectionModel
from scrapers.statmuse_player_scraper import scrape_player_game_log

# Initialize global model instance to avoid reloading every time
_GLOBAL_PROJECTION_MODEL = None

def _get_model():
    global _GLOBAL_PROJECTION_MODEL
    if _GLOBAL_PROJECTION_MODEL is None:
        _GLOBAL_PROJECTION_MODEL = PlayerProjectionModel()
    return _GLOBAL_PROJECTION_MODEL


# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class QualityTier(Enum):
    """Quality tiers for betting recommendations"""
    S = "S-Tier (Elite Value)"
    A = "A-Tier (High Quality)"
    B = "B-Tier (Playable)"
    C = "C-Tier (Do Not Bet - Pass)"
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
    historical_hit_rate: float = 0.0 # Historical hit rate %
    market: str = ""
    selection: str = ""
    line: Optional[float] = None
    odds: float = 0.0

    # Probabilities & Value
    projected_probability: float = 0.0
    calibrated_probability: float = 0.0  # PHASE 1: Single source of truth probability
    implied_probability: float = 0.0
    edge_percentage: float = 0.0
    expected_value: float = 0.0
    adjusted_ev: float = 0.0 # EV scaled by confidence
    confidence_score: float = 0.0  # PHASE 6: New confidence formula (0-100)

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

    # Minutes Stability
    minutes_stability_penalty: float = 0.0
    minutes_variance: float = 0.0
    minutes_volatility_score: float = 0.0  # NEW: 0-10 scale
    minutes_volatility_label: str = ""     # NEW: Very Stable, Stable, etc.

    # Injury / Role Change (NEW)
    role_change_detected: bool = False
    role_change_type: str = ""  # "increased_usage", "decreased_usage", "teammate_out", "TEMPORARY_SPIKE"
    role_change_impact: float = 0.0  # % projection adjustment

    # Player Archetype (PHASE 2)
    archetype_name: str = ""  # "Elite Star", "Starter", "Bench Scorer", etc.
    archetype_cap: float = 0.82  # Max probability for this archetype
    correlation_multiplier: float = 1.0  # PHASE 4: EV multiplier from correlation (0.85-1.0)

    # Line Efficiency (shaded lines)
    line_shaded: bool = False
    line_movement: float = 0.0
    expected_line_movement: str = ""  # NEW: "OVER", "UNDER", "STABLE"
    line_movement_urgency: str = ""   # NEW: "BET_NOW", "MONITOR", "WAIT"

    # Sharp/Public Indicator (NEW)
    sharp_public_indicator: str = ""  # "SHARP_OVER", "PUBLIC_OVER", "BALANCED"
    betting_pressure: str = ""  # "Heavy Over", "Heavy Under", "Balanced"

    # Final Scores
    adjusted_confidence: float = 0.0
    final_score: float = 0.0

    # Context
    game: str = ""
    player_team: Optional[str] = None
    opponent_team: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Advanced Context (restored for display)
    advanced_context: Optional[Dict] = field(default_factory=dict)
    matchup_factors: Optional[Dict] = field(default_factory=dict)


# ============================================================================
# BET ENHANCEMENT SYSTEM
# ============================================================================

class BetEnhancementSystem:
    """
    Comprehensive bet enhancement system with advanced filtering and classification
    """

    def __init__(self):
        # Quality tier thresholds (RELAXED for more bets)
        self.tier_thresholds = {
            'S': {'ev_min': 12.0, 'edge_min': 8.0, 'prob_min': 0.65},
            'A': {'ev_min': 6.0, 'edge_min': 4.0},
            'B': {'ev_min': 2.0, 'edge_min': 1.5},
            'C': {'ev_min': 0.0, 'conf_min': 50.0},
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

        # Third pass: check for excessive correlation and downgrade to C-tier if needed
        self._check_excessive_correlation(enhanced_bets)

        # Fourth pass: recalculate final scores with all adjustments
        for bet in enhanced_bets:
            self._calculate_final_score(bet)

        # PHASE 8: Fifth pass - COMPREHENSIVE QA VALIDATION (CRITICAL)
        # Use QA Validator for complete mathematical consistency checks
        # Using lenient mode (strict_mode=False) for more bets to pass through
        if QAValidator:
            validator = QAValidator(strict_mode=False)
            validated_bets = validator.validate_batch(enhanced_bets)
        else:
            # Fallback to basic validation if QA Validator not available
            validated_bets = []
            blocked_count = 0
            for bet in enhanced_bets:
                if self._validate_probability_consistency(bet):
                    validated_bets.append(bet)
                else:
                    blocked_count += 1

            if blocked_count > 0:
                logger.warning(f"QA: Blocked {blocked_count} bet(s) due to probability inconsistency")

        # Sort by quality
        validated_bets = self._sort_bets(validated_bets)

        return validated_bets

    def _create_enhanced_bet(self, rec: Dict) -> EnhancedBet:
        """Create enhanced bet from recommendation dict"""
        # Extract core data - handle both nested (insight/analysis) and flat structures
        insight = rec.get('insight', {})
        analysis = rec.get('analysis', {})

        # Handle Unified Analysis keys (player vs player_name, etc.)
        player_name = rec.get('player_name') or rec.get('player')

        # Smart market string generation
        # Try insight first (for team bets), then top level (for player props)
        raw_market = insight.get('market') or rec.get('market')
        stat = rec.get('stat', '')
        prediction = rec.get('prediction', '')
        line_val = str(rec.get('line', ''))

        if raw_market:
            market = raw_market
        else:
            # Avoid dupes like "Points Over 25.0 OVER"
            if prediction.upper() in stat.upper():
                market = f"{stat} {line_val}"
            else:
                market = f"{stat} {prediction} {line_val}"

        # Extract selection from insight or rec
        selection = insight.get('result') or rec.get('selection') or rec.get('prediction', '')
        line = rec.get('line')

        # Extract odds from insight or rec
        odds = insight.get('odds') or rec.get('odds', 0.0)

        # CRITICAL FIX: For player props, use projection model's calibrated_prob
        # Check if this is a player prop with projection model data
        is_player_prop = rec.get('_bet_type') == 'player_prop'
        has_projection_model = analysis.get('calibrated_prob') is not None

        if is_player_prop and has_projection_model:
            # USE PROJECTION MODEL'S CALIBRATED PROBABILITY (single source of truth)
            proj_prob = analysis.get('projected_prob', 0.0)  # Raw model probability
            calibrated_prob = analysis.get('calibrated_prob', 0.0)  # Archetype-capped probability
            archetype_name = analysis.get('archetype_name', '')
            archetype_cap = analysis.get('archetype_cap', 0.82)
        else:
            # For team bets, use market-heavy blended probability
            proj_prob = (analysis.get('final_probability') or
                        analysis.get('adjusted_probability') or
                        rec.get('projected_probability') or
                        rec.get('final_prob') or
                        rec.get('projected_prob') or 0.0)
            calibrated_prob = proj_prob  # No separate calibration for team bets
            archetype_name = ''
            archetype_cap = 0.82

        impl_prob = (analysis.get('bookmaker_probability') or
                    analysis.get('market_probability') or
                    rec.get('implied_probability', 0.0))

        edge = (analysis.get('value_percentage') or
               rec.get('edge_percentage') or
               rec.get('edge', 0.0))

        ev = (analysis.get('ev_per_100') or
             rec.get('expected_value') or
             rec.get('ev_per_100', 0.0))

        confidence = (analysis.get('confidence_score') or
                     rec.get('confidence_score') or
                     rec.get('confidence', 0.0))

        sample_size = (analysis.get('sample_size') or
                      rec.get('sample_size', 0))

        # Safe extraction helper
        def _safe_get(obj, key, default=0.0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        historical_hit_rate = (_safe_get(rec, 'historical_hit_rate') or 
                              _safe_get(rec, 'historical_prob'))

        # FALLBACK: Calculate using model if missing and we have player/market info
        # If player_name is missing (common in team_bets/insights), try using selection
        calc_player_name = player_name or selection
        
        if (historical_hit_rate == 0.0 or historical_hit_rate is None) and calc_player_name and market:
            try:
                import re
                # Simple extraction logic (simplified version of unified_pipeline logic)
                stat_type = ''
                line = 0.0
                
                market_lower = market.lower()
                patterns = [
                    (r'(\d+)\+?\s*points?', 'points'),
                    (r'(\d+)\+?\s*rebounds?', 'rebounds'),
                    (r'(\d+)\+?\s*assists?', 'assists'),
                    (r'(\d+)\+?\s*steals?', 'steals'),
                    (r'(\d+)\+?\s*blocks?', 'blocks'),
                    (r'(\d+)\+?\s*threes?', 'three_pt_made'),
                ]
                
                for pattern, s_type in patterns:
                    match = re.search(pattern, market_lower)
                    if match:
                        line = float(match.group(1))
                        stat_type = s_type
                        break
                        
                if stat_type and line > 0:
                    model = _get_model()
                    games = []
                    
                    
                    # PRIORITY 1: Try StatMuse (User requested primary source)
                    try:
                        sm_logs = scrape_player_game_log(calc_player_name, season="2024-25")
                        
                        if sm_logs:
                            # Convert StatMuse logs to GameLogEntry format for model
                            for sm in sm_logs:
                                entry = GameLogEntry(
                                    game_date=sm.date,
                                    game_id="", # Dummy
                                    matchup=f"{'vs' if sm.home_away == 'HOME' else '@'} {sm.opponent}",
                                    home_away=sm.home_away,
                                    opponent=sm.opponent,
                                    opponent_id=0,
                                    won=(sm.win_loss == 'W'),
                                    minutes=sm.minutes,
                                    points=sm.points,
                                    rebounds=sm.rebounds,
                                    assists=sm.assists,
                                    steals=sm.steals,
                                    blocks=sm.blocks,
                                    turnovers=sm.turnovers,
                                    fg_made=sm.fg_made,
                                    fg_attempted=sm.fg_attempted,
                                    three_pt_made=sm.three_made,
                                    three_pt_attempted=sm.three_attempted,
                                    ft_made=sm.ft_made,
                                    ft_attempted=sm.ft_attempted
                                )
                                games.append(entry)
                            logger.info(f"  ✓ StatMuse returned {len(games)} games")
                        else:
                            logger.info("  StatMuse returned no games, falling back...")
                    except Exception as e:
                        logger.warning(f"  StatMuse scraping failed: {e}")
                    
                    # PRIORITY 2: Fallback into DataballR (via legacy nba_stats_api wrapper)
                    if not games:
                        logger.info(f"  Falling back to DataballR for {calc_player_name}...")
                        games = get_player_game_log(calc_player_name, season="2024-25")

                    # Run Projection if we have games
                    if games and len(games) >= 5:
                        # Ensure games are objects (GameLogEntry) not dicts
                        if isinstance(games[0], dict):
                            try:
                                games = [GameLogEntry(**g) for g in games]
                            except Exception:
                                pass # Try best effort

                        try:
                            proj = model.project_stat(calc_player_name, stat_type, games, line)
                            if proj:
                                historical_hit_rate = proj.historical_hit_rate
                                logger.info(f"  [Fix] Calculated missing history for {calc_player_name}: {historical_hit_rate:.1%}")
                        except Exception as e:
                            print(f"DEBUG: project_stat failed: {e}")
                            import traceback
                            traceback.print_exc()
                            
                            # Also populate other missing fields if possible
                            if proj_prob == 0.0:
                                proj_prob = proj.probability_over_line
                                calibrated_prob = proj.calibrated_probability
                                ev = proj.expected_value
                                sample_size = len(games)
            except Exception as e:
                pass # Fail silently, keep defaults

        # Create base enhanced bet
        bet = EnhancedBet(
            original_rec=rec,
            player_name=player_name,
            historical_hit_rate=historical_hit_rate,
            market=market,
            selection=selection,
            line=line,
            odds=odds,
            projected_probability=proj_prob,  # Raw projection (81.4% for Mark Williams)
            calibrated_probability=calibrated_prob,  # Archetype-capped (74% for Mark Williams)
            implied_probability=impl_prob,
            edge_percentage=edge,
            expected_value=ev,
            confidence_score=confidence,
            game=rec.get('game', ''),
            player_team=rec.get('player_team'),
            opponent_team=rec.get('opponent_team'),
            sample_size=sample_size,
            projected_value=rec.get('projected_value'),
            archetype_name=archetype_name,  # Store archetype name
            archetype_cap=archetype_cap,  # Store archetype cap
            advanced_context=analysis.get('advanced_context') or rec.get('advanced_context', {}),
            matchup_factors=analysis.get('matchup_factors') or rec.get('matchup_factors', {})
        )

        # RECALCULATE EV and Edge using calibrated_probability (ensures consistency)
        if is_player_prop and has_projection_model and odds > 0 and calibrated_prob > 0:
            # Calculate fair odds from calibrated probability
            fair_odds = 1.0 / calibrated_prob

            # Edge % = ((fair_odds / market_odds) - 1) * 100 (matches QA validator formula)
            bet.edge_percentage = ((fair_odds / odds) - 1) * 100

            # EV % = (odds * calibrated_prob - 1) * 100
            bet.expected_value = (odds * calibrated_prob - 1) * 100

        # Apply enhancements
        self._calculate_adjusted_ev(bet) # User Request: 1. Adjust EV
        self._classify_quality_tier(bet, confidence)
        self._calculate_sample_size_penalty(bet, confidence)
        self._calculate_line_difficulty_penalty(bet)
        self._check_market_efficiency(bet, confidence)
        self._calculate_consistency_rank(bet)
        self._calculate_ev_ratio(bet)
        self._calculate_fair_odds(bet)
        self._calculate_projection_margin(bet)
        self._calculate_minutes_stability(bet)
        self._detect_role_changes(bet)
        self._check_line_efficiency(bet)
        self._predict_line_movement(bet)
        self._detect_sharp_public(bet)

        return bet

    def _validate_bet_mathematics(self, probability: float, odds: float, edge: float, ev: float, player_name: str = "") -> bool:
        """
        Enforce hard mathematical validation rules.
        
        Rules:
        1. Edge = (Market Odds - Fair Odds) / Fair Odds
        2. EV = (Odds × Probability) - 1  
        3. Edge and EV must have same sign (both positive or both negative)
        
        Returns: True if valid, False to block bet
        """
        if probability <= 0 or probability >= 1:
            logger.warning(f"[MATH BLOCK] {player_name}: Invalid probability {probability:.3f}")
            return False
        
        # Calculate fair odds from probability
        fair_odds = 1 / probability
        
        # Verify edge calculation
        expected_edge = (odds - fair_odds) / fair_odds
        edge_as_decimal = edge / 100  # Convert from percentage
        
        if abs(edge_as_decimal - expected_edge) > 0.02:  # Allow 2% tolerance
            logger.warning(f"[MATH BLOCK] {player_name}: Edge inconsistent - calculated {expected_edge*100:.1f}%, got {edge:.1f}%")
            return False
        
        # Verify EV calculation  
        expected_ev = (odds * probability) - 1
        ev_as_decimal = ev / 100  # Convert from percentage
        
        if abs(ev_as_decimal - expected_ev) > 0.02:  # Allow 2% tolerance
            logger.warning(f"[MATH BLOCK] {player_name}: EV inconsistent - calculated {expected_ev*100:.1f}%, got {ev:.1f}%")
            return False
        
        # Verify same sign (most critical check)
        edge_positive = edge > 0
        ev_positive = ev > 0
        
        if edge_positive != ev_positive:
            logger.error(f"[MATH BLOCK] {player_name}: CRITICAL ERROR - Edge={edge:.1f}%, EV={ev:.1f}% have opposite signs!")
            return False
        
        return True

    def _calculate_confidence_with_lag(self, final_probability: float, sample_size: int, variance: float) -> float:
        """
        Calculate confidence with volatility penalty lag.
        
        Confidence ≤ Final Probability − Volatility Penalty
        
        Args:
            final_probability: Final blended probability (0-1)
            sample_size: Number of games in sample
            variance: Statistical variance of outcomes
            
        Returns:
            Confidence score (0-100) that lags behind probability
        """
        # Base volatility penalty on sample size
        if sample_size >= 20:
            volatility_penalty = 0.05  # 5% penalty for good sample
        elif sample_size >= 10:
            volatility_penalty = 0.10  # 10% penalty for okay sample
        else:
            volatility_penalty = 0.15  # 15% penalty for small sample
        
        # Additional penalty for high variance
        if variance > 0.2:
            volatility_penalty += 0.05
        
        # Confidence MUST be below probability
        max_confidence_decimal = final_probability - volatility_penalty
        max_confidence = max_confidence_decimal * 100  # Convert to percentage
        
        # Start from a base confidence scaled with sample
        base_confidence = 50 + (sample_size / 2)  # Scale with sample (max ~65 for n=30)
        
        # Return the lower of calculated vs max allowed
        final_confidence = min(base_confidence, max_confidence, 85.0)  # Never exceed 85%
        final_confidence = max(0.0, final_confidence)  # Never below 0%
        
        return final_confidence


    def _calculate_adjusted_ev(self, bet: EnhancedBet):
        """
        Calculate Adjusted EV = EV * (Confidence / 100) * correlation_multiplier

        PHASE 4: Now applies correlation multiplier (0.85-1.0) to EV
        """
        # Get confidence score from original recommendation
        confidence = bet.original_rec.get('confidence_score') or bet.original_rec.get('confidence', 0.0)

        # Apply both confidence and correlation multiplier
        bet.adjusted_ev = bet.expected_value * (confidence / 100.0) * bet.correlation_multiplier


    def _classify_quality_tier(self, bet: EnhancedBet, confidence: float):
        """
        PHASE 5: STRICT TIER LOGIC

        Tiers:
        - S-Tier: ALL conditions must be met (no single metric can elevate)
        - A-Tier: Strong metrics with some flexibility
        - B-Tier: Minimum playable quality
        - C-Tier: Below quality thresholds
        - D-Tier: Negative EV or low probability

        HIGH EV ALONE CANNOT ELEVATE TIER - All requirements must be met.
        """
        ev = bet.expected_value
        prob = bet.calibrated_probability  # PHASE 5: Use calibrated probability
        vol = bet.minutes_volatility_score
        has_corr = bet.correlation_multiplier < 1.0

        # D-Tier: Negative EV or too low probability (more lenient)
        if ev <= -1.0 or prob < 0.45:
            bet.quality_tier = QualityTier.D
            bet.tier_emoji = "❌"
            return

        # S-Tier: ALL conditions must be met (strictest requirements)
        if (ev >= 12.0 and prob >= 0.65 and confidence >= 75.0 and
            vol < 6.0 and not has_corr):
            bet.quality_tier = QualityTier.S
            bet.tier_emoji = "💎"
            return

        # A-Tier: High quality with some flexibility
        if ev >= 6.0 and prob >= 0.60 and vol < 8.0:
            bet.quality_tier = QualityTier.A
            bet.tier_emoji = "⭐"
            return

        # B-Tier: Minimum playable (more lenient)
        if ev >= 2.0 and prob >= 0.55:
            bet.quality_tier = QualityTier.B
            bet.tier_emoji = "✓"
            return

        # C-Tier: Below thresholds but still positive EV
        bet.quality_tier = QualityTier.C
        bet.tier_emoji = "⛔"

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
        ✅ 3. Calculate conflict score for correlated bets (SCALED BY PROJECTION MARGIN)

        Penalties scaled by projection margin:
        - Same team AND same stat:
            * proj_margin < 2.0 → penalty -10
            * proj_margin 2-4 → penalty -6
            * proj_margin > 4 → penalty -4
        - Same game AND same stat:
            * proj_margin < 2.0 → penalty -10
            * proj_margin 2-4 → penalty -6
            * proj_margin > 4 → penalty -4
        """
        for i, bet in enumerate(bets):
            correlation_multiplier = 1.0  # PHASE 4: Start with no penalty
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

                multiplier = 1.0

                if same_team and same_stat and bet.player_name and other.player_name:
                    # PHASE 4: Get multiplicative penalty (0.85 or 0.88)
                    multiplier = self._get_scaled_correlation_penalty(bet, other)
                    proj_dist = abs(bet.projected_value - other.projected_value) if bet.projected_value and other.projected_value else 0
                    conflicts.append(f"Same team ({player_team}) + stat ({self._extract_stat_type(bet.market)}, {proj_dist:.1f}pts apart)")
                elif same_game and same_stat and bet.player_name and other.player_name:
                    # PHASE 4: Get multiplicative penalty (0.85 or 0.88)
                    multiplier = self._get_scaled_correlation_penalty(bet, other)
                    proj_dist = abs(bet.projected_value - other.projected_value) if bet.projected_value and other.projected_value else 0
                    conflicts.append(f"Same game + stat ({self._extract_stat_type(bet.market)}, {proj_dist:.1f}pts apart)")

                # Track lowest multiplier (most severe penalty)
                correlation_multiplier = min(correlation_multiplier, multiplier)

            # PHASE 4: Store multiplier and apply to EV
            bet.correlation_multiplier = correlation_multiplier
            bet.correlation_penalty = (1.0 - correlation_multiplier) * -100  # For legacy compatibility
            bet.conflict_score = (1.0 - correlation_multiplier) * 100

            if conflicts:
                bet.warnings.append("Warning: Correlation (same game/team)")

    def _check_excessive_correlation(self, bets: List[EnhancedBet]):
        """
        PHASE 4: HARD BLOCK if 3+ player props in same game (excessive correlation).

        Downgrades all excess props to D-Tier (completely blocked).
        This prevents over-exposure to a single game outcome.
        """
        # Count props per game
        game_prop_counts: Dict[str, List[EnhancedBet]] = {}

        for bet in bets:
            if bet.player_name:  # Only count player props
                game = bet.game
                if game not in game_prop_counts:
                    game_prop_counts[game] = []
                game_prop_counts[game].append(bet)

        # Check each game
        for game, game_bets in game_prop_counts.items():
            if len(game_bets) >= 3:
                # 3+ props in same game - HARD BLOCK all of them (D-Tier)
                for bet in game_bets:
                    bet.quality_tier = QualityTier.D
                    bet.tier_emoji = "❌"
                    bet.warnings.append("BLOCKED: 3+ props same game (excessive correlation)")

    def _get_scaled_correlation_penalty(self, bet1: EnhancedBet, bet2: EnhancedBet) -> float:
        """
        PHASE 4: STRICT CORRELATION PENALTIES (Multiplicative EV reduction)

        Returns EV multiplier based on correlation risk:
        - Two scorers same team → 0.85 (15% EV reduction)
        - Big + Guard same team → 0.88 (12% EV reduction)
        - No correlation → 1.0 (no penalty)

        This replaces the old additive penalty system with multiplicative
        factors that directly scale expected value.

        Args:
            bet1: First bet
            bet2: Second bet

        Returns:
            EV multiplier (0.85, 0.88, or 1.0)
        """
        # Check if same team
        same_team = (bet1.player_team == bet2.player_team and
                     bet1.player_team not in [None, 'Unknown', ''])

        # Check if same stat type
        same_stat = self._extract_stat_type(bet1.market) == self._extract_stat_type(bet2.market)

        if same_team and same_stat:
            # Detect if one is big man, other is guard
            is_big_guard = self._is_big_guard_combo(bet1, bet2)

            if is_big_guard:
                return 0.88  # Big + Guard: 12% EV reduction
            else:
                return 0.85  # Same position scorers: 15% EV reduction

        # No correlation detected
        return 1.0

    def _is_big_guard_combo(self, bet1: EnhancedBet, bet2: EnhancedBet) -> bool:
        """
        PHASE 4: Check if one player is a big man and the other is a guard.

        Uses archetype names to infer position:
        - "Low-Usage Big", "Defensive First" → Big man
        - Others → Guard/Wing

        Args:
            bet1: First bet
            bet2: Second bet

        Returns:
            True if one is big and one is guard/wing
        """
        big_archetypes = ['Low-Usage Big', 'Defensive First']

        arch1_is_big = bet1.archetype_name in big_archetypes
        arch2_is_big = bet2.archetype_name in big_archetypes

        # Return True if one is big and the other is not
        return arch1_is_big != arch2_is_big

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

        Filter out: EV_ratio < 0.05 (relaxed from 0.08)
        """
        if bet.projected_probability > 0:
            bet.ev_to_prob_ratio = bet.expected_value / (bet.projected_probability * 100)
        else:
            bet.ev_to_prob_ratio = 0.0

        # Relaxed threshold: 0.05 instead of 0.08
        min_ev_ratio_relaxed = 0.05
        if bet.ev_to_prob_ratio < min_ev_ratio_relaxed:
            bet.passes_ev_ratio = False
            bet.warnings.append(f"Low EV/Prob ratio ({bet.ev_to_prob_ratio:.3f} < {min_ev_ratio_relaxed})")
        else:
            bet.passes_ev_ratio = True

    def _calculate_fair_odds(self, bet: EnhancedBet):
        """
        ✅ 8. Calculate true fair odds using CALIBRATED probability

        Fair Odds = 1 / Calibrated Probability (SINGLE SOURCE OF TRUTH)
        Mispricing = Market Odds - Fair Odds
        """
        # Use calibrated_probability if available, fallback to projected_probability
        calibrated_prob = getattr(bet, 'calibrated_probability', None)
        if calibrated_prob is None:
            calibrated_prob = bet.projected_probability

        if calibrated_prob > 0:
            bet.fair_odds = 1.0 / calibrated_prob
            bet.odds_mispricing = bet.odds - bet.fair_odds
        else:
            bet.fair_odds = 0.0
            bet.odds_mispricing = 0.0

    def _validate_probability_consistency(self, bet: EnhancedBet) -> bool:
        """
        CRITICAL VALIDATION: Ensure mathematical consistency

        Checks:
        1. Fair Odds = 1 / Calibrated Probability (±1%)
        2. EV formula consistency with probability

        Returns:
            True if valid, False if inconsistent (bet should be BLOCKED)
        """
        # Get calibrated probability
        calibrated_prob = getattr(bet, 'calibrated_probability', None)
        if calibrated_prob is None:
            # If no calibrated probability, use projected as fallback
            calibrated_prob = bet.projected_probability

        if calibrated_prob <= 0:
            return False  # Invalid probability

        # 1. Check Fair Odds = 1/Probability (tolerance ±1%)
        expected_fair_odds = 1.0 / calibrated_prob
        if abs(bet.fair_odds - expected_fair_odds) > 0.01:
            bet.warnings.append(f"BLOCKED: Fair odds inconsistency ({bet.fair_odds:.3f} ≠ {expected_fair_odds:.3f})")
            return False

        # 2. Check EV formula consistency
        expected_ev = (bet.odds * calibrated_prob - 1) * 100
        if abs(bet.expected_value - expected_ev) > 1.0:
            bet.warnings.append(f"BLOCKED: EV formula inconsistency ({bet.expected_value:.2f}% ≠ {expected_ev:.2f}%)")
            return False

        return True

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

    def _calculate_minutes_stability(self, bet: EnhancedBet):
        """
        ✅ ENHANCED: Calculate minutes volatility score (0-10 scale)

        Analyzes minutes variance from advanced context.

        Volatility Score (0-10):
        - 0-2: Very Stable
        - 3-4: Stable
        - 5-6: Moderate
        - 7-8: Volatile
        - 9-10: Very Volatile

        Formula: vol = std_dev(last_5) / avg(last_5), score = clamp(vol * 10, 0, 10)
        """
        # Try to get minutes analysis from advanced context
        advanced_ctx = bet.original_rec.get('advanced_context', {})
        minutes_analysis = advanced_ctx.get('minutes_analysis', {})

        if minutes_analysis:
            recent_avg = minutes_analysis.get('recent_avg', 0)
            variance = minutes_analysis.get('variance', 0)
            stable = minutes_analysis.get('stable', True)

            bet.minutes_variance = variance

            # Calculate variance percentage and volatility score
            if recent_avg > 0:
                variance_pct = (variance / recent_avg) * 100

                # Calculate volatility score (0-10 scale)
                # Standard deviation / average gives coefficient of variation
                # Multiply by 10 to get 0-10 scale
                volatility_score = min(10.0, max(0.0, (variance / recent_avg) * 10))
                bet.minutes_volatility_score = volatility_score

                # Assign label based on score
                if volatility_score <= 2.0:
                    bet.minutes_volatility_label = "Very Stable"
                    bet.minutes_stability_penalty = 0.0
                    bet.notes.append(f"✓ Minutes Volatility: {volatility_score:.1f}/10 (Very Stable)")
                elif volatility_score <= 4.0:
                    bet.minutes_volatility_label = "Stable"
                    bet.minutes_stability_penalty = 0.0
                    bet.notes.append(f"✓ Minutes Volatility: {volatility_score:.1f}/10 (Stable)")
                elif volatility_score <= 6.0:
                    bet.minutes_volatility_label = "Moderate"
                    bet.minutes_stability_penalty = -2.0
                    bet.warnings.append(f"Minutes Volatility: {volatility_score:.1f}/10 (Moderate) - {variance:.1f}min variance")
                elif volatility_score <= 8.0:
                    bet.minutes_volatility_label = "Volatile"
                    bet.minutes_stability_penalty = -5.0
                    bet.warnings.append(f"Minutes Volatility: {volatility_score:.1f}/10 (Volatile) - {variance:.1f}min variance")
                else:
                    bet.minutes_volatility_label = "Very Volatile"
                    bet.minutes_stability_penalty = -8.0
                    bet.warnings.append(f"⚠ Minutes Volatility: {volatility_score:.1f}/10 (VERY VOLATILE) - Unreliable minutes")
            else:
                bet.minutes_stability_penalty = 0.0
                bet.minutes_volatility_score = 0.0
                bet.minutes_volatility_label = "Unknown"
        else:
            # No minutes data available
            bet.minutes_stability_penalty = 0.0
            bet.minutes_volatility_score = 0.0
            bet.minutes_volatility_label = "Unknown"

    def _detect_role_changes(self, bet: EnhancedBet):
        """
        ✅ NEW: Detect injury/role change alerts

        Detects:
        - Increased usage last 3 games (role expansion)
        - Decreased usage (role reduction)
        - Teammate out (opportunity boost)

        Adds projection adjustments and alerts.
        """
        advanced_ctx = bet.original_rec.get('advanced_context', {})

        # Check for rebounding context (has recent_form for comparison)
        rebounding_ctx = advanced_ctx.get('rebounding_context', {})
        if rebounding_ctx:
            recent_form = rebounding_ctx.get('recent_form', 0)

            # Get databallr stats for season average comparison
            databallr_stats = bet.original_rec.get('databallr_stats', {})
            season_avg = databallr_stats.get('avg_value', 0)

            if recent_form > 0 and season_avg > 0:
                # Calculate % change in recent form vs season
                pct_change = ((recent_form - season_avg) / season_avg) * 100

                # Significant increase (>15%) = role expansion
                if pct_change > 15.0:
                    bet.role_change_detected = True
                    bet.role_change_type = "increased_usage"
                    bet.role_change_impact = pct_change
                    bet.notes.append(f"⬆ Role Shift: +{pct_change:.1f}% usage last 3 games")

                # Significant decrease (<-15%) = role reduction
                elif pct_change < -15.0:
                    bet.role_change_detected = True
                    bet.role_change_type = "decreased_usage"
                    bet.role_change_impact = pct_change
                    bet.warnings.append(f"⬇ Role Shift: {pct_change:.1f}% usage decline")

        # Check minutes for role changes
        minutes_analysis = advanced_ctx.get('minutes_analysis', {})
        if minutes_analysis:
            recent_avg = minutes_analysis.get('recent_avg', 0)
            season_avg = minutes_analysis.get('season_avg', 0)
            trending = minutes_analysis.get('trending', '')

            if recent_avg > 0 and season_avg > 0:
                minutes_change = ((recent_avg - season_avg) / season_avg) * 100

                # Significant minutes increase
                if minutes_change > 10.0:
                    bet.role_change_detected = True
                    if not bet.role_change_type:  # Don't overwrite if already set
                        bet.role_change_type = "increased_minutes"
                        bet.role_change_impact = minutes_change
                    bet.notes.append(f"⬆ Minutes Trend: +{minutes_change:.1f}% ({trending})")

                # Significant minutes decrease
                elif minutes_change < -10.0:
                    bet.role_change_detected = True
                    if not bet.role_change_type:
                        bet.role_change_type = "decreased_minutes"
                        bet.role_change_impact = minutes_change
                    bet.warnings.append(f"⬇ Minutes Trend: {minutes_change:.1f}% ({trending})")

        # Check for teammate impact (placeholder - would need injury data)
        # This would be populated if we had injury/lineup data
        matchup_factors = bet.original_rec.get('matchup_factors', {})
        if matchup_factors:
            # Future enhancement: Check for key teammate absences
            # For now, just note if matchup factors exist
            pass

    def _check_line_efficiency(self, bet: EnhancedBet):
        """
        ✅ NEW: Check for line efficiency / shaded lines

        Lines can be shaded by books on:
        - Star players
        - Highly bet overs
        - Back-to-backs
        - Blowout risk

        Currently marks potential shading based on:
        - High lines (30+) for points
        - High implied probability (books getting action)

        Future: Could integrate real-time line movement data
        """
        # Check for potential line shading indicators
        line = bet.line
        odds = bet.odds
        impl_prob = bet.implied_probability

        shading_indicators = []

        # High line on points (books often shade these)
        if line and line >= 30.0 and 'point' in bet.market.lower():
            shading_indicators.append("High points line (30+)")

        # Very low odds = heavy juice = potential shading
        if odds < 1.70:
            shading_indicators.append("Heavy juice (odds < 1.70)")

        # Implied probability > 60% but not a huge favorite
        if impl_prob > 0.60 and impl_prob < 0.75:
            shading_indicators.append("Moderate favorite (potential public action)")

        if shading_indicators:
            bet.line_shaded = True
            bet.warnings.append(f"Potential line shading: {', '.join(shading_indicators)}")
        else:
            bet.line_shaded = False

        # Note: Line movement would require historical data
        # For now, set to 0 (future enhancement)
        bet.line_movement = 0.0

    def _predict_line_movement(self, bet: EnhancedBet):
        """
        ✅ NEW: Predict movement based on Tier Quality (User Request)

        States:
        - BUY NOW: S-Tier or A-Tier (High Value)
        - MONITOR: B-Tier
        - WAIT: C-Tier (Marginal)
        - FADE: D-Tier (Avoid)
        """
        tier = bet.quality_tier

        if tier in [QualityTier.S, QualityTier.A]:
            bet.line_movement_urgency = "BUY NOW"
            bet.expected_line_movement = "Line likely to worsen"
        elif tier == QualityTier.B:
            bet.line_movement_urgency = "MONITOR"
            bet.expected_line_movement = "Neutral"
        elif tier == QualityTier.C:
            bet.line_movement_urgency = "WAIT"
            bet.expected_line_movement = "Line likely to improve"
        else:
            bet.line_movement_urgency = "FADE"
            bet.expected_line_movement = "Line inflated"

    def _detect_sharp_public(self, bet: EnhancedBet):
        """
        ✅ NEW: Detect sharp vs public money

        Without real line movement data, we infer from:
        1. Odds vs our projection (sharp agreement)
        2. Implied probability zones (public favorites)
        3. Odds value (heavy favorites = public)

        Indicators:
        - SHARP_OVER: Sharp money agrees with over
        - PUBLIC_OVER: Public betting over (fade)
        - SHARP_UNDER: Sharp money on under
        - PUBLIC_UNDER: Public on under
        - BALANCED: No clear bias
        """
        proj_prob = bet.projected_probability
        impl_prob = bet.implied_probability
        odds = bet.odds
        edge = bet.edge_percentage

        # Check if our projection aligns with a value line
        is_over = "over" in bet.selection.lower()

        # Sharp indicators:
        # 1. Positive edge (we agree with sharps)
        # 2. Odds in efficient range (1.70-2.20)
        # 3. Not heavily juiced

        has_sharp_agreement = edge > 3.0 and 1.70 <= odds <= 2.20
        has_public_pattern = (impl_prob > 0.65 and odds < 1.70) or (impl_prob < 0.45 and odds > 2.30)

        if is_over:
            if has_sharp_agreement:
                bet.sharp_public_indicator = "SHARP_OVER"
                bet.betting_pressure = "Sharp money on OVER"
                bet.notes.append("💰 Sharp Agreement: Professional money on OVER")
            elif has_public_pattern and impl_prob > 0.65:
                bet.sharp_public_indicator = "PUBLIC_OVER"
                bet.betting_pressure = "Public heavy on OVER"
                bet.warnings.append("⚠ Public Favorite: Heavy retail action (fade candidate)")
            elif edge < -5.0:
                bet.sharp_public_indicator = "SHARP_UNDER"
                bet.betting_pressure = "Sharp money on UNDER"
                bet.warnings.append("⚠ Sharp Disagreement: Pros favor UNDER")
            else:
                bet.sharp_public_indicator = "BALANCED"
                bet.betting_pressure = "Balanced"
        else:
            # UNDER bets - reverse logic
            if has_sharp_agreement:
                bet.sharp_public_indicator = "SHARP_UNDER"
                bet.betting_pressure = "Sharp money on UNDER"
                bet.notes.append("💰 Sharp Agreement: Professional money on UNDER")
            elif has_public_pattern:
                bet.sharp_public_indicator = "PUBLIC_UNDER"
                bet.betting_pressure = "Public heavy on UNDER"
                bet.warnings.append("⚠ Public Favorite: Heavy retail action")
            else:
                bet.sharp_public_indicator = "BALANCED"
                bet.betting_pressure = "Balanced"

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

        # Apply minutes stability penalty
        score += bet.minutes_stability_penalty

        # Store final adjusted confidence
        bet.adjusted_confidence = max(0.0, min(100.0, score))

        # NEW: Calculate correlation impact multiplier (moderate: 15-30 point reduction)
        correlation_impact = abs(bet.correlation_penalty) * 2.5  # Amplify penalty effect

        # Calculate final score for sorting (weights different factors)
        # FIXED: Now uses adjusted_confidence (which includes penalties) instead of effective_confidence
        bet.final_score = (
            bet.adjusted_confidence * 0.4 +
            bet.expected_value * 2.0 +
            bet.edge_percentage * 3.0 +
            bet.projected_probability * 50.0 -
            correlation_impact  # NEW: Subtract correlation impact from final score
        )

        # NEW: Add visual warnings for correlation
        if bet.correlation_penalty < -8:
            bet.notes.append(f"⚠️ High Correlation: Same-game exposure reduces score by {correlation_impact:.0f} pts")
        elif bet.correlation_penalty < -5:
            bet.notes.append(f"⚠️ Correlation: Multiple bets from same game")

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

            # Check efficiency - RELAXED: Allow more bets through
            # Only reject if clearly inefficient (very low edge in efficient zone)
            if not bet.passes_efficiency_check:
                # Override: If it's B-Tier or better, allow it through anyway
                if bet.quality_tier in [QualityTier.S, QualityTier.A, QualityTier.B]:
                    pass  # Allow through despite efficiency check
                else:
                    continue

            # Check EV ratio - RELAXED: Lower threshold
            if not bet.passes_ev_ratio:
                # Override: If it's B-Tier or better, allow it through anyway
                if bet.quality_tier in [QualityTier.S, QualityTier.A, QualityTier.B]:
                    pass  # Allow through despite EV ratio check
                else:
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
        """
        PHASE 9: STANDARDIZED OUTPUT FORMAT

        Required fields:
        - Calibrated Probability
        - Fair Odds
        - Market Odds
        - Edge %
        - EV %
        - Confidence Score
        - Volatility Flags
        - Tier Justification (1-2 lines)
        """
        # Header with player and market
        team_info = ""
        if bet.player_team and bet.player_team != "Unknown":
            team_info = f" ({bet.player_team})"

        print(f"\n{index}. {bet.tier_emoji} {bet.player_name or 'TEAM'}{team_info} - {bet.market}")

        # Tier justification (1-2 lines explaining tier assignment)
        tier_justification = self._get_tier_justification(bet)
        print(f"   Tier: {bet.quality_tier.name} - {tier_justification}")

        # Core probability and odds
        print(f"   Probability: {bet.calibrated_probability:.1%} | Fair Odds: {bet.fair_odds:.2f} | Market: {bet.odds:.2f}")

        # Value metrics
        print(f"   Edge: {bet.edge_percentage:+.1f}% | EV: {bet.expected_value:+.1f}% | Confidence: {bet.confidence_score:.0f}%")

        # Volatility flag (if applicable)
        vol_flag = self._get_volatility_flag(bet)
        if vol_flag:
            print(f"   {vol_flag}")

        # Primary warning (highest priority issue)
        warning = self._get_primary_warning(bet)
        if warning:
            print(f"   {warning}")

    def _get_tier_justification(self, bet: EnhancedBet) -> str:
        """
        PHASE 9: Provide 1-2 line explanation of tier assignment.

        Returns:
            Brief explanation of why bet received this tier
        """
        if bet.quality_tier == QualityTier.S:
            return f"Elite value: EV {bet.expected_value:.1f}%, Conf {bet.confidence_score:.0f}%, Stable minutes"
        elif bet.quality_tier == QualityTier.A:
            return f"High quality: EV {bet.expected_value:.1f}%, Prob {bet.calibrated_probability:.0%}"
        elif bet.quality_tier == QualityTier.B:
            return f"Playable: EV {bet.expected_value:.1f}%, moderate risk"
        elif bet.quality_tier == QualityTier.C:
            return "Pass: Below quality thresholds"
        else:
            return "Avoid: Negative expected value"

    def _get_volatility_flag(self, bet: EnhancedBet) -> str:
        """
        PHASE 9: Return volatility status flag.

        Returns:
            Volatility warning or stability confirmation
        """
        vol = bet.minutes_volatility_score

        if vol >= 8.0:
            return f"⚠ HIGH VOLATILITY: {vol:.1f}/10 minutes variance"
        elif vol >= 6.0:
            return f"⚠ Moderate volatility: {vol:.1f}/10"
        elif vol <= 2.0:
            return f"✓ Very stable minutes: {vol:.1f}/10"

        # 2.0-6.0 range: no flag needed (normal)
        return ""

    def _get_movement_label(self, bet: EnhancedBet) -> str:
        """
        PHASE 7: ANTI-HYPE DISPLAY RESTRICTIONS

        Rules:
        - NO "BUY NOW" on B/C tiers
        - NO "High Value" if EV < 8%
        - Conservative language for lower tiers
        """
        tier = bet.quality_tier
        ev = bet.expected_value

        # S/A Tiers with high EV → BUY NOW
        if tier in [QualityTier.S, QualityTier.A] and ev >= 8.0:
            return "BUY NOW (High value)"

        # B Tier → MONITOR (never "BUY NOW")
        elif tier == QualityTier.B:
            return "MONITOR (Moderate value)"

        # C Tier → WAIT (low confidence)
        elif tier == QualityTier.C:
            return "WAIT (Low confidence)"

        # D Tier → FADE (avoid)
        else:
            return "FADE (Avoid)"

    def _get_primary_warning(self, bet: EnhancedBet) -> str:
        """
        PHASE 7: Get ONLY the most important warning (priority order)

        NEW Priority:
        1. High volatility (≥8.0) - role instability
        2. Role change/spike - temporary usage increase
        3. Correlation - EV reduced by correlation
        4. Small sample - unreliable data
        5. Negative edge - bad bet
        6. Other warnings
        """
        # 1. High volatility (highest priority - indicates unreliable role)
        if bet.minutes_volatility_score >= 8.0:
            return f"⚠ High minutes volatility ({bet.minutes_volatility_score:.1f}/10)"

        # 2. Role change or temporary spike
        if bet.role_change_detected:
            if bet.role_change_type == "TEMPORARY_SPIKE":
                return f"⚠ Role spike: Temporary usage increase"
            elif bet.role_change_type == "decreased_usage":
                return f"⚠ Usage declining"
            elif bet.role_change_type == "increased_usage":
                return f"⚠ Usage spike detected"

        # 3. Correlation (EV reduction)
        if bet.correlation_multiplier < 0.90:
            reduction_pct = (1.0 - bet.correlation_multiplier) * 100
            return f"⚠ Correlation: EV reduced {reduction_pct:.0f}%"

        # 4. Small sample
        if bet.sample_size < 5:
            return f"⚠ Small sample (n={bet.sample_size})"

        # 5. Negative edge
        if bet.edge_percentage < 0:
            return "⚠ Negative edge - avoid"

        # 6. Other warnings (lower priority)
        # Moderate volatility
        if bet.minutes_volatility_score >= 6.0:
            return f"⚠ Moderate volatility: {bet.minutes_volatility_score:.1f}/10"

        # Line difficulty
        if bet.line_difficulty_penalty < -8:
            return f"⚠ Extreme line ({bet.line:.1f})"

        # Public/Sharp signals
        if bet.sharp_public_indicator == "PUBLIC_OVER" or bet.sharp_public_indicator == "PUBLIC_UNDER":
            return "ℹ Public heavy (fade candidate)"

        # Default: no major warning
        return ""


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == '__main__':
    import json
    import sys
    import io

    # Fix Windows encoding for Unicode characters
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

    # Also save ALL enhancement metrics (V2 and V2.5)
    for i, bet in enumerate(quality_bets):
        if i < len(enhanced_output):
            enhanced_output[i]['enhanced_metrics'].update({
                # V2 features
                'minutes_stability_penalty': bet.minutes_stability_penalty,
                'minutes_variance': bet.minutes_variance,
                'line_shaded': bet.line_shaded,
                'line_movement': bet.line_movement,
                # V2.5 NEW features
                'minutes_volatility_score': bet.minutes_volatility_score,
                'minutes_volatility_label': bet.minutes_volatility_label,
                'role_change_detected': bet.role_change_detected,
                'role_change_type': bet.role_change_type,
                'role_change_impact': bet.role_change_impact,
                'expected_line_movement': bet.expected_line_movement,
                'line_movement_urgency': bet.line_movement_urgency,
                'sharp_public_indicator': bet.sharp_public_indicator,
                'betting_pressure': bet.betting_pressure
            })

    with open('betting_recommendations_enhanced.json', 'w') as f:
        json.dump(enhanced_output, f, indent=2, default=str)

    print("\n✓ Saved enhanced recommendations to betting_recommendations_enhanced.json")
