"""
Unified Analysis Pipeline
=========================
Combines team bet analysis (Option 1) and player prop predictions (Option 6)
into a single unified pipeline. NO NBA API - uses only Sportsbet + databallr + NBA.com lineups.

QUALITY OVER QUANTITY:
- Analyzes ALL available games by default
- Filters to only 70+ confidence bets
- Returns ALL high-confidence bets
- Max 2 bets per game (correlation control)

Data Flow:
1. Scrape ALL Sportsbet games (team markets, insights, player props)
2. Analyze team bets using Context-Aware Value Engine
3. Analyze player props using databallr player stats
4. Filter to 70+ confidence, rank by confidence score
5. Return ALL qualifying bets across all games

Usage:
  python unified_analysis_pipeline.py           # Analyze ALL games (recommended)
  python unified_analysis_pipeline.py all       # Analyze ALL games
  python unified_analysis_pipeline.py 5         # Analyze only 5 games
"""

# Fix Windows console encoding issues
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
import re
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time

from scrapers.player_data_fetcher import get_player_game_log
from scrapers.data_models import GameLogEntry
from scrapers.player_projection_model import PlayerProjectionModel
from scrapers.fade_detection import detect_fades

# Import new recommendation display system
from utils.convert_recommendations import convert_dict_to_recommendation
from utils.display_recommendations import display_recommendations

# Use centralized logging configuration
from config.logging_config import setup_logging, get_logger
setup_logging()  # Initialize with default (WARNING level)
logger = get_logger(__name__)

# Imports for Sportsbet scraping
from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
from scrapers.insights_to_value_analysis import analyze_all_insights

# Use HYBRID PIPELINE (StatsMuse primary + DataballR supplementary)
try:
    from scrapers.hybrid_data_pipeline import HybridPlayerDataPipeline
    HYBRID_PIPELINE_AVAILABLE = True
    DATABALLR_ROBUST_AVAILABLE = True  # Hybrid pipeline includes robust DataballR
    logger.debug("Pipeline: StatsMuse → DataballR → Inference")
except ImportError as e:
    # Fallback to DataballR only if hybrid not available
    logger.warning(f"Hybrid pipeline not available, using DataballR only")
    HYBRID_PIPELINE_AVAILABLE = False
    try:
        from scrapers.databallr_robust.integration import get_player_game_log
        DATABALLR_ROBUST_AVAILABLE = True
        logger.debug("Using robust DataballR scraper")
    except ImportError:
        from scrapers.databallr_scraper import get_player_game_log
        DATABALLR_ROBUST_AVAILABLE = False
        logger.warning("Using original DataballR scraper")

from scrapers.player_projection_model import PlayerProjectionModel

# Initialize hybrid pipeline if available
if HYBRID_PIPELINE_AVAILABLE:
    _hybrid_pipeline = HybridPlayerDataPipeline(
        use_cache=True,
        cache_ttl_hours=24,
        default_season="2024-25"
    )
    logger.debug("Pipeline initialized with persistent cache")

# Initialize NBA player cache
try:
    from scrapers.nba_player_cache import initialize_cache
    initialize_cache()
except ImportError:
    pass  # Cache optional

# Session-level game log cache (numeric ID-based keys)
# Format: "player_{player_id}_{season_year}" -> (List[GameLogEntry], datetime)
_session_game_log_cache: Dict[str, Tuple[List, datetime]] = {}


def get_player_game_log(
    player_name: str,
    last_n_games: int = 20,
    headless: bool = True,
    retries: int = 3,
    use_cache: bool = True
) -> Optional[List]:
    """
    Get player game logs - Priority: StatsMuse → DataballR → Inference.

    Uses player_data_fetcher.get_player_game_log which implements StatsMuse-first priority.
    Returns GameLogEntry objects (not dicts) for compatibility with projection model.

    Args:
        player_name: Player's full name
        last_n_games: Number of recent games to fetch
        headless: Run browser in headless mode
        retries: Number of retry attempts
        use_cache: Whether to use cached data

    Returns:
        List of GameLogEntry objects (most recent first)
    """
    # Use the StatsMuse-first version from player_data_fetcher
    # This function already handles: StatsMuse (primary) → DataballR (secondary) → Inference (fallback)
    # Returns List[GameLogEntry] which is what the projection model expects
    from scrapers.player_data_fetcher import get_player_game_log as _get_log_statsmuse_first
    
    game_log_entries = _get_log_statsmuse_first(
            player_name=player_name,
        season="2024-25",
            last_n_games=last_n_games,
            retries=retries,
            use_cache=use_cache
        )
    
    return game_log_entries if game_log_entries else []


def extract_player_props_from_markets(all_markets: List) -> Tuple[List[Dict], List[str]]:
    """
    Extract player prop markets from all Sportsbet markets.

    Sportsbet markets are single selections (Over OR Under), so we need to pair them.
    Looks for markets with player names and stat types (points, rebounds, assists, etc.)

    Returns:
        Tuple of (props, missing_players) where:
        - props: List of dicts with: player, stat, line, odds_over, odds_under
        - missing_players: List of player names that couldn't be scraped
    """
    props = []
    player_names_seen = []  # Track all player names we see
    prop_markets = {}  # Track markets by player+stat+line to pair Over/Under
    
    if not all_markets:
        return props, []

    # Common player prop market patterns
    stat_patterns = {
        'points': r'(\d+\.?\d*)\+?\s*points?',
        'rebounds': r'(\d+\.?\d*)\+?\s*rebounds?',
        'assists': r'(\d+\.?\d*)\+?\s*assists?',
        'steals': r'(\d+\.?\d*)\+?\s*steals?',
        'blocks': r'(\d+\.?\d*)\+?\s*blocks?',
        'threes': r'(\d+\.?\d*)\+?\s*(?:three|3|threes)',
    }

    # First pass: collect all potential player prop markets
    for market in all_markets:
        if not market:
            continue
            
        try:
            # BettingMarket uses selection_text, not name
            selection_text = getattr(market, 'selection_text', None) or getattr(market, 'name', '') or ''
            market_text = selection_text.lower()
            market_category = (getattr(market, 'market_category', None) or '').lower()
            odds = getattr(market, 'odds', None)

            # Check if this is a player prop market
            is_player_prop = any([
                'player' in market_category,
                'player' in market_text,
                any(stat in market_text for stat in ['points', 'rebounds', 'assists', 'steals', 'blocks', 'three', '3-point'])
            ])

            if not is_player_prop:
                continue

            # Try to extract player name from selection text
            # Patterns: "Player Name - Over X.X Points", "Player Name - Under X.X Points", "Player Name To Score X+ Points"
            player_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+(?:\s+[IVX]+)?)?)\s*-?\s*(?:Over|Under|To)', selection_text, re.IGNORECASE)
            if not player_match:
                # Try pattern without dash: "Player Name Over X.X"
                player_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+(?:\s+[IVX]+)?)?)\s+(?:Over|Under)', selection_text, re.IGNORECASE)

            if not player_match:
                continue

            player_name = player_match.group(1).strip()
            if player_name not in player_names_seen:
                player_names_seen.append(player_name)

            # Determine stat type and line
            stat_type = None
            line = None

            for stat, pattern in stat_patterns.items():
                match = re.search(pattern, market_text, re.IGNORECASE)
                if match:
                    stat_type = stat if stat != 'threes' else 'three_pt_made'
                    line = float(match.group(1))
                    break

            if not stat_type or line is None or not odds:
                continue

            # Determine if this is Over or Under
            is_over = 'over' in market_text
            is_under = 'under' in market_text
            
            # Create key for pairing: player_stat_line
            prop_key = f"{player_name.lower()}_{stat_type}_{line}"
            
            if prop_key not in prop_markets:
                prop_markets[prop_key] = {'player': player_name, 'stat': stat_type, 'line': line, 'odds_over': None, 'odds_under': None, 'market_name': selection_text}
            
            # Add odds to the appropriate field
            if is_over:
                prop_markets[prop_key]['odds_over'] = odds
            elif is_under:
                prop_markets[prop_key]['odds_under'] = odds
            else:
                # Can't determine direction, skip
                continue
                
        except Exception as e:
            logger.debug(f"  Error extracting prop from market: {e}")
            continue

    # Second pass: only add props that have both Over and Under odds
    for prop_key, prop_data in prop_markets.items():
        if prop_data['odds_over'] and prop_data['odds_under']:
            props.append({
                'player': prop_data['player'],
                'stat': prop_data['stat'],
                'line': prop_data['line'],
                'odds_over': prop_data['odds_over'],
                'odds_under': prop_data['odds_under'],
                'market_name': prop_data['market_name']
            })

    logger.debug(f"  Extracted {len(props)} player props from {len(all_markets)} markets")
    return props, player_names_seen


