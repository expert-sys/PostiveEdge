"""
NBA Betting System - Complete Pipeline
======================================
Scrapes Sportsbet NBA insights/trends → Validates with DataBallr stats → Projects high-value bets

FLOW:
1. Scrape Sportsbet for NBA games, odds, insights, and player props
2. For each insight/prop, fetch player/team stats from DataBallr
3. Calculate projections using statistical models
4. Identify high-confidence value bets (70%+ confidence, positive EV)
5. Output ranked recommendations

Usage:
    python nba_betting_system.py                    # Analyze all games
    python nba_betting_system.py --games 3          # Analyze 3 games
    python nba_betting_system.py --min-confidence 75 # Higher threshold
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse

# Fix Windows encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nba_betting_system.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("nba_betting_system")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BettingRecommendation:
    """Final betting recommendation with all analysis"""
    # Game context
    game: str
    match_time: str
    
    # Bet details
    bet_type: str  # 'team_total', 'team_spread', 'team_moneyline', 'player_prop'
    market: str
    selection: str
    odds: float
    
    # Player-specific (if player prop)
    player_name: Optional[str] = None
    player_team: Optional[str] = None  # NEW: Player's team
    opponent_team: Optional[str] = None  # NEW: Opponent team
    stat_type: Optional[str] = None
    line: Optional[float] = None
    
    # Analysis
    sportsbet_insight: Optional[str] = None
    historical_hit_rate: float = 0.0
    sample_size: int = 0
    
    # Projections
    projected_value: Optional[float] = None
    projected_probability: float = 0.0
    model_confidence: float = 0.0
    
    # Value metrics
    implied_probability: float = 0.0
    edge_percentage: float = 0.0
    expected_value: float = 0.0
    
    # Final score
    confidence_score: float = 0.0
    recommendation_strength: str = "MEDIUM"  # LOW, MEDIUM, HIGH, VERY_HIGH
    
    # Supporting data
    databallr_stats: Optional[Dict] = None
    matchup_factors: Optional[Dict] = None
    advanced_context: Optional[Dict] = None  # NEW: Advanced contextual factors
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# STEP 1: SCRAPE SPORTSBET
# ============================================================================

class SportsbetCollector:
    """Collects NBA betting data from Sportsbet"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    def collect_games(self, max_games: int = None) -> List[Dict]:
        """
        Scrape NBA games with odds, insights, and player props
        
        Returns:
            List of game dicts with:
            - game_info: {home_team, away_team, match_time, url}
            - team_markets: List of team betting markets
            - insights: List of Sportsbet insights/trends
            - player_props: List of player prop markets
            - team_recent_results: Recent game results for both teams
        """
        logger.info("=" * 80)
        logger.info("STEP 1: SCRAPING SPORTSBET NBA DATA")
        logger.info("=" * 80)
        
        try:
            from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
        except ImportError:
            logger.error("Sportsbet scraper not found. Install dependencies.")
            return []
        
        # Get all NBA games
        logger.info("Fetching NBA games from Sportsbet...")
        games = scrape_nba_overview(headless=self.headless)
        
        if not games:
            logger.error("No games found on Sportsbet")
            return []
        
        # Limit games if specified
        if max_games:
            games = games[:max_games]
        
        logger.info(f"Found {len(games)} games to analyze")
        
        # Collect detailed data for each game
        game_data = []
        for i, game in enumerate(games, 1):
            logger.info(f"\n[{i}/{len(games)}] Collecting: {game['away_team']} @ {game['home_team']}")
            
            try:
                # Scrape complete match data
                match_data = scrape_match_complete(game['url'], headless=self.headless)
                
                if not match_data:
                    logger.warning("  Failed to scrape match data")
                    continue
                
                # Extract components
                all_markets = getattr(match_data, 'all_markets', []) or []
                insights = getattr(match_data, 'match_insights', []) or []
                match_stats = getattr(match_data, 'match_stats', None)
                
                # Extract team recent results from insights (if available)
                team_results = self._extract_team_results_from_insights(insights, game['home_team'], game['away_team'])
                
                logger.info(f"  ✓ {len(all_markets)} markets, {len(insights)} insights")
                if team_results:
                    logger.info(f"  ✓ Found recent results for team markets")
                
                game_data.append({
                    'game_info': game,
                    'team_markets': all_markets,
                    'insights': insights,
                    'match_stats': match_stats,
                    'team_recent_results': team_results
                })
                
            except Exception as e:
                logger.error(f"  Error: {e}")
                continue
        
        logger.info(f"\n✓ Collected data for {len(game_data)} games")
        return game_data
    
    def _extract_team_results_from_insights(self, insights: List, home_team: str, away_team: str) -> Optional[Dict]:
        """
        Extract recent game results from insights data.
        
        Looks for insights showing "2025/26 Season Results" with scores.
        
        Returns:
            Dict with 'home_results' and 'away_results' lists of (score_for, score_against, result) tuples
        """
        import re
        
        results = {
            'home_team': home_team,
            'away_team': away_team,
            'home_results': [],
            'away_results': []
        }
        
        # Look through insights for season results
        for insight in insights:
            fact = str(getattr(insight, 'fact', ''))
            result = str(getattr(insight, 'result', ''))
            market = str(getattr(insight, 'market', ''))
            
            # Check if this is a season results insight
            combined = (fact + ' ' + result + ' ' + market).lower()
            
            if 'season results' in combined or 'last 5' in combined or 'recent games' in combined:
                # Try to extract scores in format "123-120" or "W 123-120"
                score_pattern = r'(\d{2,3})-(\d{2,3})'
                scores = re.findall(score_pattern, fact + ' ' + result)
                
                # Try to determine which team this is for
                team_name = None
                if home_team.lower() in combined:
                    team_name = 'home'
                elif away_team.lower() in combined:
                    team_name = 'away'
                
                if scores and team_name:
                    # Parse results
                    for score_for, score_against in scores[:10]:  # Max 10 games
                        score_for = int(score_for)
                        score_against = int(score_against)
                        result_char = "W" if score_for > score_against else "L"
                        
                        if team_name == 'home':
                            results['home_results'].append((score_for, score_against, result_char))
                        else:
                            results['away_results'].append((score_for, score_against, result_char))
        
        # Return None if no results found
        if not results['home_results'] and not results['away_results']:
            return None
        
        return results
    
    def _extract_player_props(self, markets: List) -> List:
        """Extract player prop markets from all markets"""
        props = []
        
        for market in markets:
            # Check if this is a player prop
            selection_text = str(getattr(market, 'selection_text', ''))
            market_category = str(getattr(market, 'market_category', '')).lower()
            
            # Player props have player names and stat keywords
            has_stat_keyword = any(keyword in selection_text.lower() for keyword in 
                                  ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-point'])
            
            # Check if it looks like a player name (starts with capital letter, has space)
            import re
            has_player_name = bool(re.match(r'^[A-Z][a-z]+\s+[A-Z]', selection_text))
            
            if has_stat_keyword and has_player_name:
                props.append(market)
        
        logger.debug(f"  Extracted {len(props)} player props from {len(markets)} markets")
        return props


# ============================================================================
# STEP 2: VALIDATE WITH DATABALLR
# ============================================================================

class DataBallrValidator:
    """Validates betting insights with DataBallr player/team stats"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._init_databallr()
    
    def _init_databallr(self):
        """Initialize DataBallr scraper"""
        try:
            from scrapers.databallr_scraper import get_player_game_log
            self.get_player_stats = get_player_game_log
            logger.info("✓ DataBallr scraper initialized")
        except ImportError:
            logger.error("DataBallr scraper not found")
            self.get_player_stats = None
    
    def validate_player_prop(self, player_name: str, stat_type: str, line: float, last_n_games: int = 20) -> Optional[Dict]:
        """
        Fetch player stats from DataBallr and calculate hit rate
        
        Returns:
            Dict with:
            - game_log: List of recent games
            - hit_rate: % of games over the line
            - avg_value: Average stat value
            - sample_size: Number of games
            - trend: Recent trend (improving/declining)
        """
        if not self.get_player_stats:
            return None
        
        logger.debug(f"  Validating {player_name} {stat_type} {line}+ with DataBallr...")
        
        try:
            # Fetch game log
            game_log = self.get_player_stats(
                player_name=player_name,
                last_n_games=last_n_games,
                headless=self.headless,
                use_cache=True
            )
            
            if not game_log or len(game_log) < 5:
                logger.debug(f"    Insufficient data (n={len(game_log) if game_log else 0})")
                return None
            
            # Extract stat values
            stat_values = []
            for game in game_log:
                if game.minutes >= 10:  # Only count games with significant minutes
                    value = getattr(game, stat_type, None)
                    if value is not None:
                        stat_values.append(value)
            
            if len(stat_values) < 5:
                return None
            
            # Calculate metrics
            over_count = sum(1 for v in stat_values if v > line)
            hit_rate = over_count / len(stat_values)
            avg_value = sum(stat_values) / len(stat_values)
            
            # Calculate trend (last 5 vs previous 5)
            recent_avg = sum(stat_values[:5]) / 5 if len(stat_values) >= 5 else avg_value
            previous_avg = sum(stat_values[5:10]) / 5 if len(stat_values) >= 10 else avg_value
            trend = "improving" if recent_avg > previous_avg * 1.1 else "declining" if recent_avg < previous_avg * 0.9 else "stable"
            
            return {
                'game_log': game_log,
                'hit_rate': hit_rate,
                'avg_value': avg_value,
                'sample_size': len(stat_values),
                'trend': trend,
                'recent_avg': recent_avg,
                'season_avg': avg_value
            }
            
        except Exception as e:
            logger.debug(f"    Error validating: {e}")
            return None


# ============================================================================
# STEP 3: PROJECT VALUE BETS
# ============================================================================

class ValueProjector:
    """Projects betting value using statistical models"""
    
    def __init__(self):
        self._init_models()
    
    def _init_models(self):
        """Initialize projection models"""
        try:
            from scrapers.player_projection_model import PlayerProjectionModel
            self.player_model = PlayerProjectionModel()
            logger.info("✓ Player projection model initialized")
        except ImportError:
            logger.warning("Player projection model not available")
            self.player_model = None
        
        # Initialize V2 confidence engine
        try:
            from confidence_engine_v2 import ConfidenceEngineV2
            self.confidence_engine = ConfidenceEngineV2()
            logger.info("✓ Confidence Engine V2 initialized")
        except ImportError:
            logger.warning("Confidence Engine V2 not available")
            self.confidence_engine = None
        
        # Initialize matchup engine
        try:
            from matchup_engine import MatchupEngine
            self.matchup_engine = MatchupEngine()
            logger.info("✓ Matchup Engine initialized")
        except ImportError:
            logger.warning("Matchup Engine not available")
            self.matchup_engine = None
    
    def project_player_prop(
        self,
        player_name: str,
        stat_type: str,
        line: float,
        odds: float,
        databallr_stats: Dict,
        match_stats: Optional[Dict] = None
    ) -> Optional[BettingRecommendation]:
        """
        Project value for a player prop using model + historical data
        
        Combines:
        - Statistical projection model (70% weight)
        - Historical hit rate from DataBallr (30% weight)
        """
        if not self.player_model or not databallr_stats:
            return None
        
        try:
            game_log = databallr_stats['game_log']
            historical_hit_rate = databallr_stats['hit_rate']
            
            # Get model projection
            projection = self.player_model.project_stat(
                player_name=player_name,
                stat_type=stat_type,
                game_log=game_log,
                prop_line=line,
                team_stats=match_stats,
                min_games=5
            )
            
            if not projection:
                return None
            
            # Combine model (70%) + historical (30%)
            model_prob = projection.probability_over_line
            final_prob = 0.7 * model_prob + 0.3 * historical_hit_rate
            
            # Calculate value metrics
            implied_prob = 1.0 / odds
            edge = final_prob - implied_prob
            ev = (final_prob * (odds - 1)) - (1 - final_prob)
            
            # Use V2 confidence engine if available
            if self.confidence_engine:
                # Extract volatility data
                stat_mean = databallr_stats['avg_value']
                stat_std_dev = projection.std_dev if projection.std_dev else stat_mean * 0.25
                
                # Check minutes stability
                minutes_stable = True
                role_change_detected = False
                if projection.minutes_projection:
                    minutes_stable = projection.minutes_projection.volatility < 8.0
                if projection.role_change:
                    role_change_detected = projection.role_change.detected
                
                # Get enhanced matchup factors from matchup engine
                matchup_factors = None
                if self.matchup_engine and match_stats:
                    # Determine teams
                    away_team = match_stats.away_team_stats.team_name if hasattr(match_stats, 'away_team_stats') else "Unknown"
                    home_team = match_stats.home_team_stats.team_name if hasattr(match_stats, 'home_team_stats') else "Unknown"
                    
                    # Try to determine which team player is on
                    # This is a simplified approach - in production, track this properly
                    player_team = away_team  # Default assumption
                    opponent_team = home_team
                    
                    try:
                        from matchup_engine import get_matchup_factors_for_confidence
                        matchup_factors = get_matchup_factors_for_confidence(
                            player_name=player_name,
                            stat_type=stat_type,
                            opponent_team=opponent_team,
                            player_team=player_team,
                            game_log=game_log
                        )
                        logger.debug(f"  Matchup factors: {matchup_factors}")
                    except Exception as e:
                        logger.debug(f"  Could not get matchup factors: {e}")
                        # Fallback to projection matchup adjustments
                        if projection.matchup_adjustments:
                            matchup_factors = {
                                'pace_multiplier': projection.matchup_adjustments.pace_multiplier,
                                'defense_adjustment': projection.matchup_adjustments.defense_adjustment
                            }
                elif projection.matchup_adjustments:
                    # Fallback to projection matchup adjustments
                    matchup_factors = {
                        'pace_multiplier': projection.matchup_adjustments.pace_multiplier,
                        'defense_adjustment': projection.matchup_adjustments.defense_adjustment
                    }
                
                # Calculate V2 confidence
                confidence_result = self.confidence_engine.calculate_confidence(
                    sample_size=databallr_stats['sample_size'],
                    historical_hit_rate=historical_hit_rate,
                    projected_probability=final_prob,
                    stat_mean=stat_mean,
                    stat_std_dev=stat_std_dev,
                    minutes_stable=minutes_stable,
                    role_change_detected=role_change_detected,
                    matchup_factors=matchup_factors,
                    injury_context=None
                )
                
                confidence = confidence_result.final_confidence
                final_prob = confidence_result.adjusted_probability
                
                # Recalculate edge and EV with adjusted probability
                edge = final_prob - implied_prob
                ev = (final_prob * (odds - 1)) - (1 - final_prob)
            else:
                # Fallback to old confidence calculation
                confidence = self._calculate_confidence(
                    model_confidence=projection.confidence_score,
                    sample_size=databallr_stats['sample_size'],
                    edge_pct=edge * 100
                )
            
            # Determine recommendation strength
            strength = self._get_recommendation_strength(confidence, ev * 100)
            
            # Only return if positive EV and sufficient confidence
            # V2 engine uses more realistic thresholds
            min_confidence = 55 if self.confidence_engine else 60
            if ev > 0 and confidence >= min_confidence:
                return BettingRecommendation(
                    game=f"{player_name}'s game",
                    match_time="TBD",
                    bet_type="player_prop",
                    market=f"{stat_type.replace('_', ' ').title()}",
                    selection=f"Over {line}",
                    odds=odds,
                    player_name=player_name,
                    stat_type=stat_type,
                    line=line,
                    historical_hit_rate=historical_hit_rate,
                    sample_size=databallr_stats['sample_size'],
                    projected_value=projection.expected_value,
                    projected_probability=final_prob,
                    model_confidence=projection.confidence_score,
                    implied_probability=implied_prob,
                    edge_percentage=edge * 100,
                    expected_value=ev * 100,
                    confidence_score=confidence,
                    recommendation_strength=strength,
                    databallr_stats={
                        'avg_value': databallr_stats['avg_value'],
                        'trend': databallr_stats['trend'],
                        'recent_avg': databallr_stats['recent_avg']
                    }
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"  Error projecting {player_name}: {e}")
            return None
    
    def _calculate_confidence(self, model_confidence: float, sample_size: int, edge_pct: float) -> float:
        """Calculate final confidence score"""
        import math
        
        # Base from model
        confidence = model_confidence
        
        # Boost for sample size
        if sample_size >= 15:
            confidence += 5
        elif sample_size >= 10:
            confidence += 3
        
        # Boost for edge
        if edge_pct > 5:
            confidence += 5
        elif edge_pct > 3:
            confidence += 3
        
        return min(95, confidence)
    
    def _get_recommendation_strength(self, confidence: float, ev_pct: float) -> str:
        """Determine recommendation strength (updated for V2 realistic confidence)"""
        # V2 confidence is more conservative, so adjust thresholds
        if confidence >= 75 and ev_pct >= 8:
            return "VERY_HIGH"
        elif confidence >= 65 and ev_pct >= 5:
            return "HIGH"
        elif confidence >= 55 and ev_pct >= 3:
            return "MEDIUM"
        else:
            return "LOW"


# ============================================================================
# MAIN PIPELINE
# ============================================================================

class NBAbettingPipeline:
    """Complete NBA betting analysis pipeline"""
    
    def __init__(self, headless: bool = True, min_confidence: float = 55.0, analyze_team_markets: bool = True):
        self.headless = headless
        self.min_confidence = min_confidence
        self.analyze_team_markets = analyze_team_markets
        
        self.sportsbet = SportsbetCollector(headless=headless)
        self.databallr = DataBallrValidator(headless=headless)
        self.projector = ValueProjector()
        
        # Initialize team betting engine
        if self.analyze_team_markets:
            try:
                from team_betting_engine import TeamBettingEngine
                self.team_engine = TeamBettingEngine()
                logger.info("✓ Team Betting Engine initialized")
            except ImportError:
                logger.warning("Team Betting Engine not available")
                self.team_engine = None
        else:
            self.team_engine = None
    
    def run(self, max_games: int = None) -> List[BettingRecommendation]:
        """
        Run complete pipeline
        
        Returns:
            List of high-confidence betting recommendations
        """
        logger.info("\n" + "=" * 80)
        logger.info("NBA BETTING SYSTEM - COMPLETE ANALYSIS")
        logger.info("=" * 80)
        
        # Step 1: Scrape Sportsbet
        games = self.sportsbet.collect_games(max_games=max_games)
        
        if not games:
            logger.error("No games to analyze")
            return []
        
        # Step 2 & 3: Validate and Project
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2 & 3: VALIDATING WITH DATABALLR & PROJECTING VALUE")
        logger.info("=" * 80)
        
        all_recommendations = []
        
        for i, game_data in enumerate(games, 1):
            game_info = game_data['game_info']
            logger.info(f"\n[{i}/{len(games)}] Analyzing: {game_info['away_team']} @ {game_info['home_team']}")
            
            # Analyze player props from insights (Sportsbet shows player stats in insights, not as separate markets)
            insights = game_data.get('insights', [])
            
            # Debug: Log all insights to see what we're working with
            logger.debug(f"  Total insights found: {len(insights)}")
            for idx, ins in enumerate(insights[:5], 1):  # Show first 5 for debugging
                logger.debug(f"    Insight {idx}: {getattr(ins, 'fact', '')[:60]}...")
            
            player_prop_insights = [ins for ins in insights if self._is_player_prop_insight(ins)]
            
            logger.info(f"  Found {len(player_prop_insights)} player prop insights out of {len(insights)} total insights")
            
            for insight in player_prop_insights:
                try:
                    # Extract prop details from insight
                    prop_details = self._parse_prop_from_insight(insight)
                    if not prop_details:
                        logger.debug(f"    ✗ Failed to parse insight")
                        continue
                    
                    player_name = prop_details['player']
                    stat_type = prop_details['stat']
                    line = prop_details['line']
                    odds = prop_details.get('odds', 1.90)  # Default odds if not in insight
                    
                    logger.debug(f"    → Processing: {player_name} {stat_type} Over {line}")
                    
                    # Validate with DataBallr
                    databallr_stats = self.databallr.validate_player_prop(
                        player_name=player_name,
                        stat_type=stat_type,
                        line=line
                    )
                    
                    if not databallr_stats:
                        logger.debug(f"    ✗ {player_name} - No DataBallr data")
                        continue
                    
                    # Project value
                    recommendation = self.projector.project_player_prop(
                        player_name=player_name,
                        stat_type=stat_type,
                        line=line,
                        odds=odds,
                        databallr_stats=databallr_stats,
                        match_stats=game_data.get('match_stats')
                    )
                    
                    if recommendation and recommendation.confidence_score >= self.min_confidence:
                        # Add game context
                        recommendation.game = f"{game_info['away_team']} @ {game_info['home_team']}"
                        recommendation.match_time = game_info.get('match_time', 'TBD')
                        
                        # Determine player's team and opponent
                        player_team, opponent = self._determine_player_team(
                            player_name, 
                            game_info['away_team'], 
                            game_info['home_team'],
                            databallr_stats
                        )
                        recommendation.player_team = player_team
                        recommendation.opponent_team = opponent
                        
                        # Add advanced context
                        recommendation.advanced_context = self._build_advanced_context(
                            player_name=player_name,
                            stat_type=stat_type,
                            databallr_stats=databallr_stats,
                            opponent_team=opponent,
                            match_stats=game_data.get('match_stats')
                        )
                        
                        # Add matchup analysis
                        if self.matchup_engine and opponent != "Unknown" and player_team != "Unknown":
                            try:
                                matchup_adj = self.matchup_engine.calculate_matchup_adjustment(
                                    player_name=player_name,
                                    stat_type=stat_type,
                                    opponent_team=opponent,
                                    player_team=player_team,
                                    game_log=databallr_stats.get('game_log')
                                )
                                
                                if not recommendation.matchup_factors:
                                    recommendation.matchup_factors = {}
                                
                                recommendation.matchup_factors.update({
                                    'pace_multiplier': matchup_adj.pace_multiplier,
                                    'defense_multiplier': matchup_adj.defense_multiplier,
                                    'blowout_risk': matchup_adj.blowout_risk_multiplier,
                                    'total_multiplier': matchup_adj.total_multiplier,
                                    'opponent_rank': matchup_adj.opponent_rank,
                                    'pace_rank': matchup_adj.pace_rank,
                                    'favorable_matchup': matchup_adj.favorable_matchup,
                                    'matchup_notes': matchup_adj.notes
                                })
                            except Exception as e:
                                logger.debug(f"    Could not add matchup analysis: {e}")
                        
                        all_recommendations.append(recommendation)
                        logger.info(f"    ✓ {player_name} ({player_team}) {stat_type} Over {line} @ {odds} - Confidence: {recommendation.confidence_score:.0f}%")
                    
                except Exception as e:
                    logger.debug(f"    Error processing prop: {e}")
                    continue
            
            # Analyze team markets (moneyline, totals, spreads)
            if self.team_engine and game_data.get('team_recent_results'):
                logger.info(f"  Analyzing team markets...")
                team_recommendations = self._analyze_team_markets(game_data)
                if team_recommendations:
                    all_recommendations.extend(team_recommendations)
                    logger.info(f"    ✓ Found {len(team_recommendations)} team market opportunities")
        
        # Rank and filter
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: RANKING RECOMMENDATIONS")
        logger.info("=" * 80)
        
        # Sort by projected probability (highest first)
        all_recommendations.sort(key=lambda x: x.projected_probability, reverse=True)
        
        # Apply correlation filter (max 2 bets per game)
        filtered_recommendations = self._apply_correlation_filter(all_recommendations)
        
        # Take top 5
        final_recommendations = filtered_recommendations[:5]
        
        logger.info(f"\n✓ Found {len(final_recommendations)} high-probability bets (sorted by projected %)")
        
        return final_recommendations
    
    def _parse_prop_market(self, market) -> Optional[Dict]:
        """Parse player prop market into structured data"""
        import re
        
        try:
            selection_text = str(getattr(market, 'selection_text', '') or getattr(market, 'name', ''))
            odds = getattr(market, 'odds', None)
            
            if not odds:
                return None
            
            # Extract player name
            player_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', selection_text)
            if not player_match:
                return None
            
            player_name = player_match.group(1).strip()
            
            # Extract stat and line
            stat_patterns = {
                'points': r'(\d+\.?\d*)\+?\s*points?',
                'rebounds': r'(\d+\.?\d*)\+?\s*rebounds?',
                'assists': r'(\d+\.?\d*)\+?\s*assists?',
                'steals': r'(\d+\.?\d*)\+?\s*steals?',
                'blocks': r'(\d+\.?\d*)\+?\s*blocks?',
                'three_pt_made': r'(\d+\.?\d*)\+?\s*(?:three|3)',
            }
            
            for stat, pattern in stat_patterns.items():
                match = re.search(pattern, selection_text.lower())
                if match:
                    line = float(match.group(1))
                    return {
                        'player': player_name,
                        'stat': stat,
                        'line': line,
                        'odds': odds
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing prop: {e}")
            return None
    
    def _is_player_prop_insight(self, insight) -> bool:
        """Check if insight is about a player prop"""
        fact = str(getattr(insight, 'fact', ''))
        result = str(getattr(insight, 'result', ''))
        market = str(getattr(insight, 'market', ''))
        
        import re
        
        # Method 1: Check for "Over/Under (+X.X) - Player Name Stat" format (most reliable)
        # Example: "Over (+3.5) - Anthony Edwards Made Threes"
        has_over_under_format = bool(re.search(r'(?:Over|Under)\s*\(\+?-?\d+\.?\d*\)\s*-\s*[A-Z]', market, re.IGNORECASE))
        
        if has_over_under_format:
            # This is definitely a player prop
            return True
        
        # Method 2: Check for player name in market/result with stat keywords
        combined_text = (fact + ' ' + result + ' ' + market).lower()
        
        # Player props mention specific stats
        stat_keywords = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-point', 'three-point', 
                        'three point', 'made threes', 'field goals', 'free throws']
        has_stat = any(keyword in combined_text for keyword in stat_keywords)
        
        # Player props have player names (2+ words, capitalized)
        has_player = bool(re.search(r'[A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2}', result + ' ' + market + ' ' + fact))
        
        # Exclude team-level insights by checking if team name appears in the market/title
        # Team insights typically have format like "Minnesota Timberwolves - Match" or mention team in market
        team_keywords = ['warriors', 'lakers', 'celtics', 'nets', 'heat', 'bulls', 'knicks', 'sixers', '76ers', 
                        'raptors', 'bucks', 'pacers', 'pistons', 'cavaliers', 'wizards', 'hornets', 'hawks',
                        'magic', 'spurs', 'mavericks', 'rockets', 'grizzlies', 'pelicans', 'thunder', 'jazz',
                        'nuggets', 'timberwolves', 'trail blazers', 'suns', 'kings', 'clippers']
        
        # Check if market contains team name (team insights have team in market, player props have player name)
        market_lower = market.lower()
        has_team_in_market = any(team in market_lower for team in team_keywords)
        
        # Also check for "- Match" suffix which indicates team insight
        is_match_insight = '- match' in market_lower or 'match' in result.lower()
        
        return has_stat and has_player and not has_team_in_market and not is_match_insight
    
    def _parse_prop_from_insight(self, insight) -> Optional[Dict]:
        """Extract player prop details from insight"""
        import re
        
        fact = str(getattr(insight, 'fact', ''))
        result = str(getattr(insight, 'result', ''))
        market = str(getattr(insight, 'market', ''))
        odds = getattr(insight, 'odds', None)
        
        # Debug logging
        logger.debug(f"    Parsing insight:")
        logger.debug(f"      Market: {market}")
        logger.debug(f"      Fact: {fact[:80]}...")
        logger.debug(f"      Result: {result}")
        logger.debug(f"      Odds: {odds}")
        
        # METHOD 1: Parse "Over/Under (+X.X) - Player Name Stat Type" format
        # Example: "Over (+3.5) - Anthony Edwards Made Threes"
        # Split on the dash first, then extract player name and stat separately
        market_split = re.split(r'\s*-\s*', market, maxsplit=1)
        player_name = None
        stat_description = None
        over_under = None
        line = None
        
        if len(market_split) == 2:
            line_part = market_split[0]  # "Over (+3.5)"
            player_stat_part = market_split[1]  # "Anthony Edwards Made Threes"
            
            # Extract over/under and line from first part
            line_match = re.search(r'(Over|Under)\s*\(\+?(-?\d+\.?\d*)\)', line_part, re.IGNORECASE)
            if line_match:
                over_under = line_match.group(1).lower()
                line = float(line_match.group(2))
                
                # Extract player name (everything before stat keywords)
                stat_keywords_pattern = r'\b(Made|Points?|Rebounds?|Assists?|Steals?|Blocks?|Threes?|3-Point|Field Goals)\b'
                stat_match = re.search(stat_keywords_pattern, player_stat_part, re.IGNORECASE)
                
                if stat_match:
                    player_name = player_stat_part[:stat_match.start()].strip()
                    stat_description = player_stat_part[stat_match.start():].strip().lower()
        
        if player_name and stat_description and line is not None:
            
            # Map stat description to stat type
            stat_type = None
            if 'point' in stat_description:
                stat_type = 'points'
            elif 'rebound' in stat_description:
                stat_type = 'rebounds'
            elif 'assist' in stat_description:
                stat_type = 'assists'
            elif 'steal' in stat_description:
                stat_type = 'steals'
            elif 'block' in stat_description:
                stat_type = 'blocks'
            elif 'three' in stat_description or 'threes' in stat_description or '3' in stat_description:
                stat_type = 'three_pt_made'
            
            if stat_type:
                logger.debug(f"    ✓ Parsed (Method 1): {player_name} {stat_type} {over_under.title()} {line} @ {odds if odds else 1.90}")
                return {
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'odds': odds if odds else 1.90,
                    'direction': over_under
                }
        
        # METHOD 2: Extract from result/fact (fallback for other formats)
        # Extract player name from result or market (handle various formats)
        player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', result)
        if not player_match:
            player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', market)
        if not player_match:
            player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', fact)
        
        if not player_match:
            logger.debug(f"    ✗ No player name found")
            return None
        
        player_name = player_match.group(1).strip()
        
        # Extract stat type and line from fact or market
        stat_patterns = {
            'points': r'(?:over\s+)?(\d+\.?\d*)\+?\s*points?',
            'rebounds': r'(?:over\s+)?(\d+\.?\d*)\+?\s*rebounds?',
            'assists': r'(?:over\s+)?(\d+\.?\d*)\+?\s*assists?',
            'steals': r'(?:over\s+)?(\d+\.?\d*)\+?\s*steals?',
            'blocks': r'(?:over\s+)?(\d+\.?\d*)\+?\s*blocks?',
            'three_pt_made': r'(?:over\s+)?(\d+\.?\d*)\+?\s*(?:three|3-point|threes|three-pointer)',
        }
        
        search_text = (fact + ' ' + market + ' ' + result).lower()
        for stat, pattern in stat_patterns.items():
            match = re.search(pattern, search_text)
            if match:
                line = float(match.group(1))
                
                # If line is a whole number with "+", it means "X or more", so use X-0.5 as the line
                # If line already has decimal (e.g., 5.5), use as-is
                if '.' not in match.group(1) and '+' in search_text:
                    line = line - 0.5
                
                logger.debug(f"    ✓ Parsed (Method 2): {player_name} {stat} Over {line} @ {odds if odds else 1.90}")
                
                return {
                    'player': player_name,
                    'stat': stat,
                    'line': line,
                    'odds': odds if odds else 1.90,
                    'direction': 'over'
                }
        
        logger.debug(f"    ✗ No stat pattern matched")
        return None
    
    def _determine_player_team(self, player_name: str, away_team: str, home_team: str, databallr_stats: Dict) -> tuple:
        """
        Determine which team the player is on and who the opponent is.
        Uses game log data to infer team.
        """
        # Try to infer from recent games in databallr stats
        if databallr_stats and 'game_log' in databallr_stats:
            game_log = databallr_stats['game_log']
            if game_log and len(game_log) > 0:
                # Check most recent game's matchup
                recent_game = game_log[0]
                matchup = getattr(recent_game, 'matchup', '')
                
                # Matchup format is usually "TEAM vs OPP" or "TEAM @ OPP"
                if away_team.split()[-1].upper() in matchup.upper():
                    return away_team, home_team
                elif home_team.split()[-1].upper() in matchup.upper():
                    return home_team, away_team
        
        # Fallback: return unknown
        return "Unknown", "Unknown"
    
    def _build_advanced_context(self, player_name: str, stat_type: str, databallr_stats: Dict, 
                                opponent_team: str, match_stats: Optional[Dict]) -> Dict:
        """
        Build advanced contextual factors for the recommendation.
        
        Includes:
        - On/off splits (if available)
        - Expected opportunities
        - Defensive matchup notes
        - Rotation/minutes stability
        """
        context = {}
        
        if not databallr_stats or 'game_log' not in databallr_stats:
            return context
        
        game_log = databallr_stats['game_log']
        
        # Minutes stability analysis
        minutes_list = [g.minutes for g in game_log if g.minutes > 0]
        if len(minutes_list) >= 5:
            recent_minutes = minutes_list[:5]
            season_avg_minutes = sum(minutes_list) / len(minutes_list)
            recent_avg_minutes = sum(recent_minutes) / len(recent_minutes)
            minutes_variance = max(recent_minutes) - min(recent_minutes)
            
            context['minutes_analysis'] = {
                'season_avg': round(season_avg_minutes, 1),
                'recent_avg': round(recent_avg_minutes, 1),
                'variance': round(minutes_variance, 1),
                'stable': minutes_variance < 8,  # Less than 8 min variance = stable
                'trending': 'up' if recent_avg_minutes > season_avg_minutes else 'down' if recent_avg_minutes < season_avg_minutes else 'stable'
            }
        
        # Stat-specific analysis
        if stat_type == 'assists':
            # Assist rate and opportunities
            assists_list = [g.assists for g in game_log if g.minutes >= 10]
            if len(assists_list) >= 5:
                recent_assists = assists_list[:5]
                
                # Calculate per-36 rate for normalization
                per_36_assists = []
                for g in game_log[:10]:
                    if g.minutes >= 10:
                        per_36 = (g.assists / g.minutes) * 36
                        per_36_assists.append(per_36)
                
                if per_36_assists:
                    context['assist_context'] = {
                        'per_36_rate': round(sum(per_36_assists) / len(per_36_assists), 2),
                        'recent_form': round(sum(recent_assists) / len(recent_assists), 1),
                        'consistency': round((sum(1 for a in recent_assists if a >= databallr_stats.get('avg_value', 0) - 1) / len(recent_assists)) * 100, 0),
                        'high_assist_games': sum(1 for a in assists_list if a >= 8)  # 8+ assist games
                    }
        
        elif stat_type == 'points':
            # Scoring efficiency
            points_list = [g.points for g in game_log if g.minutes >= 10]
            if len(points_list) >= 5:
                recent_points = points_list[:5]
                
                context['scoring_context'] = {
                    'recent_form': round(sum(recent_points) / len(recent_points), 1),
                    'consistency': round((sum(1 for p in recent_points if p >= databallr_stats.get('avg_value', 0) - 3) / len(recent_points)) * 100, 0),
                    'high_scoring_games': sum(1 for p in points_list if p >= 25)  # 25+ point games
                }
        
        elif stat_type == 'rebounds':
            # Rebounding analysis
            rebounds_list = [g.rebounds for g in game_log if g.minutes >= 10]
            if len(rebounds_list) >= 5:
                recent_rebounds = rebounds_list[:5]
                
                context['rebounding_context'] = {
                    'recent_form': round(sum(recent_rebounds) / len(recent_rebounds), 1),
                    'consistency': round((sum(1 for r in recent_rebounds if r >= databallr_stats.get('avg_value', 0) - 1) / len(recent_rebounds)) * 100, 0),
                    'double_digit_games': sum(1 for r in rebounds_list if r >= 10)
                }
        
        # Opponent defensive context (if match_stats available)
        if match_stats and opponent_team != "Unknown":
            context['defensive_matchup'] = {
                'opponent': opponent_team,
                'note': f"Check {opponent_team}'s defensive scheme vs {stat_type}"
            }
            
            # Try to extract opponent defensive stats
            try:
                if isinstance(match_stats, dict):
                    away_stats = match_stats.get('away_team_stats', {})
                    home_stats = match_stats.get('home_team_stats', {})
                    
                    # Find opponent stats
                    opp_stats = None
                    if isinstance(away_stats, dict) and away_stats.get('team_name') == opponent_team:
                        opp_stats = away_stats
                    elif isinstance(home_stats, dict) and home_stats.get('team_name') == opponent_team:
                        opp_stats = home_stats
                    
                    if opp_stats:
                        context['defensive_matchup']['avg_points_allowed'] = opp_stats.get('avg_points_against')
            except:
                pass
        
        return context
    
    def _analyze_team_markets(self, game_data: Dict) -> List[BettingRecommendation]:
        """
        Analyze team-level markets (moneyline, totals, spreads) using recent results.
        
        Returns:
            List of team market betting recommendations
        """
        from team_betting_engine import MarketType
        
        recommendations = []
        
        try:
            game_info = game_data['game_info']
            team_results = game_data.get('team_recent_results')
            team_markets = game_data.get('team_markets', [])
            
            if not team_results:
                return recommendations
            
            home_team = game_info['home_team']
            away_team = game_info['away_team']
            
            # Analyze team form
            home_form = None
            away_form = None
            
            if team_results.get('home_results') and len(team_results['home_results']) >= 5:
                home_form = self.team_engine.analyze_team_form(home_team, team_results['home_results'])
                logger.debug(f"    {home_team}: {home_form.avg_points_scored:.1f} ppg, {home_form.win_pct:.1%} win rate, {home_form.streak}")
            
            if team_results.get('away_results') and len(team_results['away_results']) >= 5:
                away_form = self.team_engine.analyze_team_form(away_team, team_results['away_results'])
                logger.debug(f"    {away_team}: {away_form.avg_points_scored:.1f} ppg, {away_form.win_pct:.1%} win rate, {away_form.streak}")
            
            if not home_form or not away_form:
                logger.debug(f"    Insufficient team data for projections")
                return recommendations
            
            # Project game
            projection = self.team_engine.project_game(
                home_team=home_team,
                away_team=away_team,
                home_form=home_form,
                away_form=away_form
            )
            
            logger.debug(f"    Projected: {away_team} {projection.projected_away_score:.1f} @ {home_team} {projection.projected_home_score:.1f}")
            logger.debug(f"    Total: {projection.projected_total:.1f}, Margin: {projection.projected_margin:+.1f}")
            
            # Find relevant markets and evaluate
            for market in team_markets:
                market_name = str(getattr(market, 'market_name', '') or getattr(market, 'name', '')).lower()
                selection = str(getattr(market, 'selection_text', '') or getattr(market, 'selection', ''))
                odds = getattr(market, 'odds', None)
                
                if not odds or odds < 1.5:  # Skip invalid odds
                    continue
                
                # Moneyline
                if 'head to head' in market_name or 'money line' in market_name or 'winner' in market_name:
                    if home_team.lower() in selection.lower():
                        bet = self.team_engine.evaluate_bet(
                            projection=projection,
                            market_type=MarketType.MONEYLINE,
                            line=0,
                            odds=odds,
                            selection=f"{home_team} ML"
                        )
                        if bet and bet.confidence_score >= self.min_confidence:
                            recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
                    
                    elif away_team.lower() in selection.lower():
                        bet = self.team_engine.evaluate_bet(
                            projection=projection,
                            market_type=MarketType.MONEYLINE,
                            line=0,
                            odds=odds,
                            selection=f"{away_team} ML"
                        )
                        if bet and bet.confidence_score >= self.min_confidence:
                            recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
                
                # Totals
                elif 'total points' in market_name or 'over/under' in market_name:
                    import re
                    line_match = re.search(r'(\d+\.?\d*)', selection)
                    if line_match:
                        line = float(line_match.group(1))
                        
                        if 'over' in selection.lower():
                            bet = self.team_engine.evaluate_bet(
                                projection=projection,
                                market_type=MarketType.TOTAL,
                                line=line,
                                odds=odds,
                                selection=f"Over {line}"
                            )
                            if bet and bet.confidence_score >= self.min_confidence:
                                recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
                        
                        elif 'under' in selection.lower():
                            bet = self.team_engine.evaluate_bet(
                                projection=projection,
                                market_type=MarketType.TOTAL,
                                line=line,
                                odds=odds,
                                selection=f"Under {line}"
                            )
                            if bet and bet.confidence_score >= self.min_confidence:
                                recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
                
                # Spreads/Handicaps
                elif 'line' in market_name or 'spread' in market_name or 'handicap' in market_name:
                    import re
                    line_match = re.search(r'([+-]?\d+\.?\d*)', selection)
                    if line_match:
                        line = float(line_match.group(1))
                        
                        # Determine which team
                        if home_team.lower() in selection.lower():
                            bet = self.team_engine.evaluate_bet(
                                projection=projection,
                                market_type=MarketType.SPREAD,
                                line=line,
                                odds=odds,
                                selection=f"{home_team} {line:+.1f}"
                            )
                            if bet and bet.confidence_score >= self.min_confidence:
                                recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
                        
                        elif away_team.lower() in selection.lower():
                            bet = self.team_engine.evaluate_bet(
                                projection=projection,
                                market_type=MarketType.SPREAD,
                                line=-line,  # Flip for away team
                                odds=odds,
                                selection=f"{away_team} {-line:+.1f}"
                            )
                            if bet and bet.confidence_score >= self.min_confidence:
                                recommendations.append(self._convert_team_bet_to_recommendation(bet, game_info))
        
        except Exception as e:
            logger.debug(f"    Error analyzing team markets: {e}")
        
        return recommendations
    
    def _convert_team_bet_to_recommendation(self, team_bet, game_info: Dict) -> BettingRecommendation:
        """Convert team betting recommendation to standard BettingRecommendation format"""
        return BettingRecommendation(
            game=f"{game_info['away_team']} @ {game_info['home_team']}",
            match_time=game_info.get('match_time', 'TBD'),
            bet_type=f"team_{team_bet.market_type.value}",
            market=team_bet.market_type.value.title(),
            selection=team_bet.selection,
            odds=team_bet.odds,
            projected_probability=team_bet.projected_probability,
            implied_probability=team_bet.implied_probability,
            edge_percentage=team_bet.edge_percentage,
            expected_value=team_bet.expected_value,
            confidence_score=team_bet.confidence_score,
            recommendation_strength=team_bet.recommendation_strength,
            sportsbet_insight="\n".join(team_bet.reasoning),
            advanced_context={
                'projection': {
                    'home_score': team_bet.projection.projected_home_score,
                    'away_score': team_bet.projection.projected_away_score,
                    'total': team_bet.projection.projected_total,
                    'margin': team_bet.projection.projected_margin,
                    'home_win_prob': team_bet.projection.home_win_probability,
                    'away_win_prob': team_bet.projection.away_win_probability
                },
                'notes': team_bet.projection.notes
            }
        )
    
    def _apply_correlation_filter(self, recommendations: List[BettingRecommendation], max_per_game: int = 2) -> List[BettingRecommendation]:
        """Limit bets per game to avoid correlation"""
        game_counts = {}
        filtered = []
        
        for rec in recommendations:
            game = rec.game
            count = game_counts.get(game, 0)
            
            if count < max_per_game:
                filtered.append(rec)
                game_counts[game] = count + 1
        
        return filtered


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="NBA Betting System - Complete Analysis Pipeline")
    parser.add_argument('--games', type=int, default=None, help="Number of games to analyze (default: all)")
    parser.add_argument('--min-confidence', type=float, default=55.0, help="Minimum confidence threshold (default: 55, V2 uses realistic scoring)")
    parser.add_argument('--headless', action='store_true', default=True, help="Run browser in headless mode")
    parser.add_argument('--output', type=str, default='betting_recommendations.json', help="Output file")
    parser.add_argument('--team-markets', action='store_true', default=True, help="Analyze team markets (moneyline, totals, spreads)")
    parser.add_argument('--player-props-only', action='store_true', help="Only analyze player props (skip team markets)")
    parser.add_argument('--enhanced', action='store_true', help="Use enhanced filtering and tier classification")
    parser.add_argument('--min-tier', type=str, default='C', choices=['S', 'A', 'B', 'C'], help="Minimum quality tier (default: C)")

    args = parser.parse_args()

    # Run pipeline
    pipeline = NBAbettingPipeline(
        headless=args.headless,
        min_confidence=args.min_confidence,
        analyze_team_markets=args.team_markets and not args.player_props_only
    )

    recommendations = pipeline.run(max_games=args.games)

    # Apply enhanced filtering if requested
    if args.enhanced:
        logger.info("\n" + "=" * 80)
        logger.info("APPLYING ENHANCED FILTERING & TIER CLASSIFICATION")
        logger.info("=" * 80)

        from bet_enhancement_system import BetEnhancementSystem, QualityTier

        # Convert recommendations to dicts
        rec_dicts = [rec.to_dict() for rec in recommendations]

        # Enhance
        enhancer = BetEnhancementSystem()
        enhanced_bets = enhancer.enhance_recommendations(rec_dicts)

        # Map tier string to enum
        tier_map = {
            'S': QualityTier.S,
            'A': QualityTier.A,
            'B': QualityTier.B,
            'C': QualityTier.C
        }
        min_tier = tier_map.get(args.min_tier, QualityTier.C)

        # Filter
        quality_bets = enhancer.filter_bets(enhanced_bets, min_tier=min_tier, exclude_d_tier=True)

        logger.info(f"Enhanced: {len(enhanced_bets)} total → {len(quality_bets)} quality bets ({args.min_tier}-Tier or better)")

        # Display enhanced bets
        enhancer.display_enhanced_bets(quality_bets, max_display=20)

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

        # Save enhanced output
        enhanced_path = args.output.replace('.json', '_enhanced.json')
        with open(enhanced_path, 'w') as f:
            json.dump(enhanced_output, f, indent=2, default=str)

        logger.info(f"\n✓ Saved {len(enhanced_output)} enhanced recommendations to {enhanced_path}")

        return  # Skip normal display
    
    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("FINAL RECOMMENDATIONS")
    logger.info("=" * 80)
    
    if not recommendations:
        logger.info("No high-confidence bets found")
        return
    
    for i, rec in enumerate(recommendations, 1):
        # Check if this is a team market or player prop
        is_team_market = rec.bet_type.startswith('team_')
        
        if is_team_market:
            logger.info(f"\n{i}. TEAM MARKET: {rec.market} - {rec.selection}")
            logger.info(f"   Game: {rec.game} ({rec.match_time})")
            logger.info(f"   Odds: {rec.odds} | Confidence: {rec.confidence_score:.0f}% | Strength: {rec.recommendation_strength}")
            logger.info(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")
            logger.info(f"   Projected Probability: {rec.projected_probability:.1%}")
            
            # Show projection details
            if rec.advanced_context and 'projection' in rec.advanced_context:
                proj = rec.advanced_context['projection']
                logger.info(f"   Projected Score: {proj['away_score']:.1f} - {proj['home_score']:.1f}")
                logger.info(f"   Projected Total: {proj['total']:.1f} | Margin: {proj['margin']:+.1f}")
            
            # Show reasoning
            if rec.sportsbet_insight:
                logger.info(f"   Reasoning:")
                for line in rec.sportsbet_insight.split('\n')[:3]:  # Show first 3 reasons
                    logger.info(f"     • {line}")
        else:
            logger.info(f"\n{i}. {rec.player_name} ({rec.player_team}) - {rec.market} {rec.selection}")
            logger.info(f"   Game: {rec.game} ({rec.match_time})")
            logger.info(f"   Matchup: vs {rec.opponent_team}")
            logger.info(f"   Odds: {rec.odds} | Confidence: {rec.confidence_score:.0f}% | Strength: {rec.recommendation_strength}")
            logger.info(f"   Edge: {rec.edge_percentage:+.1f}% | EV: {rec.expected_value:+.1f}%")
            logger.info(f"   Historical: {rec.historical_hit_rate:.1%} ({rec.sample_size} games)")
            logger.info(f"   Projected: {rec.projected_probability:.1%}")
        
        # Show advanced context if available
        if rec.advanced_context:
            ctx = rec.advanced_context
            
            # Minutes analysis
            if 'minutes_analysis' in ctx:
                mins = ctx['minutes_analysis']
                stability = "STABLE" if mins.get('stable') else "VARIABLE"
                logger.info(f"   Minutes: {mins.get('recent_avg')}min avg (last 5), {stability} rotation")
            
            # Stat-specific context
            if 'assist_context' in ctx:
                ast = ctx['assist_context']
                logger.info(f"   Assist Rate: {ast.get('per_36_rate')}/36min | Consistency: {ast.get('consistency'):.0f}%")
                logger.info(f"   High-Assist Games: {ast.get('high_assist_games')} games with 8+ assists")
            
            if 'scoring_context' in ctx:
                pts = ctx['scoring_context']
                logger.info(f"   Scoring: {pts.get('recent_form')} ppg (last 5) | Consistency: {pts.get('consistency'):.0f}%")
            
            if 'rebounding_context' in ctx:
                reb = ctx['rebounding_context']
                logger.info(f"   Rebounding: {reb.get('recent_form')} rpg (last 5) | Double-doubles: {reb.get('double_digit_games')}")
            
            # Defensive matchup
            if 'defensive_matchup' in ctx:
                defense = ctx['defensive_matchup']
                logger.info(f"   Defense: {defense.get('note')}")
                if 'avg_points_allowed' in defense:
                    logger.info(f"   {rec.opponent_team} allows {defense['avg_points_allowed']:.1f} ppg")
        
        # Show matchup factors if available
        if rec.matchup_factors:
            mf = rec.matchup_factors
            if mf.get('total_multiplier'):
                logger.info(f"   Matchup: {mf['total_multiplier']:.2f}x multiplier", end="")
                if mf.get('favorable_matchup'):
                    logger.info(" (FAVORABLE)", end="")
                logger.info("")
                
                if mf.get('pace_multiplier') and abs(mf['pace_multiplier'] - 1.0) > 0.03:
                    pace_desc = "Fast" if mf['pace_multiplier'] > 1.0 else "Slow"
                    logger.info(f"   Pace: {pace_desc} ({mf['pace_multiplier']:.2f}x)")
                
                if mf.get('defense_multiplier') and abs(mf['defense_multiplier'] - 1.0) > 0.03:
                    def_desc = "Weak" if mf['defense_multiplier'] > 1.0 else "Strong"
                    logger.info(f"   Defense: {def_desc} vs {rec.stat_type} ({mf['defense_multiplier']:.2f}x, rank {mf.get('opponent_rank', '?')})")
                
                if mf.get('blowout_risk') and mf['blowout_risk'] < 0.98:
                    logger.info(f"   Blowout Risk: {(1-mf['blowout_risk'])*100:.0f}% reduction")
                
                if mf.get('matchup_notes'):
                    for note in mf['matchup_notes'][:2]:  # Show first 2 notes
                        logger.info(f"   • {note}")
    
    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump([rec.to_dict() for rec in recommendations], f, indent=2, default=str)
    
    logger.info(f"\n✓ Saved {len(recommendations)} recommendations to {output_path}")


if __name__ == "__main__":
    main()
