"""
Quality Filtering System for Player Props
==========================================
Multi-stage filtering to select only high-quality betting opportunities.

Filters applied:
1. Consistency check: Reject high-variance players
2. Lineup certainty: Reject questionable players or unclear minutes
3. Edge quality: Require meaningful EV and confidence

Philosophy: Be highly selective (filter 85-90%) to achieve high accuracy.

Usage:
    from prop_filters import PropFilter, PropFilterCriteria

    prop_filter = PropFilter()
    passes, filter_results = prop_filter.filter_prop(
        prop_data={"player": "LeBron James", "outcomes": [1,1,0,1,1], "analysis": {...}},
        stat_values=[28, 31, 25, 27, 30],
        lineups=[...],
        team_name="Los Angeles Lakers"
    )
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger("prop_filters")


@dataclass
class PropFilterCriteria:
    """
    Quality gates for prop selection.

    These thresholds determine selectivity level. Start conservative,
    then adjust based on live results.
    """

    # Sample quality
    min_consistency_score: float = 0.35  # Filter high variance players (CV > ~0.33)

    # Lineup certainty
    exclude_questionable_players: bool = True  # Skip GTD, Out, Questionable
    min_expected_minutes: float = 18.0  # Bench players unreliable

    # Edge requirements
    min_ev_percentage: float = 4.0  # Require 4%+ edge (meaningful value)
    min_confidence_score: float = 45.0  # Only decent confidence bets

    # Statistical significance
    min_hit_rate_differential: float = 0.08  # Must be 8% different from 50% (not a coin flip)


class PropFilter:
    """Filter player props for quality using multi-stage gates"""

    def __init__(self, criteria: PropFilterCriteria = None):
        """
        Initialize filter with criteria.

        Args:
            criteria: Custom filter criteria, or None for defaults
        """
        self.criteria = criteria or PropFilterCriteria()

    def check_consistency(
        self,
        outcomes: List[int],
        stat_values: List[float]
    ) -> Tuple[bool, float, str]:
        """
        Check if player is consistent enough to bet on.

        Volatile players are unpredictable - even with good historical probability,
        they have wide confidence intervals. Filtering them improves win rate.

        Args:
            outcomes: Binary outcomes (1/0 for hit/miss)
            stat_values: Actual stat values (e.g., [28, 31, 25, 27, 30])

        Returns:
            (passes, consistency_score, reason)
        """
        if len(stat_values) < 5:
            return (False, 0.0, "Insufficient data for consistency check")

        # Calculate consistency score
        mean_val = np.mean(stat_values)
        std_val = np.std(stat_values)

        if mean_val < 0.01:
            return (False, 0.3, "Very low production")

        # Coefficient of variation
        cv = std_val / mean_val

        # Convert to 0-1 score (lower CV = higher score)
        consistency = max(0.0, min(1.0, 1.0 - (cv / 0.5)))

        if consistency < self.criteria.min_consistency_score:
            return (
                False,
                consistency,
                f"Too volatile (consistency: {consistency:.2f}, CV: {cv:.2f})"
            )

        return (
            True,
            consistency,
            f"Consistent player (score: {consistency:.2f}, CV: {cv:.2f})"
        )

    def check_lineup_status(
        self,
        player_name: str,
        lineups: List[Dict],
        team_name: str
    ) -> Tuple[bool, float, str]:
        """
        Check player lineup status and expected minutes.

        Betting on players with uncertain minutes or injury status is risky.
        Filter these out to improve hit rate.

        Args:
            player_name: Player name to check
            lineups: Lineup data from Rotowire or similar
            team_name: Team name to search in

        Returns:
            (passes, expected_minutes, reason)
        """
        if not lineups:
            # No lineup data available - use heuristic assumption
            # In production, this should be rare as lineups are usually available
            logger.warning(f"No lineup data for {player_name} - assuming starter")
            return (True, 25.0, "No lineup data - assuming starter minutes")

        # Search for player in lineup data
        for lineup_data in lineups:
            if lineup_data.get("team") == team_name:
                players = lineup_data.get("players", [])

                for p in players:
                    if p.get("name") == player_name:
                        status = p.get("status", "").lower()
                        position = p.get("position", "")

                        # Check injury status
                        if self.criteria.exclude_questionable_players:
                            if status in ["out", "questionable", "doubtful", "gtd", "game time decision"]:
                                return (False, 0.0, f"Player {status}")

                        # Estimate minutes by position
                        if "starter" in position.lower() or position in ["PG", "SG", "SF", "PF", "C"]:
                            return (True, 30.0, "Confirmed starter")
                        else:
                            # Bench player - uncertain minutes
                            return (False, 15.0, "Bench player - uncertain minutes")

        # Player not found in confirmed lineup
        logger.warning(f"{player_name} not found in lineup data for {team_name}")
        return (False, 12.0, "Not in confirmed lineup")

    def check_edge_quality(
        self,
        ev_percentage: float,
        confidence_score: float,
        hit_rate: float
    ) -> Tuple[bool, str]:
        """
        Check if the edge is significant enough to bet on.

        Even with positive EV, if the edge is tiny (1-2%), it might just be noise.
        Require meaningful edges to ensure we're not betting on false signals.

        Args:
            ev_percentage: Value percentage (historical prob - bookmaker prob) * 100
            confidence_score: Confidence score from value engine (0-100)
            hit_rate: Historical probability of hitting

        Returns:
            (passes, reason)
        """
        # Check EV requirement
        if abs(ev_percentage) < self.criteria.min_ev_percentage:
            return (
                False,
                f"Edge too small: {ev_percentage:.1f}% < {self.criteria.min_ev_percentage}%"
            )

        # Check confidence
        if confidence_score < self.criteria.min_confidence_score:
            return (
                False,
                f"Confidence too low: {confidence_score:.1f}"
            )

        # Check hit rate is meaningfully different from coin flip (50%)
        # If hit rate is 48-52%, it's basically random
        deviation = abs(hit_rate - 0.50)
        if deviation < self.criteria.min_hit_rate_differential:
            return (
                False,
                f"Hit rate too close to 50%: {hit_rate:.1%} (deviation: {deviation:.1%})"
            )

        return (
            True,
            f"Good edge: {ev_percentage:.1f}% EV, {confidence_score:.1f} confidence, {hit_rate:.1%} hit rate"
        )

    def filter_prop(
        self,
        prop_data: Dict,
        stat_values: List[float],
        lineups: List[Dict],
        team_name: str
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Apply all filters to a prop.

        Multi-stage filtering:
        1. Consistency check (reject volatile players)
        2. Lineup check (reject uncertain situations)
        3. Edge quality check (reject weak edges)

        If any filter fails, the prop is rejected.

        Args:
            prop_data: Dict with "player", "outcomes", "analysis" keys
            stat_values: List of actual stat values for consistency check
            lineups: Lineup data from scraper
            team_name: Team name for lineup lookup

        Returns:
            (passes_all_filters, filter_results_dict)
        """
        results = {}

        # Stage 1: Consistency check
        outcomes = prop_data.get("outcomes", [])
        pass_consistency, consistency_score, reason = self.check_consistency(
            outcomes, stat_values
        )
        results["consistency"] = reason
        results["consistency_score"] = consistency_score

        if not pass_consistency:
            results["filtered_by"] = "consistency"
            return (False, results)

        # Stage 2: Lineup check
        player_name = prop_data.get("player", "")
        pass_lineup, expected_mins, reason = self.check_lineup_status(
            player_name, lineups, team_name
        )
        results["lineup"] = reason
        results["expected_minutes"] = expected_mins

        if not pass_lineup:
            results["filtered_by"] = "lineup"
            return (False, results)

        # Stage 3: Edge quality check
        analysis = prop_data.get("analysis", {})
        ev_pct = analysis.get("value_percentage", 0.0)
        confidence = analysis.get("confidence_score", 0.0)
        hit_rate = analysis.get("historical_probability", 0.5)

        pass_edge, reason = self.check_edge_quality(ev_pct, confidence, hit_rate)
        results["edge_quality"] = reason

        if not pass_edge:
            results["filtered_by"] = "edge_quality"
            return (False, results)

        # All filters passed!
        results["filtered_by"] = None
        results["status"] = "PASSED"
        logger.info(f"✓ {player_name} passed all filters: {reason}")

        return (True, results)


