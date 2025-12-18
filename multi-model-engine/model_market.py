import math
import statistics
from domain import ModelInput, ModelOutput

class MarketModel:
    """
    🔴 MODEL 4 — Market-Implied Reverse Model
    
    Infers what the market thinks the mean is based on the line and odds.
    """
    
    def __init__(self, weight: float = 0.10):
        self.weight = weight
        self.name = "Market Implied"
        
    def _inverse_normal_cdf(self, p: float) -> float:
        """Approximation of Probit function (inverse CDF)"""
        # Abramowitz and Stegun approximation
        if p <= 0 or p >= 1: return 0.0
        
        # If p > 0.5, use 1-p and negate result
        if p > 0.5:
            return -self._inverse_normal_cdf(1-p)
            
        t = math.sqrt(-2.0 * math.log(p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return -((c2*t + c1)*t + c0) / (((d3*t + d2)*t + d1)*t + 1.0)

    def generate(self, input_data: ModelInput) -> ModelOutput:
        if not input_data.market_odds or input_data.market_odds <= 1.0:
            return ModelOutput(self.name, 0.0, 0.0, 0.0, reasons=["No market odds provided"])
            
        # 1. Calculate Implied Probability (vig-free ideally, but raw for now)
        # If we have implied_probability in input, use it, else 1/odds
        if input_data.implied_probability:
            prob_over = input_data.implied_probability
        else:
            # Assuming standard -110/-110 or 1.91/1.91, implied prob includes vig.
            # To get true prob, we usually need both sides.
            # Here we assume user provides a "fair" implied prob or just 1/odds.
            prob_over = 1.0 / input_data.market_odds
            
        # 2. Estimate Volatility (CV) from history
        valid_games = [g for g in input_data.game_log if g.minutes > 0]
        if valid_games:
            vals = [getattr(g, input_data.stat_type, 0) for g in valid_games]
            if len(vals) > 1:
                mean_val = statistics.mean(vals)
                std_val = statistics.stdev(vals)
                cv = std_val / mean_val if mean_val > 0 else 0.5
            else:
                cv = 0.5
        else:
            cv = 0.5
            
        # 3. Reverse Engineer Mean
        # Prob(X > Line) = prob_over
        # Z = (Line - Mean) / (Mean * CV)
        # P(Z_standard > Z) = prob_over
        # P(Z_standard < Z) = 1 - prob_over
        
        z_threshold = self._inverse_normal_cdf(1.0 - prob_over)
        
        # Line - Mean = z_threshold * Mean * CV
        # Line = Mean * (1 + z_threshold * CV)
        # Mean = Line / (1 + z_threshold * CV)
        
        denom = 1.0 + z_threshold * cv
        if denom == 0: denom = 0.001
        
        implied_mean = input_data.line / denom
        
        return ModelOutput(
            model_name=self.name,
            expected_value=implied_mean,
            probability_over=prob_over, # Just mirroring the market
            confidence=0.8, # Market is usually "right" on average
            weight=self.weight,
            reasons=[
                f"Market Prob: {prob_over:.1%}",
                f"Hist CV: {cv:.2f}",
                f"Implied Mean: {implied_mean:.2f}"
            ],
            metadata={"market_disagreement": False} # Filled by engine
        )
