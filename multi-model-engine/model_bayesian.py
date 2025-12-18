import statistics
import math
from domain import ModelInput, ModelOutput

class BayesianModel:
    """
    🟣 MODEL 5 — Bayesian Update Model
    
    Treats long-term baseline as Prior, updates with recent form (Evidence).
    posterior = combine(prior, new_evidence)
    """
    
    def __init__(self, weight: float = 0.05):
        self.weight = weight
        self.name = "Bayesian Update"
        
    def generate(self, input_data: ModelInput) -> ModelOutput:
        games = input_data.game_log
        if not games:
             return ModelOutput(self.name, 0.0, 0.0, 0.0, reasons=["No data"])
             
        # 1. Establish Prior (Long term baseline)
        # Last 50 games or full season
        long_term = games[:50] 
        vals_long = [getattr(g, input_data.stat_type, 0) for g in long_term]
        
        if not vals_long:
             return ModelOutput(self.name, 0.0, 0.0, 0.0, reasons=["No data"])

        mu_0 = statistics.mean(vals_long)
        sigma_0 = statistics.stdev(vals_long) if len(vals_long) > 1 else max(1.0, mu_0 * 0.5)
        
        # 2. Evidence (Recent form)
        # Last 5 games
        short_term = games[:5]
        vals_short = [getattr(g, input_data.stat_type, 0) for g in short_term]
        
        x_bar = statistics.mean(vals_short)
        n = len(vals_short)
        
        # Assume observation noise (sigma) is similar to population std dev
        sigma = sigma_0 
        
        # 3. Posterior Calculation (Normal-Normal Conjugate)
        # Precision = 1/variance
        prec_0 = 1.0 / (sigma_0 ** 2)
        prec_data = n / (sigma ** 2)
        
        mu_post = (prec_0 * mu_0 + prec_data * x_bar) / (prec_0 + prec_data)
        
        # Update variance (uncertainty reduces with more data)
        var_post = 1.0 / (prec_0 + prec_data)
        sigma_post = math.sqrt(var_post)
        
        # 4. Prob Over
        # Predictive distribution variance = sigma_post^2 + sigma^2
        pred_var = var_post + sigma**2
        pred_std = math.sqrt(pred_var)
        
        z = (input_data.line - mu_post) / pred_std
        prob_over = 0.5 * (1 - math.erf(z / math.sqrt(2)))
        
        return ModelOutput(
            model_name=self.name,
            expected_value=mu_post,
            probability_over=prob_over,
            confidence=0.9, # Bayesian is mathematically rigorous
            weight=self.weight,
            reasons=[
                f"Prior (L{len(long_term)}): {mu_0:.2f}",
                f"Evidence (L{n}): {x_bar:.2f}",
                f"Posterior: {mu_post:.2f}"
            ],
            metadata={"mu_post": mu_post, "sigma_post": sigma_post}
        )
