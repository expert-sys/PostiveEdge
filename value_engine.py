"""
Value Engine - Calculates implied probability, odds, and EV for sports markets
using historical performance data.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Union
from enum import Enum
import json
from decimal import Decimal, ROUND_HALF_UP


class OutcomeType(Enum):
    BINARY = "binary"
    CONTINUOUS = "continuous"


@dataclass
class HistoricalData:
    """Holds historical outcome data for analysis."""
    outcomes: List[Union[int, float]]
    weights: Optional[List[float]] = None
    
    def __post_init__(self):
        if not self.outcomes:
            raise ValueError("Outcomes list cannot be empty")
        if self.weights and len(self.weights) != len(self.outcomes):
            raise ValueError("Weights must match outcomes length")
        if self.weights:
            total = sum(self.weights)
            self.weights = [w / total for w in self.weights]


@dataclass
class MarketConfig:
    """Configuration for market analysis."""
    event_type: str
    outcome_type: OutcomeType
    bookmaker_odds: float
    minimum_sample_size: int = 5
    fallback_probability: float = 0.5
    use_recency_weighting: bool = False
    threshold: Optional[float] = None
    
    def __post_init__(self):
        if self.bookmaker_odds <= 1.0:
            raise ValueError("Bookmaker odds must be greater than 1.0")
        if not (0 < self.fallback_probability < 1):
            raise ValueError("Fallback probability must be between 0 and 1")


@dataclass
class ValueAnalysis:
    """Result of value analysis."""
    event_type: str
    sample_size: int
    historical_probability: float
    implied_odds: float
    bookmaker_odds: float
    bookmaker_probability: float
    edge_in_odds: float
    value_percentage: float
    ev_per_unit: float
    expected_return_per_100: float
    has_value: bool
    sufficient_sample: bool
    analysis_notes: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    def __str__(self) -> str:
        lines = [
            f"Event Type: {self.event_type}",
            f"Sample Size: {self.sample_size}",
            f"---",
            f"Historical Probability: {self.historical_probability:.4f} ({self.historical_probability*100:.2f}%)",
            f"Implied Odds (from history): {self.implied_odds:.2f}",
            f"Bookmaker Odds: {self.bookmaker_odds:.2f}",
            f"Bookmaker Probability: {self.bookmaker_probability:.4f} ({self.bookmaker_probability*100:.2f}%)",
            f"---",
            f"Edge (in odds): {self.edge_in_odds:+.2f}",
            f"Value %: {self.value_percentage:+.2f}%",
            f"EV per unit staked: {self.ev_per_unit:+.4f}",
            f"Expected return per $100: ${self.expected_return_per_100:+.2f}",
            f"---",
            f"Has Value: {self.has_value}",
            f"Sufficient Sample: {self.sufficient_sample}",
            f"Notes: {self.analysis_notes}"
        ]
        return "\n".join(lines)


class ValueEngine:
    """Core engine for calculating value in sports markets."""
    
    def __init__(self):
        self.default_bayesian_prior = 0.5
        self.bayesian_prior_weight = 10
    
    def calculate_historical_probability(
        self, 
        historical_data: HistoricalData, 
        outcome_type: OutcomeType,
        threshold: Optional[float] = None
    ) -> float:
        """
        Calculate historical probability from outcomes.
        
        For binary outcomes: count successes / total
        For continuous outcomes: count(outcome >= threshold) / total
        """
        outcomes = historical_data.outcomes
        weights = historical_data.weights
        
        if outcome_type == OutcomeType.BINARY:
            if weights:
                # Weighted binary: sum weights where outcome is 1
                return sum(w for w, o in zip(weights, outcomes) if o == 1)
            else:
                # Simple binary
                return sum(1 for o in outcomes if o == 1) / len(outcomes)
        
        elif outcome_type == OutcomeType.CONTINUOUS:
            if threshold is None:
                raise ValueError("Threshold required for continuous outcomes")
            
            if weights:
                return sum(w for w, o in zip(weights, outcomes) if o >= threshold)
            else:
                return sum(1 for o in outcomes if o >= threshold) / len(outcomes)
        
        raise ValueError(f"Unknown outcome type: {outcome_type}")
    
    def convert_probability_to_odds(self, probability: float) -> Optional[float]:
        """Convert probability to decimal odds."""
        if probability <= 0 or probability >= 1:
            return None
        return 1.0 / probability
    
    def convert_odds_to_probability(self, odds: float) -> float:
        """Convert decimal odds to implied probability."""
        if odds <= 1.0:
            raise ValueError("Odds must be greater than 1.0")
        return 1.0 / odds
    
    def calculate_value_percentage(
        self, 
        historical_probability: float, 
        bookmaker_probability: float
    ) -> float:
        """Calculate value as percentage difference."""
        return (historical_probability - bookmaker_probability) * 100
    
    def calculate_ev(
        self,
        historical_probability: float,
        bookmaker_odds: float,
        stake: float = 1.0
    ) -> float:
        """
        Calculate expected value per unit staked.
        EV = (probability * (odds - 1)) - (1 - probability)
        """
        ev = (historical_probability * (bookmaker_odds - 1)) - (1 - historical_probability)
        return ev * stake
    
    def apply_bayesian_shrinkage(
        self,
        success_count: int,
        total_count: int,
        prior_probability: float = None,
        prior_weight: int = None
    ) -> float:
        """
        Apply Bayesian shrinkage to adjust probability with prior.
        adjusted_probability = (successes + prior_weight * prior) / (total + prior_weight)
        """
        if prior_probability is None:
            prior_probability = self.default_bayesian_prior
        if prior_weight is None:
            prior_weight = self.bayesian_prior_weight
        
        return (success_count + prior_weight * prior_probability) / (total_count + prior_weight)
    
    def analyze_market(
        self,
        historical_data: HistoricalData,
        config: MarketConfig
    ) -> ValueAnalysis:
        """
        Perform complete value analysis on a market.
        """
        sample_size = len(historical_data.outcomes)
        sufficient_sample = sample_size >= config.minimum_sample_size
        
        # Calculate historical probability
        hist_probability = self.calculate_historical_probability(
            historical_data,
            config.outcome_type,
            config.threshold
        )
        
        # Apply Bayesian shrinkage if sample is too small
        if not sufficient_sample and config.outcome_type == OutcomeType.BINARY:
            success_count = sum(1 for o in historical_data.outcomes if o == 1)
            hist_probability = self.apply_bayesian_shrinkage(
                success_count, 
                sample_size
            )
            notes = f"Applied Bayesian shrinkage due to small sample (n={sample_size})"
        elif not sufficient_sample:
            hist_probability = config.fallback_probability
            notes = f"Using fallback probability due to small sample (n={sample_size})"
        else:
            notes = f"Analysis based on {sample_size} observations"
        
        # Convert to odds
        implied_odds = self.convert_probability_to_odds(hist_probability)
        if implied_odds is None:
            implied_odds = self.convert_probability_to_odds(config.fallback_probability)
            notes += " | Probability was invalid, using fallback"
            hist_probability = config.fallback_probability
        
        # Calculate bookmaker probability
        bookmaker_prob = self.convert_odds_to_probability(config.bookmaker_odds)
        
        # Calculate edge and value
        edge = config.bookmaker_odds - implied_odds
        value_pct = self.calculate_value_percentage(hist_probability, bookmaker_prob)
        
        # Calculate EV
        ev = self.calculate_ev(hist_probability, config.bookmaker_odds, stake=1.0)
        ev_per_100 = self.calculate_ev(hist_probability, config.bookmaker_odds, stake=100)
        
        # Determine if has value
        has_value = hist_probability > bookmaker_prob
        
        return ValueAnalysis(
            event_type=config.event_type,
            sample_size=sample_size,
            historical_probability=hist_probability,
            implied_odds=implied_odds,
            bookmaker_odds=config.bookmaker_odds,
            bookmaker_probability=bookmaker_prob,
            edge_in_odds=edge,
            value_percentage=value_pct,
            ev_per_unit=ev,
            expected_return_per_100=ev_per_100,
            has_value=has_value,
            sufficient_sample=sufficient_sample,
            analysis_notes=notes
        )


def analyze_simple_market(
    event_type: str,
    historical_outcomes: List[Union[int, float]],
    bookmaker_odds: float,
    outcome_type: str = "binary",
    minimum_sample_size: int = 5,
    threshold: Optional[float] = None,
    weights: Optional[List[float]] = None
) -> ValueAnalysis:
    """
    Simple interface for quick market analysis.
    """
    engine = ValueEngine()
    
    outcome_type_enum = OutcomeType.BINARY if outcome_type == "binary" else OutcomeType.CONTINUOUS
    
    historical_data = HistoricalData(
        outcomes=historical_outcomes,
        weights=weights
    )
    
    config = MarketConfig(
        event_type=event_type,
        outcome_type=outcome_type_enum,
        bookmaker_odds=bookmaker_odds,
        minimum_sample_size=minimum_sample_size,
        threshold=threshold
    )
    
    return engine.analyze_market(historical_data, config)
