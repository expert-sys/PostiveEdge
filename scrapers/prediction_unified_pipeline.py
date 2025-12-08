import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
import os
import requests
from scrapers.sportsbet_scraper import scrape_match_detail
# NBA API REMOVED - Using databallr only
from scrapers.databallr_scraper import get_player_game_log as get_player_game_log_databallr
from scrapers.player_projection_model import PlayerProjectionModel
import logging

logger = logging.getLogger(__name__)
from scrapers.rotowire_scraper import scrape_rotowire_lineups, find_lineup_for_matchup
from value_engine import analyze_simple_market
from value_engine_enhanced import EnhancedValueEngine, TeamStats as EnhancedTeamStats


TEAM_NAME_MAP = {
    "la lakers": "Los Angeles Lakers",
    "los angeles lakers": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers",
    "la clippers": "LA Clippers",
    "los angeles clippers": "LA Clippers",
    "clippers": "LA Clippers",
    "new york knicks": "New York Knicks",
    "ny knicks": "New York Knicks",
    "knicks": "New York Knicks",
    "golden state warriors": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "orlando magic": "Orlando Magic",
    "magic": "Orlando Magic",
    "boston celtics": "Boston Celtics",
    "celtics": "Boston Celtics",
    "miami heat": "Miami Heat",
    "heat": "Miami Heat",
    "chicago bulls": "Chicago Bulls",
    "bulls": "Chicago Bulls",
    "philadelphia 76ers": "Philadelphia 76ers",
    "sixers": "Philadelphia 76ers",
    "brooklyn nets": "Brooklyn Nets",
    "nets": "Brooklyn Nets",
    "milwaukee bucks": "Milwaukee Bucks",
    "bucks": "Milwaukee Bucks",
    "dallas mavericks": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks",
    "mavs": "Dallas Mavericks",
    "denver nuggets": "Denver Nuggets",
    "nuggets": "Denver Nuggets",
    "phoenix suns": "Phoenix Suns",
    "suns": "Phoenix Suns",
    "sacramento kings": "Sacramento Kings",
    "kings": "Sacramento Kings",
    "san antonio spurs": "San Antonio Spurs",
    "spurs": "San Antonio Spurs",
    "memphis grizzlies": "Memphis Grizzlies",
    "grizzlies": "Memphis Grizzlies",
    "toronto raptors": "Toronto Raptors",
    "raptors": "Toronto Raptors",
    "utah jazz": "Utah Jazz",
    "jazz": "Utah Jazz",
    "portland trail blazers": "Portland Trail Blazers",
    "trail blazers": "Portland Trail Blazers",
    "blazers": "Portland Trail Blazers",
    "new orleans pelicans": "New Orleans Pelicans",
    "pelicans": "New Orleans Pelicans",
    "atlanta hawks": "Atlanta Hawks",
    "hawks": "Atlanta Hawks",
    "charlotte hornets": "Charlotte Hornets",
    "hornets": "Charlotte Hornets",
    "cleveland cavaliers": "Cleveland Cavaliers",
    "cavaliers": "Cleveland Cavaliers",
    "cavs": "Cleveland Cavaliers",
    "detroit pistons": "Detroit Pistons",
    "pistons": "Detroit Pistons",
    "houston rockets": "Houston Rockets",
    "rockets": "Houston Rockets",
    "indiana pacers": "Indiana Pacers",
    "pacers": "Indiana Pacers",
    "minnesota timberwolves": "Minnesota Timberwolves",
    "timberwolves": "Minnesota Timberwolves",
    "wolves": "Minnesota Timberwolves",
    "oklahoma city thunder": "Oklahoma City Thunder",
    "thunder": "Oklahoma City Thunder",
    "washington wizards": "Washington Wizards",
    "wizards": "Washington Wizards"
}


def _normalize_team_name(name: str) -> str:
    if not name:
        return name
    k = name.strip().lower()
    return TEAM_NAME_MAP.get(k, name)


def get_player_game_log(player_name, season="2024-25", last_n_games=None, retries=2, use_cache=True):
    """
    Get player game log from databallr.com.

    Args:
        player_name: Player name to search for
        season: NBA season (not used, kept for compatibility)
        last_n_games: Number of recent games to fetch
        retries: Number of retry attempts
        use_cache: Whether to use cached data

    Returns:
        List of GameLogEntry objects
    """
    logger.info(f"Fetching {player_name} from databallr...")
    result = get_player_game_log_databallr(
        player_name=player_name,
        season=season,
        last_n_games=last_n_games,
        retries=retries,
        use_cache=use_cache,
        headless=True
    )
    if result and len(result) > 0:
        logger.info(f"✓ Retrieved {len(result)} games for {player_name} from databallr")
    else:
        logger.warning(f"No games found for {player_name}")
    return result


def _parse_total_threshold(markets: List) -> Optional[float]:
    for m in markets:
        t = m.line or m.selection_text
        if not t:
            continue
        s = str(t)
        nums = []
        buf = ""
        for ch in s:
            if ch.isdigit() or ch in ".-+":
                buf += ch
            else:
                if buf:
                    nums.append(buf)
                    buf = ""
        if buf:
            nums.append(buf)
        for n in nums:
            try:
                return float(n)
            except:
                continue
    return None


