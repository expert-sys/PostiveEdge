"""
Complete Sportsbet Analysis Pipeline with Lineup Intelligence
==============================================================
Enhanced scraper that combines Sportsbet odds with NBA.com schedule and lineup data.

This is the complete integration:
1. Scrapes NBA.com for schedule and lineup/injury data (injury status, starters, questionable players)
2. Scrapes NBA games from Sportsbet
3. Extracts betting markets and match insights
4. Cross-references lineup data with betting insights
5. Analyzes each insight with Value Engine
6. Identifies value bets with injury impact context

Features:
- Real-time schedule, lineup and injury data from NBA.com
- Historical performance insights from Sportsbet
- Implied probability and EV calculations
- Injury impact warnings for each game
- Comprehensive value bet analysis

Usage:
  python sportsbet_complete_analysis.py
  python sportsbet_complete_analysis.py 5  # Analyze 5 games
  python sportsbet_complete_analysis.py all  # Analyze all games
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("sportsbet_complete_analysis")

from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
from scrapers.insights_to_value_analysis import analyze_all_insights, print_analysis_report
from scrapers.nba_lineup_scraper import scrape_nba_lineups, find_lineup_for_matchup, get_injury_impact_summary
from scrapers.nba_schedule_scraper import scrape_nba_schedule, find_game_by_teams, get_final_games, get_upcoming_games, get_live_games
from scrapers.context_aware_analysis import ContextAwareAnalyzer

# Initialize NBA player cache on startup (ensures cache directory exists)
try:
    from scrapers.nba_player_cache import initialize_cache
    initialize_cache()
except ImportError:
    pass  # Cache module optional


def main():
    # Initialize NBA player cache early (shows progress if building)
    try:
        from scrapers.nba_player_cache import get_player_cache
        _ = get_player_cache()  # Initialize cache (will build if needed)
    except Exception as e:
        logger.debug(f"Player cache initialization: {e}")
    
    print("\n" + "="*70)
    print("  COMPLETE SPORTSBET ANALYSIS + LINEUP INTELLIGENCE")
    print("="*70)
    print("\nThis pipeline:")
    print("  1. Scrapes NBA.com for schedule and lineup/injury data")
    print("  2. Scrapes NBA games from Sportsbet")
    print("  3. Extracts betting markets and match insights")
    print("  4. Cross-references NBA.com context with insights")
    print("  5. Analyzes insights with Value Engine")
    print("  6. Identifies value bets with injury impact awareness")
    print()

    # Get number of games to analyze
    if len(sys.argv) > 1:
        max_games = int(sys.argv[1])
    else:
        # Interactive prompt
        print("How many games would you like to analyze?")
        print("  - Enter a number (e.g., 3, 5, 10)")
        print("  - Enter 'all' to analyze all available games")
        print("  - Press Enter for default (5 games)")
        choice = input("\nYour choice: ").strip().lower()

        if choice == 'all':
            max_games = 999  # Will be limited by actual games available
        elif choice == '' or choice == '0':
            max_games = 5  # Default
        else:
            try:
                max_games = int(choice)
            except ValueError:
                print("Invalid input, using default of 5 games")
                max_games = 5

    # Step 1: Get NBA.com Schedule and Lineups (for injury/lineup context)
    from datetime import datetime, timedelta
    
    # Get tomorrow's date for filtering
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("Step 1: Getting schedule and lineup data from NBA.com...\n")
    print(f"  Checking schedule for today ({today}) and tomorrow ({tomorrow})...")
    
    # Get schedule for today and tomorrow
    nba_schedule_today = scrape_nba_schedule(headless=True, date=today)
    nba_schedule_tomorrow = scrape_nba_schedule(headless=True, date=tomorrow)
    nba_schedule = nba_schedule_today + nba_schedule_tomorrow
    
    # Filter to only upcoming games (exclude FINAL games)
    upcoming_nba_games = get_upcoming_games(nba_schedule) if nba_schedule else []
    live_nba_games = get_live_games(nba_schedule) if nba_schedule else []
    valid_nba_games = upcoming_nba_games + live_nba_games
    
    nba_lineups = scrape_nba_lineups(headless=True)
    print(f"[OK] Retrieved schedule data for {len(nba_schedule)} total games")
    print(f"[OK] Found {len(valid_nba_games)} upcoming/live games (excluding FINAL)")
    print(f"[OK] Retrieved lineup data for {len(nba_lineups)} games")
    
    if len(valid_nba_games) == 0:
        print(f"[WARNING] No scheduled games found in NBA.com schedule!")
        print(f"  This might mean:")
        print(f"  - NBA.com scraper needs adjustment")
        print(f"  - No games scheduled for today/tomorrow")
        print(f"  - Will proceed with Sportsbet games but cannot verify schedule\n")
    else:
        print()

    # Step 2: Get NBA games from Sportsbet
    print("Step 2: Getting NBA games from Sportsbet...\n")
    games = scrape_nba_overview(headless=True)

    if not games:
        print("Failed to get games")
        return

    # Step 2.5: Filter Sportsbet games to only include games that are actually scheduled
    print("Step 2.5: Filtering games to only include scheduled matches...\n")
    filtered_games = []
    
    # If we have NBA schedule data, use it for filtering
    # Otherwise, we'll proceed with all Sportsbet games but warn the user
    use_schedule_filter = len(valid_nba_games) > 0
    failed_matches = []  # Track failed team matches for logging

    for game in games:
        away = game.get('away_team', '')
        home = game.get('home_team', '')

        if use_schedule_filter:
            # Check if this game exists in NBA schedule as upcoming/live
            schedule_game = find_game_by_teams(valid_nba_games, away, home)

            if schedule_game:
                # Game is scheduled and upcoming/live - include it
                game['nba_schedule_status'] = schedule_game.status
                game['nba_game_time'] = schedule_game.game_time
                game['nba_game_date'] = schedule_game.game_date
                filtered_games.append(game)
                print(f"  ✓ {away} @ {home} - Scheduled ({schedule_game.status})")

                # Log team name mapping for debugging
                logger.debug(
                    f"Team match: Sportsbet '{away}' / '{home}' → "
                    f"NBA '{schedule_game.away_team_abbr}' / '{schedule_game.home_team_abbr}'"
                )
            else:
                # Check if it's a FINAL game (should be excluded)
                final_game = find_game_by_teams(nba_schedule, away, home) if nba_schedule else None
                if final_game and final_game.status == "FINAL":
                    print(f"  ✗ {away} @ {home} - FINAL (excluded)")
                else:
                    # Game not found in NBA schedule - might be old or invalid
                    print(f"  ⚠ {away} @ {home} - Not found in NBA schedule (excluded)")
                    failed_matches.append(f"{away} @ {home}")
                    logger.warning(
                        f"Team name matching failed: Sportsbet game '{away} @ {home}' "
                        f"not found in NBA schedule"
                    )
        else:
            # No NBA schedule data - include all games but warn
            filtered_games.append(game)
            print(f"  ⚠ {away} @ {home} - Included (NBA schedule unavailable for verification)")

    # Summary of failed matches
    if failed_matches:
        logger.warning(f"Failed to match {len(failed_matches)} Sportsbet games to NBA schedule:")
        for match in failed_matches[:5]:  # Show first 5
            logger.warning(f"  - {match}")
        if len(failed_matches) > 5:
            logger.warning(f"  ... and {len(failed_matches) - 5} more")
    
    if not filtered_games:
        print("\n[WARNING] No games to analyze!")
        print("This could mean:")
        print("  - No games scheduled for today/tomorrow")
        print("  - NBA schedule scraper needs adjustment")
        print("  - Team name matching issues")
        print("  - Sportsbet scraper returned no games")
        return
    
    if not use_schedule_filter:
        print(f"\n[WARNING] NBA schedule data unavailable - cannot verify games are actually scheduled.")
        print(f"  Proceeding with {len(filtered_games)} games from Sportsbet, but they may include old/finished games.")
        print(f"  Please verify manually that these games are actually scheduled for today/tomorrow.\n")
    
    games_to_analyze = filtered_games[:max_games]
    print(f"\n[OK] Found {len(games)} total games on Sportsbet")
    print(f"[OK] Filtered to {len(filtered_games)} scheduled games")
    print(f"[OK] Will analyze {len(games_to_analyze)} game(s)\n")

    if len(games_to_analyze) > 0:
        print("Games to analyze:")
        for i, game in enumerate(games_to_analyze, 1):
            away = game.get('away_team', 'N/A')
            home = game.get('home_team', 'N/A')
            print(f"  {i}. {away} @ {home}")

            # Show lineup status if available
            lineup_data = find_lineup_for_matchup(nba_lineups, away, home)
            if lineup_data:
                impact = get_injury_impact_summary(lineup_data)
                if impact['away_team']['out_count'] > 0 or impact['home_team']['out_count'] > 0:
                    print(f"      [!] Injuries: {impact['away_team']['out_count']} ({away}), {impact['home_team']['out_count']} ({home})")
            
            # Show game status from schedule
            schedule_game = find_game_by_teams(nba_schedule, away, home)
            if schedule_game:
                status_icon = "✓" if schedule_game.status == "FINAL" else "⏰" if schedule_game.status == "UPCOMING" else "🔴"
                print(f"      {status_icon} Status: {schedule_game.status}")
                if schedule_game.status == "FINAL" and schedule_game.away_score is not None:
                    print(f"      Score: {schedule_game.away_team_abbr} {schedule_game.away_score} - {schedule_game.home_team_abbr} {schedule_game.home_score}")
                elif schedule_game.game_time:
                    print(f"      Time: {schedule_game.game_time}")
        print()

    # Step 2 & 3: Scrape each game and analyze
    all_results = []

    for i, game in enumerate(games_to_analyze, 1):
        print("="*70)
        print(f"[{i}/{len(games_to_analyze)}] {game['away_team']} @ {game['home_team']}")
        print("="*70)

        try:
            # Get lineup data for this game
            lineup_data = find_lineup_for_matchup(
                nba_lineups,
                game['away_team'],
                game['home_team']
            )
            
            # Get schedule data for this game
            schedule_game = find_game_by_teams(
                nba_schedule,
                game['away_team'],
                game['home_team']
            )

            # Show schedule context
            if schedule_game:
                status_icon = "✓" if schedule_game.status == "FINAL" else "⏰" if schedule_game.status == "UPCOMING" else "🔴"
                print(f"\n[SCHEDULE] {status_icon} {schedule_game.status}")
                if schedule_game.status == "FINAL" and schedule_game.away_score is not None:
                    print(f"  Score: {schedule_game.away_team_abbr} {schedule_game.away_score} - {schedule_game.home_team_abbr} {schedule_game.home_score}")
                elif schedule_game.game_time:
                    print(f"  Time: {schedule_game.game_time}")
            
            # Show lineup context
            if lineup_data:
                impact = get_injury_impact_summary(lineup_data)
                print(f"\n[LINEUP] Context (from NBA.com):")
                print(f"  {impact['away_team']['team']}: {len(impact['away_team']['key_injuries'])} out, {impact['away_team']['questionable_count']} questionable")
                print(f"  {impact['home_team']['team']}: {len(impact['home_team']['key_injuries'])} out, {impact['home_team']['questionable_count']} questionable")

                if impact['high_impact']:
                    print(f"  [!] HIGH INJURY IMPACT GAME")

                # Show key injuries
                if impact['away_team']['key_injuries']:
                    print(f"\n  {impact['away_team']['team']} Key Injuries:")
                    for injury in impact['away_team']['key_injuries']:
                        print(f"    - {injury}")

                if impact['home_team']['key_injuries']:
                    print(f"\n  {impact['home_team']['team']} Key Injuries:")
                    for injury in impact['home_team']['key_injuries']:
                        print(f"    - {injury}")

            # Scrape complete match data
            match_data = scrape_match_complete(game['url'], headless=True)

            if not match_data:
                print("  Failed to scrape match\n")
                continue

            print(f"\n[DATA] Extracted from Sportsbet:")
            print(f"  - {len(match_data.all_markets)} betting markets")
            print(f"  - {len(match_data.match_insights)} match insights")
            if match_data.match_stats:
                print(f"  - Team statistics (Records, Performance, Under Pressure)")

            # Display match stats if available
            if match_data.match_stats:
                stats = match_data.match_stats
                away_stats = stats.away_team_stats
                home_stats = stats.home_team_stats

                print(f"\n[STATS] {stats.data_range}:")
                print(f"  {away_stats.team_name} (Away) vs {home_stats.team_name} (Home)")

                if away_stats.avg_points_for and home_stats.avg_points_for:
                    print(f"  Points For: {away_stats.avg_points_for:.1f} | {home_stats.avg_points_for:.1f}")
                if away_stats.favorite_win_pct and home_stats.favorite_win_pct:
                    print(f"  Favorite %: {away_stats.favorite_win_pct:.1f}% | {home_stats.favorite_win_pct:.1f}%")
                if away_stats.clutch_win_pct and home_stats.clutch_win_pct:
                    print(f"  Clutch Win: {away_stats.clutch_win_pct:.1f}% | {home_stats.clutch_win_pct:.1f}%")

            if not match_data.match_insights:
                print("  No insights to analyze\n")
                continue

            # Create context from lineup data
            from scrapers.context_aware_analysis import ContextFactors

            lineup_ctx = None
            if lineup_data and impact:
                lineup_ctx = ContextFactors(
                    injury_impact="HIGH" if impact['high_impact'] else
                                  "MODERATE" if impact['total_injuries'] > 1 else "LOW",
                    home_away="AWAY" if game['away_team'] in lineup_data.away_team.team_name else "HOME"
                )

            # Analyze insights with Context-Aware Engine
            print(f"\n[ANALYSIS] Analyzing insights with Context-Aware Engine...")

            insights_dicts = [
                {
                    'fact': insight.fact,
                    'market': insight.market,
                    'result': insight.result,
                    'odds': insight.odds,
                    'tags': insight.tags,
                    'icon': insight.icon
                }
                for insight in match_data.match_insights
            ]

            analyzed = analyze_all_insights(
                insights_dicts,
                minimum_sample_size=5,
                lineup_context=lineup_ctx,
                home_team=game['home_team'],
                away_team=game['away_team']
            )

            value_count = sum(1 for a in analyzed if a['analysis']['has_value'])
            print(f"  [OK] Analyzed: {len(analyzed)} insights")
            print(f"  [OK] Value bets found: {value_count}")

            # Show breakdown by recommendation
            recommendations = {}
            for a in analyzed:
                rec = a['analysis']['recommendation']
                recommendations[rec] = recommendations.get(rec, 0) + 1

            print(f"  [OK] Breakdown: ", end="")
            for rec, count in sorted(recommendations.items()):
                print(f"{rec}={count} ", end="")
            print()

            # Store results with lineup context and match stats
            game_result = {
                'game_info': game,
                'lineup_data': lineup_data.to_dict() if lineup_data else None,
                'injury_impact': impact if lineup_data else None,
                'match_data': {
                    'away_team': match_data.away_team,
                    'home_team': match_data.home_team,
                    'total_markets': len(match_data.all_markets),
                    'total_insights': len(match_data.match_insights)
                },
                'match_stats': match_data.match_stats.to_dict() if match_data.match_stats else None,
                'analyzed_insights': analyzed
            }

            all_results.append(game_result)

            # Show top value bet for this game (ranked by confidence score - highest first)
            value_bets = [a for a in analyzed if a['analysis']['has_value']]
            if value_bets:
                value_bets.sort(key=lambda x: x['analysis'].get('confidence_score', 0), reverse=True)
                top = value_bets[0]
                print(f"\n  TOP VALUE BET (Highest Confidence):")
                print(f"    {top['insight']['fact'][:70]}...")
                confidence = top['analysis'].get('confidence_score', 50)
                odds = top['insight']['odds']
                print(f"    Confidence: {confidence:.0f}/100 | Odds: {odds:.2f}")
                print(f"    Edge: {top['analysis']['value_percentage']:+.1f}% | Sample: n={top['analysis']['sample_size']}")

            print()

            # Throttle between games
            if i < len(games_to_analyze):
                time.sleep(2)

        except Exception as e:
            print(f"  Error: {e}\n")
            import traceback
            traceback.print_exc()
            continue

    # Step 4: Generate comprehensive report
    print("\n" + "="*70)
    print("  COMPLETE ANALYSIS REPORT")
    print("="*70)

    if not all_results:
        print("\nNo games were successfully analyzed\n")
        return

    # Combine all analyzed insights
    all_analyzed_insights = []
    for result in all_results:
        for analyzed in result['analyzed_insights']:
            # Add game context
            analyzed_with_game = analyzed.copy()
            analyzed_with_game['game'] = f"{result['match_data']['away_team']} @ {result['match_data']['home_team']}"
            all_analyzed_insights.append(analyzed_with_game)

    # Deduplication: Remove duplicate bets (keep highest EV)
    print("\n" + "="*70)
    print("  DEDUPLICATION & CORRELATION ENFORCEMENT")
    print("="*70)

    # Group by market+result to find duplicates
    market_groups = {}
    for bet in all_analyzed_insights:
        if not bet['analysis']['has_value']:
            continue
        key = f"{bet['insight']['market']}_{bet['insight']['result']}"
        if key not in market_groups:
            market_groups[key] = []
        market_groups[key].append(bet)

    # Deduplicate: keep only the highest EV for each market
    deduplicated_bets = []
    duplicates_removed = 0
    for key, bets in market_groups.items():
        if len(bets) > 1:
            # Sort by risk-adjusted EV and keep the best
            bets.sort(key=lambda x: x['analysis'].get('risk_adjusted_ev', x['analysis']['ev_per_100']), reverse=True)
            best = bets[0]
            deduplicated_bets.append(best)
            duplicates_removed += len(bets) - 1
            logger.info(f"Removed {len(bets)-1} duplicate(s) for {key} (kept best EV: ${best['analysis']['ev_per_100']:+.2f})")
        else:
            deduplicated_bets.append(bets[0])

    # Add non-value bets back (for reporting purposes)
    for bet in all_analyzed_insights:
        if not bet['analysis']['has_value']:
            deduplicated_bets.append(bet)

    print(f"Duplicates Removed: {duplicates_removed}")

    # Correlation Enforcement: Limit to 3 bets per game
    game_groups = {}
    for bet in deduplicated_bets:
        if not bet['analysis']['has_value']:
            continue
        game = bet['game']
        if game not in game_groups:
            game_groups[game] = []
        game_groups[game].append(bet)

    # Enforce max 3 bets per game
    correlation_limited_bets = []
    bets_limited = 0
    for game, bets in game_groups.items():
        if len(bets) > 3:
            # Sort by risk-adjusted EV and keep top 3
            bets.sort(key=lambda x: x['analysis'].get('risk_adjusted_ev', x['analysis']['ev_per_100']), reverse=True)
            top_3 = bets[:3]
            correlation_limited_bets.extend(top_3)
            bets_limited += len(bets) - 3
            logger.info(f"Limited {game} to 3 bets (removed {len(bets)-3} lower EV bets)")
        else:
            correlation_limited_bets.extend(bets)

    # Add non-value bets back
    for bet in deduplicated_bets:
        if not bet['analysis']['has_value']:
            correlation_limited_bets.append(bet)

    print(f"Bets Limited (correlation): {bets_limited}")
    print(f"Final Value Bets: {sum(1 for b in correlation_limited_bets if b['analysis']['has_value'])}")
    print()

    # Use the filtered list for all subsequent analysis
    all_analyzed_insights = correlation_limited_bets

    # Print comprehensive report
    print_analysis_report(all_analyzed_insights)

    # Save results
    output_dir = Path(__file__).parent.parent / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"complete_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'games_analyzed': len(all_results),
            'total_insights': len(all_analyzed_insights),
            'value_bets_found': sum(1 for a in all_analyzed_insights if a['analysis']['has_value']),
            'results': all_results
        }, f, indent=2, ensure_ascii=False)

    print(f"Complete analysis saved to: {filename}")

    # Summary statistics
    total_insights = len(all_analyzed_insights)
    value_bets = [a for a in all_analyzed_insights if a['analysis']['has_value']]
    total_value_bets = len(value_bets)

    # Show value bets per game
    print("\n" + "="*70)
    print("  VALUE BETS PER GAME")
    print("="*70)
    for result in all_results:
        game_name = f"{result['match_data']['away_team']} @ {result['match_data']['home_team']}"
        game_value_bets = [a for a in result['analyzed_insights'] if a['analysis']['has_value']]
        print(f"{game_name}: {len(game_value_bets)} value bets (out of {len(result['analyzed_insights'])} insights)")

    if value_bets:
        avg_ev = sum(a['analysis']['ev_per_100'] for a in value_bets) / len(value_bets)
        best_ev = max(a['analysis']['ev_per_100'] for a in value_bets)

        # Risk-adjusted metrics
        avg_risk_ev = sum(a['analysis'].get('risk_adjusted_ev', a['analysis']['ev_per_100']) for a in value_bets) / len(value_bets)
        best_risk_ev = max(a['analysis'].get('risk_adjusted_ev', a['analysis']['ev_per_100']) for a in value_bets)

        avg_historical_prob = sum(a['analysis']['historical_probability'] for a in value_bets) / len(value_bets)
        avg_value_pct = sum(a['analysis']['value_percentage'] for a in value_bets) / len(value_bets)
        avg_sample_size = sum(a['analysis']['sample_size'] for a in value_bets) / len(value_bets)
        avg_confidence = sum(a['analysis'].get('confidence_score', 50) for a in value_bets) / len(value_bets)

        print("\n" + "="*70)
        print("  SUMMARY STATISTICS")
        print("="*70)
        print(f"\nGames Analyzed: {len(all_results)}")
        print(f"Total Insights: {total_insights}")
        print(f"Value Bets Found: {total_value_bets} ({total_value_bets/total_insights*100:.1f}%)")
        print(f"\nValue Bet Averages:")
        print(f"  Average Historical Win Rate: {avg_historical_prob*100:.1f}%")
        print(f"  Average Sample Size: {avg_sample_size:.1f} games")
        print(f"  Average Edge: {avg_value_pct:+.1f}%")
        print(f"  Average Confidence: {avg_confidence:.0f}/100")
        print(f"  Average EV: ${avg_ev:+.2f} per $100")
        print(f"  Average Risk-Adjusted EV: ${avg_risk_ev:+.2f} per $100")
        print(f"\nBest Metrics:")
        print(f"  Highest Historical Win Rate: {max(a['analysis']['historical_probability'] for a in value_bets)*100:.1f}%")
        print(f"  Largest Sample Size: {max(a['analysis']['sample_size'] for a in value_bets)} games")
        print(f"  Biggest Edge: {max(a['analysis']['value_percentage'] for a in value_bets):+.1f}%")
        print(f"  Best EV: ${best_ev:+.2f} per $100")
        print(f"  Best Risk-Adjusted EV: ${best_risk_ev:+.2f} per $100")

        # IMPROVEMENT: Fix #7 - Correlation Analysis
        analyzer = ContextAwareAnalyzer()
        correlation_analysis = analyzer.analyze_correlation(value_bets)
        
        if correlation_analysis['correlation_risk'] == 'HIGH':
            print("\n" + "!"*70)
            print("  CORRELATION WARNING: Multiple bets on same games detected")
            print("!"*70)
            for warning in correlation_analysis['warnings']:
                print(f"  ⚠️  {warning}")
            for rec in correlation_analysis['recommendations']:
                print(f"  💡 {rec}")
            print()

        # Top 10 value bets sorted by confidence score (descending = highest confidence first)
        value_bets.sort(key=lambda x: x['analysis'].get('confidence_score', 0), reverse=True)

        print("\n" + "-"*70)
        print("TOP 10 VALUE BETS - RANKED BY CONFIDENCE SCORE (HIGHEST FIRST)")
        print("-"*70)

        for i, bet in enumerate(value_bets[:10], 1):
            analysis = bet['analysis']
            sample_size = analysis['sample_size']

            # Get all enhanced metrics
            confidence_score = analysis.get('confidence_score', 50)
            risk_adjusted_ev = analysis.get('risk_adjusted_ev', analysis['ev_per_100'])
            edge_pct = analysis['value_percentage']
            standard_ev = analysis['ev_per_100']

            # Get component scores
            edge_component = analysis.get('edge_component', 0)
            sample_component = analysis.get('sample_component', 0)
            recency_component = analysis.get('recency_component', 0)

            # Get streak and variance info
            recent_streak = analysis.get('recent_streak', '')
            historical_variance = analysis.get('historical_variance', None)
            sample_weight = analysis.get('sample_weight', 1.0)
            weighted_edge = analysis.get('weighted_edge', edge_pct)

            # Get market variance info
            market_variance = analysis.get('market_variance', {})
            if isinstance(market_variance, dict):
                market_type = market_variance.get('market_type', 'Default')
                confidence_mult = market_variance.get('confidence_multiplier', 1.0)
            else:
                market_type = 'Default'
                confidence_mult = 1.0

            # Bayesian smoothing info
            bayesian_adjusted = analysis.get('bayesian_adjusted', False)
            effective_n = analysis.get('effective_sample_size', sample_size)

            # Create visual bars for edge and confidence (out of 100)
            def make_bar(value, max_val=100, width=20):
                filled = int((value / max_val) * width)
                return '[' + '=' * filled + '-' * (width - filled) + ']'

            edge_bar = make_bar(min(abs(edge_pct), 30), 30, 15)  # Scale edge to 30% max
            confidence_bar = make_bar(confidence_score, 100, 15)

            print(f"\n{i}. {bet.get('game', 'Unknown')}")
            print(f"   {bet['insight']['fact']}")
            print(f"   Market: {bet['insight'].get('market', 'N/A')} | Odds: {bet['insight'].get('odds', 'N/A')}")

            # PRIMARY METRIC: Confidence Score (since we're sorting by this)
            print(f"\n   ⭐ Confidence Score: {confidence_score:.0f}/100 (Sorting Metric) | Sample: n={sample_size}")
            print(f"   💰 Risk-Adjusted EV: ${risk_adjusted_ev:+.2f}/100 (EV ${standard_ev:+.2f})")

            # STAKE GUIDANCE (Kelly Criterion)
            recommended_stake = analysis.get('recommended_stake_pct', 0.0)
            if recommended_stake > 0:
                print(f"   Recommended Stake: {recommended_stake:.2f}% of bankroll")

            # EDGE vs CONFIDENCE VISUALIZATION
            print(f"\n   Edge:       {edge_bar} {edge_pct:+.1f}%")
            print(f"   Confidence: {confidence_bar} {confidence_score:.0f}/100")

            # KEY STATS - Show improved statistical metrics (SPECIFICATION FORMAT)
            raw_freq = analysis.get('raw_historical_frequency', analysis['historical_probability'])
            bayesian_prob = analysis.get('bayesian_probability', analysis['historical_probability'])
            blended_prob = analysis.get('blended_probability', analysis['historical_probability'])
            ci_lower = analysis.get('confidence_interval_lower', None)
            ci_upper = analysis.get('confidence_interval_upper', None)
            kelly_frac = analysis.get('kelly_fraction', 0.0)
            edge_cat = analysis.get('edge_category', 'No edge')

            # SPECIFICATION FORMAT: Probability Estimation
            print(f"\n   Historical Trend: {raw_freq*100:.1f}% (n={sample_size})")
            print(f"   Bayesian Probability: {bayesian_prob*100:.1f}%")
            print(f"   Final Probability: {blended_prob*100:.1f}%")
            if ci_lower and ci_upper:
                print(f"   95% Confidence Interval: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
            
            # SPECIFICATION FORMAT: Edge
            print(f"\n   Edge: {edge_pct:+.2f}% ({edge_cat})")
            
            # SPECIFICATION FORMAT: EV
            # EV % is the percentage return on stake (EV per 100 / 100)
            ev_pct = (standard_ev / 100.0)
            print(f"   EV per 100 units: ${standard_ev:+.2f}")
            print(f"   EV %: {ev_pct:+.2f}%")
            
            if kelly_frac > 0:
                print(f"   Kelly Fraction: {kelly_frac*100:.2f}% of bankroll")
            
            print(f"   Sample Weight: {sample_weight:.2f}")
            if recent_streak:
                print(f"   Streak: {recent_streak}")
            if historical_variance is not None:
                variance_label = "Low" if historical_variance < 0.15 else "Medium" if historical_variance < 0.30 else "High"
                reliability_icon = "[+++]" if variance_label == "Low" else "[++-]" if variance_label == "Medium" else "[+--]"
                print(f"   Reliability: {reliability_icon} {variance_label} Variance")
            if market_type != 'Default' and abs(confidence_mult - 1.0) > 0.05:
                print(f"   Market: {market_type} ({confidence_mult:.2f}x confidence)")

        print("\n" + "="*70)
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
