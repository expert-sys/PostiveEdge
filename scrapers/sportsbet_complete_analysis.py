"""
Complete Sportsbet Analysis Pipeline with Lineup Intelligence
==============================================================
Enhanced scraper that combines Sportsbet odds with RotoWire lineup data.

This is the complete integration:
1. Scrapes RotoWire for lineup/injury data (injury status, starters, questionable players)
2. Scrapes NBA games from Sportsbet
3. Extracts betting markets and match insights
4. Cross-references lineup data with betting insights
5. Analyzes each insight with Value Engine
6. Identifies value bets with injury impact context

Features:
- Real-time lineup and injury data from RotoWire
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
from datetime import datetime
import time

from scrapers.sportsbet_final_enhanced import scrape_nba_overview, scrape_match_complete
from scrapers.insights_to_value_analysis import analyze_all_insights, print_analysis_report
from scrapers.rotowire_scraper import scrape_rotowire_lineups, find_lineup_for_matchup, get_injury_impact_summary


def main():
    print("\n" + "="*70)
    print("  COMPLETE SPORTSBET ANALYSIS + LINEUP INTELLIGENCE")
    print("="*70)
    print("\nThis pipeline:")
    print("  1. Scrapes RotoWire for lineup/injury data")
    print("  2. Scrapes NBA games from Sportsbet")
    print("  3. Extracts betting markets and match insights")
    print("  4. Cross-references lineup context with insights")
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

    # Step 1: Get RotoWire Lineups (for injury/lineup context)
    print("Step 1: Getting lineup data from RotoWire...\n")
    rotowire_lineups = scrape_rotowire_lineups(headless=True)
    print(f"[OK] Retrieved lineup data for {len(rotowire_lineups)} games\n")

    # Step 2: Get NBA games from Sportsbet
    print("Step 2: Getting NBA games from Sportsbet...\n")
    games = scrape_nba_overview(headless=True)

    if not games:
        print("Failed to get games")
        return

    games_to_analyze = games[:max_games]
    print(f"\n[OK] Found {len(games)} games available")
    print(f"[OK] Will analyze {len(games_to_analyze)} game(s)\n")

    if len(games_to_analyze) > 0:
        print("Games to analyze:")
        for i, game in enumerate(games_to_analyze, 1):
            away = game.get('away_team', 'N/A')
            home = game.get('home_team', 'N/A')
            print(f"  {i}. {away} @ {home}")

            # Show lineup status if available
            lineup_data = find_lineup_for_matchup(rotowire_lineups, away, home)
            if lineup_data:
                impact = get_injury_impact_summary(lineup_data)
                if impact['away_team']['out_count'] > 0 or impact['home_team']['out_count'] > 0:
                    print(f"      [!] Injuries: {impact['away_team']['out_count']} ({away}), {impact['home_team']['out_count']} ({home})")
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
                rotowire_lineups,
                game['away_team'],
                game['home_team']
            )

            # Show lineup context
            if lineup_data:
                impact = get_injury_impact_summary(lineup_data)
                print(f"\n[LINEUP] Context:")
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

            analyzed = analyze_all_insights(insights_dicts, minimum_sample_size=4, lineup_context=lineup_ctx)

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

            # Show top value bet for this game (ranked by risk-adjusted EV)
            value_bets = [a for a in analyzed if a['analysis']['has_value']]
            if value_bets:
                value_bets.sort(key=lambda x: x['analysis'].get('risk_adjusted_ev', x['analysis']['ev_per_100']), reverse=True)
                top = value_bets[0]
                print(f"\n  TOP VALUE BET:")
                print(f"    {top['insight']['fact'][:70]}...")
                risk_adj_ev = top['analysis'].get('risk_adjusted_ev', top['analysis']['ev_per_100'])
                print(f"    Risk-Adjusted EV: ${risk_adj_ev:+.2f} per $100")
                print(f"    Edge: {top['analysis']['value_percentage']:+.1f}% | Confidence: {top['analysis'].get('confidence_score', 50):.0f}/100")

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

        # Top 10 value bets sorted by risk-adjusted EV
        value_bets.sort(key=lambda x: x['analysis'].get('risk_adjusted_ev', x['analysis']['ev_per_100']), reverse=True)

        print("\n" + "-"*70)
        print("TOP 10 VALUE BETS - RANKED BY RISK-ADJUSTED EV")
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

            # PRIMARY METRIC: Risk-Adjusted EV
            print(f"\n   Risk-Adjusted EV: ${risk_adjusted_ev:+.2f}/100 (EV ${standard_ev:+.2f} x {confidence_score:.0f}% confidence)")

            # STAKE GUIDANCE (Kelly Criterion)
            recommended_stake = analysis.get('recommended_stake_pct', 0.0)
            if recommended_stake > 0:
                print(f"   Recommended Stake: {recommended_stake:.2f}% of bankroll")

            # EDGE vs CONFIDENCE VISUALIZATION
            print(f"\n   Edge:       {edge_bar} {edge_pct:+.1f}%")
            print(f"   Confidence: {confidence_bar} {confidence_score:.0f}/100")

            # KEY STATS
            print(f"\n   Historical: {analysis['historical_probability']*100:.1f}% | Sample: n={sample_size} (weight={sample_weight:.2f})")
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