def _analyze_moneyline(match, headless: bool, no_api: bool = False) -> Optional[Dict]:
    ml = match.get_moneyline()
    if not ml or len(ml) < 2:
        # Fallback: scan all markets for team win labels
        ml = []
        for mkt in getattr(match, 'all_markets', []) or []:
            sel = (mkt.selection_text or '').lower()
            at = _normalize_team_name(match.away_team).lower().split()[-1]
            ht = _normalize_team_name(match.home_team).lower().split()[-1]
            if (at in sel or ht in sel) and ('win' in sel or 'to win' in sel) and '(' not in mkt.selection_text:
                ml.append(mkt)
        if not ml or len(ml) < 2:
            ml = []
    away_team = _normalize_team_name(match.away_team)
    home_team = _normalize_team_name(match.home_team)
    away_odds = None
    home_odds = None
    for m in ml:
        if m.team:
            mt = m.team.lower()
            at = away_team.lower()
            ht = home_team.lower()
            if at in mt or mt in at:
                away_odds = m.odds
            if ht in mt or mt in ht:
                home_odds = m.odds
    # Fallback: derive odds from match insights if present
    if (away_odds is None or home_odds is None) and hasattr(match, 'match_insights') and match.match_insights:
        for ins in match.match_insights:
            if ins.market and 'Match' in ins.market and ins.odds:
                tags = [t.lower() for t in (ins.tags or [])]
                if away_team.lower() in tags and away_odds is None:
                    away_odds = ins.odds
                if home_team.lower() in tags and home_odds is None:
                    home_odds = ins.odds
    # Fallback: use Odds API
    if away_odds is None or home_odds is None:
        key = os.environ.get('ODDS_API_KEY') or globals().get('_ODDS_API_KEY')
        if key:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
                params = {
                    'regions': 'us',
                    'markets': 'h2h',
                    'oddsFormat': 'decimal',
                    'dateFormat': 'iso',
                    'apiKey': key
                }
                r = requests.get(url, params=params, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    best_away = None
                    best_home = None
                    ev = _select_odds_event(data, away_team, home_team)
                    if ev:
                        at_canon = _normalize_team_name(away_team)
                        ht_canon = _normalize_team_name(home_team)
                        at_aliases = {at_canon.lower(), away_team.strip().lower()}
                        ht_aliases = {ht_canon.lower(), home_team.strip().lower()}
                        for k, v in TEAM_NAME_MAP.items():
                            if v == at_canon:
                                at_aliases.add(k)
                            if v == ht_canon:
                                ht_aliases.add(k)
                        for bm in ev.get('bookmakers', []):
                            for mk in bm.get('markets', []):
                                if mk.get('key') == 'h2h':
                                    for oc in mk.get('outcomes', []):
                                        name = oc.get('name', '').lower()
                                        price = oc.get('price')
                                        if price is None:
                                            continue
                                        if any(alias in name for alias in at_aliases):
                                            best_away = max(best_away, price) if best_away is not None else price
                                        elif any(alias in name for alias in ht_aliases):
                                            best_home = max(best_home, price) if best_home is not None else price
                    if best_away is not None and away_odds is None:
                        away_odds = float(best_away)
                    if best_home is not None and home_odds is None:
                        home_odds = float(best_home)
            except Exception:
                pass
    if not away_odds or not home_odds:
        return None
    if no_api:
        engine = EnhancedValueEngine()
        ms = getattr(match, "match_stats", None)
        a_stats = None
        h_stats = None
        if ms and ms.away_team_stats and ms.home_team_stats:
            a_raw = ms.away_team_stats
            h_raw = ms.home_team_stats
            a_stats = EnhancedTeamStats(
                team_name=away_team,
                avg_points_for=a_raw.avg_points_for,
                avg_points_against=a_raw.avg_points_against,
                avg_total_points=a_raw.avg_total_points,
                favorite_win_pct=a_raw.favorite_win_pct,
                underdog_win_pct=a_raw.underdog_win_pct,
                clutch_win_pct=a_raw.clutch_win_pct
            )
            h_stats = EnhancedTeamStats(
                team_name=home_team,
                avg_points_for=h_raw.avg_points_for,
                avg_points_against=h_raw.avg_points_against,
                avg_total_points=h_raw.avg_total_points,
                favorite_win_pct=h_raw.favorite_win_pct,
                underdog_win_pct=h_raw.underdog_win_pct,
                clutch_win_pct=h_raw.clutch_win_pct
            )
        away_enh = engine.analyze_with_team_stats(
            historical_outcomes=[],
            bookmaker_odds=away_odds,
            team_a_stats=a_stats,
            team_b_stats=h_stats,
            market_type="match",
            is_favourite=True if away_odds < home_odds else False
        )
        home_enh = engine.analyze_with_team_stats(
            historical_outcomes=[],
            bookmaker_odds=home_odds,
            team_a_stats=h_stats,
            team_b_stats=a_stats,
            market_type="match",
            is_favourite=True if home_odds < away_odds else False
        )
        pick = away_team if away_odds <= home_odds else home_team
        chosen = away_enh if pick == away_team else home_enh
        return {
            "type": "moneyline",
            "away_team": away_team,
            "home_team": home_team,
            "away_odds": away_odds,
            "home_odds": home_odds,
            "pick": pick,
            "analysis": chosen.to_dict()
        }
    # NBA API REMOVED - Always use empty lists (will fallback to Sportsbet H2H if available)
    away_hist = []
    home_hist = []
    if not away_hist or not home_hist:
        try:
            detailed = scrape_match_detail(match.url)
            if detailed and detailed.head_to_head:
                h2h = detailed.head_to_head
                away_hist = []
                home_hist = []
                for g in h2h:
                    if g.final_home is not None and g.final_away is not None:
                        home_hist.append(1 if g.final_home > g.final_away else 0)
                        away_hist.append(1 if g.final_away > g.final_home else 0)
                if not away_hist or not home_hist:
                    pass
            else:
                pass
        except Exception:
            pass
    if not away_hist or not home_hist:
        try:
            detailed = scrape_match_detail(match.url)
            ts = detailed.team_stats if detailed else {}
            if ts:
                a = ts.get(_normalize_team_name(match.away_team))
                h = ts.get(_normalize_team_name(match.home_team))
                if a and h and a.win_percentage is not None and h.win_percentage is not None:
                    aw = max(1, int(a.win_percentage * 20))
                    hw = max(1, int(h.win_percentage * 20))
                    away_hist = [1]*aw + [0]*(20 - aw)
                    home_hist = [1]*hw + [0]*(20 - hw)
        except Exception:
            pass
    if not away_hist or not home_hist:
        if away_odds and home_odds:
            engine = EnhancedValueEngine()
            ms = getattr(match, "match_stats", None)
            a_stats = None
            h_stats = None
            if ms and ms.away_team_stats and ms.home_team_stats:
                a_raw = ms.away_team_stats
                h_raw = ms.home_team_stats
                a_stats = EnhancedTeamStats(
                    team_name=away_team,
                    avg_points_for=a_raw.avg_points_for,
                    avg_points_against=a_raw.avg_points_against,
                    avg_total_points=a_raw.avg_total_points,
                    favorite_win_pct=a_raw.favorite_win_pct,
                    underdog_win_pct=a_raw.underdog_win_pct,
                    clutch_win_pct=a_raw.clutch_win_pct
                )
                h_stats = EnhancedTeamStats(
                    team_name=home_team,
                    avg_points_for=h_raw.avg_points_for,
                    avg_points_against=h_raw.avg_points_against,
                    avg_total_points=h_raw.avg_total_points,
                    favorite_win_pct=h_raw.favorite_win_pct,
                    underdog_win_pct=h_raw.underdog_win_pct,
                    clutch_win_pct=h_raw.clutch_win_pct
                )
            away_enh = engine.analyze_with_team_stats(
                historical_outcomes=[],
                bookmaker_odds=away_odds,
                team_a_stats=a_stats,
                team_b_stats=h_stats,
                market_type="match",
                is_favourite=True if away_odds < home_odds else False
            )
            home_enh = engine.analyze_with_team_stats(
                historical_outcomes=[],
                bookmaker_odds=home_odds,
                team_a_stats=h_stats,
                team_b_stats=a_stats,
                market_type="match",
                is_favourite=True if home_odds < away_odds else False
            )
            pick = away_team if away_odds <= home_odds else home_team
            chosen = away_enh if pick == away_team else home_enh
            return {
                "type": "moneyline",
                "away_team": away_team,
                "home_team": home_team,
                "away_odds": away_odds,
                "home_odds": home_odds,
                "pick": pick,
                "analysis": chosen.to_dict()
            }
        return None
    if away_odds and home_odds:
        engine = EnhancedValueEngine()
        a_stats = None
        h_stats = None
        ms = getattr(match, "match_stats", None)
        if ms and ms.away_team_stats and ms.home_team_stats:
            a_raw = ms.away_team_stats
            h_raw = ms.home_team_stats
            a_stats = EnhancedTeamStats(
                team_name=away_team,
                avg_points_for=a_raw.avg_points_for,
                avg_points_against=a_raw.avg_points_against,
                avg_total_points=a_raw.avg_total_points,
                favorite_win_pct=a_raw.favorite_win_pct,
                underdog_win_pct=a_raw.underdog_win_pct,
                clutch_win_pct=a_raw.clutch_win_pct
            )
            h_stats = EnhancedTeamStats(
                team_name=home_team,
                avg_points_for=h_raw.avg_points_for,
                avg_points_against=h_raw.avg_points_against,
                avg_total_points=h_raw.avg_total_points,
                favorite_win_pct=h_raw.favorite_win_pct,
                underdog_win_pct=h_raw.underdog_win_pct,
                clutch_win_pct=h_raw.clutch_win_pct
            )
        away_enh = engine.analyze_with_team_stats(
            historical_outcomes=away_hist,
            bookmaker_odds=away_odds,
            team_a_stats=a_stats,
            team_b_stats=h_stats,
            market_type="match",
            is_favourite=True if away_odds < home_odds else False
        )
        home_enh = engine.analyze_with_team_stats(
            historical_outcomes=home_hist,
            bookmaker_odds=home_odds,
            team_a_stats=h_stats,
            team_b_stats=a_stats,
            market_type="match",
            is_favourite=True if home_odds < away_odds else False
        )
        pick = away_team if away_enh.value_percentage > home_enh.value_percentage else home_team
        chosen = away_enh if pick == away_team else home_enh
        return {
            "type": "moneyline",
            "away_team": away_team,
            "home_team": home_team,
            "away_odds": away_odds,
            "home_odds": home_odds,
            "pick": pick,
            "analysis": chosen.to_dict()
        }
    else:
        aw_rate = (sum(away_hist) / len(away_hist)) if away_hist else 0.0
        ho_rate = (sum(home_hist) / len(home_hist)) if home_hist else 0.0
        pick = away_team if aw_rate >= ho_rate else home_team
        rate = max(aw_rate, ho_rate)
        n = max(len(away_hist), len(home_hist))
        return {
            "type": "moneyline",
            "away_team": away_team,
            "home_team": home_team,
            "pick": pick,
            "analysis": {"win_rate": rate, "sample_size": n, "method": "fallback"}
        }


def _analyze_totals(match, no_api: bool = False) -> Optional[Dict]:
    totals = match.get_totals()
    if not totals:
        return None
    threshold = _parse_total_threshold(totals)
    if threshold is None:
        return None
    away_team = _normalize_team_name(match.away_team)
    home_team = _normalize_team_name(match.home_team)
    away_odds = None
    home_odds = None
    for m in totals:
        t = (m.selection_text or "").lower()
        if "over" in t:
            away_odds = m.odds
        if "under" in t:
            home_odds = m.odds
    if not away_odds or not home_odds:
        key = os.environ.get('ODDS_API_KEY') or globals().get('_ODDS_API_KEY')
        if key:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
                params = {
                    'regions': 'us',
                    'markets': 'totals',
                    'oddsFormat': 'decimal',
                    'dateFormat': 'iso',
                    'apiKey': key
                }
                r = requests.get(url, params=params, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    best_over = None
                    best_under = None
                    best_line = None
                    ev = _select_odds_event(data, away_team, home_team)
                    if ev:
                        for bm in ev.get('bookmakers', []):
                            for mk in bm.get('markets', []):
                                if mk.get('key') == 'totals':
                                    for oc in mk.get('outcomes', []):
                                        label = oc.get('name', '').lower()
                                        price = oc.get('price')
                                        point = oc.get('point')
                                        if label == 'over':
                                            best_over = max(best_over, price) if best_over is not None else price
                                            best_line = point if point is not None else best_line
                                        elif label == 'under':
                                            best_under = max(best_under, price) if best_under is not None else price
                                            best_line = point if point is not None else best_line
                    if away_odds is None and best_over is not None:
                        away_odds = float(best_over)
                    if home_odds is None and best_under is not None:
                        home_odds = float(best_under)
                    if threshold is None and best_line is not None:
                        threshold = float(best_line)
            except Exception:
                pass
    if not away_odds or not home_odds or threshold is None:
        return None
    # NBA API REMOVED - Team stats not available
    away_log = []
    home_log = []
    away_outcomes = []
    home_outcomes = []
    combined = []  # No team game log data available
    engine = EnhancedValueEngine()
    a_stats = None
    h_stats = None
    ms = getattr(match, "match_stats", None)
    if ms and ms.away_team_stats and ms.home_team_stats:
        a_raw = ms.away_team_stats
        h_raw = ms.home_team_stats
        a_stats = EnhancedTeamStats(
            team_name=away_team,
            avg_points_for=a_raw.avg_points_for,
            avg_points_against=a_raw.avg_points_against,
            avg_total_points=a_raw.avg_total_points,
            favorite_win_pct=a_raw.favorite_win_pct,
            underdog_win_pct=a_raw.underdog_win_pct,
            clutch_win_pct=a_raw.clutch_win_pct
        )
        h_stats = EnhancedTeamStats(
            team_name=home_team,
            avg_points_for=h_raw.avg_points_for,
            avg_points_against=h_raw.avg_points_against,
            avg_total_points=h_raw.avg_total_points,
            favorite_win_pct=h_raw.favorite_win_pct,
            underdog_win_pct=h_raw.underdog_win_pct,
            clutch_win_pct=h_raw.clutch_win_pct
        )
    over_enh = engine.analyze_with_team_stats(
        historical_outcomes=combined,
        bookmaker_odds=away_odds,
        team_a_stats=a_stats,
        team_b_stats=h_stats,
        market_type="total",
        market_line=threshold
    )
    under_enh = engine.analyze_with_team_stats(
        historical_outcomes=[1 - o for o in combined] if combined else [],
        bookmaker_odds=home_odds,
        team_a_stats=h_stats,
        team_b_stats=a_stats,
        market_type="total",
        market_line=threshold
    )
    pick = "Over" if over_enh.value_percentage > under_enh.value_percentage else "Under"
    chosen = over_enh if pick == "Over" else under_enh
    return {
        "type": "totals",
        "threshold": threshold,
        "over_odds": away_odds,
        "under_odds": home_odds,
        "pick": pick,
        "analysis": chosen.to_dict()
    }


def _parse_prop(selection_text: str) -> Optional[Dict]:
    s = selection_text.strip()
    lower = s.lower()
    side = "over" if "over" in lower else ("under" if "under" in lower else None)
    if not side:
        return None
    nums = []
    buf = ""
    for ch in s:
        if ch.isdigit() or ch in ".-+":
            buf += ch
        else:
            if buf:
                nums.append(buf)
                buf = ""
    if buf:
        nums.append(buf)
    threshold = None
    for n in nums:
        try:
            threshold = float(n)
            break
        except:
            continue
    if threshold is None:
        return None
    parts = s.split()
    player_name = []
    for w in parts:
        if w.lower() in ["over", "under", "points", "pts", "reb", "rebounds", "ast", "assists", "pra", "3pm", "threes"]:
            break
        player_name.append(w)
    name = " ".join(player_name).strip()
    stat = None
    if "point" in lower or "pts" in lower:
        stat = "points"
    elif "reb" in lower:
        stat = "rebounds"
    elif "ast" in lower:
        stat = "assists"
    elif "pra" in lower:
        stat = "pra"
    elif "3pm" in lower or "three" in lower:
        stat = "three_pt_made"
    if not stat or not name:
        return None
    return {"name": name, "stat": stat, "threshold": threshold, "side": side}


def _get_match_lineup_players(lineups, away_team: str, home_team: str) -> List[str]:
    names = []
    if not lineups:
        return names
    lineup = find_lineup_for_matchup(lineups, away_team, home_team)
    if not lineup:
        return names
    for p in lineup.away_team.starters + lineup.away_team.bench_news:
        names.append(p.name)
    for p in lineup.home_team.starters + lineup.home_team.bench_news:
        names.append(p.name)
    return [n.strip() for n in names if n]


def _analyze_player_props(match, lineups=None, no_api: bool = False) -> List[Dict]:
    results = []
    props = match.get_props()
    if not props:
        return results
    roster_names = _get_match_lineup_players(lineups, match.away_team, match.home_team)
    for m in props:
        info = _parse_prop(m.selection_text or "")
        if not info:
            continue
        if info["stat"] not in ["points", "rebounds", "assists", "three_pt_made"]:
            continue
        name = info["name"]
        if roster_names and name not in roster_names:
            continue
        threshold = info["threshold"]
        side = info["side"]
        if no_api:
            continue

        # Dynamic sample sizing - get maximum available games first
        from sample_size_optimizer import calculate_optimal_sample_size, get_season_stage

        full_log = get_player_game_log(name, last_n_games=40, retries=1)
        if not full_log:
            continue

        # Extract recent stat values for consistency check
        stat_field = info["stat"]
        recent_values = []
        for g in full_log[:15]:  # Use last 15 for variance calc
            if stat_field == "points":
                recent_values.append(g.points)
            elif stat_field == "rebounds":
                recent_values.append(g.rebounds)
            elif stat_field == "assists":
                recent_values.append(g.assists)
            elif stat_field == "three_pt_made":
                recent_values.append(g.three_pt_made)

        # Calculate optimal sample size
        optimal_n, reasoning = calculate_optimal_sample_size(
            player_name=name,
            available_games=len(full_log),
            recent_stats=recent_values,
            season_stage=None  # Auto-detect
        )

        if optimal_n == 0:
            logger.info(f"Skipping {name} {stat_field}: {reasoning}")
            continue

        # Use optimal sample
        log = full_log[:optimal_n]
        logger.info(f"{name} {stat_field}: {reasoning}")

        # Calculate outcomes
        outcomes = []
        stat_values = []  # Store actual values for filtering
        for g in log:
            if info["stat"] == "points":
                outcomes.append(1 if g.points >= threshold else 0)
                stat_values.append(g.points)
            elif info["stat"] == "rebounds":
                outcomes.append(1 if g.rebounds >= threshold else 0)
                stat_values.append(g.rebounds)
            elif info["stat"] == "assists":
                outcomes.append(1 if g.assists >= threshold else 0)
                stat_values.append(g.assists)
            elif info["stat"] == "three_pt_made":
                outcomes.append(1 if g.three_pt_made >= threshold else 0)
                stat_values.append(g.three_pt_made)
        if not outcomes:
            continue
        if side == "under":
            outcomes = [1 - o for o in outcomes]

        # Determine player's team and opponent for defensive context
        from nba_stats_api_scraper import get_opponent_defensive_context

        team_name = None
        if name in _get_match_lineup_players(lineups, match.away_team, None):
            team_name = match.away_team
            opponent_team = match.home_team
        elif name in _get_match_lineup_players(lineups, None, match.home_team):
            team_name = match.home_team
            opponent_team = match.away_team
        else:
            opponent_team = None

        # Get opponent defensive context
        opp_def_context = None
        if opponent_team and not no_api:
            opp_def_context = get_opponent_defensive_context(
                opponent_team=_normalize_team_name(opponent_team),
                player_position="SG",  # Placeholder - would need position mapping
                season="2024-25"
            )

        # Calculate current season games (2024-25 season started Oct 2024)
        from value_engine_enhanced import player_prop_sample_weight
        current_season_start = datetime(2024, 10, 1)
        current_season_games = 0
        for g in log:
            try:
                game_date = datetime.strptime(g.game_date, "%Y-%m-%d")
                if game_date >= current_season_start:
                    current_season_games += 1
            except Exception:
                pass

        # Apply player prop sample weight with current season awareness
        prop_weight_info = player_prop_sample_weight(
            current_season_games=current_season_games,
            historical_games=len(log)
        )

        logger.info(f"  Sample weighting: {current_season_games} current season / {len(log)} historical")
        logger.info(f"  → Weight: {prop_weight_info['sample_weight']:.3f}, Cap: {prop_weight_info['confidence_cap']:.2f}")
        logger.info(f"  → {prop_weight_info['recommendation']}: {prop_weight_info['reason']}")

        # PROJECTION MODEL (PRIMARY SIGNAL - 70% weight)
        projection_model = PlayerProjectionModel()
        projection = projection_model.project_stat(
            player_name=name,
            stat_type=stat_field,
            game_log=log,
            prop_line=threshold,
            opponent_team=opponent_team,
            player_team=team_name,
            team_stats=match.match_stats if hasattr(match, 'match_stats') else None,
            min_games=5
        )

        # HISTORICAL ANALYSIS (SECONDARY SIGNAL - 30% weight)
        engine = EnhancedValueEngine()
        days = []
        for g in log:
            try:
                d = datetime.strptime(g.game_date, "%Y-%m-%d")
                days.append((datetime.now() - d).days)
            except Exception:
                days.append(None)
        enh = engine.analyze_with_team_stats(
            historical_outcomes=outcomes,
            bookmaker_odds=m.odds,
            market_type="prop",
            days_ago=days,
            confidence_cap=prop_weight_info['confidence_cap']
        )

        # Adjust probability based on opponent defense
        if opp_def_context:
            def_adjustment = 0.0
            def_rating = opp_def_context.get("def_rating", 110.0)

            if def_rating < 108:  # Top 10 defense
                def_adjustment = -0.03  # Reduce probability by 3%
            elif def_rating > 114:  # Bottom 10 defense
                def_adjustment = +0.03  # Increase probability by 3%

            # Apply adjustment to historical probability
            adjusted_prob = enh.historical_probability + def_adjustment
            enh.historical_probability = max(0.0, min(1.0, adjusted_prob))

            # Recalculate dependent metrics
            enh.value_percentage = (enh.historical_probability - enh.bookmaker_probability) * 100
            enh.ev_per_unit = (enh.historical_probability * enh.bookmaker_odds) - 1

            logger.info(f"  Opponent defense adjustment: {def_adjustment:+.1%} (DEF RTG: {def_rating:.1f})")

        # COMBINE PROJECTION (70%) + HISTORICAL (30%)
        final_prob = enh.historical_probability
        final_confidence = enh.confidence_score
        
        if projection:
            projection_prob = projection.probability_over_line
            historical_prob = enh.historical_probability
            
            # For "under" bets, flip the probability
            if side == "under":
                projection_prob = 1.0 - projection_prob
                historical_prob = 1.0 - historical_prob
            
            # Combined probability
            final_prob = 0.7 * projection_prob + 0.3 * historical_prob
            
            # Use projection confidence as primary, but blend with historical confidence
            projection_confidence = projection.confidence_score
            historical_confidence = enh.confidence_score
            final_confidence = 0.7 * projection_confidence + 0.3 * historical_confidence
            
            # Update enhanced analysis with combined probability
            enh.historical_probability = final_prob
            enh.confidence_score = final_confidence
            
            # Recalculate value metrics
            enh.bookmaker_probability = 1.0 / m.odds
            enh.value_percentage = (final_prob - enh.bookmaker_probability) * 100
            enh.ev_per_unit = (final_prob * m.odds) - 1
            enh.ev_per_100 = enh.ev_per_unit * 100
            
            logger.info(f"  Projection: {projection_prob:.3f}, Historical: {historical_prob:.3f}, Final: {final_prob:.3f}")
            logger.info(f"  Projection confidence: {projection_confidence:.0f}, Final confidence: {final_confidence:.0f}")
        else:
            logger.info(f"  Projection model unavailable, using historical only")

        # Use player prop sample weight (accounts for current season games)
        sample_weight = prop_weight_info['sample_weight']
        risk_adjusted = enh.ev_per_100 * sample_weight

        # Skip if insufficient current season sample
        if prop_weight_info['recommendation'] == 'SKIP':
            logger.info(f"✗ Skipped {name} {info['stat']} {side}: {prop_weight_info['reason']}")
            continue

        # Apply quality filtering
        from prop_filters import PropFilter

        prop_filter = PropFilter()

        # Prepare prop data for filtering
        prop_data = {
            "player": name,
            "outcomes": outcomes,
            "analysis": enh.to_dict()
        }

        # Apply filters
        passes, filter_results = prop_filter.filter_prop(
            prop_data=prop_data,
            stat_values=stat_values,
            lineups=lineups,
            team_name=team_name
        )

        if not passes:
            logger.info(f"✗ Filtered out {name} {info['stat']} {side}: {filter_results.get('filtered_by', 'unknown')}")
            continue

        logger.info(f"✓ Selected {name} {info['stat']} {side}: {filter_results.get('edge_quality', 'passed')}")

        # Determine recommendation and confidence tier
        ev_pct = enh.value_percentage
        confidence = enh.confidence_score

        recommendation = "BET" if passes and ev_pct > 5.0 else "SKIP"
        confidence_tier = "HIGH" if confidence > 70 else "MEDIUM" if confidence > 50 else "LOW"

        # Create enhanced result with all context
        result = {
            "type": "prop",
            "player": name,
            "stat": info["stat"],
            "side": side,
            "threshold": threshold,
            "odds": m.odds,

            # Core analysis
            "analysis": enh.to_dict(),
            "risk_adjusted_ev_per_100": risk_adjusted,
            "sample_weight": sample_weight,

            # Sample details
            "sample_size": len(log),
            "current_season_games": current_season_games,
            "sample_reasoning": reasoning,
            "season_stage": get_season_stage(),
            "sample_weight_info": {
                "current_season_weight": prop_weight_info['current_season_weight'],
                "historical_weight": prop_weight_info['historical_weight'],
                "confidence_cap": prop_weight_info['confidence_cap'],
                "recommendation": prop_weight_info['recommendation'],
                "reason": prop_weight_info['reason']
            },

            # Filter results
            "filter_results": filter_results,
            "consistency_score": filter_results.get("consistency_score", 0.0),
            "expected_minutes": filter_results.get("expected_minutes", 0.0),

            # Opponent context
            "opponent": opponent_team if opponent_team else "Unknown",
            "opponent_defense": opp_def_context,

            # Projection model details (if available)
            "projection": {
                "expected_value": round(projection.expected_value, 1) if projection else None,
                "projected_prob": round(projection.probability_over_line, 3) if projection else None,
                "historical_prob": round(enh.historical_probability, 3),
                "final_prob": round(final_prob, 3) if projection else round(enh.historical_probability, 3),
                "std_dev": round(projection.std_dev, 2) if projection else None,
                "confidence": round(projection.confidence_score, 0) if projection else None,
                "minutes_projected": round(projection.minutes_projection.projected_minutes, 1) if projection and projection.minutes_projection else None,
                "pace_multiplier": round(projection.matchup_adjustments.pace_multiplier, 3) if projection and projection.matchup_adjustments else None,
                "defense_adjustment": round(projection.matchup_adjustments.defense_adjustment, 3) if projection and projection.matchup_adjustments else None,
                "role_change_detected": projection.role_change.detected if projection and projection.role_change else False,
                "distribution_type": projection.distribution_type if projection else None
            } if projection else None,

            # Recommendation
            "recommendation": recommendation,
            "confidence_tier": confidence_tier
        })
    return results


def _collect_context(match, no_api: bool = False) -> Dict:
    away = _normalize_team_name(match.away_team)
    home = _normalize_team_name(match.home_team)
    # NBA API REMOVED - Team pace and advanced stats not available
    pace = {"team_pace": 0.0, "opponent_pace": 0.0, "tempo_diff": 0.0}
    home_adv = None
    away_adv = None
    return {
        "pace": pace,
        "home_team_adv": home_adv.__dict__ if home_adv else None,
        "away_team_adv": away_adv.__dict__ if away_adv else None,
    }


def run(max_matches: int = 3, headless: bool = True, no_api: bool = False) -> Dict:
    overview = scrape_nba_overview(headless=headless)
    lineups = []
    try:
        lineups = scrape_rotowire_lineups(headless=headless)
    except Exception:
        lineups = []
    results = []
    for g in overview[:max_matches]:
        m = scrape_match_complete(g["url"], headless=headless)
        if not m:
            continue
        r = {"match": {"away_team": m.away_team, "home_team": m.home_team, "url": m.url}}
        r["predictions"] = []
        ml = _analyze_moneyline(m, headless, no_api=no_api)
        if ml:
            r["predictions"].append(ml)
        tot = _analyze_totals(m, no_api=no_api)
        if tot:
            r["predictions"].append(tot)
        props = _analyze_player_props(m, lineups=lineups, no_api=no_api)
        if no_api and (not props or len(props) == 0) and hasattr(m, 'match_insights') and m.match_insights:
            # Build props from insights
            built_props = []
            for ins in m.match_insights:
                fact = ins.fact or ""
                f = fact.lower()
                import re
                # Only consider player prop markets
                mk = (ins.market or "").lower()
                if not any(k in mk for k in ["points", "rebounds", "assists", "threes", "to record", "to score"]):
                    continue
                mm = re.search(r"(\d+)\s+of\s+(?:his|their)\s+last\s+(\d+)", f)
                if not mm:
                    mm = re.search(r"each\s+of\s+(?:his|their)\s+last\s+(\d+)", f)
                    if mm:
                        hits = int(mm.group(1))
                        total = hits
                    else:
                        continue
                else:
                    hits = int(mm.group(1))
                    total = int(mm.group(2))
                outcomes = [1]*hits + [0]*(max(0, total - hits))
                stat = None
                threshold = None
                sm = re.search(r"(\d+\+?|\d+\s+or\s+more)\s+(points|rebounds|assists|threes)", f)
                if sm:
                    thr_txt = sm.group(1)
                    stat_word = sm.group(2)
                    stat = 'three_pt_made' if stat_word == 'threes' else stat_word
                    try:
                        threshold = int(re.search(r"\d+", thr_txt).group(0))
                    except:
                        threshold = None
                if ins.odds and outcomes:
                    engine = EnhancedValueEngine()
                    enh = engine.analyze_with_team_stats(
                        historical_outcomes=outcomes,
                        bookmaker_odds=ins.odds,
                        market_type='prop'
                    )
                    built_props.append({
                        'type': 'prop',
                        'player': None,
                        'stat': stat,
                        'side': ins.result or None,
                        'threshold': threshold,
                        'odds': ins.odds,
                        'analysis': enh.to_dict(),
                        'risk_adjusted_ev_per_100': enh.ev_per_100 * enh.sample_weight,
                        'sample_weight': enh.sample_weight
                    })
            if built_props:
                props = built_props
        if props:
            r["predictions"].extend(props)
        r["context"] = _collect_context(m, no_api=no_api)
        results.append(r)
    # Calculate summary statistics
    from sample_size_optimizer import get_season_stage
    import numpy as np

    all_props = []
    for r in results:
        all_props.extend([p for p in r.get("predictions", []) if p.get("type") == "prop"])

    bet_props = [p for p in all_props if p.get("recommendation") == "BET"]
    skip_props = [p for p in all_props if p.get("recommendation") == "SKIP"]

    summary = {
        "total_props_analyzed": len(all_props),
        "props_recommended": len(bet_props),
        "props_filtered": len(skip_props),
        "selectivity_pct": (len(skip_props) / len(all_props) * 100) if all_props else 0,
        "avg_ev_of_bets": float(np.mean([p["analysis"]["ev_per_unit"] for p in bet_props])) if bet_props else 0,
        "avg_confidence_of_bets": float(np.mean([p["analysis"]["confidence_score"] for p in bet_props])) if bet_props else 0,
        "season_stage": get_season_stage()
    }

    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY: {len(bet_props)}/{len(all_props)} props recommended ({summary['selectivity_pct']:.1f}% filtered)")
    logger.info(f"Avg EV: {summary['avg_ev_of_bets']:.3f} | Avg Confidence: {summary['avg_confidence_of_bets']:.1f}")
    logger.info(f"Season: {summary['season_stage']}")
    logger.info(f"{'='*60}\n")

    out_dir = Path(__file__).parent.parent / "data" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    fn = out_dir / f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "results": results
        }, f, indent=2)
    return {"file": str(fn), "count": len(results), "summary": summary}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--max", type=int, default=3)
    p.add_argument("--headless", type=str, default="y")
    p.add_argument("--no_api", type=str, default="n")
    p.add_argument("--odds_key", type=str, default="")
    args = p.parse_args()
    headless = args.headless.strip().lower() != "n"
    no_api = args.no_api.strip().lower() == "y"
    if args.odds_key:
        globals()["_ODDS_API_KEY"] = args.odds_key
    res = run(max_matches=args.max, headless=headless, no_api=no_api)
    print(json.dumps(res, indent=2))
def _select_odds_event(data, away_team: str, home_team: str):
    at = _normalize_team_name(away_team).lower()
    ht = _normalize_team_name(home_team).lower()
    now = datetime.utcnow()
    chosen = None
    chosen_bm_count = -1
    for ev in data:
        ct = ev.get('commence_time')
        try:
            ev_time = datetime.fromisoformat(ct.replace('Z', '+00:00')) if ct else None
        except Exception:
            ev_time = None
        if ev_time and ev_time < now - timedelta(hours=24):
            continue
        if ev_time and ev_time > now + timedelta(days=7):
            continue
        a = (ev.get('away_team') or '').lower()
        h = (ev.get('home_team') or '').lower()
        if at in a and ht in h:
            bm_count = len(ev.get('bookmakers', []))
            if bm_count > chosen_bm_count:
                chosen = ev
                chosen_bm_count = bm_count
    return chosen