def scrape_games(max_games: int, headless: bool = True) -> List[Dict]:
    """
    Scrape NBA games from Sportsbet with all data needed for analysis.

    Returns:
        List of game dicts with: game_info, team_markets, team_insights, match_stats, player_props
    """
    logger.debug("Scraping NBA games from Sportsbet...")
    try:
        games = scrape_nba_overview(headless=headless)
    except Exception as e:
        logger.error(f"Failed to scrape NBA overview: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []

    if not games:
        logger.error("Failed to get games from Sportsbet")
        return []

    # Limit to actual games available
    actual_max = min(max_games, len(games))
    logger.info(f"Found {len(games)} games, analyzing {actual_max}")

    results = []
    for i, game in enumerate(games[:actual_max], 1):
        logger.debug(f"Game {i}/{min(max_games, len(games))}: {game['away_team']} @ {game['home_team']}")

        try:
            # Get complete match data
            match_data = scrape_match_complete(game['url'], headless=headless)

            if not match_data:
                logger.warning(f"  Failed to scrape match data")
                continue

            # Safely extract attributes with defaults
            all_markets = getattr(match_data, 'all_markets', []) or []
            match_insights = getattr(match_data, 'match_insights', []) or []
            match_stats = getattr(match_data, 'match_stats', None)

            # Extract player props from all markets
            player_props, market_players = extract_player_props_from_markets(all_markets)

            # Count player props from insights (they're embedded in insights, not separate markets)
            player_props_from_insights = sum(1 for insight in match_insights if _is_player_prop_insight({
                'fact': _safe_insight_get(insight, 'fact', ''),
                'market': _safe_insight_get(insight, 'market', ''),
                'result': _safe_insight_get(insight, 'result', '')
            }))
            
            total_player_props = len(player_props) + player_props_from_insights

            logger.debug(f"  Retrieved {len(all_markets)} markets, {len(match_insights)} insights, {total_player_props} player props")

            # Convert match_stats to dict if it's an object
            match_stats_dict = None
            if match_stats:
                if hasattr(match_stats, 'to_dict'):
                    match_stats_dict = match_stats.to_dict()
                elif isinstance(match_stats, dict):
                    match_stats_dict = match_stats
                else:
                    # Try to extract as dict manually
                    try:
                        match_stats_dict = {
                            'away_team_stats': getattr(match_stats, 'away_team_stats', None),
                            'home_team_stats': getattr(match_stats, 'home_team_stats', None),
                            'data_range': getattr(match_stats, 'data_range', '')
                        }
                        # Convert team stats to dict if they're objects
                        if match_stats_dict['away_team_stats'] and hasattr(match_stats_dict['away_team_stats'], 'to_dict'):
                            match_stats_dict['away_team_stats'] = match_stats_dict['away_team_stats'].to_dict()
                        if match_stats_dict['home_team_stats'] and hasattr(match_stats_dict['home_team_stats'], 'to_dict'):
                            match_stats_dict['home_team_stats'] = match_stats_dict['home_team_stats'].to_dict()
                    except Exception as e:
                        logger.debug(f"  Could not convert match_stats to dict: {e}")
                        match_stats_dict = None
            
            results.append({
                'game_info': game or {},
                'team_markets': all_markets or [],
                'team_insights': match_insights or [],
                'match_stats': match_stats_dict,  # Store as dict for easier access
                'player_props': player_props or [],
                'market_players': market_players or []  # Players seen in markets
            })
            
            if match_stats_dict:
                logger.debug(f"  Match stats available: away={match_stats_dict.get('away_team_stats', {}).get('team_name', 'Unknown')}, home={match_stats_dict.get('home_team_stats', {}).get('team_name', 'Unknown')}")
            else:
                logger.debug(f"  No match stats available for {game.get('away_team', 'Unknown')} @ {game.get('home_team', 'Unknown')}")

            # Throttle between games
            if i < actual_max:
                time.sleep(2)

        except Exception as e:
            logger.error(f"  Error scraping game: {e}")
            continue

    return results


def _safe_insight_get(insight, key: str, default=None):
    """
    Safely get value from insight whether it's a dict or MatchInsight object.
    
    Args:
        insight: Either a dict or MatchInsight dataclass object
        key: Key/attribute name to retrieve
        default: Default value if key/attr not found
    
    Returns:
        Value from insight or default
    """
    if isinstance(insight, dict):
        return insight.get(key, default)
    else:
        # MatchInsight object - use getattr
        return getattr(insight, key, default)


def _is_player_prop_insight(insight: Dict) -> bool:
    """Check if an insight is a player prop (points, rebounds, assists, etc.)"""
    fact = (_safe_insight_get(insight, 'fact') or '').lower()
    market = (_safe_insight_get(insight, 'market') or '').lower()
    result = (_safe_insight_get(insight, 'result') or '').lower()
    
    # Check for player prop keywords
    prop_keywords = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-pointers']
    stat_indicators = ['scored', 'recorded', 'made', 'grabbed', 'dished']
    
    # Must have a player name in result and a stat keyword
    has_player = result and len(result.split()) >= 2  # Likely a player name
    has_stat = any(keyword in fact or keyword in market for keyword in prop_keywords)
    has_indicator = any(indicator in fact for indicator in stat_indicators)
    
    return has_player and (has_stat or has_indicator)


def _extract_prop_info_from_insight(insight: Dict) -> Optional[Dict]:
    """Extract player name, stat type, and line from insight"""
    import re
    
    fact = _safe_insight_get(insight, 'fact') or ''
    result = _safe_insight_get(insight, 'result') or ''
    market = _safe_insight_get(insight, 'market') or ''
    
    # Extract player name (usually in result field)
    player_name = result.strip() if result else None
    
    # Extract stat type and threshold from fact
    # Pattern: "scored 20+ points" or "recorded 8+ assists"
    patterns = [
        (r'(\d+)\+?\s*points?', 'points'),
        (r'(\d+)\+?\s*rebounds?', 'rebounds'),
        (r'(\d+)\+?\s*assists?', 'assists'),
        (r'(\d+)\+?\s*steals?', 'steals'),
        (r'(\d+)\+?\s*blocks?', 'blocks'),
        (r'(\d+)\+?\s*threes?', 'three_pt_made'),
    ]
    
    stat_type = None
    line = None
    
    for pattern, stat in patterns:
        match = re.search(pattern, fact.lower())
        if match:
            line = float(match.group(1))
            stat_type = stat
            break
            
    # Fallback: Check market string if no stat found in fact
    if not stat_type:
        for pattern, stat in patterns:
            match = re.search(pattern, market.lower())
            if match:
                line = float(match.group(1))
                stat_type = stat
                break
    
    if not player_name or not stat_type or not line:
        return None
        
    return {
        'player': player_name,
        'stat': stat_type,
        'line': line
    }


def _calculate_team_projections(game_data: Dict, insight: Dict) -> Optional[Dict]:
    """
    Calculate model-based projections for team markets using match stats and Databallr data.
    
    Uses team stats (avg_points_for, avg_points_against) to project:
    - Totals (over/under)
    - Spreads (handicap)
    - Moneyline probabilities
    
    Returns:
        Dict with projection_details including:
        - projected_total, projected_spread, pace_factor
        - model_probability (projected probability from stats)
        - confidence_score (based on data quality)
    """
    match_stats = game_data.get('match_stats')
    
    # If no match_stats, try to extract from game_info or use defaults
    if not match_stats:
        # Try to get team names to at least provide some projection data
        game_info = game_data.get('game_info', {})
        away_team = game_info.get('away_team', '')
        home_team = game_info.get('home_team', '')
        
        if not away_team or not home_team:
            logger.debug(f"  No match_stats and no team names - cannot calculate projections")
            return None
        
        # Create minimal stats from league averages if no match_stats available
        # This allows us to still calculate basic projections
        logger.debug(f"  No match_stats available, using league averages for {away_team} @ {home_team}")
        match_stats = {
            'away_team_stats': {
                'team_name': away_team,
                'avg_points_for': 112.0,  # League average
                'avg_points_against': 112.0,
                'avg_total_points': 224.0
            },
            'home_team_stats': {
                'team_name': home_team,
                'avg_points_for': 112.0,
                'avg_points_against': 112.0,
                'avg_total_points': 224.0
            }
        }
    
    try:
        try:
            from value_engine_enhanced import TeamStats, project_total_from_team_stats, calculate_form_score
        except ImportError:
            logger.warning("value_engine_enhanced not available, using fallback functions")
            # Fallback TeamStats class
            from dataclasses import dataclass
            @dataclass
            class TeamStats:
                team_name: str = ""
                avg_points_for: Optional[float] = None
                avg_points_against: Optional[float] = None
                avg_total_points: Optional[float] = None
                favorite_win_pct: Optional[float] = None
                underdog_win_pct: Optional[float] = None
                clutch_win_pct: Optional[float] = None
            
            def project_total_from_team_stats(away_stats, home_stats):
                """Fallback: Simple projection from averages"""
                if away_stats.avg_points_for and home_stats.avg_points_for:
                    return away_stats.avg_points_for + home_stats.avg_points_for
                elif away_stats.avg_total_points and home_stats.avg_total_points:
                    return (away_stats.avg_total_points + home_stats.avg_total_points) / 2.0
                return 224.0  # League average
            
            def calculate_form_score(team_stats):
                """Fallback: Simple form score"""
                if not team_stats:
                    return 0.0
                pf = team_stats.avg_points_for or 0.0
                pa = team_stats.avg_points_against or 0.0
                return pf - pa
        
        # Extract team stats - handle both dict and object formats
        if isinstance(match_stats, dict):
            away_stats_dict = match_stats.get('away_team_stats', {}) or match_stats.get('away_team', {})
            home_stats_dict = match_stats.get('home_team_stats', {}) or match_stats.get('home_team', {})
            
            # Convert dict to TeamStats if needed
            if isinstance(away_stats_dict, dict):
                away_stats = TeamStats(
                    team_name=away_stats_dict.get('team_name', ''),
                    avg_points_for=away_stats_dict.get('avg_points_for'),
                    avg_points_against=away_stats_dict.get('avg_points_against'),
                    avg_total_points=away_stats_dict.get('avg_total_points'),
                    favorite_win_pct=away_stats_dict.get('favorite_win_pct'),
                    underdog_win_pct=away_stats_dict.get('underdog_win_pct'),
                    clutch_win_pct=away_stats_dict.get('clutch_win_pct')
                )
            else:
                away_stats = away_stats_dict
                
            if isinstance(home_stats_dict, dict):
                home_stats = TeamStats(
                    team_name=home_stats_dict.get('team_name', ''),
                    avg_points_for=home_stats_dict.get('avg_points_for'),
                    avg_points_against=home_stats_dict.get('avg_points_against'),
                    avg_total_points=home_stats_dict.get('avg_total_points'),
                    favorite_win_pct=home_stats_dict.get('favorite_win_pct'),
                    underdog_win_pct=home_stats_dict.get('underdog_win_pct'),
                    clutch_win_pct=home_stats_dict.get('clutch_win_pct')
                )
            else:
                home_stats = home_stats_dict
        else:
            # Object format
            away_stats = getattr(match_stats, 'away_team_stats', None)
            home_stats = getattr(match_stats, 'home_team_stats', None)
        
        if not away_stats or not home_stats:
            return None
        
        # Project total points
        projected_total = project_total_from_team_stats(away_stats, home_stats)
        
        # Calculate pace factor (average of both teams' pace)
        away_pace = None
        home_pace = None
        if away_stats.avg_points_for and away_stats.avg_points_against:
            away_pace = (away_stats.avg_points_for + away_stats.avg_points_against) / 2.0
        if home_stats.avg_points_for and home_stats.avg_points_against:
            home_pace = (home_stats.avg_points_for + home_stats.avg_points_against) / 2.0
        
        pace_factor = 1.0
        if away_pace and home_pace:
            avg_pace = (away_pace + home_pace) / 2.0
            league_avg_pace = 230.0  # Approximate NBA average
            pace_factor = avg_pace / league_avg_pace
        
        # Calculate form scores
        away_form = calculate_form_score(away_stats)
        home_form = calculate_form_score(home_stats)
        form_diff = home_form - away_form  # Home advantage
        
        # Determine market type from insight
        market = _safe_insight_get(insight, 'market', '').lower()
        fact = _safe_insight_get(insight, 'fact', '').lower()
        
        model_probability = None
        projected_spread = None
        
        # Project based on market type
        if 'total' in market or 'over' in market or 'under' in market:
            # Total market - extract line from market/fact
            import re
            # Try multiple patterns to find the line
            line_match = re.search(r'(\d+\.?\d*)', market + ' ' + fact)
            if not line_match:
                # Try "Under X" or "Over X" patterns
                line_match = re.search(r'(?:under|over)\s*(\d+\.?\d*)', fact, re.I)
            if not line_match:
                # Try "X+" pattern
                line_match = re.search(r'(\d+\.?\d*)\+', fact)
            if not line_match:
                # Try finding number in parentheses like "(Under 228.5)"
                line_match = re.search(r'\(.*?(\d+\.?\d*)\)', market + ' ' + fact)
            
            if line_match and projected_total:
                line = float(line_match.group(1))
                # Probability based on projected vs line
                diff = projected_total - line
                # Each point difference = 1.5% probability shift
                base_prob = 0.5
                adjustment = diff * 0.015
                model_probability = max(0.1, min(0.9, base_prob + adjustment))
                
                # Adjust for Over/Under direction
                if 'under' in market.lower() or 'under' in fact.lower():
                    # For UNDER, flip the probability
                    model_probability = 1.0 - model_probability
                
                logger.debug(f"  Total projection: {projected_total:.1f} vs line {line:.1f} = {model_probability:.3f} prob")
            elif projected_total:
                # Have projected total but no line - use historical trend as base
                logger.debug(f"  Total projection: {projected_total:.1f} but no line found in market/fact")
        
        elif 'handicap' in market or 'spread' in market:
            # Spread market
            if away_stats.avg_points_for and home_stats.avg_points_for:
                projected_spread = home_stats.avg_points_for - away_stats.avg_points_for
                # Add home court advantage (~3 points)
                projected_spread += 3.0
                # For spread, probability based on form differential
                base_prob = 0.5
                form_adjustment = form_diff * 0.006
                model_probability = max(0.1, min(0.9, base_prob + form_adjustment))
                logger.debug(f"  Spread projection: {projected_spread:.1f}, form diff {form_diff:.1f} = {model_probability:.3f} prob")
        
        elif 'winner' in market or 'moneyline' in market:
            # Moneyline - use form differential
            # Form diff of +5 = ~3% probability boost
            base_prob = 0.5
            form_adjustment = form_diff * 0.006
            model_probability = max(0.1, min(0.9, base_prob + form_adjustment))
            logger.debug(f"  Moneyline projection: form diff {form_diff:.1f} = {model_probability:.3f} prob")
        
        # For any other market type, still provide projection data even without probability
        if model_probability is None:
            logger.debug(f"  Market type '{market}' - no probability calculated, but projection data available")
        
        # Calculate confidence based on data quality
        confidence_score = 50.0  # Base confidence
        if away_stats.avg_points_for and home_stats.avg_points_for:
            confidence_score += 20.0  # Have scoring data
        if projected_total:
            confidence_score += 10.0  # Can project total
        if away_stats.avg_total_points and home_stats.avg_total_points:
            confidence_score += 10.0  # Have direct total data
        confidence_score = min(80.0, confidence_score)  # Cap at 80

        # NEW: Extract situational data from TeamStats objects
        clutch_factor = None
        reliability_factor = None
        pace_advantage = None
        opponent_def_rating = None

        # Clutch win % differential (for away team perspective)
        if hasattr(away_stats, 'clutch_win_pct') and hasattr(home_stats, 'clutch_win_pct'):
            if away_stats.clutch_win_pct is not None and home_stats.clutch_win_pct is not None:
                clutch_factor = away_stats.clutch_win_pct - home_stats.clutch_win_pct

        # Reliability % differential (halftime lead protection)
        if hasattr(away_stats, 'reliability_pct') and hasattr(home_stats, 'reliability_pct'):
            if away_stats.reliability_pct is not None and home_stats.reliability_pct is not None:
                reliability_factor = away_stats.reliability_pct - home_stats.reliability_pct

        # Pace advantage
        if away_pace and home_pace:
            pace_advantage = away_pace - home_pace

        # Opponent defensive rating (for away team, opponent is home team)
        if hasattr(home_stats, 'avg_points_against') and home_stats.avg_points_against:
            opponent_def_rating = home_stats.avg_points_against

        return {
            'projected_total': projected_total,
            'projected_spread': projected_spread,
            'pace_factor': pace_factor,
            'model_probability': model_probability,
            'confidence_score': confidence_score,
            'away_form_score': away_form,
            'home_form_score': home_form,
            'form_differential': form_diff,
            # NEW: Situational factors for context-aware analysis
            'clutch_factor': clutch_factor,
            'reliability_factor': reliability_factor,
            'pace_advantage': pace_advantage,
            'opponent_def_rating': opponent_def_rating
        }
        
    except Exception as e:
        logger.debug(f"  Could not calculate team projections: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


# FIX #5: Insight weights for quantifying Sportsbet insights
INSIGHT_WEIGHTS = {
    "Win/Loss": 0.04,
    "Head-to-Head": 0.03,
    "Against Division": 0.025,
    "Recent Form": 0.02,
    "Streak": 0.015,
    "Home/Away": 0.015
}


def quantify_insight_boost(insights: List[Dict]) -> float:
    """
    Convert Sportsbet insight tags to probability delta.
    
    Args:
        insights: List of insight dictionaries with 'tags' field
    
    Returns:
        Probability boost (0.0 to 0.08 max)
    """
    total_boost = 0.0
    for insight in insights:
        tags = _safe_insight_get(insight, 'tags', [])
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            if isinstance(tag, str):
                # Try exact match first
                boost = INSIGHT_WEIGHTS.get(tag, 0)
                if boost == 0:
                    # Try case-insensitive partial match
                    tag_lower = tag.lower()
                    for key, value in INSIGHT_WEIGHTS.items():
                        if key.lower() in tag_lower or tag_lower in key.lower():
                            boost = value
                            break
                total_boost += boost
    # Cap total boost at 8%
    return min(total_boost, 0.08)


def analyze_team_bets(game_data: Dict, headless: bool = True) -> List[Dict]:
    """
    Analyze team-based betting insights using Context-Aware Value Engine.
    
    For player prop insights, applies projection model (70%) + historical (30%).
    For team insights, attempts to calculate model projections from match_stats.

    Returns:
        List of value bets with analysis details
    """
    if not game_data.get('team_insights'):
        return []

    # Team projections are now calculated per-insight in the analysis loop below

    # Separate player prop insights from team insights
    player_prop_insights = []
    team_insights = []
    
    team_insights_raw = game_data.get('team_insights', []) or []
    for insight in team_insights_raw:
        try:
            # Handle both dict and object insight formats using helper function
            insight_dict = {
                'fact': _safe_insight_get(insight, 'fact', ''),
                'market': _safe_insight_get(insight, 'market', ''),
                'result': _safe_insight_get(insight, 'result', ''),
                'odds': _safe_insight_get(insight, 'odds', 0),
                'tags': _safe_insight_get(insight, 'tags', []),
                'icon': _safe_insight_get(insight, 'icon', '')
            }
            
            if _is_player_prop_insight(insight_dict):
                player_prop_insights.append(insight_dict)
            else:
                team_insights.append(insight_dict)
        except Exception as e:
            logger.warning(f"  Error processing insight: {e}")
            continue
    
    # Analyze team insights with projection model integration
    analyzed_team = []
    if team_insights:
        # NEW: Calculate team projections first to extract clutch stats
        # Use first insight to get team stats (all insights share same game/teams)
        team_projection = _calculate_team_projections(game_data, team_insights[0]) if team_insights else None

        # NEW: Create ContextFactors with clutch stats if available
        from scrapers.context_aware_analysis import ContextFactors
        lineup_context = None
        if team_projection:
            lineup_context = ContextFactors(
                clutch_factor=team_projection.get('clutch_factor'),
                reliability_factor=team_projection.get('reliability_factor'),
                pace_advantage=team_projection.get('pace_advantage'),
                opponent_def_rating=team_projection.get('opponent_def_rating')
            )

        # Get base historical analysis with clutch stats passed via lineup_context
        base_analyzed = analyze_all_insights(
            team_insights,
            minimum_sample_size=4,  # RELAXED: Lower threshold to catch more insights
            lineup_context=lineup_context,  # NEW: Pass clutch stats
            home_team=game_data['game_info']['home_team'],
            away_team=game_data['game_info']['away_team']
        )
        
        # Enhance each analysis with projection model
        for analyzed_item in base_analyzed:
            insight = analyzed_item.get('insight', {})
            analysis = analyzed_item.get('analysis', {})
            
            # Calculate team projections for this specific insight
            team_projection = _calculate_team_projections(game_data, insight)
            
            if team_projection:
                # Always add projection_details if we have any projection data
                analysis['projection_details'] = {
                    'projected_total': team_projection.get('projected_total'),
                    'projected_spread': team_projection.get('projected_spread'),
                    'pace_factor': team_projection.get('pace_factor', 1.0),
                    'form_differential': team_projection.get('form_differential', 0.0),
                    'away_form_score': team_projection.get('away_form_score', 0.0),
                    'home_form_score': team_projection.get('home_form_score', 0.0)
                }
                
                # If we have model_probability, combine with historical
                if team_projection.get('model_probability') is not None:
                    # Combine projection (60%) + historical (40%) for team bets
                    hist_prob = analysis.get('historical_probability', 0.5)
                    model_prob = team_projection['model_probability']
                    
                    # Combine probabilities
                    final_prob = 0.6 * model_prob + 0.4 * hist_prob
                    
                    # FIX #5: Apply insight boost (quantify Sportsbet insights)
                    insight_boost = quantify_insight_boost([insight])
                    final_prob = min(final_prob + insight_boost, 0.99)
                    analysis['insight_boost'] = insight_boost  # Store for display
                    
                    # Combine confidence scores
                    hist_confidence = analysis.get('confidence_score', 50)
                    model_confidence = team_projection.get('confidence_score', 50)
                    final_confidence = 0.6 * model_confidence + 0.4 * hist_confidence
                    
                    # Update analysis with projection-based values
                    analysis['historical_probability'] = final_prob
                    analysis['original_historical_probability'] = hist_prob
                    analysis['confidence_score'] = min(final_confidence, 85.0)  # Cap at 85
                    analysis['projected_prob'] = model_prob
                    
                    # Recalculate EV with new probability (final_prob is the single source of truth)
                    odds_val = _safe_insight_get(insight, 'odds', 2.0)
                    bookmaker_prob = 1.0 / odds_val if odds_val > 0 else 0.5
                    edge = (final_prob - bookmaker_prob) * 100
                    ev_per_100 = (final_prob * (odds_val - 1) * 100) - ((1 - final_prob) * 100)
                    
                    # Safety assertion - EV must match probability
                    expected_ev = (final_prob * (odds_val - 1) * 100) - ((1 - final_prob) * 100)
                    assert abs(ev_per_100 - expected_ev) < 0.001, f"EV calculation mismatch: {ev_per_100} vs {expected_ev} for prob {final_prob}"
                    
                    analysis['value_percentage'] = edge
                    analysis['ev_per_100'] = ev_per_100
                    analysis['has_value'] = ev_per_100 > 0
                    analysis['projection_source'] = 'blended'  # Model + historical blend for team bets
                    
                    logger.debug(f"  Team bet ({_safe_insight_get(insight, 'market', 'Unknown')}): prob={final_prob:.1%}, conf={final_confidence:.0f}")
                else:
                    # Have projection data but no probability - try to calculate from projected_total if available
                    projected_total = team_projection.get('projected_total')
                    if projected_total:
                        # Try to extract line from insight
                        import re
                        market = _safe_insight_get(insight, 'market', '').lower()
                        fact = _safe_insight_get(insight, 'fact', '').lower()
                        line_match = re.search(r'(\d+\.?\d*)', market + ' ' + fact)
                        if not line_match:
                            line_match = re.search(r'(?:under|over)\s*(\d+\.?\d*)', fact, re.I)
                        
                        if line_match:
                            line = float(line_match.group(1))
                            diff = projected_total - line
                            base_prob = 0.5
                            adjustment = diff * 0.015
                            model_prob = max(0.1, min(0.9, base_prob + adjustment))
                            
                            # Adjust for Over/Under direction
                            if 'under' in market.lower() or 'under' in fact.lower():
                                model_prob = 1.0 - model_prob
                            
                            # Combine with historical
                            hist_prob = analysis.get('historical_probability', 0.5)
                            final_prob = 0.6 * model_prob + 0.4 * hist_prob
                            
                            # FIX #5: Apply insight boost (quantify Sportsbet insights)
                            insight_boost = quantify_insight_boost([insight])
                            final_prob = min(final_prob + insight_boost, 0.99)
                            analysis['insight_boost'] = insight_boost  # Store for display
                            
                            analysis['historical_probability'] = final_prob
                            analysis['original_historical_probability'] = hist_prob
                            analysis['projected_prob'] = model_prob
                            
                            # Recalculate EV (final_prob is the single source of truth)
                            odds_val = _safe_insight_get(insight, 'odds', 2.0)
                            bookmaker_prob = 1.0 / odds_val if odds_val > 0 else 0.5
                            edge = (final_prob - bookmaker_prob) * 100
                            ev_per_100 = (final_prob * (odds_val - 1) * 100) - ((1 - final_prob) * 100)
                            
                            # Safety assertion - EV must match probability
                            odds_val = _safe_insight_get(insight, 'odds', 2.0)
                            expected_ev = (final_prob * (odds_val - 1) * 100) - ((1 - final_prob) * 100)
                            assert abs(ev_per_100 - expected_ev) < 0.001, f"EV calculation mismatch: {ev_per_100} vs {expected_ev} for prob {final_prob}"
                            
                            analysis['value_percentage'] = edge
                            analysis['ev_per_100'] = ev_per_100
                            analysis['has_value'] = ev_per_100 > 0
                            analysis['projection_source'] = 'blended'  # Model (from projected_total) + historical blend
                            
                            logger.debug(f"  Team bet ({_safe_insight_get(insight, 'market', 'Unknown')}): prob={final_prob:.1%}")
                        else:
                            logger.debug(f"  [OK] Team bet has projection data (projected_total={projected_total:.1f}) but no line found for probability calculation")
                    else:
                        logger.debug(f"  [OK] Team bet has projection data (no probability calculated): {_safe_insight_get(insight, 'market', 'Unknown')}")
            
            # Set projection_source for team bets that don't have model projections
            if 'projection_source' not in analysis:
                analysis['projection_source'] = 'insight-derived'  # Pure historical/insight analysis
                logger.debug(f"  [PROJECTION SOURCE] Team bet ({_safe_insight_get(insight, 'market', 'Unknown')}): insight-derived (prob: {analysis.get('historical_probability', 0):.1%})")
            
            analyzed_team.append(analyzed_item)
    
    # Analyze player prop insights with projection model
    analyzed_props = []
    if player_prop_insights:
        projection_model = PlayerProjectionModel()
        
        for insight in player_prop_insights:
            prop_info = _extract_prop_info_from_insight(insight)
            if not prop_info:
                # Skip if we can't extract prop info - no fallbacks
                logger.debug(f"  Skipping insight - cannot extract prop info: {_safe_insight_get(insight, 'fact', '')[:50]}...")
                continue
            
            # Get player game log - Priority: StatsMuse → DataballR → Inference
            # Returns List[GameLogEntry] objects for projection model
            try:
                game_log = get_player_game_log(
                    player_name=prop_info['player'],
                    last_n_games=20,
                    headless=headless,
                    retries=3,  # Increased retries for reliability
                    use_cache=True
                )
                
                # Convert dicts to GameLogEntry if needed (for compatibility)
                if game_log and len(game_log) > 0 and isinstance(game_log[0], dict):
                    from scrapers.data_models import GameLogEntry
                    game_log = [GameLogEntry(**g) if isinstance(g, dict) else g for g in game_log]
                
                # Require sufficient game log data
                if not game_log or len(game_log) < 5:
                    logger.debug(f"  Skipping {prop_info['player']} - insufficient game log data (n={len(game_log) if game_log else 0})")
                    continue
                
                # Log data source for debugging
                if hasattr(game_log[0], '__class__'):
                    logger.debug(f"  [DATA] Game log for {prop_info['player']}: {len(game_log)} games, type: {type(game_log[0]).__name__}")
                
                # Get historical analysis - required for combining with projection
                # RELAXED: Lower sample size to catch more insights (projection model will validate)
                analyzed = analyze_all_insights([insight], minimum_sample_size=4,
                    home_team=game_data['game_info']['home_team'],
                    away_team=game_data['game_info']['away_team'])
                
                if not analyzed:
                    logger.debug(f"  Skipping {prop_info['player']} - historical analysis failed")
                    continue
                
                hist_analysis = analyzed[0]['analysis']
                
                # Apply projection model - must succeed
                try:
                    # Get team stats for matchup adjustments
                    # Convert dict to MatchStats object if needed
                    team_stats = game_data.get('match_stats')
                    if team_stats and isinstance(team_stats, dict):
                        # Convert dict to MatchStats object for projection model
                        try:
                            from scrapers.sportsbet_final_enhanced import MatchStats, TeamStats
                            away_stats_dict = team_stats.get('away_team_stats', {})
                            home_stats_dict = team_stats.get('home_team_stats', {})
                            
                            if away_stats_dict and home_stats_dict:
                                # Convert dicts to TeamStats objects
                                away_stats = TeamStats(**away_stats_dict) if isinstance(away_stats_dict, dict) else away_stats_dict
                                home_stats = TeamStats(**home_stats_dict) if isinstance(home_stats_dict, dict) else home_stats_dict
                                
                                # Create MatchStats object
                                team_stats = MatchStats(
                                    away_team_stats=away_stats,
                                    home_team_stats=home_stats,
                                    data_range=team_stats.get('data_range', '')
                                )
                                logger.debug(f"  Team stats converted to MatchStats object for {prop_info['player']}")
                            else:
                                team_stats = None
                        except Exception as e:
                            logger.debug(f"  Could not convert team_stats dict to MatchStats: {e}")
                            team_stats = None
                    
                    if team_stats:
                        logger.debug(f"  Team stats available for {prop_info['player']} - will calculate matchup adjustments")
                    else:
                        logger.debug(f"  No team stats for {prop_info['player']} - matchup adjustments will be 1.0x")
                    
                    try:
                        projection = projection_model.project_stat(
                            player_name=prop_info['player'],
                            stat_type=prop_info['stat'],
                            game_log=game_log,
                            prop_line=prop_info['line'],
                            opponent_team=None,  # Will try to infer from match_stats
                            player_team=None,
                            team_stats=team_stats,
                            min_games=5
                        )
                    except Exception as proj_error:
                        logger.warning(f"  [PROJECTION ERROR] Failed to project {prop_info['player']} {prop_info['stat']}: {proj_error}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        projection = None
                    
                    if projection and hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
                        logger.debug(f"  Matchup adjustments for {prop_info['player']}: pace={projection.matchup_adjustments.pace_multiplier:.3f}x, defense={projection.matchup_adjustments.defense_adjustment:.3f}x")
                    elif projection:
                        logger.debug(f"  No matchup adjustments for {prop_info['player']}")
                    
                    # PROJECTION FALLBACK: If projection model returned None, use historical analysis
                    if not projection:
                        logger.debug(f"  Projection model returned None for {prop_info['player']} {prop_info['stat']}, trying fallback...")
                        # Use historical analysis as fallback
                        hist_analysis = analyzed[0]['analysis']
                        hist_prob = hist_analysis.get('historical_probability', 0)
                        hist_conf = hist_analysis.get('confidence_score', 0)
                        
                        # Only use fallback if historical analysis is reasonable
                        if hist_prob >= 0.45 and hist_conf >= 35:
                            logger.debug(f"  Fallback: {prop_info['player']} {prop_info['stat']} (prob: {hist_prob:.1%})")
                            # Create a simplified bet entry from historical analysis
                            odds_val = _safe_insight_get(insight, 'odds', 2.0)
                            if odds_val > 0:
                                bookmaker_prob = 1.0 / odds_val
                                edge = (hist_prob - bookmaker_prob) * 100
                                ev_per_100 = (hist_prob * (odds_val - 1) * 100) - ((1 - hist_prob) * 100)
                                
                                # Only add if positive edge
                                if edge > 0:
                                    # Create fallback analysis structure (match format expected by pipeline)
                                    fallback_analysis = analyzed[0]['analysis'].copy()
                                    fallback_analysis['historical_probability'] = hist_prob
                                    fallback_analysis['final_prob'] = hist_prob  # For filtering consistency
                                    fallback_analysis['confidence_score'] = hist_conf
                                    fallback_analysis['has_model_projection'] = False
                                    fallback_analysis['fallback_mode'] = True
                                    fallback_analysis['projection_failure_reason'] = 'Model returned None'
                                    fallback_analysis['projection_source'] = 'fallback'  # Track projection source
                                    fallback_analysis['value_percentage'] = edge
                                    fallback_analysis['ev_per_100'] = ev_per_100
                                    fallback_analysis['has_value'] = ev_per_100 > 0
                                    
                                    analyzed_props.append({'insight': insight, 'analysis': fallback_analysis})
                                    logger.debug(f"  {prop_info['player']} {prop_info['stat']}: fallback (prob: {hist_prob:.1%}, edge: {edge:+.1f}%)")
                                    continue  # Skip to next insight
                        # If fallback didn't work, skip this prop
                        logger.debug(f"  Skipping {prop_info['player']} {prop_info['stat']} - projection returned None and fallback not viable")
                        continue
                    
                    # Save original historical probability for reference
                    original_hist_prob = hist_analysis['historical_probability']

                    # FIX #1: Probability flow - raw_model_prob → adjusted_model_prob → final_blended_prob → EV
                    # calibrated_probability is the adjusted_model_prob (after role/volatility/archetype adjustments)
                    calibrated_prob = projection.calibrated_probability
                    calibrated_confidence = projection.confidence_score  # Already includes lag check
                    
                    # Blend with market probability to get final_blended_prob (single source of truth for EV)
                    from scrapers.player_projection_model import blend_probabilities
                    odds_val = _safe_insight_get(insight, 'odds', 2.0)
                    bookmaker_prob = 1.0 / odds_val if odds_val > 0 else 0.5
                    MODEL_WEIGHT = 0.70
                    MARKET_WEIGHT = 0.30
                    final_blended_prob = blend_probabilities(
                        model_prob=calibrated_prob,
                        market_prob=bookmaker_prob,
                        weight_model=MODEL_WEIGHT,
                        weight_market=MARKET_WEIGHT
                    )
                    
                    # Warn if market probability dominates model (>65% weight)
                    market_weight_pct = MARKET_WEIGHT * 100
                    if market_weight_pct > 65:
                        model_disagreement = abs(calibrated_prob - bookmaker_prob) * 100
                        if model_disagreement > 15:  # Significant disagreement (>15%)
                            logger.warning(f"  [MARKET-DOMINANT] Market weight {market_weight_pct:.0f}%, model disagreement: model={calibrated_prob:.1%} vs market={bookmaker_prob:.1%} (diff={model_disagreement:+.1f}%)")
                    
                    # Ensure probability is in valid range
                    final_blended_prob = max(0.01, min(0.99, final_blended_prob))

                    # Update analysis with projection-based values
                    hist_analysis['historical_probability'] = final_blended_prob  # Use final blended probability (SINGLE SOURCE OF TRUTH)
                    hist_analysis['original_historical_probability'] = original_hist_prob  # Save original
                    hist_analysis['calibrated_prob'] = calibrated_prob  # Save calibrated (before market blend)
                    hist_analysis['confidence_score'] = calibrated_confidence  # Use calibrated confidence
                    hist_analysis['projected_prob'] = projection.probability_over_line  # Raw probability (before caps/penalties)
                    hist_analysis['projected_expected_value'] = projection.expected_value
                    hist_analysis['archetype_name'] = projection.archetype_name
                    hist_analysis['archetype_cap'] = projection.archetype_cap
                    # Extract projection details with proper fallbacks
                    pace_mult = 1.0
                    defense_adj = 1.0
                    if hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
                        pace_mult = getattr(projection.matchup_adjustments, 'pace_multiplier', 1.0)
                        defense_adj = getattr(projection.matchup_adjustments, 'defense_adjustment', 1.0)
                    
                    # Extract structured role information from projection
                    role_modifier_details = getattr(projection, 'role_modifier_details', None)
                    role_info = {}
                    if role_modifier_details:
                        role_info = {
                            'offensive_role': role_modifier_details.get('offensive_role', 'secondary'),
                            'usage_state': role_modifier_details.get('usage_state', 'normal'),
                            'minutes_state': role_modifier_details.get('minutes_state', 'stable')
                        }
                    
                    hist_analysis['projection_details'] = {
                        'std_dev': getattr(projection, 'std_dev', None),
                        'minutes_projected': projection.minutes_projection.projected_minutes if (hasattr(projection, 'minutes_projection') and projection.minutes_projection) else None,
                        'pace_multiplier': pace_mult,
                        'defense_adjustment': defense_adj,
                        'role_change_detected': projection.role_change.detected if (hasattr(projection, 'role_change') and projection.role_change) else False,
                        'player_role': getattr(projection, 'player_role', None),  # Display name (e.g., "Secondary Creator (Elevated Usage)")
                        'role_structured': role_info if role_info else None,  # Structured role (offensive_role, usage_state, minutes_state)
                        'role_modifier': role_modifier_details  # Role modifier details (modifier, confidence, rationale)
                    }
                    
                    # Recalculate EV using FINAL_BLENDED_PROB (single source of truth)
                    edge = (final_blended_prob - bookmaker_prob) * 100
                    ev_per_100 = (final_blended_prob * (odds_val - 1) * 100) - ((1 - final_blended_prob) * 100)
                    
                    # Safety assertion - EV must match probability
                    # odds_val already set above from bookmaker_prob calculation
                    expected_ev = (final_blended_prob * (odds_val - 1) * 100) - ((1 - final_blended_prob) * 100)
                    assert abs(ev_per_100 - expected_ev) < 0.001, f"EV calculation mismatch: {ev_per_100} vs {expected_ev} for prob {final_blended_prob}"
                    
                    hist_analysis['value_percentage'] = edge
                    hist_analysis['ev_per_100'] = ev_per_100
                    hist_analysis['has_value'] = ev_per_100 > 0
                    hist_analysis['projection_source'] = 'blended'  # Model + market blend (track projection source)
                    
                    # Only add if projection succeeded
                    analyzed_props.append(analyzed[0])
                    logger.debug(f"  {prop_info['player']} {prop_info['stat']}: prob={final_blended_prob:.1%}, conf={calibrated_confidence:.0f}")
                    
                except Exception as proj_e:
                    logger.warning(f"  Skipping {prop_info.get('player', 'unknown')} - projection model error: {proj_e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    
                    # PROJECTION FALLBACK: If projection failed but we have historical analysis, use it
                    # This prevents "16 props found, 0 projections" scenarios
                    if analyzed and len(analyzed) > 0:
                        hist_analysis = analyzed[0]['analysis']
                        hist_prob = hist_analysis.get('historical_probability', 0)
                        hist_conf = hist_analysis.get('confidence_score', 0)
                        
                        # Only use fallback if historical analysis is reasonable
                        if hist_prob >= 0.45 and hist_conf >= 35:
                            logger.debug(f"  Fallback: {prop_info['player']} {prop_info['stat']} (prob: {hist_prob:.1%})")
                            # Create a simplified bet entry from historical analysis
                            odds_val = _safe_insight_get(insight, 'odds', 2.0)
                            if odds_val > 0:
                                bookmaker_prob = 1.0 / odds_val
                                edge = (hist_prob - bookmaker_prob) * 100
                                ev_per_100 = (hist_prob * (odds_val - 1) * 100) - ((1 - hist_prob) * 100)
                                
                                # Only add if positive edge
                                if edge > 0:
                                    fallback_bet = {
                                        'type': 'player_prop',
                                        'player': prop_info['player'],
                                        'stat': prop_info['stat'],
                                        'line': prop_info['line'],
                                        'prediction': 'OVER' if hist_prob > 0.50 else 'UNDER',
                                        'odds': odds_val,
                                        'final_prob': hist_prob,
                                        'historical_probability': hist_prob,
                                        'confidence': hist_conf,
                                        'edge': edge,
                                        'ev_per_100': ev_per_100,
                                        'has_model_projection': False,  # Flag as fallback
                                        'fallback_mode': True,
                                        'projection_source': 'fallback',  # Track projection source
                                        'projection_failure_reason': str(proj_e)[:100]
                                    }
                                    analyzed_props.append({'insight': insight, 'analysis': fallback_bet})
                                    logger.debug(f"  {prop_info['player']} {prop_info['stat']}: fallback (prob: {hist_prob:.1%}, edge: {edge:+.1f}%)")
                    continue
                    
            except Exception as e:
                logger.warning(f"  Skipping {prop_info.get('player', 'unknown')} - error fetching game log: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
    
    # Combine all analyzed insights, but mark player props separately
    all_analyzed = []
    
    # Add team bets
    for bet in analyzed_team:
        bet['_bet_type'] = 'team_bet'  # Mark as team bet
        all_analyzed.append(bet)
    
    # Add player prop bets
    for bet in analyzed_props:
        bet['_bet_type'] = 'player_prop'  # Mark as player prop
        all_analyzed.append(bet)

    # Filter to value bets only and add game context
    value_bets = []
    for bet in all_analyzed:
        analysis = bet.get('analysis', {}) or {}
        if analysis.get('has_value', False):
            game_info = game_data.get('game_info', {}) or {}
            away_team = game_info.get('away_team', 'Unknown')
            home_team = game_info.get('home_team', 'Unknown')
            bet['game'] = f"{away_team} @ {home_team}"
            value_bets.append(bet)

    return value_bets


def analyze_player_props(game_data: Dict, headless: bool = True) -> Tuple[List[Dict], List[str]]:
    """
    Analyze player prop bets using projection-based model (PRIMARY) + historical hit-rate (SECONDARY).

    Uses PlayerProjectionModel as the primary signal (70% weight) and historical hit-rate
    as secondary validation (30% weight).

    Returns:
        Tuple of (predictions, missing_players) where:
        - predictions: List of player prop predictions with confidence scores
        - missing_players: List of player names that need to be added to cache
    """
    predictions = []
    projection_model = PlayerProjectionModel()

    player_props = game_data.get('player_props', []) or []
    game_info = game_data.get('game_info', {}) or {}
    match_stats = game_data.get('match_stats')

    if not player_props:
        logger.debug("  No player props to analyze")
        return [], []  # Return empty predictions and empty missing players list
    
    logger.info(f"  Analyzing {len(player_props)} player props with projection model...")
    
    # Track failures for reporting
    missing_data_players = []
    insufficient_games_players = []
    projection_failed_players = []
    
    # P1: Track projection sources separately
    projection_source_counts = {
        'model': 0,      # Direct model projection (no blending needed)
        'blended': 0,    # Model + market blend
        'fallback': 0,   # Fallback to historical analysis
        'insight-derived': 0  # Derived from insights (handled elsewhere)
    }

    for prop in player_props:
        try:
            player_name = prop['player']
            stat_type = prop['stat']
            line = prop['line']
            odds_over = prop['odds_over']
            odds_under = prop['odds_under']

            # Get player stats - Priority: StatsMuse → DataballR → Inference
            logger.debug(f"  Fetching stats for {player_name}...")
            game_log = get_player_game_log(
                player_name=player_name,
                last_n_games=20,
                headless=headless,
                retries=3,
                use_cache=True
            )
            
            # Convert dicts to GameLogEntry if needed (for projection model compatibility)
            if game_log and len(game_log) > 0 and isinstance(game_log[0], dict):
                from scrapers.data_models import GameLogEntry
                game_log = [GameLogEntry(**g) if isinstance(g, dict) else g for g in game_log]

            if not game_log:
                logger.debug(f"  FAILED: No data found for {player_name} - may need to add to cache")
                missing_data_players.append(player_name)
                continue
            
            if len(game_log) < 5:
                logger.debug(f"  FAILED: Insufficient data for {player_name} (n={len(game_log)})")
                insufficient_games_players.append((player_name, len(game_log)))
                continue

            # Determine player's team and opponent
            player_team = None
            opponent_team = None
            
            # Try to infer from game context (this is a simplified approach)
            # In a full implementation, you'd match player to team from lineup data
            away_team = game_info.get('away_team', '') if game_info else ''
            home_team = game_info.get('home_team', '') if game_info else ''
            
            # Use projection model (PRIMARY SIGNAL - 70% weight)
            try:
                projection = projection_model.project_stat(
                    player_name=player_name,
                    stat_type=stat_type,
                    game_log=game_log,
                    prop_line=line,
                    opponent_team=opponent_team,
                    player_team=player_team,
                    team_stats=match_stats,
                    min_games=5
                )
            except Exception as proj_err:
                logger.warning(f"  [PROJECTION ERROR] Failed to project {player_name} {stat_type}: {proj_err}")
                import traceback
                logger.debug(traceback.format_exc())
                projection = None

            if not projection:
                logger.debug(f"  FAILED: Projection model returned None for {player_name} {stat_type}")
                projection_failed_players.append((player_name, stat_type))
                continue

            # Calculate historical hit-rate (SECONDARY SIGNAL - 30% weight)
            stat_values = []
            for g in game_log:
                # Handle both GameLogEntry objects and dicts
                minutes = g.minutes if hasattr(g, 'minutes') else g.get('minutes', 0)
                if minutes >= 10:
                    val = getattr(g, stat_type, None) if hasattr(g, stat_type) else g.get(stat_type, None)
                    if val is not None:
                        stat_values.append(val)

            if len(stat_values) < 5:
                logger.debug(f"  Insufficient valid games for {player_name} (n={len(stat_values)})")
                continue

            # Historical hit-rate (for reference only)
            over_count = sum(1 for v in stat_values if v > line)
            historical_prob = over_count / len(stat_values) if len(stat_values) > 0 else 0.5

            # FIX #1: Probability flow - raw_model_prob → adjusted_model_prob → final_blended_prob → EV
            # calibrated_probability is the adjusted_model_prob (after role/volatility/archetype adjustments)
            calibrated_prob = projection.calibrated_probability

            # Use calibrated confidence (already includes lag check)
            confidence = projection.confidence_score

            # Blend with market probability to get final_blended_prob (single source of truth for EV)
            from scrapers.player_projection_model import blend_probabilities
            MODEL_WEIGHT = 0.70
            MARKET_WEIGHT = 0.30
            
            # Determine recommendation using CALIBRATED probability (for direction)
            recommendation = None
            selected_odds = None

            # CRITICAL FIX: Relaxed thresholds - don't require 55%/45% split
            # Allow 50-55% range for OVER and 45-50% range for UNDER
            # Confidence and tiering will handle quality control
            if calibrated_prob > 0.50 and confidence >= 50:
                recommendation = 'OVER'
                selected_odds = odds_over
            elif calibrated_prob < 0.50 and confidence >= 50:
                recommendation = 'UNDER'
                selected_odds = odds_under

            if recommendation:
                # Blend calibrated prob with market prob for final probability
                implied_prob = 1.0 / selected_odds
                calibrated_for_direction = calibrated_prob if recommendation == 'OVER' else (1 - calibrated_prob)
                final_blended_prob = blend_probabilities(
                    model_prob=calibrated_for_direction,
                    market_prob=implied_prob,
                    weight_model=MODEL_WEIGHT,
                    weight_market=MARKET_WEIGHT
                )
                
                # Warn if market probability dominates model (>65% weight)
                market_weight_pct = MARKET_WEIGHT * 100
                if market_weight_pct > 65:
                    model_disagreement = abs(calibrated_for_direction - implied_prob) * 100
                    if model_disagreement > 15:  # Significant disagreement (>15%)
                        logger.warning(f"  [MARKET-DOMINANT] Market weight {market_weight_pct:.0f}%, model disagreement: model={calibrated_for_direction:.1%} vs market={implied_prob:.1%} (diff={model_disagreement:+.1f}%)")
                
                final_blended_prob = max(0.01, min(0.99, final_blended_prob))
                
                # Calculate EV using FINAL_BLENDED_PROB (single source of truth)
                edge = final_blended_prob - implied_prob
                ev_per_100 = (final_blended_prob * (selected_odds - 1) * 100) - ((1 - final_blended_prob) * 100)
                
                # Safety assertion - EV must match probability
                expected_ev = (final_blended_prob * (selected_odds - 1) * 100) - ((1 - final_blended_prob) * 100)
                assert abs(ev_per_100 - expected_ev) < 0.001, f"EV calculation mismatch: {ev_per_100} vs {expected_ev} for prob {final_blended_prob}"

                prediction = {
                    'type': 'player_prop',
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'prediction': recommendation,
                    'odds': selected_odds,
                    'expected_value': round(projection.expected_value, 1),
                    'projected_prob': round(calibrated_for_direction, 3),  # Calibrated prob (before market blend)
                    'historical_prob': round(historical_prob, 3),
                    'final_prob': round(final_blended_prob, 3),  # Final blended probability (SINGLE SOURCE OF TRUTH)
                    'confidence': round(confidence, 0),
                    'sample_size': len(stat_values),
                    'edge': round(edge * 100, 1),
                    'ev_per_100': round(ev_per_100, 2),
                    'game': f"{away_team} @ {home_team}",
                    'market_name': prop.get('market_name', ''),
                    'projection_source': 'blended'  # P1: Track projection source (model + market blend)
                }
                
                # P1: Count projection source
                projection_source_counts['blended'] += 1
                
                # Extract projection details with proper fallbacks (outside dict)
                pace_mult = 1.0
                defense_adj = 1.0
                if hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
                    pace_mult = getattr(projection.matchup_adjustments, 'pace_multiplier', 1.0)
                    defense_adj = getattr(projection.matchup_adjustments, 'defense_adjustment', 1.0)
                
                prediction['projection_details'] = {
                    'std_dev': getattr(projection, 'std_dev', None),
                    'minutes_projected': projection.minutes_projection.projected_minutes if (hasattr(projection, 'minutes_projection') and projection.minutes_projection) else None,
                    'pace_multiplier': pace_mult,
                    'defense_adjustment': defense_adj,
                    'role_change_detected': projection.role_change.detected if (hasattr(projection, 'role_change') and projection.role_change) else False,
                    'player_role': getattr(projection, 'player_role', None),  # FIX #3: Store role for display
                    'distribution_type': getattr(projection, 'distribution_type', None)
                }
                
                predictions.append(prediction)
                logger.debug(f"  {player_name} {stat_type} {recommendation} {line} - Projected: {projection.probability_over_line:.3f}, Historical: {historical_prob:.3f}, Final: {final_prob:.3f}, Confidence: {confidence:.0f}")

        except Exception as e:
            logger.warning(f"  Error analyzing {prop.get('player', 'unknown')}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            continue

    # P1: Return projection source counts for logging
    # Report summary of failures
    total_attempted = len(player_props)
    total_succeeded = len(predictions)
    total_failed = total_attempted - total_succeeded
    
    if total_failed > 0:
        logger.info(f"\n  Player Prop Analysis Summary:")
        logger.info(f"    Total props: {total_attempted}")
        logger.info(f"    Successful: {total_succeeded}")
        logger.info(f"    Failed: {total_failed}")
        
        if missing_data_players:
            logger.warning(f"\n  WARNING: {len(missing_data_players)} player(s) missing from cache:")
            for player in missing_data_players:
                logger.warning(f"      - {player}")
            logger.warning(f"\n  ACTION REQUIRED:")
            logger.warning(f"     1. Add player names to PLAYERS_TO_ADD.txt (one per line)")
            logger.warning(f"     2. Run: python build_databallr_player_cache.py")
            logger.warning(f"     3. Re-run analysis to include these props")
        
        if insufficient_games_players:
            logger.info(f"\n  INFO: {len(insufficient_games_players)} player(s) with insufficient games:")
            for player, games in insufficient_games_players:
                logger.info(f"      - {player} (n={games}, need 5+)")
        
        if projection_failed_players:
            logger.info(f"\n  INFO: {len(projection_failed_players)} prop(s) failed projection:")
            for player, stat in projection_failed_players:
                logger.info(f"      - {player} ({stat})")

    # P1: Store projection source counts in first prediction for retrieval (if any)
    if predictions:
        predictions[0]['_projection_source_counts'] = projection_source_counts

    return predictions, missing_data_players


def calculate_trend_score(hit_rate: float, sample_size: int) -> float:
    """
    Calculate trend quality score.
    
            trend_score = (hit_rate - 50%) * (sample_size / 10)
    
    Returns:
        Trend score (negative for weak trends, positive for strong trends)
    """
    if sample_size == 0:
        return 0.0
    return (hit_rate - 0.5) * (sample_size / 10.0)


def fade_display_bet(fade_bet: Dict, fade_type: str):
    """
    Display a fade alert bet with reasons.
    
    Args:
        fade_bet: Bet dictionary with fade information
        fade_type: Type of fade ("STRONG FADE", "FADE LEAN", etc.)
    """
    bet_type = fade_bet.get('type', 'unknown')
    fade_score = fade_bet.get('fade_score', 0)
    fade_reasons = fade_bet.get('fade_reasons', [])
    fade_emoji = fade_bet.get('fade_emoji', '')
    
    if bet_type == 'player_prop':
        desc = f"{fade_bet.get('player', 'Unknown')} - {fade_bet.get('stat', 'points').title()} {fade_bet.get('prediction', 'OVER')} {fade_bet.get('line', 0)}"
    else:
        desc = f"{fade_bet.get('market', 'Unknown')} - {fade_bet.get('result', 'N/A')}"
    
    model_prob = fade_bet.get('final_prob', fade_bet.get('historical_probability', 0))
    market_prob = 1.0 / fade_bet.get('odds', 2.0) if fade_bet.get('odds', 0) > 0 else 0.5
    edge = fade_bet.get('edge', 0)
    conf = fade_bet.get('confidence', 0)
    sample_size = fade_bet.get('sample_size', 0)
    
    logger.debug(f"Fade detected: {fade_type} - {desc} (score: {fade_score}/100)")
    if fade_reasons:
        print(f"       Why: {' | '.join(fade_reasons)}")
    
    # Show opposite side if viable
    if fade_bet.get('has_viable_opposite'):
        opp_prob = fade_bet.get('opposite_prob', 0)
        opp_ev = fade_bet.get('opposite_ev', 0)
        print(f"       → Consider opposite side: Prob {opp_prob:.1%}, EV {opp_ev:+.1f}%")


def calculate_weighted_confidence(
    base_confidence: float,
    ev_percent: float,
    sample_size: int,
    has_matchup_alignment: bool = False,
    is_trend_only: bool = False,
    trend_score: Optional[float] = None
) -> float:
    """
    Calculate weighted confidence using multiple factors.
    
    weighted_conf = base_conf
                  + EV_weight
                  + matchup_weight
                  + sample_strength
                  - correlation_penalty (handled separately)
                  - trend_only_penalty
    
    Args:
        base_confidence: Base confidence score (0-100)
        ev_percent: EV percentage (e.g., 3.5 for +3.5%)
        sample_size: Sample size for historical data
        has_matchup_alignment: Whether defense/pace aligns strongly
        is_trend_only: Whether this is a trend-only bet (no model)
        trend_score: Trend quality score (if available)
    
    Returns:
        Weighted confidence score
    """
    weighted = base_confidence
    
        # EV_weight: +0.5 * EV%
    ev_weight = 0.5 * ev_percent
    weighted += ev_weight
    
        # Sample_strength: +1 * log(sample_size)
    import math
    if sample_size > 0:
        sample_strength = 1.0 * math.log(max(1, sample_size))
        weighted += sample_strength
    
    # Matchup_weight: +2 if defense/pace aligns strongly
    if has_matchup_alignment:
        weighted += 2.0
    
    # Trend-only penalty: Apply based on trend_score
    if is_trend_only:
        if trend_score is not None:
            if trend_score < 1:
                # Very weak trend: -20 confidence penalty
                weighted -= 20.0
            elif trend_score < 3:
                # Weak trend: -10 confidence penalty
                weighted -= 10.0
            elif trend_score >= 10:
                # Strong trend: +5 confidence boost
                weighted += 5.0
        else:
            # Default trend-only penalty if no trend_score available
            weighted -= 20.0
    
    # FIX #2: Apply sample-size reliability dampening to confidence
    from scrapers.player_projection_model import sample_reliability
    reliability_mult = sample_reliability(sample_size)
    weighted = weighted * reliability_mult
    
    return max(0.0, min(100.0, weighted))


def calculate_correlation_score(bet1: Dict, bet2: Dict) -> float:
    """
    Calculate correlation score between two bets.
    
    Returns:
        - 1.0: Very high correlation (same player)
        - 0.5: Moderate correlation (props + total, same game)
        - 0.0: Low correlation (opposite teams, different games)
    """
    # Same player = very high correlation
    if (bet1.get('type') == 'player_prop' and bet2.get('type') == 'player_prop' and
        bet1.get('player') == bet2.get('player')):
        return 1.0
    
    # Same game
    if bet1.get('game') == bet2.get('game'):
        # Props + total = moderate correlation
        if ((bet1.get('type') == 'player_prop' and bet2.get('market', '').lower() in ['total', 'over/under']) or
            (bet2.get('type') == 'player_prop' and bet1.get('market', '').lower() in ['total', 'over/under'])):
            return 0.5
        
        # Same game, different types = moderate correlation
        return 0.5
    
    # Different games = low correlation
    return 0.0


def promote_best_b_tier(
    all_bets: List[Dict],
    min_confidence: int = 48,
    min_probability: float = 0.55,
    min_edge: float = 4.0
) -> List[Dict]:
    """
    P4: Promote one B-tier bet per slate if justified.
    
    Criteria:
    - Confidence 48-64 (B-tier range)
    - Probability >= 55%
    - Edge >= +4%
    - CLV favorable (if available): must be positive OR unavailable, never negative
    - Critical guardrail: confidence_after_penalties >= confidence_before_penalties - 25
      Prevents promoting bets that were heavily suppressed for good reasons
    
    Args:
        all_bets: List of all bets (may already be tiered)
        min_confidence: Minimum confidence for promotion (default: 48)
        min_probability: Minimum probability for promotion (default: 0.55)
        min_edge: Minimum edge % for promotion (default: 4.0)
    
    Returns:
        Updated bet list with promoted bet(s) if criteria met
    """
    # Filter B-tier bets (confidence 48-64)
    b_tier_bets = [b for b in all_bets if 48 <= b.get('confidence', 0) < 65]
    
    if not b_tier_bets:
        return all_bets  # No B-tier bets to promote
    
    # Apply strict criteria
    candidates = []
    for bet in b_tier_bets:
        conf_after = bet.get('confidence', 0)
        conf_before = bet.get('confidence_before_penalties', bet.get('original_confidence', conf_after))
        prob = bet.get('final_prob', bet.get('historical_probability', 0))
        edge = bet.get('edge', 0)
        clv = bet.get('clv', None)  # None = unavailable, positive = favorable, negative = unfavorable
        
        # Guardrail: not heavily suppressed (confidence_after >= confidence_before - 25)
        if conf_after < conf_before - 25:
            continue
        
        # CLV check: must be positive OR unavailable (never negative)
        if clv is not None and clv < 0:
            continue
        
        # Other criteria
        if prob >= min_probability and edge >= min_edge:
            candidates.append(bet)
    
    # Promote best candidate (highest edge * confidence)
    if candidates:
        best = max(candidates, key=lambda b: b.get('edge', 0) * b.get('confidence', 0))
        
        # Update tier
        best['tier'] = 'A'
        best['promoted_from'] = 'B'
        best['promotion_reason'] = f"Strong edge ({best.get('edge', 0):.1f}%) with CLV confirmation"
        
        # Log promotion
        bet_type = best.get('type', 'unknown')
        if bet_type == 'player_prop':
            bet_desc = f"{best.get('player', 'Unknown')} - {best.get('stat', 'points').title()} {best.get('prediction', 'OVER')} {best.get('line', 0)}"
        else:
            bet_desc = f"{best.get('market', 'Unknown')} - {best.get('result', '')}"
        
        logger.debug(f"B-Tier promotion: {bet_desc} - {best['promotion_reason']}")
    
    return all_bets


def rank_all_bets(team_bets: List[Dict], player_props: List[Dict]) -> List[Dict]:
    """
    Combine team bets and player props into a unified ranking.

    QUALITY OVER QUANTITY with STRICT EV THRESHOLDS:
    - Props: Minimum +3% EV
    - Sides/Totals: Minimum +2% EV
    - Minimum confidence threshold: 50/100
    - Maximum 2 bets per game (correlation control)
    - Trend-only bets (no model projections) get confidence penalty

    Returns:
        List of ALL high-confidence bets
    """
    # Initialize team bet rejection tracking for this function call
    rank_all_bets._team_bet_rejections = []
    all_bets = []
    
    # Initialize projection model for insight props
    model = PlayerProjectionModel()

    # Convert team bets to unified format
    for bet in team_bets:
        try:
            if not bet or not isinstance(bet, dict):
                continue
                
            insight = bet.get('insight', {})
            analysis = bet.get('analysis', {})
            
            # Check if this is actually a player prop (marked in analyze_team_bets)
            bet_type = bet.get('_bet_type', 'team_bet')
            
            # Handle player props from insights differently
            if bet_type == 'player_prop':
                # Extract player prop info from insight
                prop_info = _extract_prop_info_from_insight(insight)
                if not prop_info:
                    logger.debug(f"  Skipping player prop from insight - cannot extract prop info")
                    continue
                
                player_name = prop_info.get('player', '').strip()
                stat_type = prop_info.get('stat', 'points')
                line = prop_info.get('line', 0)
                
                # VALIDATION: Skip if invalid
                if not player_name or player_name == 'Unknown' or line <= 0:
                    logger.debug(f"  Skipping player prop - invalid data: player={player_name}, line={line}")
                    continue
                
                # Check for projection details
                projection_details = analysis.get('projection_details', {})
                if not projection_details or not isinstance(projection_details, dict):
                    # Try to CALCULATE projection using the model (Fix for 0% history)
                    try:
                        # Get game logs - use StatsMuse-first version
                        games = get_player_game_log(
                            player_name=player_name,
                            last_n_games=20,
                            headless=True,
                            retries=3,
                            use_cache=True
                        )
                        # Convert dicts to GameLogEntry if needed
                        if games and len(games) > 0 and isinstance(games[0], dict):
                            from scrapers.data_models import GameLogEntry
                            games = [GameLogEntry(**g) if isinstance(g, dict) else g for g in games]
                        if games and len(games) >= 5:
                            # Run projection
                            proj = model.project_stat(player_name, stat_type, games, line)
                            if proj:
                                # Update analysis with REAL model data
                                analysis['projection_details'] = {
                                    'std_dev': getattr(proj, 'std_dev', 0),
                                    'minutes_projected': proj.minutes_projection.projected_minutes if (hasattr(proj, 'minutes_projection') and proj.minutes_projection) else 0,
                                    'pace_multiplier': 1.0,
                                    'defense_adjustment': 1.0, 
                                    'role_change_detected': proj.role_change.detected if (hasattr(proj, 'role_change') and proj.role_change) else False,
                                    'player_role': getattr(proj, 'player_role', None)  # FIX #3: Store role for display
                                }
                                analysis['projected_prob'] = proj.probability_over_line
                                analysis['historical_probability'] = proj.historical_hit_rate
                                analysis['original_historical_probability'] = proj.historical_hit_rate # Redundant key for safety
                                analysis['projected_expected_value'] = proj.expected_value
                                analysis['sample_size'] = len(games)
                                # Update projection_details variable
                                projection_details = analysis['projection_details']
                                logger.info(f"  Calculated missing projection for {player_name}: Hist={proj.historical_hit_rate:.1%}")
                    except Exception as e:
                         logger.warning(f"  Failed to calculate projection for {player_name}: {e}")

                if not projection_details:
                    logger.debug(f"  Skipping player prop {player_name} - missing projection_details and calculation failed")
                    continue
                
                # Calculate weighted confidence for player props from insights
                base_conf = analysis.get('confidence_score', 50)
                ev_percent = analysis.get('value_percentage', 0)
                sample_size = analysis.get('sample_size', 0)
                
                # Check for matchup alignment
                has_matchup_alignment = False
                if projection_details:
                    pace_mult = projection_details.get('pace_multiplier', 1.0)
                    def_adj = projection_details.get('defense_adjustment', 1.0)
                    if abs(pace_mult - 1.0) > 0.05 or abs(def_adj - 1.0) > 0.05:
                        has_matchup_alignment = True
                
                weighted_conf = calculate_weighted_confidence(
                    base_confidence=base_conf,
                    ev_percent=ev_percent,
                    sample_size=sample_size,
                    has_matchup_alignment=has_matchup_alignment,
                    is_trend_only=False,  # Player props always have model projections
                    trend_score=None
                )
                
                # P1: Ensure projection_source is set (from analysis or default to insight-derived)
                projection_source = analysis.get('projection_source', 'insight-derived')
                
                all_bets.append({
                    'type': 'player_prop',
                    'game': bet.get('game', 'Unknown Game'),
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'prediction': 'OVER',  # Default, should be determined from analysis
                    'odds': _safe_insight_get(insight, 'odds', 0),
                    'confidence': weighted_conf,
                    'original_confidence': base_conf,
                    'has_model_projection': True,
                    'ev_per_100': analysis.get('ev_per_100', 0),
                    'edge': analysis.get('value_percentage', 0),
                    'sample_size': analysis.get('sample_size', 0),
                    'expected_value': analysis.get('projected_expected_value', 0),
                    'projected_prob': analysis.get('projected_prob', 0),
                    'historical_prob': analysis.get('original_historical_probability', analysis.get('historical_probability', 0)),
                    'final_prob': analysis.get('historical_probability', 0),  # Store final probability for filtering
                    'historical_probability': analysis.get('historical_probability', 0),  # Also store for compatibility
                    'projection_details': projection_details,
                    'has_matchup_alignment': has_matchup_alignment,
                    'projection_source': projection_source  # P1: Track projection source
                })
                continue
            
            # Handle team bets
            # Check if this is a trend-only bet (no model projections)
            has_model_projection = analysis.get('projection_details') is not None
            base_confidence = analysis.get('confidence_score', 50)
            
            # Calculate trend score for trend-only bets
            trend_score = None
            if bet_type == 'team_bet' and not has_model_projection:
                # Calculate trend score from historical data
                hit_rate = analysis.get('historical_probability', 0.5)
                sample_size = analysis.get('sample_size', 0)
                trend_score = calculate_trend_score(hit_rate, sample_size)
            
            # Calculate weighted confidence
            ev_percent = analysis.get('value_percentage', 0)  # Edge percentage
            sample_size = analysis.get('sample_size', 0)
            
            # Check for matchup alignment (defense/pace factors)
            proj_details = analysis.get('projection_details', {})
            has_matchup_alignment = False
            if proj_details:
                # Check if pace or defense adjustments are significant
                pace_mult = proj_details.get('pace_multiplier', 1.0)
                def_adj = proj_details.get('defense_adjustment', 1.0)
                # Strong alignment if adjustments are > 5% from baseline
                if abs(pace_mult - 1.0) > 0.05 or abs(def_adj - 1.0) > 0.05:
                    has_matchup_alignment = True
            
            confidence = calculate_weighted_confidence(
                base_confidence=base_confidence,
                ev_percent=ev_percent,
                sample_size=sample_size,
                has_matchup_alignment=has_matchup_alignment,
                is_trend_only=(bet_type == 'team_bet' and not has_model_projection),
                trend_score=trend_score
            )
            
            if bet_type == 'team_bet' and not has_model_projection:
                logger.debug(f"  Trend-only bet - base: {base_confidence:.0f}, weighted: {confidence:.0f}, trend_score: {trend_score:.2f if trend_score else 'N/A'}")
            
            # Calculate EV using final_prob (single source of truth)
            final_prob = analysis.get('historical_probability', 0.5)
            odds = _safe_insight_get(insight, 'odds', 0)
            ev_per_100 = analysis.get('ev_per_100', 0)
            
            # VALIDATION: Assert EV consistency at creation time
            if odds > 0 and final_prob > 0:
                from scrapers.bet_validation import calculate_ev
                expected_ev = calculate_ev(final_prob, odds, stake=100.0)
                if abs(expected_ev - ev_per_100) >= 0.01:  # 1 cent tolerance
                    logger.debug(f"[VALIDATION] EV mismatch at creation: expected {expected_ev:.2f}, got {ev_per_100:.2f} "
                               f"(prob={final_prob:.4f}, odds={odds:.2f})")
                    # Recalculate to fix
                    ev_per_100 = expected_ev
            
            all_bets.append({
                'type': bet_type,  # Use marked type instead of always 'team_bet'
                'game': bet.get('game', 'Unknown Game'),
                'market': _safe_insight_get(insight, 'market', 'Unknown Market'),
                'result': _safe_insight_get(insight, 'result', ''),
                'odds': odds,
                'confidence': confidence,
                'original_confidence': base_confidence,
                'has_model_projection': has_model_projection,
                'ev_per_100': ev_per_100,
                'edge': analysis.get('value_percentage', 0),
                'sample_size': analysis.get('sample_size', 0),
                'fact': (_safe_insight_get(insight, 'fact', '') or '')[:100],  # Truncate for display
                'historical_probability': final_prob,
                'final_prob': final_prob,  # Store as final_prob for filtering consistency
                'analysis': analysis,  # Include full analysis for projection details
                'trend_score': trend_score,  # Store trend score for reference
                'has_matchup_alignment': has_matchup_alignment  # Store matchup alignment flag
            })
        except Exception as e:
            logger.warning(f"  Error processing team bet: {e}")
            continue

    # Add player props (already in unified format, just need to ensure all fields)
    for prop in player_props:
        try:
            if not prop or not isinstance(prop, dict):
                continue
            
            # VALIDATION: Skip if player name or line is missing/invalid
            player_name = prop.get('player', '').strip()
            line = prop.get('line', 0)
            
            if not player_name or player_name == 'Unknown' or player_name == 'Unknown Player':
                logger.debug(f"  Skipping player prop - invalid player name: {player_name}")
                continue
            
            if not line or line <= 0:
                logger.debug(f"  Skipping player prop - invalid line: {line}")
                continue
            
            # VALIDATION: Require projection_details for player props
            projection_details = prop.get('projection_details', {})
            if not projection_details or not isinstance(projection_details, dict):
                logger.debug(f"  Skipping player prop {player_name} - missing projection_details")
                continue
                
            # Calculate weighted confidence for player props
            base_conf = prop.get('confidence', 50)
            ev_percent = prop.get('edge', 0)
            sample_size = prop.get('sample_size', 0)
            
            # Check for matchup alignment
            has_matchup_alignment = False
            if projection_details:
                pace_mult = projection_details.get('pace_multiplier', 1.0)
                def_adj = projection_details.get('defense_adjustment', 1.0)
                if abs(pace_mult - 1.0) > 0.05 or abs(def_adj - 1.0) > 0.05:
                    has_matchup_alignment = True
            
            weighted_conf = calculate_weighted_confidence(
                base_confidence=base_conf,
                ev_percent=ev_percent,
                sample_size=sample_size,
                has_matchup_alignment=has_matchup_alignment,
                is_trend_only=False,  # Player props always have model projections
                trend_score=None
            )
            
            # Calculate EV using final_prob (single source of truth)
            final_prob = prop.get('final_prob', 0)
            odds = prop.get('odds', 0)
            ev_per_100 = prop.get('ev_per_100', 0)
            
            # VALIDATION: Assert EV consistency at creation time
            if odds > 0 and final_prob > 0:
                from scrapers.bet_validation import calculate_ev
                expected_ev = calculate_ev(final_prob, odds, stake=100.0)
                if abs(expected_ev - ev_per_100) >= 0.01:  # 1 cent tolerance
                    logger.debug(f"[VALIDATION] EV mismatch at creation for {player_name}: expected {expected_ev:.2f}, got {ev_per_100:.2f} "
                               f"(prob={final_prob:.4f}, odds={odds:.2f})")
                    # Recalculate to fix
                    ev_per_100 = expected_ev
            
            all_bets.append({
                'type': 'player_prop',
                'game': prop.get('game', 'Unknown Game'),
                'player': player_name,
                'stat': prop.get('stat', 'points'),
                'line': line,
                'prediction': prop.get('prediction', 'OVER'),
                'odds': odds,
                'confidence': weighted_conf,
                'original_confidence': base_conf,  # Store original for display
                'has_model_projection': True,  # Player props always have projections
                'ev_per_100': ev_per_100,
                'edge': prop.get('edge', 0),
                'sample_size': prop.get('sample_size', 0),
                'expected_value': prop.get('expected_value', 0),
                'projected_prob': prop.get('projected_prob', 0),
                'historical_prob': prop.get('historical_prob', 0),
                'final_prob': final_prob,
                'projection_details': projection_details,
                'market_name': prop.get('market_name', ''),
                'player_role': projection_details.get('player_role') if isinstance(projection_details, dict) else None,  # FIX #3: Store role for display
                'projection_source': prop.get('projection_source', 'blended')  # P1: Track projection source (default to blended for analyze_player_props bets)
            })
        except Exception as e:
            logger.warning(f"  Error processing player prop: {e}")
            continue

    # VALIDATION: Apply core invariants before filtering
    from scrapers.bet_validation import validate_bet_list, health_snapshot_from_dicts
    
    # Generate health snapshot before filtering
    pre_filter_health = health_snapshot_from_dicts(all_bets)
    if pre_filter_health["count"] > 0:
        logger.debug(f"[VALIDATION] Pre-filter health: {pre_filter_health['valid_count']}/{pre_filter_health['count']} valid, "
                    f"EV inconsistencies: {pre_filter_health.get('ev_inconsistencies', 0)}")
    
    # Validate all bets (filter invalid ones silently)
    validated_bets = validate_bet_list(all_bets, strict=False)

    # IMPROVEMENT 2.2: Combined EV + Probability Cutoff
    # Reject bets where:
    # - probability < 60%, OR
    # - edge < 0%, OR
    # - sample < 5 (unless model-driven)
    ev_filtered_bets = []
    rejected_bets = []
    team_bet_rejections = []  # Track team bet rejections separately
    
    for bet in validated_bets:
        probability = bet.get('final_prob', bet.get('historical_probability', 0))
        edge = bet.get('edge', 0)  # Edge percentage
        sample_size = bet.get('sample_size', 0)
        has_model = bet.get('has_model_projection', False)
        bet_type = bet.get('type', 'unknown')
        confidence = bet.get('confidence', 0)
        
        # CRITICAL FIX: Decouple "Projection Validity" from "Bet Eligibility"
        # Use market-specific probability floors instead of hard 50% rejection
        # This allows props like Ja Morant (49.1%) to survive to tiering
        from scrapers.bet_validation import get_market_type, MIN_PROBABILITY, MIN_PROBABILITY_LEGACY
        market_type = get_market_type(bet)
        min_prob = MIN_PROBABILITY.get(market_type, MIN_PROBABILITY_LEGACY)
        
        rejection_reason = None
        
        # Flag low probability but don't reject - let tiering handle it
        if probability < min_prob:
            # Only reject if probability is very low (< 45% for all markets)
            # 47-49% props should survive to tiering (especially with +edge)
            if probability < 0.45:
                rejection_reason = f'Probability too low ({probability:.1%} < 45%, min for {market_type} is {min_prob:.1%})'
            else:
                # Otherwise, flag it but continue (will be handled by tiering/confidence)
                bet['low_prob_flag'] = True
        
        # Reject if edge < 0%
        if not rejection_reason and edge < 0:
            rejection_reason = f'Negative edge ({edge:.1f}%)'
        
        # Reject if sample < 5 (unless model-driven)
        if not rejection_reason and sample_size < 5 and not has_model:
            rejection_reason = f'Sample too small (n={sample_size} < 5, no model)'
        
        # Reject team bets with confidence below 40 (after all penalties)
        if not rejection_reason and bet_type == 'team_bet' and confidence < 40:
            rejection_reason = f'Confidence below 40 ({confidence:.0f})'
        
        # Check for correlation with player prop (team bets)
        if not rejection_reason and bet_type == 'team_bet':
            correlated_with = bet.get('correlated_with', [])
            if correlated_with:
                # Don't reject, but note it (correlation penalty already applied)
                pass  # Correlation handled by penalty, not rejection
        
        # Record rejection
        if rejection_reason:
            rejected_bets.append({'bet': bet, 'reason': rejection_reason})
            if bet_type == 'team_bet':
                team_bet_rejections.append({
                    'bet': bet,
                    'reason': rejection_reason,
                    'market': bet.get('market', 'Unknown'),
                    'result': bet.get('result', ''),
                    'confidence': confidence,
                    'edge': edge,
                    'probability': probability
                })
            continue
        
        ev_filtered_bets.append(bet)
    
    logger.info(f"EV filtering: {len(ev_filtered_bets)}/{len(all_bets)} bets passed")
    
    # Log team bet rejections separately
    if team_bet_rejections:
        team_bet_count = sum(1 for b in all_bets if b.get('type') == 'team_bet')
        team_bet_passed = sum(1 for b in ev_filtered_bets if b.get('type') == 'team_bet')
        reason_counts = {}
        for r in team_bet_rejections:
            reason = r['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        logger.info(f"Team bets: {team_bet_passed} selected from {team_bet_count} found")
        print(f"  Team bet rejections: {len(team_bet_rejections)}")
        for r in team_bet_rejections[:5]:  # Show top 5 team bet rejections
            desc = f"{r['market']} - {r['result']}"
            print(f"    - {desc}: {r['reason']} (Prob: {r['probability']:.1%}, Edge: {r['edge']:+.1f}%, Conf: {r['confidence']:.0f})")
    
    if rejected_bets:
        player_rejections = [r for r in rejected_bets if r['bet'].get('type') == 'player_prop']
        if player_rejections:
            print(f"  Rejected {len(player_rejections)} player prop bets:")
            for r in player_rejections[:10]:  # Show more rejected bets
                bet = r['bet']
                desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()}"
                prob = bet.get('final_prob', bet.get('historical_probability', 0))
                edge = bet.get('edge', 0)
                conf = bet.get('confidence', 0)
                print(f"    - {desc}: {r['reason']} (Prob: {prob:.1%}, Edge: {edge:+.1f}%, Conf: {conf:.0f})")
    
    # FIX #4: Apply correlation penalty BEFORE sorting
    # Group bets by game first
    game_groups = {}
    for bet in ev_filtered_bets:
        game = bet.get('game', 'Unknown')
        if game not in game_groups:
            game_groups[game] = []
        game_groups[game].append(bet)
    
    # Apply correlation awareness: De-tier correlated bets instead of blocking
    # Identify correlated bets (same player different stats, same game pace props)
    for game, bets_in_game in game_groups.items():
        # Sort by confidence within game to identify order
        bets_in_game.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Identify correlated bets
        for i, bet1 in enumerate(bets_in_game):
            correlated_with = []
            correlation_reasons = []
            
            for j, bet2 in enumerate(bets_in_game):
                if i == j:
                    continue
                
                # Same player, different stats (high correlation)
                if (bet1.get('type') == 'player_prop' and bet2.get('type') == 'player_prop' and
                    bet1.get('player') == bet2.get('player') and
                    bet1.get('stat') != bet2.get('stat')):
                    correlated_with.append(f"{bet2.get('player')} {bet2.get('stat')}")
                    correlation_reasons.append(f"Same player ({bet1.get('player')}) different stat")
                
                # Same game pace-sensitive props (moderate correlation)
                elif bet1.get('game') == bet2.get('game'):
                    bet1_market = bet1.get('market', '').lower()
                    bet2_market = bet2.get('market', '').lower()
                    if 'total' in bet1_market or 'total' in bet2_market:
                        # Pace-sensitive props
                        if bet1.get('type') == 'player_prop' or bet2.get('type') == 'player_prop':
                            correlated_with.append(f"{bet2.get('market', 'Unknown')} {bet2.get('result', '')}")
                            correlation_reasons.append("Same game pace-sensitive props")
            
            if correlated_with:
                bet1['correlated_with'] = correlated_with
                bet1['correlation_reason'] = '; '.join(set(correlation_reasons))  # Deduplicate
            
            # Apply confidence penalty (2nd bet: 88%, 3rd: 76%, 4th: 64%, etc.)
            penalty_multiplier = 1.0 - (i * 0.12)  # 1st: 100%, 2nd: 88%, 3rd: 76%, etc.
            if i > 0:  # Only penalize 2nd bet and beyond
                original_conf = bet1.get('confidence', 0)
                bet1['confidence'] = max(0, original_conf * penalty_multiplier)
                bet1['correlation_penalty'] = original_conf - bet1['confidence']
    
    # FADE DETECTION: Identify public traps and evaluate opposite sides
    # Must happen after EV filtering but before tiered confidence filtering
    logger.debug(f"Fade detection: Analyzing {len(ev_filtered_bets)} bets")
    fade_alerts, opposite_side_bets = detect_fades(ev_filtered_bets, games_data=None)
    
    # Show fade detection summary
    if ev_filtered_bets:
        # Calculate fade score stats for all bets
        fade_scores = [b.get('fade_score', 0) for b in ev_filtered_bets if 'fade_score' in b]
        if fade_scores:
            max_fade = max(fade_scores)
            avg_fade = sum(fade_scores) / len(fade_scores)
            print(f"  [FADE DETECTION] Fade scores: Max {max_fade:.0f}, Avg {avg_fade:.1f} (across {len(fade_scores)} bets)")
    
    if fade_alerts:
        strong_fades = [f for f in fade_alerts if f.get('fade_score', 0) >= 70]
        fade_leans = [f for f in fade_alerts if 50 <= f.get('fade_score', 0) < 70]
        watch_fades = [f for f in fade_alerts if 30 <= f.get('fade_score', 0) < 50]
        
        print(f"  [FADE DETECTION] Found {len(fade_alerts)} fade candidate(s): {len(strong_fades)} strong, {len(fade_leans)} leans, {len(watch_fades)} watch")
        
        if strong_fades:
            print(f"\n  [FADE ALERTS 🔴] {len(strong_fades)} STRONG FADE(s) detected:")
            for fade in strong_fades[:5]:  # Show top 5
                fade_display_bet(fade, "STRONG FADE")
        
        if fade_leans:
            print(f"\n  [FADE LEANS 🟠] {len(fade_leans)} fade lean(s) detected:")
            for fade in fade_leans[:3]:  # Show top 3
                fade_display_bet(fade, "FADE LEAN")
        
        if watch_fades and len(watch_fades) <= 5:
            print(f"\n  [WATCH 🟡] {len(watch_fades)} watch/avoid bet(s):")
            for fade in watch_fades[:3]:
                fade_display_bet(fade, "WATCH")
    else:
        print(f"  [FADE DETECTION] ✓ No fades detected (all bets have fade scores < 30)")
    
    # Add viable opposite side bets to the pool for consideration
    if opposite_side_bets:
        print(f"\n  [FADE OPPOSITE] Found {len(opposite_side_bets)} viable opposite-side opportunities:")
        for opp_bet in opposite_side_bets[:5]:  # Show top 5
            bet_type = opp_bet.get('type', 'unknown')
            if bet_type == 'player_prop':
                desc = f"{opp_bet.get('player', 'Unknown')} - {opp_bet.get('stat', 'points').title()} {opp_bet.get('prediction', 'OVER')} {opp_bet.get('line', 0)}"
            else:
                desc = f"{opp_bet.get('market', 'Unknown')} - {opp_bet.get('result', 'N/A')}"
            prob = opp_bet.get('final_prob', 0)
            ev = opp_bet.get('ev_per_100', 0)
            odds = opp_bet.get('odds', 0)
            print(f"    → {desc}: Prob {prob:.1%}, EV {ev:+.1f}%, Odds {odds:.2f}")
        ev_filtered_bets.extend(opposite_side_bets)
    
    # VALIDATION: Validate EV consistency after filtering
    from scrapers.bet_validation import BetEvaluation, validate_bet
    ev_validated_bets = []
    ev_validation_failures = []
    
    for bet in ev_filtered_bets:
        bet_eval = BetEvaluation.from_bet_dict(bet)
        if bet_eval:
            try:
                validate_bet(bet_eval, strict=False)
                ev_validated_bets.append(bet)
            except ValueError as e:
                ev_validation_failures.append({'bet': bet, 'error': str(e)})
                logger.debug(f"[VALIDATION] EV validation failed for bet: {e}")
        else:
            ev_validated_bets.append(bet)  # Include even if we can't validate
    
    if ev_validation_failures:
        logger.warning(f"[VALIDATION] {len(ev_validation_failures)} bet(s) failed EV consistency check")
        for failure in ev_validation_failures[:3]:  # Log first 3
            logger.debug(f"  - {failure['error']}")
    
    # Market-specific tiered confidence thresholds with soft floor
    # Import BEFORE using these functions
    from scrapers.bet_validation import (
        MARKET_TIER_THRESHOLDS, MARKET_WEIGHTS,
        get_market_type, calculate_effective_confidence, get_tier_thresholds
    )
    
    # Now sort ALL bets by confidence (penalties applied)
    try:
        all_bets_sorted = sorted(ev_validated_bets, key=lambda x: x.get('confidence', 0), reverse=True)
    except Exception as e:
        logger.warning(f"Error sorting bets: {e}")
        all_bets_sorted = ev_validated_bets
    
    # CRITICAL FIX: Tier assignment happens FIRST with RAW confidence
    # Then market weight is applied for soft floor (only helps borderline cases)
    # Correct order: raw_conf → tier assignment → market weight → display confidence
    
    a_tier_bets = []
    b_tier_bets = []
    c_tier_bets = []
    
    for bet in all_bets_sorted:
        market_type = get_market_type(bet)
        raw_conf = float(bet.get('confidence', 0))
        
        # Store for later
        bet['market_type'] = market_type
        bet['raw_confidence'] = raw_conf
        
        # STEP 1: Assign tier using RAW confidence
        thresholds = get_tier_thresholds(market_type)
        initial_tier = None
        if raw_conf >= thresholds["A"]:
            initial_tier = 'A'
        elif raw_conf >= thresholds["B"]:
            initial_tier = 'B'
        elif raw_conf >= thresholds["C"]:
            initial_tier = 'C'
        else:
            initial_tier = 'WATCHLIST'
        
        # STEP 2: Apply market weight for soft floor (helps borderline cases)
        effective_conf = calculate_effective_confidence(bet)
        bet['effective_confidence'] = effective_conf
        
        # STEP 3: If effective_confidence would upgrade tier, use it (soft floor benefit)
        # But don't downgrade tier based on effective_confidence
        final_tier = initial_tier
        if effective_conf >= thresholds["A"] and initial_tier != 'A':
            final_tier = 'A'  # Soft floor upgraded to A
        elif effective_conf >= thresholds["B"] and initial_tier not in ['A', 'B']:
            final_tier = 'B'  # Soft floor upgraded to B
        elif effective_conf >= thresholds["C"] and initial_tier == 'WATCHLIST':
            final_tier = 'C'  # Soft floor upgraded to C
        
        # Store tier
        bet['initial_tier'] = initial_tier
        bet['tier'] = final_tier
        
        # Add to appropriate tier list
        if final_tier == 'A':
            a_tier_bets.append(bet)
        elif final_tier == 'B':
            b_tier_bets.append(bet)
        elif final_tier == 'C':
            c_tier_bets.append(bet)
    
    # Get global thresholds for display (use team_sides as default)
    default_thresholds = MARKET_TIER_THRESHOLDS["team_sides"]
    A_TIER_CONFIDENCE = default_thresholds["A"]  # 65
    B_TIER_CONFIDENCE = default_thresholds["B"]  # 50
    C_TIER_CONFIDENCE = default_thresholds["C"]  # 40 (but will vary by market)
    
    # Near-miss bucket for calibration review (prob >= 55%, edge >= +4%, conf 35-49)
    # Check from all bets to catch near-misses even if they failed probability threshold
    # Use EFFECTIVE confidence for near-miss detection (accounts for soft floor)
    # All bets now have effective_confidence already calculated above
    near_miss_bets = []
    c_tier_near_misses = []  # Effective conf just below C-Tier threshold
    for bet in all_bets_sorted:  # Check all bets that passed EV filtering
        # effective_confidence already calculated above
        effective_conf = float(bet.get('effective_confidence', bet.get('confidence', 0)))
        raw_conf = float(bet.get('raw_confidence', bet.get('confidence', 0)))
        prob = float(bet.get('final_prob', bet.get('historical_probability', 0)))
        edge = float(bet.get('edge', 0))
        
        # Get market-specific C-tier threshold
        market_type = bet.get('market_type', 'team_sides')
        thresholds = get_tier_thresholds(market_type)
        c_threshold = thresholds["C"]
        
        # Near-miss criteria: Effective conf 32-49, Prob >= 55%, Edge >= +4%
        # For player props, effective conf 32-49 (accounting for soft floor 0.92x: raw 35 = effective 32.2)
        # For team sides, effective conf 35-49
        if (c_threshold - 3.0) <= effective_conf < 50.0 and prob >= 0.55 and edge >= 4.0:
            near_miss_bets.append(bet)
            # Identify C-Tier near-misses (effective conf just below threshold)
            # For player props: effective conf 32-34.99 (raw 35-38 with 0.92x = 32.2-34.96)
            # For team sides: effective conf 35-39.99 (raw 35-40)
            if (c_threshold - 3.0) <= effective_conf < c_threshold:
                c_tier_near_misses.append(bet)
    
    # Log near-miss bets for post-game review
    if near_miss_bets:
        print(f"\n  [WATCHLIST] {len(near_miss_bets)} near-miss bet(s) for post-game review:")
        for bet in sorted(near_miss_bets, key=lambda x: x.get('confidence', 0), reverse=True)[:10]:
            bet_type = bet.get('type', 'unknown')
            if bet_type == 'player_prop':
                bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
            else:
                bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', 'N/A')}"
            prob = bet.get('final_prob', bet.get('historical_probability', 0))
            edge = bet.get('edge', 0)
            conf = float(bet.get('confidence', 0))
            # Note C-Tier near-misses (use effective confidence)
            note = ""
            effective_conf = bet.get('effective_confidence', conf)
            market_type = bet.get('market_type', 'team_sides')
            thresholds = get_tier_thresholds(market_type)
            c_threshold = thresholds["C"]
            if (c_threshold - 3.0) <= effective_conf < c_threshold:
                note = f" (C-Tier near-miss, effective conf {effective_conf:.1f} below {c_threshold} threshold for {market_type})"
            print(f"    - {bet_desc}: Raw Conf {conf:.0f} (Effective: {effective_conf:.1f}), Prob {prob:.1%}, Edge {edge:+.1f}%{note}")
    
    # Combine A and B tier bets (all allowed)
    high_confidence_bets = a_tier_bets + b_tier_bets
    
    # UPGRADED: Signal-density auto-promotion (instead of empty-slate only)
    # Avoids over-promotion on small slates but prevents silence on normal slates
    total_props_found = len([b for b in ev_validated_bets if b.get('type') == 'player_prop'])
    props_passing = len([b for b in high_confidence_bets + c_tier_bets if b.get('type') == 'player_prop'])
    
    auto_promoted_c_tier = False
    # Signal-density condition: If we found many props but few passed, auto-promote best watchlist
    should_auto_promote = (
        (total_props_found >= 10 and props_passing < 2) or  # Many props found, few passed
        (len(c_tier_bets) == 0 and len(high_confidence_bets) == 0 and c_tier_near_misses)  # Empty slate fallback
    )
    
    if should_auto_promote and c_tier_near_misses:
        # Check if we have a strong watchlist candidate
        best_near_miss = max(c_tier_near_misses, key=lambda x: (
            x.get('confidence', 0),
            x.get('final_prob', 0),
            x.get('edge', 0)
        ))
        conf = best_near_miss.get('confidence', 0)
        prob = best_near_miss.get('final_prob', 0)
        edge = best_near_miss.get('edge', 0)
        
        # Auto-promote if strong enough (use effective_confidence - already calculated above)
        effective_conf = float(best_near_miss.get('effective_confidence', conf))
        market_type = best_near_miss.get('market_type', 'team_sides')
        thresholds = get_tier_thresholds(market_type)
        c_threshold = thresholds["C"]
        
        # Auto-promote if effective conf is within 3 points of C-tier threshold
        if effective_conf >= (c_threshold - 3.0) and prob >= 0.57 and edge >= 4.0:
            # Add as C-Tier
            best_near_miss['tier'] = 'C'
            best_near_miss['stake_cap_pct'] = 0.12
            high_confidence_bets.append(best_near_miss)
            auto_promoted_c_tier = True
            bet_type = best_near_miss.get('type', 'unknown')
            if bet_type == 'player_prop':
                bet_desc = f"{best_near_miss.get('player', 'Unknown')} - {best_near_miss.get('stat', 'points').title()} {best_near_miss.get('prediction', 'OVER')} {best_near_miss.get('line', 0)}"
            else:
                bet_desc = f"{best_near_miss.get('market', 'Unknown')} - {best_near_miss.get('result', 'N/A')}"
            reason = "signal-density escape" if total_props_found >= 10 else "empty slate escape"
            print(f"  [INFO] Auto-promoted to C-Tier ({reason}, {total_props_found} props found, {props_passing} passed): {bet_desc} (Raw Conf {conf:.0f}, Effective {effective_conf:.1f}, Prob {prob:.1%}, Edge {edge:+.1f}%)")
    
    # Add max 1 C-tier bet (best one only) - unless auto-promotion happened
    if c_tier_bets and not auto_promoted_c_tier:
        high_confidence_bets.append(c_tier_bets[0])  # Best C-tier bet only
        remaining_c_tier = c_tier_bets[1:] if len(c_tier_bets) > 1 else []
        
        # Track team bet rejections from C-tier limiting
        if not hasattr(rank_all_bets, '_team_bet_rejections'):
            rank_all_bets._team_bet_rejections = []
        
        # Fix #3: Add explicit logging for excluded C-tier bets (including player props)
        for rejected_c_tier_bet in remaining_c_tier:
            bet_type = rejected_c_tier_bet.get('type', 'unknown')
            if bet_type == 'team_bet':
                rejection_entry = {
                    'bet': rejected_c_tier_bet,
                    'reason': f'C-tier limit (best of {len(c_tier_bets)} selected)',
                    'market': rejected_c_tier_bet.get('market', 'Unknown'),
                    'result': rejected_c_tier_bet.get('result', ''),
                    'confidence': rejected_c_tier_bet.get('confidence', 0),
                    'edge': rejected_c_tier_bet.get('edge', 0),
                    'probability': rejected_c_tier_bet.get('final_prob', rejected_c_tier_bet.get('historical_probability', 0))
                }
                team_bet_rejections.append(rejection_entry)
                rank_all_bets._team_bet_rejections.append(rejection_entry)
            elif bet_type == 'player_prop':
                # Fix #3: Log excluded player props explicitly
                player_name = rejected_c_tier_bet.get('player', 'Unknown')
                stat = rejected_c_tier_bet.get('stat', 'points')
                line = rejected_c_tier_bet.get('line', 0)
                best_bet = c_tier_bets[0]
                best_player = best_bet.get('player', 'Unknown')
                best_stat = best_bet.get('stat', 'points')
                logger.debug(f"  Excluded: {player_name} - {stat.title()} OVER {line} (C-tier limit)")
        
        if len(c_tier_bets) > 1:
            print(f"  [INFO] Limited to 1 C-tier bet (best of {len(c_tier_bets)} candidates)")
            # Fix #3: Show which bets were excluded
            excluded_names = []
            for excluded in remaining_c_tier[:3]:  # Show first 3
                bet_type = excluded.get('type', 'unknown')
                if bet_type == 'player_prop':
                    excluded_names.append(f"{excluded.get('player', 'Unknown')} {excluded.get('stat', 'points').title()}")
                else:
                    excluded_names.append(f"{excluded.get('market', 'Unknown')}")
            if excluded_names:
                print(f"    Excluded: {', '.join(excluded_names)}" + (f" (+{len(remaining_c_tier)-3} more)" if len(remaining_c_tier) > 3 else ""))
    
    # Mark tier assignments with market-specific thresholds
    for bet in high_confidence_bets:
        market_type = bet.get('market_type', 'team_sides')
        effective_conf = bet.get('effective_confidence', bet.get('confidence', 0))
        thresholds = get_tier_thresholds(market_type)
        
        # Initial tier assignment
        if effective_conf >= thresholds["A"]:
            initial_tier = 'A'
        elif effective_conf >= thresholds["B"]:
            initial_tier = 'B'
        elif effective_conf >= thresholds["C"]:
            initial_tier = 'C'
        else:
            initial_tier = 'WATCHLIST'  # Below C-tier threshold
        
        # CORRELATION AWARENESS: De-tier correlated bets instead of blocking
        if bet.get('correlated_with'):
            # Downgrade tier by one level (A→B, B→C, C→WATCHLIST)
            tier_map = {'A': 'B', 'B': 'C', 'C': 'WATCHLIST', 'WATCHLIST': 'WATCHLIST'}
            initial_tier = tier_map.get(initial_tier, initial_tier)
            bet['tier_downgrade_reason'] = 'correlation'
        
        bet['tier'] = initial_tier
        
        # Fix #2: Apply sample-size-based stake caps for C-tier bets
        if bet['tier'] == 'C':
            sample_size = bet.get('sample_size', 0)
            bet_type = bet.get('type', '')
            
            # Default stake cap for C-tier (sample >= 10)
            stake_cap_pct = 0.12  # 12%
            
            # Reduce stake cap for small samples (<10 games)
            if sample_size < 10 and bet_type == 'player_prop':
                stat_type = bet.get('stat_type', '')
                if stat_type == 'rebounds':
                    stake_cap_pct = 0.08  # 8% for rebounds (most volatile)
                elif stat_type in ['points', 'assists']:
                    stake_cap_pct = 0.09  # 9% for usage-sensitive props
                else:
                    stake_cap_pct = 0.10  # 10% for other stats
            
            bet['stake_cap_pct'] = stake_cap_pct
        
        # EXPLANATION CONSISTENCY CHECK: Downgrade tier if rationale contradicts data
        from scrapers.consistency_validator import apply_consistency_check
        bet = apply_consistency_check(bet)
        
        # Validate tier assignment with market type
        bet_eval = BetEvaluation.from_bet_dict(bet)
        if bet_eval:
            try:
                # Fix #1: Pass promoted_from for promoted bets (bypasses Tier A validation with lower floor)
                promoted_from = bet.get('promoted_from')
                if promoted_from:
                    setattr(bet_eval, 'promoted_from', promoted_from)
                validate_bet(bet_eval, strict=False, market_type=market_type)  # Log warnings, don't fail
            except ValueError as e:
                logger.debug(f"[VALIDATION] Tier validation warning for {bet.get('tier', 'unknown')} bet: {e}")

    # CORRELATION AWARENESS: Keep all bets but track correlation warnings
    # (Correlation already handled by de-tiering above)
    filtered_bets = []
    correlation_warnings = []

    if high_confidence_bets:
        for bet in high_confidence_bets:
            if not bet or not isinstance(bet, dict):
                continue
            
            # Include all bets (de-tiering handles correlation risk)
            filtered_bets.append(bet)
                
            # Track correlation warnings for display
            if bet.get('correlated_with'):
                bet_type = bet.get('type', 'unknown')
                if bet_type == 'player_prop':
                    bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
                else:
                    bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', '')}"
                correlation_warnings.append({
                    'desc': bet_desc,
                    'correlated_with': bet.get('correlated_with', []),
                    'reason': bet.get('correlation_reason', 'Correlated bets'),
                    'tier': bet.get('tier', 'Unknown')
                })

    # Show filtering summary with tier breakdown
    a_tier_count = sum(1 for b in filtered_bets if b.get('tier') == 'A')
    b_tier_count = sum(1 for b in filtered_bets if b.get('tier') == 'B')
    c_tier_count = sum(1 for b in filtered_bets if b.get('tier') == 'C')
    
    logger.info(f"Tier evaluation: {len(filtered_bets)} passed (A: {a_tier_count}, B: {b_tier_count})")
    
    # Show market-specific C-tier thresholds
    prop_c_threshold = MARKET_TIER_THRESHOLDS["player_prop"]["C"]
    sides_c_threshold = MARKET_TIER_THRESHOLDS["team_sides"]["C"]
    totals_c_threshold = MARKET_TIER_THRESHOLDS["totals"]["C"]
    
    if c_tier_count > 0:
        # Fix #2: Show variable stake caps (8-12% depending on sample size)
        c_tier_bet_caps = [b.get('stake_cap_pct', 0.12) for b in filtered_bets if b.get('tier') == 'C']
        if c_tier_bet_caps:
            unique_caps = sorted(set(c_tier_bet_caps))
            if len(unique_caps) == 1:
                cap_display = f"stake capped at {int(unique_caps[0]*100)}%"
            else:
                cap_display = f"stake capped at {', '.join([f'{int(c*100)}%' for c in unique_caps])}"
        else:
            cap_display = "stake capped at 12%"
        print(f"    - C-Tier (Player Props >= {prop_c_threshold}, Sides >= {sides_c_threshold}, Totals >= {totals_c_threshold}, max 1): {c_tier_count} bet ({cap_display})")
    elif len(c_tier_bets) > 0:
        print(f"    - C-Tier candidates: {len(c_tier_bets)}, C-Tier allowed: 0 (already have A/B-tier bets or max 1 limit)")
    elif len(c_tier_bets) == 0 and len(ev_filtered_bets) > 0:
        # Check if there were any bets in the C-Tier range that failed (market-specific)
        c_tier_candidates = []
        for b in ev_filtered_bets:
            market_type = get_market_type(b)
            thresholds = get_tier_thresholds(market_type)
            effective_conf = calculate_effective_confidence(b)
            if B_TIER_CONFIDENCE > effective_conf >= thresholds["C"]:
                c_tier_candidates.append(b)
        if c_tier_candidates:
            print(f"    - C-Tier candidates: {len(c_tier_candidates)}, C-Tier allowed: 0 (effective confidence below market-specific threshold after penalties)")
    
    if len(all_bets) > 0 and len(filtered_bets) == 0:
        # No bets passed - show detailed breakdown
        print(f"\n  [WARNING] All {len(all_bets)} bets were filtered out. Breakdown:")
        
        # Check each filter stage
        ev_passed = len(ev_filtered_bets)
        conf_passed = len(high_confidence_bets)
        
        print(f"    - EV/Probability filter: {ev_passed}/{len(all_bets)} passed")
        print(f"    - Confidence Tier Evaluation (Market-Specific):")
        print(f"        A-Tier (>= {A_TIER_CONFIDENCE}): {len(a_tier_bets)}")
        print(f"        B-Tier (>= {B_TIER_CONFIDENCE}): {len(b_tier_bets)}")
        print(f"        C-Tier (Props >= {prop_c_threshold}, Sides >= {sides_c_threshold}, Totals >= {totals_c_threshold}, max 1): {len(c_tier_bets)}")
        print(f"    - Correlation/Game limit: {len(filtered_bets)}/{conf_passed} passed")
        
        # Show top bets that almost made it
        if ev_filtered_bets:
            print(f"\n  Top bets that failed confidence tier thresholds:")
            # Filter to bets that didn't make it into high_confidence_bets
            failed_bets = [b for b in ev_filtered_bets if b not in high_confidence_bets]
            for bet in sorted(failed_bets, key=lambda x: x.get('effective_confidence', x.get('confidence', 0)), reverse=True)[:5]:
                bet_type = bet.get('type', 'unknown')
                if bet_type == 'player_prop':
                    bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
                else:
                    bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', '')}"
                prob = bet.get('final_prob', bet.get('historical_probability', 0))
                edge = bet.get('edge', 0)
                raw_conf = float(bet.get('confidence', 0))
                effective_conf = bet.get('effective_confidence', raw_conf)
                market_type = bet.get('market_type', 'team_sides')
                thresholds = get_tier_thresholds(market_type)
                c_threshold = thresholds["C"]
                # Check if it's a watchlist near-miss (use effective confidence)
                note = ""
                if (c_threshold - 3.0) <= effective_conf < c_threshold and prob >= 0.55 and edge >= 4.0:
                    note = f" (C-Tier near-miss, effective conf {effective_conf:.1f} below {c_threshold} threshold for {market_type}, see WATCHLIST)"
                elif (c_threshold - 3.0) <= effective_conf < 50.0 and prob >= 0.55 and edge >= 4.0:
                    note = " (see WATCHLIST)"
                # Show both raw and effective confidence
                print(f"    - {bet_desc}: Raw Conf {raw_conf:.0f} (Effective: {effective_conf:.1f}, need >= {c_threshold} for C-Tier {market_type}){note}, Prob {prob:.1%}, Edge {edge:+.1f}%")

    if len(filtered_bets) < len(ev_filtered_bets) and len(filtered_bets) > 0:
        total_available = len(ev_filtered_bets)
        print(f"  {len(filtered_bets)}/{total_available} bets passed all criteria")

        # Show bets that passed EV but failed confidence tiers
        if total_available > len(filtered_bets):
            # Market-specific low confidence filtering
            # Ensure effective_confidence is calculated for all bets first
            # get_market_type is imported at the function level (line 2120)
            from scrapers.bet_validation import get_market_type, calculate_effective_confidence
            for bet in ev_filtered_bets:
                if 'effective_confidence' not in bet:
                    bet['effective_confidence'] = calculate_effective_confidence(bet)
                    bet['market_type'] = get_market_type(bet)
            
            low_confidence = []
            for bet in ev_filtered_bets:
                market_type = bet.get('market_type', 'team_sides')
                thresholds = get_tier_thresholds(market_type)
                effective_conf = bet.get('effective_confidence', calculate_effective_confidence(bet))
                if effective_conf < thresholds["C"]:
                    low_confidence.append(bet)
                    # Track team bet rejections from tier filtering
                    if bet.get('type') == 'team_bet':
                        team_bet_rejections.append({
                            'bet': bet,
                            'reason': f'Confidence below C-tier threshold ({effective_conf:.1f} < {thresholds["C"]} for {market_type})',
                            'market': bet.get('market', 'Unknown'),
                            'result': bet.get('result', ''),
                            'confidence': effective_conf,
                            'edge': bet.get('edge', 0),
                            'probability': bet.get('final_prob', bet.get('historical_probability', 0))
                        })
            if low_confidence:
                print(f"  {len(low_confidence)} bets filtered by confidence tier (below market-specific C-tier threshold):")
                for bet in sorted(low_confidence, key=lambda x: x.get('confidence', 0), reverse=True)[:5]:
                    bet_type = bet.get('type', 'unknown')
                    if bet_type == 'player_prop':
                        bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
                    else:
                        bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', '')}"
                    print(f"    - {bet_desc}: Conf {bet.get('confidence', 0):.0f}, EV {bet.get('edge', 0):.1f}%")
        
        # Show correlation warnings (bets that were de-tiered)
        if correlation_warnings:
            print(f"\n  [CORRELATION] {len(correlation_warnings)} bet(s) de-tiered due to correlation:")
            for warning in correlation_warnings[:5]:
                correlated_list = ', '.join(warning['correlated_with'][:3])  # Show first 3
                if len(warning['correlated_with']) > 3:
                    correlated_list += f" (+{len(warning['correlated_with']) - 3} more)"
                print(f"    - {warning['desc']} (Tier: {warning['tier']}): {warning['reason']}")
                print(f"      Correlated with: {correlated_list}")
    
    # VALIDATION: Final health snapshot before returning
    if filtered_bets:
        final_health = health_snapshot_from_dicts(filtered_bets)
        if final_health.get('validation_failures', 0) > 0 or final_health.get('ev_inconsistencies', 0) > 0:
            logger.warning(f"[VALIDATION] Final bet list has {final_health.get('validation_failures', 0)} validation failures, "
                          f"{final_health.get('ev_inconsistencies', 0)} EV inconsistencies")
        elif final_health.get('count', 0) > 0:
            logger.debug(f"[VALIDATION] Final bet list: {final_health['valid_count']}/{final_health['count']} valid, "
                        f"mean EV: {final_health.get('mean_ev', 'N/A')}, mean conf: {final_health.get('mean_confidence', 'N/A')}")
    
    # Store team bet rejections for caller access
    if hasattr(rank_all_bets, '_team_bet_rejections'):
        rank_all_bets._team_bet_rejections.extend(team_bet_rejections)
    
    return filtered_bets


def print_unified_report(final_bets: List[Dict]):
    """
    Print comprehensive report of all value bets (team + player props).

    Shows ALL high-confidence bets that meet quality thresholds.
    """
    if not final_bets:
        print("\n" + "="*70)
        print("  NO HIGH-CONFIDENCE BETS FOUND")
        logger.debug("="*70)
        logger.warning("No bets met the minimum confidence threshold (50/100)")
        return

    logger.info(f"Found {len(final_bets)} high-confidence bets")

    team_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'team_bet')
    prop_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'player_prop')

    logger.info(f"Breakdown: {team_count} team bets, {prop_count} player props")
    # Determine actual confidence threshold used
    if final_bets:
        confidences = [bet.get('confidence', 0) for bet in final_bets if bet and isinstance(bet, dict)]
        if confidences:
            min_confidence = min(confidences)
            max_confidence = max(confidences)
            print(f"Confidence Range: {min_confidence:.0f}-{max_confidence:.0f}/100 | Max per Game: 2")
        else:
            print(f"Minimum Confidence: 50/100 | Max per Game: 2")
    else:
        print(f"Minimum Confidence: 50/100 | Max per Game: 2")
    print()

    for i, bet in enumerate(final_bets, 1):
        if not bet or not isinstance(bet, dict):
            continue
        try:
            bet_type = bet.get('type', 'UNKNOWN')
            print(f"{i}. [{bet_type.upper().replace('_', ' ')}] ", end="")

            if bet_type == 'team_bet':
                print(f"{bet.get('result', 'N/A')} - {bet.get('market', 'N/A')}")
                print(f"   {bet.get('fact', 'N/A')}")
            
                # Check if model projections are available
                has_model = bet.get('has_model_projection', False)
                analysis = bet.get('analysis', {})
                proj_details = analysis.get('projection_details')
                projected_ev = analysis.get('projected_expected_value')
                projected_prob = analysis.get('projected_prob')
                historical_prob = analysis.get('historical_probability', 0)
                
                if proj_details:
                    # Team bet with projection details - show projected_total
                    projected_total = proj_details.get('projected_total')
                    if projected_total:
                        print(f"   Projected Total: {projected_total:.1f} | Prob: {historical_prob:.1%}", end="")
                        if projected_prob is not None:
                            original_hist_prob = analysis.get('original_historical_probability', historical_prob)
                            print(f" (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                        else:
                            print()
                        # Show pace factor if available
                        pace_factor = proj_details.get('pace_factor')
                        if pace_factor and pace_factor != 1.0:
                            print(f"   Pace Factor: {pace_factor:.3f}x")
                    else:
                        # No projected_total but have other projection data
                        if projected_prob is not None:
                            original_hist_prob = analysis.get('original_historical_probability', historical_prob)
                            print(f"   Projected Prob: {projected_prob:.1%} | Final Prob: {historical_prob:.1%} (Hist: {original_hist_prob:.1%})")
                        else:
                            print(f"   Prob: {historical_prob:.1%}")
                elif projected_ev is not None:
                    # Player prop insight in team bet format
                    original_hist_prob = analysis.get('original_historical_probability', historical_prob)
                    if projected_prob is not None:
                        print(f"   Projected EV: ${projected_ev:.2f}/100 | Prob: {historical_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                    else:
                        print(f"   Projected EV: ${projected_ev:.2f}/100 | Prob: {historical_prob:.1%}")
                    
                    if proj_details:
                        proj = proj_details
                        if proj.get('minutes_projected') is not None:
                            pace_mult = proj.get('pace_multiplier', 1.0)
                            def_adj = proj.get('defense_adjustment', 1.0)
                            print(f"   Minutes: {proj['minutes_projected']:.1f} | Pace: {pace_mult:.3f}x | Defense: {def_adj:.3f}x")
                        if proj.get('role_change_detected'):
                            print(f"   WARNING: Role change detected")
                else:
                    # TREND-ONLY BET: No model projections
                    if not has_model:
                        original_conf = bet.get('original_confidence', bet.get('confidence', 0))
                        print(f"   WARNING: TREND-ONLY (No Model Projections)")
                        print(f"   Missing: Projected Total, Pace Impact, Efficiency Multipliers")
                        if original_conf != bet.get('confidence', 0):
                            print(f"   Confidence Penalty: {original_conf:.0f} -> {bet.get('confidence', 0):.0f} (-20 for trend-only)")
                
                # Print standard metrics for all team bets
                print(f"   Odds: {bet.get('odds', 0):.2f} | Confidence: {bet.get('confidence', 0):.0f}/100 | SAMPLE SIZE: {bet.get('sample_size', 0)} games")
                print(f"   EV: ${bet.get('ev_per_100', 0):+.2f}/100 | Edge: {bet.get('edge', 0):+.1f}%")
                print(f"   Game: {bet.get('game', 'Unknown')}")

            elif bet_type == 'player_prop':
                # Actual player prop
                print(f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}")
                
                # Show projection model details - only show if projection exists (no fallbacks)
                proj_details = bet.get('projection_details')
                if not proj_details:
                    # This should never happen if we're strict, but log it if it does
                    logger.error(f"  WARNING: Player prop {bet.get('player')} missing projection_details - this should not happen!")
                    continue
                
                proj = proj_details
                # Get projected stat value (e.g., 26.5 points) not EV
                projected_stat = proj.get('projected_value') or proj.get('projected_points') or proj.get('projected_total') or 0
                projected_ev = bet.get('expected_value') or bet.get('projected_expected_value', 0)
                projected_prob = bet.get('projected_prob', 0)
                final_prob = bet.get('final_prob', bet.get('historical_probability', 0))
                original_hist_prob = bet.get('historical_prob', bet.get('original_historical_probability', final_prob))
                
                # P1: Show projection source in final display
                projection_source = bet.get('projection_source', 'unknown')
                source_display = {
                    'model': 'Model',
                    'blended': 'Blended (Model+Market)',
                    'fallback': 'Fallback (Historical)',
                    'insight-derived': 'Insight-Derived'
                }.get(projection_source, projection_source.title())
                
                # Show projected stat value (e.g., "26.5 points") not EV
                if projected_stat > 0:
                    print(f"   Projected: {projected_stat:.1f} | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%}) | Source: {source_display}")
                else:
                    print(f"   Projected EV: ${projected_ev:.2f}/100 | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%}) | Source: {source_display}")
                
                if proj.get('minutes_projected') is not None:
                    pace_mult = proj.get('pace_multiplier', 1.0)
                    def_adj = proj.get('defense_adjustment', 1.0)
                    print(f"   Minutes: {proj['minutes_projected']:.1f} | Pace: {pace_mult:.3f}x | Defense: {def_adj:.3f}x")
                
                if proj.get('role_change_detected'):
                    print(f"   WARNING: Role change detected")
                
                # Always print odds, EV, edge, and sample size (CRITICAL METRICS)
                odds = bet.get('odds', 0)
                confidence = bet.get('confidence', 0)
                ev_per_100 = bet.get('ev_per_100', 0)
                edge = bet.get('edge', 0)
                sample = bet.get('sample_size', 0)

                print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100 | SAMPLE SIZE: {sample} games")
                print(f"   EV: ${ev_per_100:+.2f}/100 | Edge: {edge:+.1f}%")
                print(f"   Game: {bet.get('game', 'Unknown')}")

            print()
        except Exception as e:
            logger.warning(f"  Error displaying bet {i}: {e}")
            continue

    logger.debug("="*70)


def save_results(final_bets: List[Dict], games_data: List[Dict]):
    """
    Save analysis results to JSON file.
    """
    output_dir = Path(__file__).parent.parent / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = output_dir / f"unified_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Prepare data for JSON serialization
    results = {
        'analysis_date': datetime.now().isoformat(),
        'games_analyzed': len(games_data),
        'total_bets': len(final_bets),
        'team_bets': sum(1 for b in final_bets if b['type'] == 'team_bet'),
        'player_props': sum(1 for b in final_bets if b['type'] == 'player_prop'),
        'bets': final_bets,
        'games': [
            {
                'away_team': g.get('game_info', {}).get('away_team', 'Unknown'),
                'home_team': g.get('game_info', {}).get('home_team', 'Unknown'),
                'total_markets': len(g.get('team_markets', []) or []),
                'total_insights': len(g.get('team_insights', []) or []),
                'total_props': len(g.get('player_props', []) or [])
            }
            for g in games_data if g
        ]
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\nResults saved to: {filename}")


def main():
    """
    Main pipeline execution.
    """
    try:
        print("\n" + "="*70)
        print("  UNIFIED ANALYSIS PIPELINE")
        print("  QUALITY OVER QUANTITY - ALL High-Confidence Bets")
        logger.debug("="*70)
        print("\nPipeline Flow:")
        print("  1. [SPORTSBET SCRAPER] Scrapes games, markets, insights, and player props")
        print("  2. [DATA SOURCES] Player data priority: StatsMuse (0.85 conf) → DataballR (0.90 conf) → Inference (0.60 conf)")
        print("  3. [INSIGHT ANALYZER] Analyzes team bets using Context-Aware Value Engine with decay penalties")
        print("  4. [MODEL PROJECTIONS] Calculates player prop projections with role modifiers, PVI, and matchup adjustments")
        print("  5. [FILTER & DISPLAY] Market-specific tiers, correlation de-tiering, consistency validation, CLV tracking")
        print()
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        traceback.print_exc()
        return

    # Get number of games
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'all':
            max_games = 999  # Will be limited by actual games available
        else:
            try:
                max_games = int(arg)
            except ValueError:
                print("Invalid argument. Usage: python unified_analysis_pipeline.py [num_games|all]")
                max_games = 999
    else:
        print("Recommended: Analyze ALL games to find the best 4-6 high-confidence bets")
        choice = input("How many games to analyze? (Enter 'all' or a number, default: all): ").strip().lower()
        if choice == '' or choice == 'all':
            max_games = 999  # Analyze all available games
        elif choice == '0':
            max_games = 3
        else:
            try:
                max_games = int(choice)
            except ValueError:
                print("Invalid input, analyzing all available games")
                max_games = 999

    if max_games >= 999:
        logger.info("Analyzing ALL available games to find high-confidence bets...")
    else:
        logger.info(f"Starting analysis of {max_games} game(s)...")

    # Step 1: Scrape Sportsbet data
    logger.info("Step 1: Scraping games, markets, insights, and player props")

    try:
        games_data = scrape_games(max_games, headless=True)
    except Exception as e:
        logger.error(f"Failed to scrape games: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return

    if not games_data:
        logger.error("No games data retrieved. Exiting.")
        return

    logger.info(f"Successfully scraped {len(games_data)} game(s)")
    
    # Generate post-scraping health snapshot (if bets exist)
    if 'all_bets' in locals() and all_bets:
        post_health = health_snapshot_from_dicts(all_bets)
        if post_health.get('validation_failures', 0) > 0:
            logger.debug(f"Validation: {post_health['valid_count']}/{post_health['count']} valid bets, "
                       f"{post_health.get('ev_inconsistencies', 0)} EV inconsistencies")

    # Step 2: Analyze each game (DataballR -> Insights -> Model)
    logger.info("Step 2: Analyzing bets (DataballR -> Insights -> Model)")

    all_team_bets = []
    all_player_props = []
    all_missing_players = set()  # Track all missing players across games
    headless = True  # Run browser in headless mode

    for i, game_data in enumerate(games_data, 1):
        try:
            game_info = game_data.get('game_info', {}) or {}
            away_team = game_info.get('away_team', 'Unknown')
            home_team = game_info.get('home_team', 'Unknown')
            game_name = f"{away_team} @ {home_team}"
            print(f"\n[{i}/{len(games_data)}] {game_name}")

            # Analyze team bets (returns both team bets AND player props from insights)
            print(f"  Analyzing team insights...")
            try:
                team_bets_result = analyze_team_bets(game_data, headless=headless)
                # Separate team bets from player props in the result for tracking
                team_bets_only = [b for b in team_bets_result if b.get('_bet_type') != 'player_prop']
                player_props_from_insights_count = len([b for b in team_bets_result if b.get('_bet_type') == 'player_prop'])
                print(f"  Team bets: {len(team_bets_only)} value bets found")
                # Keep all bets together (they'll be separated later in rank_all_bets)
                all_team_bets.extend(team_bets_result)
            except Exception as e:
                logger.error(f"  Error analyzing team bets: {e}")
                import traceback
                logger.debug(traceback.format_exc())

            # Analyze player props
            print(f"  Analyzing player props...")
            try:
                player_props_list = game_data.get('player_props', []) or []
                market_players = game_data.get('market_players', []) or []
                all_markets = game_data.get('team_markets', []) or []
                
                # Count player props from insights (they're extracted from insights, not markets)
                # Check both match_insights and team_insights (different data structures)
                match_insights = game_data.get('match_insights', []) or []
                team_insights_raw = game_data.get('team_insights', []) or []
                all_insights_to_check = match_insights + team_insights_raw
                
                player_prop_insights_count = 0
                player_prop_stats_count = {
                    'points': 0,
                    'assists': 0,
                    'rebounds': 0
                }
                for insight in all_insights_to_check:
                    try:
                        # Handle both dict and object formats using helper
                        insight_dict = {
                            'fact': _safe_insight_get(insight, 'fact', ''),
                            'market': _safe_insight_get(insight, 'market', ''),
                            'result': _safe_insight_get(insight, 'result', '')
                        }
                        if _is_player_prop_insight(insight_dict):
                            player_prop_insights_count += 1
                            # Count by stat type
                            prop_info = _extract_prop_info_from_insight(insight_dict)
                            if prop_info:
                                stat_type = prop_info.get('stat', 'points')
                                if stat_type == 'points':
                                    player_prop_stats_count['points'] += 1
                                elif stat_type == 'assists':
                                    player_prop_stats_count['assists'] += 1
                                elif stat_type == 'rebounds':
                                    player_prop_stats_count['rebounds'] += 1
                    except Exception as e:
                        continue  # Skip invalid insights
                
                # Market breakdown logging
                if all_markets:
                    market_counts = {
                        'sides': 0,
                        'totals': 0,
                        'player_points': 0,
                        'player_assists': 0,
                        'player_rebounds': 0,
                        'other': 0
                    }
                    
                    for market in all_markets:
                        # Handle both dict and dataclass objects
                        if isinstance(market, dict):
                            market_category = str(market.get('market_category', market.get('market_type', 'unknown'))).lower()
                            market_text = str(market.get('selection_text', '')).lower()
                        else:
                            market_category = str(getattr(market, 'market_category', getattr(market, 'market_type', 'unknown'))).lower()
                            market_text = str(getattr(market, 'selection_text', '')).lower()
                        
                        # Count market types by category first, then by text if needed
                        if market_category == 'prop' or 'player' in market_category or 'prop' in market_category:
                            # Player prop - check text for specific stat
                            if 'assist' in market_text:
                                market_counts['player_assists'] += 1
                            elif 'rebound' in market_text:
                                market_counts['player_rebounds'] += 1
                            elif 'points' in market_text:
                                market_counts['player_points'] += 1
                            else:
                                market_counts['other'] += 1  # Unknown prop type
                        elif market_category == 'total' or 'over' in market_category or 'under' in market_category:
                            market_counts['totals'] += 1
                        elif market_category in ['moneyline', 'match']:
                            market_counts['sides'] += 1
                        elif market_category == 'handicap' or 'spread' in market_category:
                            market_counts['sides'] += 1
                        elif 'points' in market_text and ('player' in market_text or 'player' in market_category):
                            # Fallback: check text for player props
                            if 'assist' in market_text:
                                market_counts['player_assists'] += 1
                            elif 'rebound' in market_text:
                                market_counts['player_rebounds'] += 1
                            else:
                                market_counts['player_points'] += 1
                        else:
                            market_counts['other'] += 1
                    
                    # Print market breakdown
                    breakdown_parts = []
                    if market_counts['sides'] > 0:
                        breakdown_parts.append(f"Sides: {market_counts['sides']}")
                    if market_counts['totals'] > 0:
                        breakdown_parts.append(f"Totals: {market_counts['totals']}")
                    if market_counts['player_points'] > 0:
                        breakdown_parts.append(f"Player Points: {market_counts['player_points']}")
                    if market_counts['player_assists'] > 0:
                        breakdown_parts.append(f"Player Assists: {market_counts['player_assists']}")
                    if market_counts['player_rebounds'] > 0:
                        breakdown_parts.append(f"Player Rebounds: {market_counts['player_rebounds']}")
                    if market_counts['other'] > 0:
                        breakdown_parts.append(f"Other: {market_counts['other']}")
                    
                    if breakdown_parts:
                        print(f"  Markets found: {', '.join(breakdown_parts)}")
                
                # Add player props from insights to breakdown
                if player_prop_insights_count > 0:
                    insight_prop_parts = []
                    if player_prop_stats_count['points'] > 0:
                        insight_prop_parts.append(f"Player Points (insights): {player_prop_stats_count['points']}")
                    if player_prop_stats_count['assists'] > 0:
                        insight_prop_parts.append(f"Player Assists (insights): {player_prop_stats_count['assists']}")
                    if player_prop_stats_count['rebounds'] > 0:
                        insight_prop_parts.append(f"Player Rebounds (insights): {player_prop_stats_count['rebounds']}")
                    if insight_prop_parts:
                        print(f"  Player props from insights: {', '.join(insight_prop_parts)}")
                
                # Show player props count (from both markets and insights)
                total_player_props = len(player_props_list) + player_prop_insights_count
                if total_player_props > 0:
                    prop_source_parts = []
                    if len(player_props_list) > 0:
                        prop_source_parts.append(f"{len(player_props_list)} from markets")
                    if player_prop_insights_count > 0:
                        prop_source_parts.append(f"{player_prop_insights_count} from insights")
                    print(f"  Found {total_player_props} total player prop(s) ({', '.join(prop_source_parts)})")
                    if market_players:
                        print(f"  Players in markets: {', '.join(market_players[:5])}" + ("..." if len(market_players) > 5 else ""))
                else:
                    # Debug: Check why no player props were extracted
                    prop_markets = [m for m in all_markets if 'player' in str(getattr(m, 'market_category', '')).lower() or any(stat in str(getattr(m, 'selection_text', '')).lower() for stat in ['points', 'rebounds', 'assists'])]
                    if prop_markets:
                        print(f"  WARNING: {len(prop_markets)} potential player prop markets found in markets but not extracted (check extraction logic)")
                        logger.debug(f"  Sample market texts: {[getattr(m, 'selection_text', '')[:50] for m in prop_markets[:3]]}")
                    else:
                        print(f"  WARNING: No player prop markets matched supported schemas (total markets: {len(all_markets)}, insights: {len(all_insights_to_check)})")
                
                player_props, missing_players = analyze_player_props(game_data, headless=headless)
                
                # P1: Extract projection source counts for accurate logging
                source_counts = {'model': 0, 'blended': 0, 'fallback': 0, 'insight-derived': 0}
                if player_props:
                    source_counts = player_props[0].get('_projection_source_counts', source_counts)
                    # Remove temporary field
                    if '_projection_source_counts' in player_props[0]:
                        del player_props[0]['_projection_source_counts']
                
                # Count sources from all bets (including insight-derived from analyze_player_prop_insights)
                total_all_sources = sum(source_counts.values())
                if total_all_sources == 0:
                    # Fallback: count from projection_source field in bets
                    for prop in player_props:
                        source = prop.get('projection_source', 'unknown')
                        if source in source_counts:
                            source_counts[source] += 1
                
                # P1: Update logging to show accurate counts
                model_count = source_counts.get('model', 0)
                blended_count = source_counts.get('blended', 0)
                fallback_count = source_counts.get('fallback', 0)
                insight_count = source_counts.get('insight-derived', 0)
                
                # Fix #2: Count player props from all sources (analyze_player_props + insights)
                total_player_props_from_markets = len(player_props)
                # Use player_prop_insights_count (already calculated above from insights)
                total_player_props_from_insights = player_prop_insights_count  # Count of insights that are player props
                total_all_player_props = total_player_props_from_markets + total_player_props_from_insights
                
                if total_all_player_props > 0:
                    parts = []
                    if model_count > 0:
                        parts.append(f"{model_count} model")
                    if blended_count > 0:
                        parts.append(f"{blended_count} blended")
                    if fallback_count > 0:
                        parts.append(f"{fallback_count} fallback")
                    if insight_count > 0 or total_player_props_from_insights > 0:
                        insight_total = insight_count + total_player_props_from_insights
                        if insight_total > 0:
                            parts.append(f"{insight_total} insight-derived")
                    
                    if parts:
                        print(f"  Player props: {total_all_player_props} predictions found ({', '.join(parts)})")
                    else:
                        print(f"  Player props: {total_all_player_props} predictions found")
                else:
                    print(f"  Player props: 0 predictions found")
                
                if missing_players:
                    print(f"  WARNING: {len(missing_players)} players missing from cache")
                
                all_player_props.extend(player_props)
                all_missing_players.update(missing_players)
            except Exception as e:
                logger.error(f"  Error analyzing player props: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            logger.error(f"  Error processing game {i}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            continue

    # Step 3: Filter and rank bets
    print("\n" + "-"*70)
    print("STEP 3: [DISPLAY] Filtering and ranking (Quality over Quantity)")
    print("-"*70)
    print("\nFilter Criteria:")
    print("  * EV Thresholds: Props >= +3%, Sides/Totals >= +2%")
    print("  * Confidence Tiers (Market-Specific):")
    print("    - Player Props: A >= 65, B >= 50, C >= 35")
    print("    - Team Sides: A >= 65, B >= 50, C >= 40")
    print("    - Totals: A >= 65, B >= 50, C >= 45")
    print("  * Soft Floor: Market weights applied (Player Props: 0.92x, Totals: 1.05x)")
    print("  * Correlation: De-tier correlated bets (A→B, B→C, C→WATCHLIST) instead of blocking")
    print("  * Consistency: Downgrade tier if rationale contradicts data")
    print("  * Watchlist: Near-miss bets (Conf 35-49, Prob >= 55%, Edge >= +4%) logged for review")

    try:
        final_bets = rank_all_bets(all_team_bets, all_player_props)

        # P4: Apply B-tier promotion if no A-tier bets exist
        a_tier_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('tier') == 'A')
        if a_tier_count == 0:
            final_bets = promote_best_b_tier(final_bets, min_confidence=48, min_probability=0.55, min_edge=4.0)
        
        # Log team bet rejections summary if available
        if hasattr(rank_all_bets, '_team_bet_rejections') and rank_all_bets._team_bet_rejections:
            total_team_bets_found = len(all_team_bets)
            final_team_bets = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'team_bet')
            rejections = rank_all_bets._team_bet_rejections
            
            reason_summary = {}
            for r in rejections:
                reason = r['reason']
                reason_summary[reason] = reason_summary.get(reason, 0) + 1
            
            logger.info(f"Team bets summary: {final_team_bets} selected from {total_team_bets_found} found")
    except Exception as e:
        logger.error(f"Error ranking bets: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        final_bets = []

    if final_bets:
        try:
            print(f"\n[OK] Top {len(final_bets)} high-confidence bets selected")
            team_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'team_bet')
            prop_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'player_prop')
            print(f"  Team bets: {team_count}")
            print(f"  Player props: {prop_count}")
            confidences = [b.get('confidence', 0) for b in final_bets if b and isinstance(b, dict)]
            if confidences:
                print(f"  Minimum confidence: {min(confidences):.0f}/100")
        except Exception as e:
            logger.error(f"Error printing bet summary: {e}")
        
        # Show how many have model projections
        try:
            with_model = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('has_model_projection', False))
            trend_only = len(final_bets) - with_model
            if trend_only > 0:
                print(f"  WARNING: {trend_only} trend-only bets (missing model projections)")
        except Exception as e:
            logger.error(f"Error calculating model projection stats: {e}")
    else:
        print("\n[INFO] No bets met the quality thresholds")
        print("  Possible reasons:")
        print("  - All bets below minimum EV (Props < 3%, Sides < 2%)")
        print("  - All bets below required confidence tiers")
        print("  - Insufficient data quality")

    # Step 4: Display results using new BettingRecommendation display system
    try:
        if final_bets:
            # VALIDATION: Validate all bets before display (strict=False to filter invalid ones)
            # Fix promotion validation: preserve promoted_from for validation
            from scrapers.bet_validation import validate_bet_list, BetEvaluation
            for bet in final_bets:
                if bet.get('promoted_from') and bet.get('tier') == 'A':
                    # Ensure promoted_from is preserved for validation
                    pass  # Already in dict, will be handled by validate_bet_dict
            
            validated_final_bets = validate_bet_list(final_bets, strict=False)
            
            if len(validated_final_bets) < len(final_bets):
                logger.warning(f"[VALIDATION] Filtered {len(final_bets) - len(validated_final_bets)} invalid bet(s) before display")
                final_bets = validated_final_bets
            
            # CLV TRACKING: Record bets at creation time
            try:
                from scrapers.clv_tracker import get_clv_tracker
                from config.settings import Config
                
                if Config.ENABLE_CLV_TRACKING:
                    clv_tracker = get_clv_tracker()
                    for bet in final_bets:
                        try:
                            bet_id = clv_tracker.record_bet(
                                bet=bet,
                                opening_line=bet.get('line') or bet.get('market_line'),
                                opening_odds=bet.get('odds')
                            )
                            # Store bet_id for later updates
                            bet['bet_id'] = bet_id
                        except Exception as e:
                            logger.debug(f"[CLV] Failed to record bet: {e}")
            except Exception as e:
                logger.debug(f"[CLV] CLV tracking not available: {e}")
            
            # Convert dictionaries to BettingRecommendation objects
            recommendations = []
            for bet in final_bets:
                if not bet or not isinstance(bet, dict):
                    continue
                
                # Try to get game info from the bet or use default
                game_info = bet.get('game_info')
                if not game_info:
                    # Try to extract from game string
                    game_str = bet.get('game', '')
                    if game_str and ' @ ' in game_str:
                        parts = game_str.split(' @ ')
                        if len(parts) == 2:
                            game_info = {
                                'away_team': parts[0].strip(),
                                'home_team': parts[1].strip(),
                                'match_time': bet.get('match_time', 'TBD')
                            }
                
                rec = convert_dict_to_recommendation(bet, game_info)
                if rec:
                    recommendations.append(rec)
            
            # Display using new system (use print for compatibility with unified pipeline)
            if recommendations:
                display_recommendations(recommendations, max_display=len(recommendations), use_print=True)
            else:
                print("\n[INFO] No valid recommendations to display")
        else:
            print("\n[INFO] No bets to display")
    except Exception as e:
        logger.error(f"Error printing report: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] Failed to display results: {e}")
        print("Attempting to show basic bet list...")
        try:
            for i, bet in enumerate(final_bets, 1):
                if bet and isinstance(bet, dict):
                    bet_type = bet.get('type', 'UNKNOWN')
                    if bet_type == 'player_prop':
                        print(f"{i}. {bet.get('player', 'Unknown')} - {bet.get('stat', 'points')} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}")
                    else:
                        print(f"{i}. {bet.get('market', 'Unknown')} - {bet.get('result', 'N/A')}")
        except:
            pass

    # Step 5: Save results
    try:
        save_results(final_bets, games_data)
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        import traceback
        logger.debug(traceback.format_exc())

    logger.info("Analysis complete")
    
    # Show missing players summary if any
    if all_missing_players:
        print("\n" + "="*70)
        print("  WARNING: MISSING PLAYER DATA - ACTION REQUIRED")
        logger.debug("="*70)
        print(f"\n{len(all_missing_players)} player(s) need to be added to cache:")
        print()
        
        sorted_missing = sorted(all_missing_players)
        for player in sorted_missing:
            print(f"  * {player}")
        
        # Auto-create PLAYERS_TO_ADD.txt file
        try:
            missing_file = Path(__file__).parent.parent / "PLAYERS_TO_ADD.txt"
            with open(missing_file, 'w', encoding='utf-8') as f:
                for player in sorted_missing:
                    f.write(f"{player}\n")
            print()
            print(f"[OK] Saved to: {missing_file}")
        except Exception as e:
            logger.error(f"Could not create PLAYERS_TO_ADD.txt: {e}")
        
        logger.info("To fix: Run build_databallr_player_cache.py to add missing players")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        # Log to file AND display
        error_log = Path(__file__).parent.parent / "error_log.txt"
        try:
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"ERROR at {datetime.now()}\n")
                f.write(f"{str(e)}\n\n")
                f.write(traceback.format_exc())
        except:
            pass  # If logging fails, still show error
        
        logger.error(f"Script failed: {e}")
        traceback.print_exc()
        print(f"\nError also saved to: {error_log}")
        print("\nPress Enter to close...")
        try:
            input()
        except:
            pass  # If input fails, just continue
