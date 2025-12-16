    def _validate_bet_mathematics(self, probability: float, odds: float, edge: float, ev: float, player_name: str = "") -> bool:
        """
        Enforce hard mathematical validation rules.
        
        Rules:
        1. Edge = (Market Odds - Fair Odds) / Fair Odds
        2. EV = (Odds × Probability) - 1  
        3. Edge and EV must have same sign (both positive or both negative)
        
        Returns: True if valid, False to block bet
        """
        if probability <= 0 or probability >= 1:
            logger.warning(f"[MATH BLOCK] {player_name}: Invalid probability {probability:.3f}")
            return False
        
        # Calculate fair odds from probability
        fair_odds = 1 / probability
        
        # Verify edge calculation
        expected_edge = (odds - fair_odds) / fair_odds
        edge_as_decimal = edge / 100  # Convert from percentage
        
        if abs(edge_as_decimal - expected_edge) > 0.02:  # Allow 2% tolerance
            logger.warning(f"[MATH BLOCK] {player_name}: Edge inconsistent - calculated {expected_edge*100:.1f}%, got {edge:.1f}%")
            return False
        
        # Verify EV calculation  
        expected_ev = (odds * probability) - 1
        ev_as_decimal = ev / 100  # Convert from percentage
        
        if abs(ev_as_decimal - expected_ev) > 0.02:  # Allow 2% tolerance
            logger.warning(f"[MATH BLOCK] {player_name}: EV inconsistent - calculated {expected_ev*100:.1f}%, got {ev:.1f}%")
            return False
        
        # Verify same sign (most critical check)
        edge_positive = edge > 0
        ev_positive = ev > 0
        
        if edge_positive != ev_positive:
            logger.error(f"[MATH BLOCK] {player_name}: CRITICAL ERROR - Edge={edge:.1f}%, EV={ev:.1f}% have opposite signs!")
            return False
        
        return True

    def _calculate_confidence_with_lag(self, final_probability: float, sample_size: int, variance: float) -> float:
        """
        Calculate confidence with volatility penalty lag.
        
        Confidence ≤ Final Probability − Volatility Penalty
        
        Args:
            final_probability: Final blended probability (0-1)
            sample_size: Number of games in sample
            variance: Statistical variance of outcomes
            
        Returns:
            Confidence score (0-100) that lags behind probability
        """
        # Base volatility penalty on sample size
        if sample_size >= 20:
            volatility_penalty = 0.05  # 5% penalty for good sample
        elif sample_size >= 10:
            volatility_penalty = 0.10  # 10% penalty for okay sample
        else:
            volatility_penalty = 0.15  # 15% penalty for small sample
        
        # Additional penalty for high variance
        if variance > 0.2:
            volatility_penalty += 0.05
        
        # Confidence MUST be below probability
        max_confidence_decimal = final_probability - volatility_penalty
        max_confidence = max_confidence_decimal * 100  # Convert to percentage
        
        # Start from a base confidence scaled with sample
        base_confidence = 50 + (sample_size / 2)  # Scale with sample (max ~65 for n=30)
        
        # Return the lower of calculated vs max allowed
        final_confidence = min(base_confidence, max_confidence, 85.0)  # Never exceed 85%
        final_confidence = max(0.0, final_confidence)  # Never below 0%
        
        return final_confidence

