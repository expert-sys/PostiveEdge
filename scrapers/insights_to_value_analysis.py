"""
Insights to Value Analysis Converter
====================================
Converts Sportsbet match insights into historical outcomes for Value Engine analysis.

Uses real historical patterns from insights like:
- "The Pistons have won each of their last nine games" → [1,1,1,1,1,1,1,1,1]
- "Each of the Pacers' last seven games... have gone UNDER" → [1,1,1,1,1,1,1]
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from typing import List, Dict, Optional, Tuple
from scrapers.context_aware_analysis import ContextAwareAnalyzer, ContextFactors, ContextAwareAnalysis


def extract_historical_outcomes_from_insight(fact: str) -> Tuple[Optional[List[int]], int]:
    """
    Extract historical outcomes from an insight fact.

    Returns:
        (outcomes, sample_size) where outcomes is a list of 1s and 0s, or None if can't parse

    Examples:
        "won each of their last nine games" → ([1,1,1,1,1,1,1,1,1], 9)
        "lost all quarters in each of their last four games" → ([0,0,0,0], 4)
        "recorded six or more assists in each of his last five" → ([1,1,1,1,1], 5)
        "scored 20+ points in 13 of his last 14 appearances" → ([1,1,1,1,1,1,1,1,1,1,1,1,1,0], 14)
    """

    fact_lower = fact.lower()

    # Word to number mapping
    word_to_num = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20
    }

    # Pattern 1: "each of their/his last X games/appearances"
    # Or: "in each of their/his last X"
    # Or: "each of the ... last X"
    # This means X consecutive successes
    # X can be a word (five, nine) or digit (5, 9)

    # More flexible pattern for "last X" - accepts words or digits
    pattern1 = r'last (\w+) (?:games?|appearances?|road|home)'
    match1 = re.search(pattern1, fact_lower)

    if match1 and ('each' in fact_lower or 'all' in fact_lower):
        count_str = match1.group(1)

        # Convert to int
        try:
            count = int(count_str)
        except ValueError:
            count = word_to_num.get(count_str)

        if count:
            # Determine if it's wins or losses
            if 'won' in fact_lower or 'recorded' in fact_lower or 'scored' in fact_lower or 'made' in fact_lower or 'gone over' in fact_lower:
                # All successes
                return ([1] * count, count)
            elif 'lost' in fact_lower or 'failed' in fact_lower or 'gone under' in fact_lower or 'have gone under' in fact_lower:
                # All failures (or successes for UNDER bets)
                # If it's an UNDER bet that succeeded, mark as success
                if 'under' in fact_lower:
                    return ([1] * count, count)  # UNDER hit = success
                else:
                    return ([0] * count, count)  # Lost = failure

    # Pattern 2: "X of their last Y" or "X of his last Y" or "in X of ... last Y"
    # This means X successes out of Y attempts
    # Handle both word and digit numbers for both X and Y
    pattern2 = r'(?:in )?(\w+) of (?:their|his|the)?\s*last (\w+)'
    match2 = re.search(pattern2, fact_lower)

    if match2:
        successes_str = match2.group(1)
        total_str = match2.group(2)

        # Convert to ints
        try:
            successes = int(successes_str)
        except ValueError:
            successes = word_to_num.get(successes_str)

        try:
            total = int(total_str)
        except ValueError:
            total = word_to_num.get(total_str)

        if successes is not None and total is not None and successes <= total:
            # Create list with successes (1s) and failures (0s)
            outcomes = [1] * successes + [0] * (total - successes)
            return (outcomes, total)

    # Pattern 3: "last X games/appearances" without "each" - need to check context
    # If it says "have gone UNDER" or similar, assume all
    if match1 and ('gone under' in fact_lower or 'gone over' in fact_lower):
        count_str = match1.group(1)

        # Convert to int (handle both word and digit numbers)
        try:
            count = int(count_str)
        except ValueError:
            count = word_to_num.get(count_str)

        if count:
            if 'under' in fact_lower:
                return ([1] * count, count)  # All went under
            elif 'over' in fact_lower:
                return ([1] * count, count)  # All went over

    return (None, 0)


def extract_recent_vs_historical(fact: str, outcomes: List[int]) -> Tuple[List[int], List[int]]:
    """
    Try to separate recent form from full historical data based on insight wording.

    Examples:
        "7 of his last 10" → recent = last 3, historical = all 10
        "each of his last 5" → recent = last 2, historical = all 5

    Returns:
        (recent_outcomes, historical_outcomes)
    """

    # Default: last 30% as "recent", all as historical
    recent_size = max(3, min(5, len(outcomes) // 3))

    return (outcomes[-recent_size:], outcomes)


def create_context_from_insight(insight: Dict, lineup_context: Optional[ContextFactors] = None) -> ContextFactors:
    """
    Create ContextFactors from insight tags and lineup data.

    Args:
        insight: Insight dictionary
        lineup_context: Optional lineup context from RotoWire

    Returns:
        ContextFactors object
    """

    if lineup_context:
        # Start with lineup context if provided
        context = lineup_context
    else:
        context = ContextFactors()

    tags = insight.get('tags', [])
    fact = insight.get('fact', '').lower()

    # Extract context from tags
    for tag in tags:
        tag_lower = tag.lower()

        if 'home' in tag_lower:
            context.home_away = "HOME"
        elif 'away' in tag_lower or 'road' in tag_lower:
            context.home_away = "AWAY"

    # Look for context in fact text
    if 'home' in fact:
        context.home_away = "HOME"
    elif 'away' in fact or 'road' in fact:
        context.home_away = "AWAY"

    return context


def analyze_insight_with_context(
    insight: Dict,
    minimum_sample_size: int = 4,
    lineup_context: Optional[ContextFactors] = None
) -> Optional[ContextAwareAnalysis]:
    """
    Analyze a single insight using Context-Aware Analysis.

    Args:
        insight: Dictionary with keys 'fact', 'market', 'result', 'odds', 'tags'
        minimum_sample_size: Minimum number of historical games needed (default: 4)
        lineup_context: Optional lineup context from RotoWire

    Returns:
        ContextAwareAnalysis object or None if can't analyze
    """

    fact = insight.get('fact', '')
    odds = insight.get('odds')
    market = insight.get('market', 'Unknown Market')
    result = insight.get('result', 'Unknown')

    if not odds:
        return None

    # Extract historical outcomes from the insight
    outcomes, sample_size = extract_historical_outcomes_from_insight(fact)

    if not outcomes:
        return None

    # FILTER: Absolute minimum of 4 samples
    if sample_size < minimum_sample_size:
        return None

    # Extract recent vs historical
    recent_outcomes, historical_outcomes = extract_recent_vs_historical(fact, outcomes)

    # Create context from insight and lineup data
    context_factors = create_context_from_insight(insight, lineup_context)

    # Analyze with Context-Aware Engine
    try:
        analyzer = ContextAwareAnalyzer()

        analysis = analyzer.analyze_with_context(
            historical_outcomes=historical_outcomes,
            recent_outcomes=recent_outcomes,
            bookmaker_odds=odds,
            context_factors=context_factors,
            player_name=f"{result} - {market}",
            insight_fact=fact,  # Pass fact for trend classification
            market=market       # Pass market for context
        )

        return analysis

    except Exception as e:
        print(f"Error analyzing insight: {e}")
        import traceback
        traceback.print_exc()
        return None


# Keep old function for backward compatibility
def analyze_insight_with_value_engine(
    insight: Dict,
    minimum_sample_size: int = 4
) -> Optional[ContextAwareAnalysis]:
    """Legacy wrapper - now uses context-aware analysis."""
    return analyze_insight_with_context(insight, minimum_sample_size)


def analyze_all_insights(
    insights: List[Dict],
    minimum_sample_size: int = 4,
    lineup_context: Optional[ContextFactors] = None
) -> List[Dict]:
    """
    Analyze all insights with context-aware analysis.

    Args:
        insights: List of insight dictionaries
        minimum_sample_size: Minimum historical sample size
        lineup_context: Optional lineup context from RotoWire

    Returns:
        List of dictionaries with insight + context-aware analysis
    """

    results = []

    for insight in insights:
        analysis = analyze_insight_with_context(insight, minimum_sample_size, lineup_context)

        if analysis:
            # Calculate sample size from historical probability
            # Estimate: if historical_prob = successes/total, we can approximate
            # For now, use a reasonable estimate based on the context
            sample_size = 10  # Default estimate

            # Try to get actual sample size from the insight fact
            fact = insight.get('fact', '')
            outcomes, actual_size = extract_historical_outcomes_from_insight(fact)
            if outcomes:
                sample_size = actual_size

            result = {
                'insight': insight,
                'analysis': {
                    # Core metrics
                    'sample_size': sample_size,
                    'historical_probability': analysis.historical_probability,
                    'adjusted_probability': analysis.adjusted_probability,
                    'bookmaker_probability': analysis.bookmaker_probability,
                    'value_percentage': analysis.value_percentage,
                    'ev_per_100': analysis.ev_per_100,
                    'has_value': analysis.has_value,

                    # Context-aware enhancements
                    'recommendation': analysis.recommendation,
                    'confidence_level': analysis.confidence_level,
                    'confidence_score': analysis.confidence_score,
                    'risk_level': analysis.overall_risk,
                    'risk_score': analysis.risk_score,

                    # Trend info
                    'trend': analysis.recency_adjustment.trend_direction,
                    'recent_form_prob': analysis.recency_adjustment.recent_form_prob,

                    # Minutes risk
                    'benching_risk': analysis.minutes_projection.benching_risk,
                    'recent_minutes_avg': analysis.minutes_projection.recent_avg,

                    # Warnings and reasons
                    'warnings': analysis.warnings,
                    'reasons': analysis.reasons
                }
            }

            results.append(result)

    return results


def print_analysis_report(analyzed_insights: List[Dict]):
    """Print a formatted context-aware report."""

    print("\n" + "="*70)
    print("  CONTEXT-AWARE VALUE ANALYSIS REPORT")
    print("="*70)

    # Categorize by recommendation
    strong_bets = [r for r in analyzed_insights if r['analysis']['recommendation'] == 'STRONG BET']
    bets = [r for r in analyzed_insights if r['analysis']['recommendation'] == 'BET']
    consider = [r for r in analyzed_insights if r['analysis']['recommendation'] == 'CONSIDER']
    pass_bets = [r for r in analyzed_insights if r['analysis']['recommendation'] in ['PASS', 'AVOID']]

    print(f"\nTotal Insights Analyzed: {len(analyzed_insights)}")
    print(f"  [+] STRONG BET: {len(strong_bets)}")
    print(f"  [+] BET: {len(bets)}")
    print(f"  [!] CONSIDER: {len(consider)}")
    print(f"  [-] PASS/AVOID: {len(pass_bets)}")

    # Show actionable bets (Strong Bet + Bet + Consider)
    actionable = strong_bets + bets + consider

    if actionable:
        print("\n" + "-"*70)
        print("RECOMMENDED BETS (sorted by confidence)")
        print("-"*70)

        # Sort by confidence score - highest first
        actionable.sort(key=lambda x: x['analysis']['confidence_score'], reverse=True)

        for i, item in enumerate(actionable, 1):
            insight = item['insight']
            analysis = item['analysis']

            # Extract team from icon URL (most reliable method)
            player_name = insight.get('result', 'N/A')
            team = None

            # Try to get team from icon URL
            icon = insight.get('icon', '')
            if icon:
                # Icon URL format: https://cdn.gtgnetwork.com/icons/teams/basketball/sportsbet/detroit_pistons.png
                if 'detroit_pistons' in icon:
                    team = 'Detroit Pistons'
                elif 'indiana_pacers' in icon:
                    team = 'Indiana Pacers'
                elif 'los_angeles_lakers' in icon:
                    team = 'Los Angeles Lakers'
                elif 'golden_state_warriors' in icon or 'gs_warriors' in icon:
                    team = 'Golden State Warriors'
                elif 'boston_celtics' in icon:
                    team = 'Boston Celtics'
                elif 'miami_heat' in icon:
                    team = 'Miami Heat'
                elif 'milwaukee_bucks' in icon:
                    team = 'Milwaukee Bucks'
                elif 'cleveland_cavaliers' in icon:
                    team = 'Cleveland Cavaliers'
                elif 'denver_nuggets' in icon:
                    team = 'Denver Nuggets'
                elif 'phoenix_suns' in icon:
                    team = 'Phoenix Suns'
                elif 'philadelphia_76ers' in icon:
                    team = 'Philadelphia 76ers'
                elif 'dallas_mavericks' in icon:
                    team = 'Dallas Mavericks'
                elif 'new_york_knicks' in icon:
                    team = 'New York Knicks'
                elif 'brooklyn_nets' in icon:
                    team = 'Brooklyn Nets'
                elif 'toronto_raptors' in icon:
                    team = 'Toronto Raptors'
                elif 'chicago_bulls' in icon:
                    team = 'Chicago Bulls'
                elif 'atlanta_hawks' in icon:
                    team = 'Atlanta Hawks'
                elif 'charlotte_hornets' in icon:
                    team = 'Charlotte Hornets'
                elif 'orlando_magic' in icon:
                    team = 'Orlando Magic'
                elif 'washington_wizards' in icon:
                    team = 'Washington Wizards'
                elif 'san_antonio_spurs' in icon:
                    team = 'San Antonio Spurs'
                elif 'new_orleans_pelicans' in icon:
                    team = 'New Orleans Pelicans'
                elif 'memphis_grizzlies' in icon:
                    team = 'Memphis Grizzlies'
                elif 'houston_rockets' in icon:
                    team = 'Houston Rockets'
                elif 'minnesota_timberwolves' in icon:
                    team = 'Minnesota Timberwolves'
                elif 'portland_trail_blazers' in icon:
                    team = 'Portland Trail Blazers'
                elif 'utah_jazz' in icon:
                    team = 'Utah Jazz'
                elif 'oklahoma_city_thunder' in icon:
                    team = 'Oklahoma City Thunder'
                elif 'sacramento_kings' in icon:
                    team = 'Sacramento Kings'
                elif 'la_clippers' in icon or 'los_angeles_clippers' in icon:
                    team = 'Los Angeles Clippers'

            sample_size = analysis['sample_size']

            # Get confidence from enhanced analysis (or fallback to old calculation)
            confidence_level = analysis.get('confidence_level', 'MEDIUM')
            confidence_score = analysis.get('confidence_score', 50)
            bayesian_adjusted = analysis.get('bayesian_adjusted', False)
            effective_n = analysis.get('effective_sample_size', sample_size)

            # Recommendation marker
            rec_marker = {
                "STRONG BET": "[+]",
                "BET": "[+]",
                "CONSIDER": "[!]",
                "PASS": "[-]",
                "AVOID": "[-]"
            }
            marker = rec_marker.get(analysis['recommendation'], '•')

            print(f"\n{i}. {marker} {insight['fact']}")
            print(f"   Market: {insight.get('market', 'N/A')}")
            print(f"   Bookmaker Odds: {insight.get('odds', 'N/A')}")

            print(f"\n   ANALYSIS:")
            print(f"   - Historical: {analysis['historical_probability']*100:.1f}%")
            print(f"   - Adjusted: {analysis['adjusted_probability']*100:.1f}% (after context)")
            print(f"   - Bookmaker: {analysis['bookmaker_probability']*100:.1f}%")
            print(f"   - Edge: {analysis['value_percentage']:+.1f}%")
            print(f"   - EV: ${analysis['ev_per_100']:+.2f} per $100")

            print(f"\n   RECOMMENDATION: {analysis['recommendation']}")
            print(f"   - Confidence: {analysis['confidence_level']} ({analysis['confidence_score']}/100)")
            print(f"   - Risk: {analysis['risk_level']} ({analysis['risk_score']}/100)")

            # Trend info
            if analysis.get('trend'):
                trend_marker = {"IMPROVING": "[UP]", "DECLINING": "[DOWN]", "STABLE": "[=]"}
                print(f"\n   {trend_marker.get(analysis['trend'], '[-]')} TREND: {analysis['trend']}")
                print(f"   - Recent Form: {analysis['recent_form_prob']*100:.1f}%")

            # Minutes risk
            if analysis.get('benching_risk') and analysis['benching_risk'] != "LOW":
                print(f"\n   MINUTES RISK: {analysis['benching_risk']}")
                print(f"   - Recent Avg: {analysis['recent_minutes_avg']:.1f} min")

            # Warnings
            if analysis.get('warnings'):
                print(f"\n   WARNINGS:")
                for warning in analysis['warnings']:
                    print(f"      - {warning}")

            # Reasons
            if analysis.get('reasons'):
                print(f"\n   REASONS:")
                for reason in analysis['reasons']:
                    print(f"      - {reason}")

    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    """Test the conversion with sample data"""

    print("\n" + "="*70)
    print("  TESTING INSIGHTS TO VALUE ANALYSIS CONVERTER")
    print("="*70)

    # Test insight parsing
    test_insights = [
        "The Pistons have won each of their last nine games.",
        "Each of the Pacers' last seven games as road underdogs have gone UNDER the total match points line.",
        "Andrew Nembhard has recorded six or more assists in each of his last five road appearances.",
        "Pascal Siakam has scored 20+ points in 13 of his last 14 appearances against the Pistons.",
        "Duncan Robinson has scored 16+ points in four of his last five home appearances against the Pacers."
    ]

    print("\n1. Testing Historical Outcomes Extraction:\n")

    for fact in test_insights:
        outcomes, sample_size = extract_historical_outcomes_from_insight(fact)
        if outcomes:
            win_rate = sum(outcomes) / len(outcomes) * 100
            print(f"Fact: {fact[:60]}...")
            print(f"  => Outcomes: {outcomes}")
            print(f"  => Sample: n={sample_size}, Win Rate: {win_rate:.1f}%\n")
        else:
            print(f"Fact: {fact[:60]}...")
            print(f"  => Could not extract outcomes\n")

    # Test full analysis with sample data
    print("\n2. Testing Full Value Analysis:\n")

    sample_insights = [
        {
            'fact': 'The Pistons have won each of their last nine games.',
            'market': 'Match Betting',
            'result': 'Detroit Pistons',
            'odds': 1.21,
            'tags': ['Detroit Pistons', 'Win/Loss']
        },
        {
            'fact': 'Pascal Siakam has scored 20+ points in 13 of his last 14 appearances against the Pistons.',
            'market': 'Pascal Siakam To Score 20+ Points',
            'result': 'Pascal Siakam',
            'odds': 1.39,
            'tags': ['Pascal Siakam', 'Alt 20+']
        },
        {
            'fact': 'Each of the Pacers\' last seven games as road underdogs have gone UNDER the total match points line.',
            'market': 'Total Points',
            'result': 'Under',
            'odds': 1.9,
            'tags': ['Over/Under']
        }
    ]

    analyzed = analyze_all_insights(sample_insights, minimum_sample_size=3)
    print_analysis_report(analyzed)

    print("\nTest complete!")
