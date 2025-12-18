from typing import List
import statistics
from domain import ModelInput, ModelOutput, GameLogEntry

class EmpiricalModel:
    """
    🟢 MODEL 2 — Rolling Distribution / Empirical Percentiles
    
    Instead of “projecting”, you ask:
    How often does this player beat this line historically under similar conditions?
    """
    
    def __init__(self, weight: float = 0.25):
        self.weight = weight
        self.name = "Empirical (Rolling Dist)"
        
    def generate(self, input_data: ModelInput) -> ModelOutput:
        if not input_data.game_log:
            return ModelOutput(self.name, 0.0, 0.0, 0.0, reasons=["No data"])
            
        # Target minutes
        target_minutes = input_data.minutes_projected or 30.0
        min_threshold = target_minutes * 0.8
        max_threshold = target_minutes * 1.2
        
        # Filter games with similar minutes
        similar_games = [
            g for g in input_data.game_log 
            if min_threshold <= g.minutes <= max_threshold
        ]
        
        # If not enough similar games, fallback to all recent games
        used_games = similar_games if len(similar_games) >= 5 else input_data.game_log[:30]
        used_games = used_games[:50] # Limit to last 50 relevant games
        
        if not used_games:
             return ModelOutput(self.name, 0.0, 0.0, 0.0, reasons=["No relevant games"])

        values = [getattr(g, input_data.stat_type, 0) for g in used_games]
        
        # Calculate Hit Rate
        hits = sum(1 for v in values if v > input_data.line)
        prob_over = hits / len(values)
        
        # Expected Value = Median (robust to outliers)
        expected_val = statistics.median(values)
        
        reasons = [
            f"Found {len(similar_games)} games with mins {min_threshold:.1f}-{max_threshold:.1f}",
            f"Used {len(used_games)} games for distribution",
            f"Hit Rate: {hits}/{len(values)} ({prob_over:.1%})"
        ]
        
        return ModelOutput(
            model_name=self.name,
            expected_value=expected_val,
            probability_over=prob_over,
            confidence=0.6 if len(similar_games) >= 10 else 0.4,
            weight=self.weight,
            reasons=reasons,
            metadata={
                "sample_size": len(used_games),
                "hit_rate": prob_over
            }
        )
