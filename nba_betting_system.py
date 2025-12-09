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
import re
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

# Import configuration
from config import Config

# Setup logging with rotation to prevent large log files
from utils.logging_config import setup_logger
from utils.error_handling import safe_call, handle_import_error, log_and_continue

logger = setup_logger(
    "nba_betting_system",
    log_file=Config.LOG_FILE,
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    max_bytes=Config.LOG_MAX_BYTES,
    backup_count=Config.LOG_BACKUP_COUNT
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

# Import data models from models module
from models import BettingRecommendation

# Import collectors and engines from nba_betting module
from nba_betting.collectors import SportsbetCollector, DataBallrValidator
from nba_betting.engines import ValueProjector


# ============================================================================
# DATA COLLECTORS, VALIDATORS, AND PROJECTION ENGINES
# ============================================================================
# NOTE: All class definitions have been moved to modular structure:
#   - SportsbetCollector -> nba_betting.collectors
#   - DataBallrValidator -> nba_betting.collectors
#   - ValueProjector -> nba_betting.engines
# They are imported at the top for use in the pipeline.



class NBAbettingPipeline:
    """Complete NBA betting analysis pipeline"""
    
    def __init__(self, headless: bool = None, min_confidence: float = None, analyze_team_markets: bool = True):
        # Use config defaults if not provided
        self.headless = headless if headless is not None else Config.HEADLESS_MODE
        self.min_confidence = min_confidence if min_confidence is not None else Config.MIN_CONFIDENCE
        self.analyze_team_markets = analyze_team_markets
        
        self.sportsbet = SportsbetCollector(headless=headless)
        self.databallr = DataBallrValidator(headless=headless)
        self.projector = ValueProjector()
        
        # Get matchup engine from projector if available
        self.matchup_engine = getattr(self.projector, 'matchup_engine', None)
        
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
            
            parsed_count = 0
            failed_parse_count = 0
            no_data_count = 0
            rejected_count = 0
            accepted_count = 0
            
            for insight in player_prop_insights:
                try:
                    # Extract prop details from insight
                    prop_details = self._parse_prop_from_insight(insight)
                    if not prop_details:
                        failed_parse_count += 1
                        logger.debug(f"    ✗ Failed to parse insight")
                        continue
                    
                    parsed_count += 1
                    
                    try:
                        player_name = prop_details['player']
                        stat_type = prop_details['stat']
                        line = prop_details['line']
                        odds = prop_details.get('odds', 1.90)  # Default odds if not in insight
                    except KeyError as e:
                        logger.warning(f"    ✗ Missing key in prop_details: {e}, keys: {prop_details.keys()}")
                        continue
                    
                    # Clean up player name (remove any trailing "To Record", "To Score", or just "To")
                    try:
                        # Remove " To Record", " To Score", or just " To" at the end
                        player_name = re.sub(r'\s+To\s+(?:Record|Score).*$', '', player_name, flags=re.IGNORECASE).strip()
                        player_name = re.sub(r'\s+To$', '', player_name, flags=re.IGNORECASE).strip()
                    except Exception as e:
                        logger.warning(f"    ✗ Error cleaning player name '{player_name}': {e}")
                        continue
                    
                    # Normalize player name to match DataBallr cache format
                    # DataBallr normalizes: lowercase, remove periods, remove double spaces, trim
                    try:
                        normalized_player_name = self._normalize_player_name_for_databallr(player_name)
                    except Exception as e:
                        logger.warning(f"    ✗ Error normalizing player name '{player_name}': {e}")
                        continue
                    
                    logger.info(f"    → Processing: {player_name} ({normalized_player_name}) {stat_type} Over {line} @ {odds}")
                    
                    # Validate with DataBallr (use normalized name)
                    databallr_stats = self.databallr.validate_player_prop(
                        player_name=normalized_player_name,
                        stat_type=stat_type,
                        line=line
                    )
                    
                    if not databallr_stats:
                        no_data_count += 1
                        logger.debug(f"    ✗ {player_name} - No DataBallr data available")
                        continue
                    
                    logger.info(f"    ✓ DataBallr data found: {databallr_stats.get('sample_size', 0)} games, {databallr_stats.get('hit_rate', 0):.1%} hit rate")
                    
                    # Project value
                    recommendation = self.projector.project_player_prop(
                        player_name=player_name,
                        stat_type=stat_type,
                        line=line,
                        odds=odds,
                        databallr_stats=databallr_stats,
                        match_stats=game_data.get('match_stats')
                    )
                    
                    if not recommendation:
                        rejected_count += 1
                        logger.debug(f"    ✗ {player_name} - Projection returned None (likely EV <= -2% or confidence < {self.min_confidence}%)")
                        continue
                    
                    if recommendation.confidence_score < self.min_confidence:
                        rejected_count += 1
                        logger.debug(f"    ✗ {player_name} - Confidence {recommendation.confidence_score:.0f}% below threshold {self.min_confidence}%")
                        continue
                    
                    accepted_count += 1
                    
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
                    import traceback
                    logger.warning(f"    ✗ Error processing prop: {e}")
                    logger.debug(f"    Full traceback: {traceback.format_exc()}")
                    continue
            
            # Summary of processing
            logger.info(f"  Processing summary: {parsed_count} parsed, {failed_parse_count} failed parse, {no_data_count} no data, {rejected_count} rejected, {accepted_count} accepted")
            
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
        
        # Apply correlation filter (max 3 bets per game - relaxed for more options)
        filtered_recommendations = self._apply_correlation_filter(all_recommendations, max_per_game=3)
        
        # Don't limit to top 5 - let all pass through to enhanced filtering
        # Enhanced filtering will apply quality tiers and final selection
        final_recommendations = filtered_recommendations
        
        logger.info(f"\n✓ Found {len(final_recommendations)} bets passing initial filters (will be filtered by enhanced system)")
        
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
        
        # Debug logging (reduced verbosity)
        logger.debug(f"    Parsing insight: Market={market}, Result={result}, Odds={odds}")
        
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
                # Handle "Made Threes" as a special case (two words)
                stat_keywords_pattern = r'\b(Made\s+Threes?|Points?|Rebounds?|Assists?|Steals?|Blocks?|Threes?|3-Point|Field\s+Goals)\b'
                stat_match = re.search(stat_keywords_pattern, player_stat_part, re.IGNORECASE)
                
                if stat_match:
                    player_name = player_stat_part[:stat_match.start()].strip()
                    stat_description = player_stat_part[stat_match.start():].strip().lower()
                    # Normalize "Made Threes" to just "threes" for stat type mapping
                    if 'made threes' in stat_description:
                        stat_description = 'threes'
        
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
                logger.info(f"    ✓ Parsed (Method 1): {player_name} {stat_type} {over_under.title()} {line} @ {odds if odds else 1.90}")
                return {
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'odds': odds if odds else 1.90,
                    'direction': over_under
                }
        
        # METHOD 2: Handle "Player Name Made Threes" or "Player Name To Record X+ Stat" formats
        # Try to extract player name from market first (most reliable)
        # Pattern: "First Last" or "T.J. Last" or "First 'Nickname' Last"
        player_name_patterns = [
            r'^([A-Z][a-zA-Z\'-]+(?:\.[A-Z]\.)?(?:\s+[A-Z][a-zA-Z\'-]+){1,2})',  # Start of market
            r'([A-Z][a-zA-Z\'-]+(?:\.[A-Z]\.)?(?:\s+[A-Z][a-zA-Z\'-]+){1,2})\s+(?:Made|To Record|To Score)',  # Before "Made/To Record"
        ]
        
        player_name = None
        for pattern in player_name_patterns:
            player_match = re.search(pattern, market)
            if player_match:
                player_name = player_match.group(1).strip()
                # Clean up common suffixes
                player_name = re.sub(r'\s+To\s+Record$', '', player_name, flags=re.IGNORECASE)
                break
        
        # Fallback to result or fact if not found in market
        if not player_name:
            player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\.[A-Z]\.)?(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', result)
            if player_match:
                player_name = player_match.group(1).strip()
            else:
                player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\.[A-Z]\.)?(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', fact)
                if player_match:
                    player_name = player_match.group(1).strip()
        
        if not player_name:
            logger.info(f"    ✗ No player name found in result/market/fact")
            return None
        
        # Extract stat type and line from fact or market
        # First, check market for "To Record X+" or "To Score X+" format
        market_lower = market.lower()
        stat_type = None
        line = None
        
        # Check for "To Record X+ Stat" or "To Score X+ Points" format in market
        record_match = re.search(r'to\s+(?:record|score)\s+(\d+)\+?\s*(points|rebounds|assists|steals|blocks|threes?)', market_lower)
        if record_match:
            line = float(record_match.group(1))
            stat_word = record_match.group(2)
            # Map to stat type
            if 'point' in stat_word:
                stat_type = 'points'
            elif 'rebound' in stat_word:
                stat_type = 'rebounds'
            elif 'assist' in stat_word:
                stat_type = 'assists'
            elif 'steal' in stat_word:
                stat_type = 'steals'
            elif 'block' in stat_word:
                stat_type = 'blocks'
            elif 'three' in stat_word:
                stat_type = 'three_pt_made'
            
            # If line is whole number with "+", use X-0.5
            if '+' in market_lower or 'or more' in market_lower:
                line = line - 0.5
        
        # If not found in market, check for "Made Threes" format and extract from fact
        if not stat_type and 'made threes' in market_lower:
            stat_type = 'three_pt_made'
            # Extract line from fact: "has made two three-pointers" or "three or more"
            three_match = re.search(r'(?:made|has made)\s+(\d+)\s*(?:or more\s+)?(?:three|3-point)', fact.lower())
            if three_match:
                line = float(three_match.group(1))
                if 'or more' in fact.lower():
                    line = line - 0.5
        
        # Fallback: Extract from fact/market using standard patterns
        if not stat_type or line is None:
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
                    stat_type = stat
                    
                    # If line is a whole number with "+", it means "X or more", so use X-0.5 as the line
                    # If line already has decimal (e.g., 5.5), use as-is
                    if '.' not in match.group(1) and ('+' in search_text or 'or more' in search_text):
                        line = line - 0.5
                    break
        
        if stat_type and line is not None:
            logger.info(f"    ✓ Parsed (Method 2): {player_name} {stat_type} Over {line} @ {odds if odds else 1.90}")
            
            return {
                'player': player_name,
                'stat': stat_type,
                'line': line,
                'odds': odds if odds else 1.90,
                'direction': 'over'
            }
        
        logger.info(f"    ✗ No stat pattern matched in fact/market/result")
        return None
    
    def _normalize_player_name_for_databallr(self, player_name: str) -> str:
        """
        Normalize player name to match DataBallr cache format.
        
        DataBallr cache uses: lowercase, remove periods, remove double spaces, trim
        This matches the normalization in scrapers/databallr_scraper.py:_get_player_id()
        
        Examples:
        - "T.J. McConnell" -> "tj mcconnell"
        - "De'Aaron Fox" -> "de'aaron fox" (apostrophe kept for cache lookup)
        - "LeBron James" -> "lebron james"
        - "McConnell To Record" -> "mcconnell to record" (should be cleaned before this)
        """
        if not player_name:
            return ""
        
        # Lowercase
        normalized = player_name.lower()
        
        # Remove ALL punctuation (including periods, apostrophes, etc.)
        # This matches the cache normalization: re.sub(r'[^\w\s]', '', normalized)
        # DataBallr cache removes all punctuation, so "De'Aaron Fox" -> "deaaron fox"
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common suffixes that might be in the name
        normalized = re.sub(r'\s+(jr|sr|iii|ii|iv|v)\b', '', normalized, flags=re.IGNORECASE)
        
        # Trim whitespace
        normalized = normalized.strip()
        
        return normalized
    
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
    
    def _apply_correlation_filter(self, recommendations: List[BettingRecommendation], max_per_game: int = 3) -> List[BettingRecommendation]:
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
    parser.add_argument('--min-confidence', type=float, default=40.0, help="Minimum confidence threshold (default: 40, relaxed to let more bets through to enhanced filtering)")
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
