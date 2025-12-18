import math
import statistics
from datetime import datetime
from typing import List, Tuple
from domain import ModelInput, ModelOutput, GameLogEntry

class RegressionModel:
    """
    🟡 MODEL 3 — Regression-Based Expectation Model
    
    A statistical model mapping inputs → output.
    Features: Minutes, Home/Away, Days Rest
    """
    
    def __init__(self, weight: float = 0.20):
        self.weight = weight
        self.name = "Regression (Linear)"
        
    def _parse_date(self, date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return datetime.now() # Fallback

    def _get_days_rest(self, current_date: datetime, prev_game_date: datetime) -> float:
        delta = (current_date - prev_game_date).days
        return min(float(delta), 5.0) # Cap at 5 days

    def _solve_ols(self, X: List[List[float]], y: List[float]) -> List[float]:
        """
        Solves beta = (X^T X)^-1 X^T y using basic matrix ops.
        If singular or unstable, returns zeroes.
        """
        try:
            n = len(X)
            if n == 0: return []
            k = len(X[0]) # num features
            
            # Transpose X
            Xt = [[X[i][j] for i in range(n)] for j in range(k)]
            
            # Xt * X (k x k matrix)
            XtX = [[sum(Xt[i][m] * X[m][j] for m in range(n)) for j in range(k)] for i in range(k)]
            
            # Xt * y (k x 1 vector)
            Xty = [sum(Xt[i][m] * y[m] for m in range(n)) for i in range(k)]
            
            # Inverse of XtX (Gauss-Jordan)
            # Add identity matrix to right side
            aug = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(XtX)]
            
            # Forward elimination
            for i in range(k):
                pivot = aug[i][i]
                if abs(pivot) < 1e-9: return [0.0]*k # Singular
                
                # Normalize row i
                for j in range(2*k):
                    aug[i][j] /= pivot
                
                # Eliminate other rows
                for r in range(k):
                    if r != i:
                        factor = aug[r][i]
                        for j in range(2*k):
                            aug[r][j] -= factor * aug[i][j]
            
            # Extract inverse
            inv = [row[k:] for row in aug]
            
            # Beta = inv * Xty
            beta = [sum(inv[i][j] * Xty[j] for j in range(k)) for i in range(k)]
            
            return beta
        except:
            return [0.0] * len(X[0])

    def generate(self, input_data: ModelInput) -> ModelOutput:
        games = input_data.game_log
        if len(games) < 10:
             return ModelOutput(self.name, 0.0, 0.0, 0.0, weight=self.weight, reasons=["Need 10+ games for regression"])
             
        # Prepare Training Data
        X = []
        y = []
        
        # Sort by date ascending
        sorted_games = sorted(games, key=lambda x: x.game_date)
        
        for i in range(1, len(sorted_games)):
            g = sorted_games[i]
            prev = sorted_games[i-1]
            
            if g.minutes <= 0: continue
            
            is_home = 1.0 if g.home_away == "HOME" else 0.0
            days_rest = self._get_days_rest(self._parse_date(g.game_date), self._parse_date(prev.game_date))
            
            # Bias term (1.0), Minutes, IsHome, DaysRest
            X.append([1.0, g.minutes, is_home, days_rest])
            y.append(float(getattr(g, input_data.stat_type, 0)))
            
        if len(X) < 5:
            return ModelOutput(self.name, 0.0, 0.0, 0.0, weight=self.weight, reasons=["Not enough valid samples"])

        # Train
        beta = self._solve_ols(X, y)
        
        if all(b == 0.0 for b in beta):
             return ModelOutput(self.name, 0.0, 0.0, 0.0, weight=self.weight, reasons=["Singular matrix / training failed"])

        # Predict
        # Input features
        # We need "current" context. Assuming context is today.
        # Days rest? We don't have last game date easily unless we look at log.
        last_game_date = self._parse_date(sorted_games[-1].game_date)
        today = datetime.now()
        curr_rest = self._get_days_rest(today, last_game_date)
        
        input_mins = input_data.minutes_projected or 30.0
        input_home = 1.0 if input_data.is_home else 0.0
        
        x_new = [1.0, input_mins, input_home, curr_rest]
        
        prediction = sum(b * x for b, x in zip(beta, x_new))
        
        # Calculate Error / Variance (RMSE)
        residuals = []
        for i in range(len(X)):
            pred_i = sum(beta[j] * X[i][j] for j in range(len(beta)))
            residuals.append((y[i] - pred_i)**2)
        
        mse = sum(residuals) / len(residuals)
        std_err = math.sqrt(mse)
        
        # Prob over
        if std_err > 0:
            z = (input_data.line - prediction) / std_err
            prob = 0.5 * (1 - math.erf(z / math.sqrt(2)))
        else:
            prob = 1.0 if prediction > input_data.line else 0.0
            
        return ModelOutput(
            model_name=self.name,
            expected_value=prediction,
            probability_over=prob,
            confidence=0.5, # Moderate confidence
            weight=self.weight,
            reasons=[f"Beta: {beta}", f"Intercept: {beta[0]:.2f}, Mins Coeff: {beta[1]:.2f}"],
            metadata={"beta": beta, "rmse": std_err}
        )
