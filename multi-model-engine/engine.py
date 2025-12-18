import statistics
import math
from typing import List, Dict, Any
from dataclasses import dataclass, field

from domain import ModelInput, ModelOutput
from model_deterministic import DeterministicModel
from model_empirical import EmpiricalModel
from model_regression import RegressionModel
from model_market import MarketModel
from model_bayesian import BayesianModel

@dataclass
class EnsembleResult:
    final_projection: float
    final_probability: float
    confidence_score: float
    is_bet: bool
    model_outputs: Dict[str, ModelOutput]
    disagreement_level: float # Coefficient of Variation of models
    notes: List[str]

class MultiModelEngine:
    def __init__(self):
        # Initialize models
        self.models = [
            DeterministicModel(weight=0.45),
            EmpiricalModel(weight=0.25),
            RegressionModel(weight=0.20),
            MarketModel(weight=0.10),
            BayesianModel(weight=0.05) # Optional, can adjust weight
        ]
        
        # Re-normalize weights if Bayesian is added or user changes things
        total_weight = sum(m.weight for m in self.models)
        for m in self.models:
            m.weight /= total_weight

    def analyze(self, input_data: ModelInput) -> EnsembleResult:
        outputs = {}
        projections = []
        probabilities = []
        
        weighted_proj_sum = 0.0
        weighted_prob_sum = 0.0
        
        notes = []
        
        # Run all models
        for model in self.models:
            out = model.generate(input_data)
            outputs[model.name] = out
            
            weighted_proj_sum += out.expected_value * out.weight
            weighted_prob_sum += out.probability_over * out.weight
            
            # For disagreement calculation (exclude Market usually, but user said include it)
            # Market model output IS the implied mean, so it's comparable.
            projections.append(out.expected_value)
            probabilities.append(out.probability_over)
            
            notes.append(f"[{model.name}] Proj: {out.expected_value:.1f}, Prob: {out.probability_over:.1%}, Conf: {out.confidence:.2f}")
            if out.reasons and out.confidence < 0.1:
                notes.extend([f"  - {r}" for r in out.reasons])
            
        final_proj = weighted_proj_sum
        final_prob = weighted_prob_sum
        
        # Calculate Disagreement (Standard Deviation of projections)
        if len(projections) > 1:
            proj_std = statistics.stdev(projections)
            proj_mean = statistics.mean(projections)
            disagreement = proj_std / proj_mean if proj_mean > 0 else 0.0
        else:
            disagreement = 0.0
            
        # Confidence Calculation
        # Base confidence is weighted average of model confidences
        avg_conf = sum(outputs[m.name].confidence * m.weight for m in self.models)
        
        # Disagreement Penalty
        # If disagreement > 10%, reduce confidence
        if disagreement > 0.10:
            penalty = (disagreement - 0.10) * 2.0 # Steep penalty
            avg_conf *= max(0.5, 1.0 - penalty)
            notes.append(f"⚠️ High Disagreement ({disagreement:.1%}). Confidence reduced.")
            
        # Market Disagreement Check
        market_out = outputs.get("Market Implied")
        if market_out:
            market_mean = market_out.expected_value
            # Compare "My Projection" (excluding market weight roughly) vs Market
            # But final_proj includes market.
            diff = abs(final_proj - market_mean)
            pct_diff = diff / market_mean if market_mean > 0 else 0.0
            
            if pct_diff > 0.15:
                notes.append(f"🚨 Fighting the Market! (Diff: {pct_diff:.1%})")
                # Further reduce confidence or require higher EV
                avg_conf *= 0.8
        
        # Determine if Bet
        # EV Check
        # EV = Prob * (Odds - 1) - (1 - Prob)
        # Using final_prob
        odds = input_data.market_odds or 1.91
        ev = final_prob * (odds - 1.0) - (1.0 - final_prob)
        
        is_bet = False
        if ev > 0.05 and avg_conf > 0.6:
            is_bet = True
            
        notes.append(f"Final: Proj {final_proj:.1f}, Prob {final_prob:.1%}, EV {ev:.2f}")
        
        return EnsembleResult(
            final_projection=final_proj,
            final_probability=final_prob,
            confidence_score=avg_conf,
            is_bet=is_bet,
            model_outputs=outputs,
            disagreement_level=disagreement,
            notes=notes
        )
