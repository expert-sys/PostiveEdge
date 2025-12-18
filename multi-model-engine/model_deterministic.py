import statistics
import math
from typing import List
from domain import ModelInput, ModelOutput, GameLogEntry

class DeterministicModel:
    """
    MODEL 1 — Deterministic Usage × Minutes
    
    A structured, physics-like model:
    Projection = Minutes × Usage × Pace × Opponent Modifier
    """
    
    def __init__(self, weight: float = 0.45):
        self.weight = weight
        self.name = "Deterministic (Usage x Min)"
        
    def generate(self, input_data: ModelInput) -> ModelOutput:
        """
        Generates projection based on deterministic factors.
        """
        if not input_data.game_log:
            return ModelOutput(
                model_name=self.name,
                expected_value=0.0,
                probability_over=0.0,
                confidence=0.0,
                reasons=["No game log data"]
            )
            
        # 1. Calculate Per-Minute production (Usage proxy)
        # Filter games with >0 minutes
        valid_games = [g for g in input_data.game_log if g.minutes > 0]
        if not valid_games:
            return ModelOutput(
                model_name=self.name,
                expected_value=0.0,
                probability_over=0.0,
                confidence=0.0,
                reasons=["No games with minutes"]
            )
            
        # Weighted average of Per-Minute production (Recent games weighted higher)
        pmr_values = []
        for g in valid_games[:20]: # Last 20 games
            val = getattr(g, input_data.stat_type, 0)
            pmr = val / g.minutes
            pmr_values.append(pmr)
            
        # Simple weighted average (linear decay)
        n = len(pmr_values)
        weights = [n - i for i in range(n)] # 20, 19, 18...
        weighted_pmr = sum(p * w for p, w in zip(pmr_values, weights)) / sum(weights)
        
        # 2. Get Minutes Projection
        # If not provided, assume average of last 5
        if input_data.minutes_projected:
            proj_minutes = input_data.minutes_projected
        else:
            recent_mins = [g.minutes for g in valid_games[:5]]
            proj_minutes = statistics.mean(recent_mins) if recent_mins else 0
            
        # 3. Pace Adjustment
        # Avg pace is approx 100
        pace_factor = 1.0
        if input_data.team_pace > 0 and input_data.opponent_pace > 0:
            game_pace = (input_data.team_pace + input_data.opponent_pace) / 2.0
            pace_factor = game_pace / 100.0
            
        # 4. Opponent Modifier
        # If we have def rating, use it. 
        # Lower def rating = harder opponent. League avg ~115 (modern NBA)
        opp_factor = 1.0
        if input_data.opponent_def_rating:
            # Normalized around 115. 
            # If opp def is 110 (good), factor should be < 1
            # If opp def is 120 (bad), factor should be > 1
            # But normally DefRtg is pts allowed per 100 poss.
            # So 110 is better defense than 120.
            # Production should be proportional to allowed points.
            opp_factor = input_data.opponent_def_rating / 115.0
            
        # Final Projection
        projection = weighted_pmr * proj_minutes * pace_factor * opp_factor
        
        # Calculate Probability Over Line
        # Assuming normal distribution with CV (Coefficient of Variation) derived from history
        stat_values = [getattr(g, input_data.stat_type, 0) for g in valid_games[:20]]
        if len(stat_values) > 1:
            std_dev = statistics.stdev(stat_values)
            mean_val = statistics.mean(stat_values)
            cv = std_dev / mean_val if mean_val > 0 else 0.5
        else:
            cv = 0.5
            
        # Projected Std Dev assumes same CV scales with projection
        proj_std = projection * cv
        
        if proj_std > 0:
            z_score = (input_data.line - projection) / proj_std
            # Cumulative distribution function for normal dist
            # P(X > line) = 1 - P(X < line)
            prob_over = 0.5 * (1 - math.erf(z_score / math.sqrt(2)))
        else:
            prob_over = 1.0 if projection > input_data.line else 0.0
            
        reasons = [
            f"Per-Min Rate: {weighted_pmr:.2f}",
            f"Proj Minutes: {proj_minutes:.1f}",
            f"Pace Factor: {pace_factor:.2f}",
            f"Opp Factor: {opp_factor:.2f}",
            f"Raw Proj: {projection:.2f}"
        ]
        
        return ModelOutput(
            model_name=self.name,
            expected_value=projection,
            probability_over=prob_over,
            confidence=0.7, # High confidence in base mechanics
            weight=self.weight,
            reasons=reasons,
            metadata={
                "base_projection": projection,
                "projected_minutes": proj_minutes,
                "weighted_pmr": weighted_pmr
            }
        )
