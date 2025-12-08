"""
Unified Analysis Pipeline
=========================
Combines team bet analysis (Option 1) and player prop predictions (Option 6)
into a single unified pipeline. NO NBA API - uses only Sportsbet + databallr + NBA.com lineups.

QUALITY OVER QUANTITY:
- Analyzes ALL available games by default
- Filters to only 70+ confidence bets
- Returns top 5 high-confidence bets
- Max 2 bets per game (correlation control)

Data Flow:
1. Scrape ALL Sportsbet games (team markets, insights, player props)
2. Analyze team bets using Context-Aware Value Engine
3. Analyze player props using databallr player stats
4. Filter to 70+ confidence, rank by confidence score
5. Return top 5 bets across all games

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

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("unified_pipeline")

# Imports for Sportsbet scraping
from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
from scrapers.insights_to_value_analysis import analyze_all_insights

# Use robust DataballR scraper (with fallback to original for compatibility)
try:
    from scrapers.databallr_robust.integration import get_player_game_log
    DATABALLR_ROBUST_AVAILABLE = True
    logger.info("[PIPELINE] Using robust DataballR scraper with retry logic and schema mapping")
except ImportError as e:
    from scrapers.databallr_scraper import get_player_game_log
    DATABALLR_ROBUST_AVAILABLE = False
    logger.warning(f"[PIPELINE] Robust DataballR scraper not available ({e}), using original scraper")

from scrapers.player_projection_model import PlayerProjectionModel

# Initialize NBA player cache
try:
    from scrapers.nba_player_cache import initialize_cache
    initialize_cache()
except ImportError:
    pass  # Cache optional


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
    logger.info("Scraping NBA games from Sportsbet...")
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
    logger.info(f"Found {len(games)} games on Sportsbet, analyzing {actual_max}")

    results = []
    for i, game in enumerate(games[:actual_max], 1):
        logger.info(f"[{i}/{min(max_games, len(games))}] Scraping {game['away_team']} @ {game['home_team']}...")

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

            logger.info(f"  Retrieved {len(all_markets)} markets, {len(match_insights)} insights, {len(player_props)} player props")

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


def _is_player_prop_insight(insight: Dict) -> bool:
    """Check if an insight is a player prop (points, rebounds, assists, etc.)"""
    fact = (insight.get('fact') or '').lower()
    market = (insight.get('market') or '').lower()
    result = (insight.get('result') or '').lower()
    
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
    
    fact = insight.get('fact') or ''
    result = insight.get('result') or ''
    market = insight.get('market') or ''
    
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
        market = insight.get('market', '').lower()
        fact = insight.get('fact', '').lower()
        
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
        
        return {
            'projected_total': projected_total,
            'projected_spread': projected_spread,
            'pace_factor': pace_factor,
            'model_probability': model_probability,
            'confidence_score': confidence_score,
            'away_form_score': away_form,
            'home_form_score': home_form,
            'form_differential': form_diff
        }
        
    except Exception as e:
        logger.debug(f"  Could not calculate team projections: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


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
            # Handle both dict and object insight formats
            if isinstance(insight, dict):
                insight_dict = {
                    'fact': insight.get('fact', ''),
                    'market': insight.get('market', ''),
                    'result': insight.get('result', ''),
                    'odds': insight.get('odds', 0),
                    'tags': insight.get('tags', []),
                    'icon': insight.get('icon', '')
                }
            else:
                # Object format with attributes
                insight_dict = {
                    'fact': getattr(insight, 'fact', ''),
                    'market': getattr(insight, 'market', ''),
                    'result': getattr(insight, 'result', ''),
                    'odds': getattr(insight, 'odds', 0),
                    'tags': getattr(insight, 'tags', []),
                    'icon': getattr(insight, 'icon', '')
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
        # Get base historical analysis
        base_analyzed = analyze_all_insights(
            team_insights,
            minimum_sample_size=4,  # RELAXED: Lower threshold to catch more insights
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
                    
                    # Combine confidence scores
                    hist_confidence = analysis.get('confidence_score', 50)
                    model_confidence = team_projection.get('confidence_score', 50)
                    final_confidence = 0.6 * model_confidence + 0.4 * hist_confidence
                    
                    # Update analysis with projection-based values
                    analysis['historical_probability'] = final_prob
                    analysis['original_historical_probability'] = hist_prob
                    analysis['confidence_score'] = min(final_confidence, 85.0)  # Cap at 85
                    analysis['projected_prob'] = model_prob
                    
                    # Recalculate EV with new probability
                    bookmaker_prob = 1.0 / insight.get('odds', 2.0) if insight.get('odds', 0) > 0 else 0.5
                    analysis['value_percentage'] = (final_prob - bookmaker_prob) * 100
                    analysis['ev_per_100'] = (final_prob * (insight.get('odds', 2.0) - 1) * 100) - ((1 - final_prob) * 100)
                    analysis['has_value'] = analysis['ev_per_100'] > 0
                    
                    logger.debug(f"  [OK] Enhanced team bet with projection: {insight.get('market', 'Unknown')} - Proj: {model_prob:.3f}, Hist: {hist_prob:.3f}, Final: {final_prob:.3f}")
                else:
                    # Have projection data but no probability - try to calculate from projected_total if available
                    projected_total = team_projection.get('projected_total')
                    if projected_total:
                        # Try to extract line from insight
                        import re
                        market = insight.get('market', '').lower()
                        fact = insight.get('fact', '').lower()
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
                            
                            analysis['historical_probability'] = final_prob
                            analysis['original_historical_probability'] = hist_prob
                            analysis['projected_prob'] = model_prob
                            
                            # Recalculate EV
                            bookmaker_prob = 1.0 / insight.get('odds', 2.0) if insight.get('odds', 0) > 0 else 0.5
                            analysis['value_percentage'] = (final_prob - bookmaker_prob) * 100
                            analysis['ev_per_100'] = (final_prob * (insight.get('odds', 2.0) - 1) * 100) - ((1 - final_prob) * 100)
                            analysis['has_value'] = analysis['ev_per_100'] > 0
                            
                            logger.debug(f"  [OK] Calculated probability from projected_total: {projected_total:.1f} vs line {line:.1f} = {model_prob:.3f}")
                        else:
                            logger.debug(f"  [OK] Team bet has projection data (projected_total={projected_total:.1f}) but no line found for probability calculation")
                    else:
                        logger.debug(f"  [OK] Team bet has projection data (no probability calculated): {insight.get('market', 'Unknown')}")
            
            analyzed_team.append(analyzed_item)
    
    # Analyze player prop insights with projection model
    analyzed_props = []
    if player_prop_insights:
        projection_model = PlayerProjectionModel()
        
        for insight in player_prop_insights:
            prop_info = _extract_prop_info_from_insight(insight)
            if not prop_info:
                # Skip if we can't extract prop info - no fallbacks
                logger.debug(f"  Skipping insight - cannot extract prop info: {insight.get('fact', '')[:50]}...")
                continue
            
            # Get player game log - NO FALLBACKS, must succeed
            try:
                game_log = get_player_game_log(
                    player_name=prop_info['player'],
                    last_n_games=20,
                    headless=headless,
                    retries=3,  # Increased retries for reliability
                    use_cache=True
                )
                
                # Require sufficient game log data
                if not game_log or len(game_log) < 5:
                    logger.debug(f"  Skipping {prop_info['player']} - insufficient game log data (n={len(game_log) if game_log else 0})")
                    continue
                
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
                    
                    if projection and hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
                        logger.debug(f"  Matchup adjustments for {prop_info['player']}: pace={projection.matchup_adjustments.pace_multiplier:.3f}x, defense={projection.matchup_adjustments.defense_adjustment:.3f}x")
                    else:
                        logger.debug(f"  No matchup adjustments for {prop_info['player']}")
                    
                    if not projection:
                        logger.debug(f"  Skipping {prop_info['player']} {prop_info['stat']} - projection model returned None")
                        continue
                    
                    # Save original historical probability before combining
                    original_hist_prob = hist_analysis['historical_probability']
                    
                    # Combine: 70% projection, 30% historical
                    final_prob = 0.7 * projection.probability_over_line + 0.3 * original_hist_prob
                    final_confidence = 0.7 * projection.confidence_score + 0.3 * hist_analysis['confidence_score']
                    
                    # Update analysis with projection-based values
                    hist_analysis['historical_probability'] = final_prob  # Final combined probability
                    hist_analysis['original_historical_probability'] = original_hist_prob  # Save original
                    hist_analysis['confidence_score'] = min(final_confidence, 80.0)  # Cap at 80 for small samples
                    hist_analysis['projected_prob'] = projection.probability_over_line
                    hist_analysis['projected_expected_value'] = projection.expected_value
                    # Extract projection details with proper fallbacks
                    pace_mult = 1.0
                    defense_adj = 1.0
                    if hasattr(projection, 'matchup_adjustments') and projection.matchup_adjustments:
                        pace_mult = getattr(projection.matchup_adjustments, 'pace_multiplier', 1.0)
                        defense_adj = getattr(projection.matchup_adjustments, 'defense_adjustment', 1.0)
                    
                    hist_analysis['projection_details'] = {
                        'std_dev': getattr(projection, 'std_dev', None),
                        'minutes_projected': projection.minutes_projection.projected_minutes if (hasattr(projection, 'minutes_projection') and projection.minutes_projection) else None,
                        'pace_multiplier': pace_mult,
                        'defense_adjustment': defense_adj,
                        'role_change_detected': projection.role_change.detected if (hasattr(projection, 'role_change') and projection.role_change) else False
                    }
                    
                    # Recalculate EV with new probability
                    bookmaker_prob = 1.0 / insight['odds']
                    hist_analysis['value_percentage'] = (final_prob - bookmaker_prob) * 100
                    hist_analysis['ev_per_100'] = (final_prob * (insight['odds'] - 1) * 100) - ((1 - final_prob) * 100)
                    hist_analysis['has_value'] = hist_analysis['ev_per_100'] > 0
                    
                    # Only add if projection succeeded
                    analyzed_props.append(analyzed[0])
                    logger.debug(f"  SUCCESS: Projected {prop_info['player']} {prop_info['stat']}")
                    
                except Exception as proj_e:
                    logger.warning(f"  Skipping {prop_info.get('player', 'unknown')} - projection model error: {proj_e}")
                    import traceback
                    logger.debug(traceback.format_exc())
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

    for prop in player_props:
        try:
            player_name = prop['player']
            stat_type = prop['stat']
            line = prop['line']
            odds_over = prop['odds_over']
            odds_under = prop['odds_under']

            # Get player stats from databallr
            logger.debug(f"  Fetching stats for {player_name}...")
            game_log = get_player_game_log(
                player_name=player_name,
                last_n_games=20,
                headless=headless,
                retries=1,
                use_cache=True
            )

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

            if not projection:
                logger.debug(f"  FAILED: Projection model returned None for {player_name}")
                projection_failed_players.append((player_name, stat_type))
                continue

            # Calculate historical hit-rate (SECONDARY SIGNAL - 30% weight)
            stat_values = []
            for g in game_log:
                if g.minutes >= 10:
                    val = getattr(g, stat_type, None)
                    if val is not None:
                        stat_values.append(val)

            if len(stat_values) < 5:
                logger.debug(f"  Insufficient valid games for {player_name} (n={len(stat_values)})")
                continue

            # Historical hit-rate
            over_count = sum(1 for v in stat_values if v > line)
            historical_prob = over_count / len(stat_values) if len(stat_values) > 0 else 0.5

            # Combine projection (70%) + historical (30%)
            final_prob = 0.7 * projection.probability_over_line + 0.3 * historical_prob

            # Use projection confidence as primary confidence
            confidence = projection.confidence_score

            # Determine recommendation
            recommendation = None
            selected_odds = None

            if final_prob > 0.55 and confidence >= 60:
                recommendation = 'OVER'
                selected_odds = odds_over
            elif final_prob < 0.45 and confidence >= 60:
                recommendation = 'UNDER'
                selected_odds = odds_under

            if recommendation:
                # Calculate EV
                implied_prob = 1.0 / selected_odds
                actual_prob = final_prob if recommendation == 'OVER' else (1 - final_prob)
                edge = actual_prob - implied_prob
                ev_per_100 = (actual_prob * (selected_odds - 1) * 100) - ((1 - actual_prob) * 100)

                prediction = {
                    'type': 'player_prop',
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'prediction': recommendation,
                    'odds': selected_odds,
                    'expected_value': round(projection.expected_value, 1),
                    'projected_prob': round(projection.probability_over_line, 3),
                    'historical_prob': round(historical_prob, 3),
                    'final_prob': round(final_prob, 3),
                    'confidence': round(confidence, 0),
                    'sample_size': len(stat_values),
                    'edge': round(edge * 100, 1),
                    'ev_per_100': round(ev_per_100, 2),
                    'game': f"{away_team} @ {home_team}",
                    'market_name': prop.get('market_name', '')
                }
                
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
                    'distribution_type': getattr(projection, 'distribution_type', None)
                }
                
                predictions.append(prediction)
                logger.debug(f"  {player_name} {stat_type} {recommendation} {line} - Projected: {projection.probability_over_line:.3f}, Historical: {historical_prob:.3f}, Final: {final_prob:.3f}, Confidence: {confidence:.0f}")

        except Exception as e:
            logger.warning(f"  Error analyzing {prop.get('player', 'unknown')}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            continue

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


def rank_all_bets(team_bets: List[Dict], player_props: List[Dict]) -> List[Dict]:
    """
    Combine team bets and player props into a unified ranking.

    QUALITY OVER QUANTITY with STRICT EV THRESHOLDS:
    - Props: Minimum +3% EV
    - Sides/Totals: Minimum +2% EV
    - Minimum confidence threshold: 50/100
    - Maximum 5 bets total
    - Maximum 2 bets per game (correlation control)
    - Trend-only bets (no model projections) get confidence penalty

    Returns:
        List of top 5 high-confidence bets
    """
    all_bets = []

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
                    logger.debug(f"  Skipping player prop {player_name} - missing projection_details")
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
                
                all_bets.append({
                    'type': 'player_prop',
                    'game': bet.get('game', 'Unknown Game'),
                    'player': player_name,
                    'stat': stat_type,
                    'line': line,
                    'prediction': 'OVER',  # Default, should be determined from analysis
                    'odds': insight.get('odds', 0),
                    'confidence': weighted_conf,
                    'original_confidence': base_conf,
                    'has_model_projection': True,
                    'ev_per_100': analysis.get('ev_per_100', 0),
                    'edge': analysis.get('value_percentage', 0),
                    'sample_size': analysis.get('sample_size', 0),
                    'expected_value': analysis.get('projected_expected_value', 0),
                    'projected_prob': analysis.get('projected_prob', 0),
                    'historical_prob': analysis.get('original_historical_probability', analysis.get('historical_probability', 0)),
                    'final_prob': analysis.get('historical_probability', 0),
                    'projection_details': projection_details,
                    'has_matchup_alignment': has_matchup_alignment
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
            
            all_bets.append({
                'type': bet_type,  # Use marked type instead of always 'team_bet'
                'game': bet.get('game', 'Unknown Game'),
                'market': insight.get('market', 'Unknown Market'),
                'result': insight.get('result', ''),
                'odds': insight.get('odds', 0),
                'confidence': confidence,
                'original_confidence': base_confidence,
                'has_model_projection': has_model_projection,
                'ev_per_100': analysis.get('ev_per_100', 0),
                'edge': analysis.get('value_percentage', 0),
                'sample_size': analysis.get('sample_size', 0),
                'fact': (insight.get('fact', '') or '')[:100],  # Truncate for display
                'historical_probability': analysis.get('historical_probability', 0.5),
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
            
            all_bets.append({
                'type': 'player_prop',
                'game': prop.get('game', 'Unknown Game'),
                'player': player_name,
                'stat': prop.get('stat', 'points'),
                'line': line,
                'prediction': prop.get('prediction', 'OVER'),
                'odds': prop.get('odds', 0),
                'confidence': weighted_conf,
                'original_confidence': base_conf,  # Store original for display
                'has_model_projection': True,  # Player props always have projections
                'ev_per_100': prop.get('ev_per_100', 0),
                'edge': prop.get('edge', 0),
                'sample_size': prop.get('sample_size', 0),
                'expected_value': prop.get('expected_value', 0),
                'projected_prob': prop.get('projected_prob', 0),
                'historical_prob': prop.get('historical_prob', 0),
                'final_prob': prop.get('final_prob', 0),
                'projection_details': projection_details,
                'market_name': prop.get('market_name', '')
            })
        except Exception as e:
            logger.warning(f"  Error processing player prop: {e}")
            continue

    # IMPROVEMENT 2.2: Combined EV + Probability Cutoff
    # Reject bets where:
    # - probability < 60%, OR
    # - edge < 0%, OR
    # - sample < 5 (unless model-driven)
    ev_filtered_bets = []
    rejected_bets = []
    
    for bet in all_bets:
        probability = bet.get('final_prob', bet.get('historical_probability', 0))
        edge = bet.get('edge', 0)  # Edge percentage
        sample_size = bet.get('sample_size', 0)
        has_model = bet.get('has_model_projection', False)
        
        # Reject if probability < 60%
        if probability < 0.60:
            rejected_bets.append({'bet': bet, 'reason': f'Probability too low ({probability:.1%} < 60%)'})
            continue
        
        # Reject if edge < 0%
        if edge < 0:
            rejected_bets.append({'bet': bet, 'reason': f'Negative edge ({edge:.1f}%)'})
            continue
        
        # Reject if sample < 5 (unless model-driven)
        if sample_size < 5 and not has_model:
            rejected_bets.append({'bet': bet, 'reason': f'Sample too small (n={sample_size} < 5, no model)'})
            continue
        
        ev_filtered_bets.append(bet)
    
    logger.info(f"EV + Probability Filtering: {len(ev_filtered_bets)}/{len(all_bets)} bets passed")
    if rejected_bets:
        logger.debug(f"  Rejected {len(rejected_bets)} bets:")
        for r in rejected_bets[:5]:
            bet = r['bet']
            bet_type = bet.get('type', 'unknown')
            if bet_type == 'player_prop':
                desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()}"
            else:
                desc = f"{bet.get('market', 'Unknown')}"
            logger.debug(f"    - {desc}: {r['reason']}")
    
    # Sort by confidence
    try:
        all_bets_sorted = sorted(ev_filtered_bets, key=lambda x: x.get('confidence', 0), reverse=True)
    except Exception as e:
        logger.warning(f"Error sorting bets: {e}")
        all_bets_sorted = ev_filtered_bets
    
    # RELAXED: Lower confidence thresholds to catch more insights (projection model will validate)
    confidence_thresholds = [50, 45, 40, 35, 30, 25, 20]  # Start at 50
    filtered_bets = []
    used_threshold = None
    confidence_filtered_out = []
    
    for threshold in confidence_thresholds:
        high_confidence_bets = [bet for bet in all_bets_sorted if bet.get('confidence', 0) >= threshold]
        
        if not high_confidence_bets:
            continue
        
        # IMPROVEMENT 2.3: Correlation Control Upgrade
        # Instead of "max 2 per game", calculate correlation score:
        # - Props from same player = very high correlation -> allow max 1
        # - Props + total = moderate correlation -> allow max 2
        # - Props from opposite teams = low correlation -> allow 3 max
        filtered_bets = []
        player_counts = {}  # Track bets per player
        game_counts = {}  # Track bets per game
        game_bets = {}  # Track bets by game for correlation calculation
        
        for bet in high_confidence_bets:
            if not bet or not isinstance(bet, dict):
                continue
            try:
                game = bet.get('game', 'Unknown')
                player = bet.get('player', None)
                bet_type = bet.get('type', 'unknown')
                
                # Calculate correlation with existing bets
                max_allowed = 3  # Default: low correlation
                correlation_penalty = 0
                
                if bet_type == 'player_prop' and player:
                    # Check if we already have a bet for this player
                    if player in player_counts:
                        # Same player = very high correlation -> allow max 1
                        max_allowed = 1
                        correlation_penalty = -10
                    else:
                        # Check correlation with existing bets in same game
                        game_bet_list = game_bets.get(game, [])
                        for existing_bet in game_bet_list:
                            corr_score = calculate_correlation_score(bet, existing_bet)
                            if corr_score >= 1.0:  # Very high correlation
                                max_allowed = 1
                                correlation_penalty = -10
                                break
                            elif corr_score >= 0.5:  # Moderate correlation
                                max_allowed = 2
                                correlation_penalty = -5
                elif bet_type == 'team_bet':
                    # Check correlation with existing bets in same game
                    game_bet_list = game_bets.get(game, [])
                    for existing_bet in game_bet_list:
                        corr_score = calculate_correlation_score(bet, existing_bet)
                        if corr_score >= 0.5:  # Moderate correlation
                            max_allowed = 2
                            correlation_penalty = -5
                            break
                
                # Apply correlation penalty to confidence
                if correlation_penalty < 0:
                    bet['confidence'] = max(0, bet.get('confidence', 0) + correlation_penalty)
                    bet['correlation_penalty'] = correlation_penalty
                
                # Check limits
                game_count = game_counts.get(game, 0)
                player_count = player_counts.get(player, 0) if player else 0
                
                # Apply limits based on correlation
                can_add = True
                if bet_type == 'player_prop' and player:
                    if player_count >= max_allowed:
                        can_add = False
                        reason = f'Player limit (already {player_count} bets for {player}, max {max_allowed})'
                elif game_count >= max_allowed:
                    can_add = False
                    reason = f'Game limit (already {game_count} bets for {game}, max {max_allowed})'
                
                if can_add and len(filtered_bets) < 5:
                    filtered_bets.append(bet)
                    game_counts[game] = game_count + 1
                    if player:
                        player_counts[player] = player_count + 1
                    if game not in game_bets:
                        game_bets[game] = []
                    game_bets[game].append(bet)
                else:
                    # Track bets filtered by correlation limits
                    if bet_type == 'player_prop':
                        bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
                    else:
                        bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', '')}"
                    confidence_filtered_out.append({
                        'desc': bet_desc,
                        'reason': reason if not can_add else f'Total limit (already {len(filtered_bets)} bets)',
                        'confidence': bet.get('confidence', 0),
                        'ev_pct': bet.get('edge', 0)
                    })
                
                # Stop if we have 5 bets
                if len(filtered_bets) >= 5:
                    break
            except Exception as e:
                logger.debug(f"  Error processing bet in ranking: {e}")
                continue
        
        if len(filtered_bets) >= 5:
            used_threshold = threshold
            break
        elif len(filtered_bets) > 0:
            # Keep the best we found so far, but continue trying
            used_threshold = threshold
            if threshold == confidence_thresholds[-1]:
                # Last threshold, use what we have
                break
    
    if used_threshold and used_threshold < 50:
        logger.info(f"Lowered confidence threshold to {used_threshold}/100 to find 5 bets (found {len(filtered_bets)})")
    
    # Show why we don't have 5 bets
    if len(filtered_bets) < 5:
        total_available = len(ev_filtered_bets)
        logger.info(f"  Only {len(filtered_bets)}/{total_available} bets meet all criteria (need 5)")
        
        # Show bets that passed EV but failed confidence
        if total_available > len(filtered_bets):
            low_confidence = [bet for bet in ev_filtered_bets if bet.get('confidence', 0) < (used_threshold or 50)]
            if low_confidence:
                logger.info(f"  {len(low_confidence)} bets filtered by confidence (< {used_threshold or 50}):")
                for bet in sorted(low_confidence, key=lambda x: x.get('confidence', 0), reverse=True)[:5]:
                    bet_type = bet.get('type', 'unknown')
                    if bet_type == 'player_prop':
                        bet_desc = f"{bet.get('player', 'Unknown')} - {bet.get('stat', 'points').title()} {bet.get('prediction', 'OVER')} {bet.get('line', 0)}"
                    else:
                        bet_desc = f"{bet.get('market', 'Unknown')} - {bet.get('result', '')}"
                    logger.info(f"    - {bet_desc}: Conf {bet.get('confidence', 0):.0f}, EV {bet.get('edge', 0):.1f}%")
        
        # Show bets filtered by game limit
        if confidence_filtered_out:
            logger.info(f"  {len(confidence_filtered_out)} bets filtered by game limit (max 2 per game):")
            for filtered in confidence_filtered_out[:5]:
                logger.info(f"    - {filtered['desc']}: {filtered['reason']}")
    
    return filtered_bets


def print_unified_report(final_bets: List[Dict]):
    """
    Print comprehensive report of all value bets (team + player props).

    Shows top 5 high-confidence bets only (QUALITY OVER QUANTITY).
    """
    if not final_bets:
        print("\n" + "="*70)
        print("  NO HIGH-CONFIDENCE BETS FOUND")
        print("="*70)
        print("\nNo bets met the minimum confidence threshold (50/100).")
        print("Consider analyzing more games or waiting for better opportunities.")
        return

    print("\n" + "="*70)
    print(f"  TOP {len(final_bets)} HIGH-CONFIDENCE BETS (Quality over Quantity)")
    print("="*70)

    team_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'team_bet')
    prop_count = sum(1 for b in final_bets if b and isinstance(b, dict) and b.get('type') == 'player_prop')

    print(f"\nTotal: {len(final_bets)} bets ({team_count} team, {prop_count} player)")
    # Determine actual confidence threshold used
    if final_bets:
        confidences = [bet.get('confidence', 0) for bet in final_bets if bet and isinstance(bet, dict)]
        if confidences:
            min_confidence = min(confidences)
            max_confidence = max(confidences)
            print(f"Confidence Range: {min_confidence:.0f}-{max_confidence:.0f}/100 | Max per Game: 2 | Max Total: 5")
        else:
            print(f"Minimum Confidence: 50/100 | Max per Game: 2 | Max Total: 5")
    else:
        print(f"Minimum Confidence: 50/100 | Max per Game: 2 | Max Total: 5")
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
                print(f"   Odds: {bet.get('odds', 0):.2f} | Confidence: {bet.get('confidence', 0):.0f}/100")
                print(f"   EV: ${bet.get('ev_per_100', 0):+.2f}/100 | Edge: {bet.get('edge', 0):+.1f}% | Sample: n={bet.get('sample_size', 0)}")
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
                
                # Show projected stat value (e.g., "26.5 points") not EV
                if projected_stat > 0:
                    print(f"   Projected: {projected_stat:.1f} | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                else:
                    print(f"   Projected EV: ${projected_ev:.2f}/100 | Prob: {final_prob:.1%} (Proj: {projected_prob:.1%}, Hist: {original_hist_prob:.1%})")
                
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
                
                print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100")
                print(f"   EV: ${ev_per_100:+.2f}/100 | Edge: {edge:+.1f}% | Sample: n={sample}")
                print(f"   Game: {bet.get('game', 'Unknown')}")

            print()
        except Exception as e:
            logger.warning(f"  Error displaying bet {i}: {e}")
            continue

    print("="*70)


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
        print("  QUALITY OVER QUANTITY - Top 5 High-Confidence Bets")
        print("="*70)
        print("\nPipeline Flow:")
        print("  1. [SPORTSBET SCRAPER] Scrapes games, markets, insights, and player props")
        print("  2. [DATABALLR SCRAPER] Fetches player game logs (robust, with retries)")
        print("  3. [INSIGHT ANALYZER] Analyzes team bets using Context-Aware Value Engine")
        print("  4. [MODEL PROJECTIONS] Calculates player prop projections with matchup adjustments")
        print("  5. [DISPLAY] Filters to high-confidence bets and returns top 5 (max 2 per game)")
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
        print(f"\nAnalyzing ALL available games to find top 5 high-confidence bets...")
    else:
        print(f"\nAnalyzing {max_games} game(s)...")

    # Step 1: Scrape Sportsbet data
    print("\n" + "-"*70)
    print("STEP 1: [SPORTSBET SCRAPER] Scraping games, markets, insights, and player props")
    print("-"*70)

    try:
        games_data = scrape_games(max_games, headless=True)
    except Exception as e:
        print(f"\n[ERROR] Failed to scrape games: {e}")
        logger.error(f"Scraping error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return

    if not games_data:
        print("\n[ERROR] No games data retrieved. Exiting.")
        return

    print(f"\n[OK] Successfully scraped {len(games_data)} game(s)")

    # Step 2: Analyze each game (DataballR -> Insights -> Model)
    print("\n" + "-"*70)
    print("STEP 2: [DATABALLR -> INSIGHTS -> MODEL] Analyzing bets")
    print("-"*70)
    if DATABALLR_ROBUST_AVAILABLE:
        print("  * DataballR: Fetching player game logs ([OK] ROBUST scraper with retries & schema mapping)")
    else:
        print("  * DataballR: Fetching player game logs ([WARNING] Original scraper - robust version not available)")
    print("  * Insights: Analyzing team bets with Context-Aware Value Engine")
    print("  * Model: Calculating player prop projections with matchup adjustments")

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

            # Analyze team bets
            print(f"  Analyzing team insights...")
            try:
                team_bets = analyze_team_bets(game_data, headless=headless)
                print(f"  Team bets: {len(team_bets)} value bets found")
                all_team_bets.extend(team_bets)
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
                
                if player_props_list:
                    print(f"  Found {len(player_props_list)} player prop markets to analyze")
                    if market_players:
                        print(f"  Players in markets: {', '.join(market_players[:5])}" + ("..." if len(market_players) > 5 else ""))
                else:
                    # Debug: Check why no player props were extracted
                    prop_markets = [m for m in all_markets if 'player' in str(getattr(m, 'market_category', '')).lower() or any(stat in str(getattr(m, 'selection_text', '')).lower() for stat in ['points', 'rebounds', 'assists'])]
                    if prop_markets:
                        print(f"  WARNING: {len(prop_markets)} potential player prop markets found but not extracted (check extraction logic)")
                        logger.debug(f"  Sample market texts: {[getattr(m, 'selection_text', '')[:50] for m in prop_markets[:3]]}")
                    else:
                        print(f"  WARNING: No player prop markets found in this game (total markets: {len(all_markets)})")
                
                player_props, missing_players = analyze_player_props(game_data, headless=headless)
                print(f"  Player props: {len(player_props)} predictions found (projection model)")
                
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
    print("  * Confidence: 50+/100 (lowered if needed)")
    print("  * Max per game: 2 bets (correlation control)")
    print("  * Max total: 5 bets")
    print("  * Trend-only bets: -20 confidence penalty")

    try:
        final_bets = rank_all_bets(all_team_bets, all_player_props)
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
        print("  - All bets below confidence threshold (50+)")
        print("  - Insufficient data quality")

    # Step 4: Display results
    try:
        if final_bets:
            print_unified_report(final_bets)
        else:
            print("\n[INFO] No bets to display")
    except Exception as e:
        logger.error(f"Error printing report: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] Failed to display results: {e}")
        print("Attempting to show basic bet list...")
        try:
            for i, bet in enumerate(final_bets[:5], 1):
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

    print("\n" + "="*70)
    print("  ANALYSIS COMPLETE")
    print("="*70)
    
    # Show missing players summary if any
    if all_missing_players:
        print("\n" + "="*70)
        print("  WARNING: MISSING PLAYER DATA - ACTION REQUIRED")
        print("="*70)
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
        
        print()
        print("TO FIX:")
        print("  1. Run: python build_databallr_player_cache.py")
        print("     (This will add the players listed in PLAYERS_TO_ADD.txt)")
        print("  2. Re-run this analysis to include these props")
        print()
        print(f"This will unlock {len(all_missing_players)} additional player prop opportunities!")
        print("="*70)
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
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
        
        print("\n" + "="*70)
        print("  ERROR - Script Failed")
        print("="*70)
        print(f"\n{e}\n")
        print("\nFull traceback:")
        traceback.print_exc()
        print(f"\nError also saved to: {error_log}")
        print("\nPress Enter to close...")
        try:
            input()
        except:
            pass  # If input fails, just continue