# Utility function for batch filtering
def filter_props_batch(
    props: List[Dict],
    filter_criteria: PropFilterCriteria = None
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Filter a batch of props and return statistics.

    Args:
        props: List of prop dicts with required fields
        filter_criteria: Custom filter criteria

    Returns:
        (passed_props, filtered_props, summary_stats)
    """
    prop_filter = PropFilter(filter_criteria)

    passed = []
    filtered = []

    for prop in props:
        passes, results = prop_filter.filter_prop(
            prop_data=prop,
            stat_values=prop.get("stat_values", []),
            lineups=prop.get("lineups", []),
            team_name=prop.get("team_name", "")
        )

        if passes:
            prop["filter_results"] = results
            passed.append(prop)
        else:
            prop["filter_results"] = results
            filtered.append(prop)

    # Summary statistics
    total = len(props)
    summary = {
        "total_props": total,
        "passed": len(passed),
        "filtered": len(filtered),
        "selectivity_pct": (len(filtered) / total * 100) if total > 0 else 0,
        "filtered_by_consistency": sum(1 for p in filtered if p["filter_results"].get("filtered_by") == "consistency"),
        "filtered_by_lineup": sum(1 for p in filtered if p["filter_results"].get("filtered_by") == "lineup"),
        "filtered_by_edge": sum(1 for p in filtered if p["filter_results"].get("filtered_by") == "edge_quality")
    }

    return (passed, filtered, summary)
