"""
Data processor for handling historical sports data.
Supports CSV, JSON, and direct data input.
"""

import csv
import json
from typing import List, Dict, Union, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta


class DataProcessor:
    """Processes and manages historical sports data."""
    
    @staticmethod
    def load_csv(file_path: str) -> List[Dict]:
        """Load data from CSV file."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or invalid")
            data = list(reader)
        
        return data
    
    @staticmethod
    def load_json(file_path: str) -> Union[List, Dict]:
        """Load data from JSON file."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    @staticmethod
    def save_json(data: Union[List, Dict], file_path: str) -> None:
        """Save data to JSON file."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    @staticmethod
    def extract_outcomes(
        data: List[Dict],
        outcome_field: str,
        convert_to_numeric: bool = True
    ) -> List[Union[int, float]]:
        """
        Extract outcomes from data list.
        
        Args:
            data: List of dictionaries containing outcome data
            outcome_field: Field name containing the outcome
            convert_to_numeric: If True, converts to int/float
        
        Returns:
            List of outcomes
        """
        outcomes = []
        for record in data:
            if outcome_field not in record:
                raise ValueError(f"Field '{outcome_field}' not found in data")
            
            value = record[outcome_field]
            
            if convert_to_numeric:
                try:
                    # Try int first, then float
                    if isinstance(value, str):
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    else:
                        value = float(value) if isinstance(value, (int, float)) else float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot convert '{value}' to numeric")
            
            outcomes.append(value)
        
        return outcomes
    
    @staticmethod
    def filter_by_window(
        data: List[Dict],
        date_field: str = None,
        window_games: int = None,
        window_days: int = None,
        recent_first: bool = True
    ) -> List[Dict]:
        """
        Filter data by time window.
        
        Args:
            data: List of records with date information
            date_field: Field name containing date
            window_games: Limit to last N games
            window_days: Limit to last N days
            recent_first: If True, sorts most recent first
        
        Returns:
            Filtered data
        """
        filtered = data.copy()
        
        # Filter by date window if specified
        if window_days and date_field:
            cutoff_date = datetime.now() - timedelta(days=window_days)
            filtered = [
                r for r in filtered
                if DataProcessor._parse_date(r.get(date_field)) >= cutoff_date
            ]
        
        # Sort by date if available (most recent first)
        if date_field and recent_first:
            filtered.sort(
                key=lambda x: DataProcessor._parse_date(x.get(date_field)),
                reverse=True
            )
        
        # Limit to last N games
        if window_games:
            filtered = filtered[:window_games]
        
        return filtered
    
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """
        Parse various date formats.
        """
        if isinstance(date_str, datetime):
            return date_str
        
        if not isinstance(date_str, str):
            return datetime.now()
        
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%d-%m-%Y",
            "%d-%m-%Y %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If no format matches, return now
        return datetime.now()
    
    @staticmethod
    def calculate_recency_weights(
        data: List[Dict],
        date_field: str = None,
        decay_factor: float = 0.95
    ) -> List[float]:
        """
        Calculate exponential decay weights for recency.
        More recent games get higher weights.
        
        Args:
            data: List of records (should be sorted recent-first)
            date_field: Field name containing date (optional, uses position if not provided)
            decay_factor: Decay factor (0-1), lower = stronger recency emphasis
        
        Returns:
            List of weights
        """
        n = len(data)
        weights = [decay_factor ** i for i in range(n)]
        
        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]
        
        return weights
    
    @staticmethod
    def apply_opponent_adjustment(
        outcomes: List[Union[int, float]],
        opponent_strengths: List[float]
    ) -> List[Union[int, float]]:
        """
        Adjust outcomes based on opponent strength.
        
        Args:
            outcomes: List of binary/numeric outcomes
            opponent_strengths: Strength ratings (0-1, higher = stronger)
        
        Returns:
            Adjusted outcomes
        """
        if len(outcomes) != len(opponent_strengths):
            raise ValueError("Outcomes and opponent strengths must have same length")
        
        adjusted = []
        for outcome, strength in zip(outcomes, opponent_strengths):
            # Simple adjustment: scale outcome by inverse of opponent strength
            # Stronger opponent (higher strength) = lower adjusted probability
            if isinstance(outcome, (int, float)) and outcome in [0, 1]:
                # Binary outcome
                adjusted_value = outcome / (1 + strength * 0.5)
            else:
                # Continuous outcome
                adjusted_value = outcome / (1 + strength * 0.2)
            
            adjusted.append(adjusted_value)
        
        return adjusted
    
    @staticmethod
    def calculate_home_away_split(
        data: List[Dict],
        outcome_field: str,
        location_field: str
    ) -> Tuple[List[Union[int, float]], List[Union[int, float]]]:
        """
        Split outcomes by home/away location.
        
        Returns:
            Tuple of (home_outcomes, away_outcomes)
        """
        home_outcomes = []
        away_outcomes = []
        
        for record in data:
            outcome = record.get(outcome_field)
            location = str(record.get(location_field, "")).lower()
            
            if outcome is None:
                continue
            
            try:
                if '.' in str(outcome):
                    outcome = float(outcome)
                else:
                    outcome = int(outcome)
            except (ValueError, TypeError):
                continue
            
            if "home" in location or location == "h":
                home_outcomes.append(outcome)
            elif "away" in location or location == "a":
                away_outcomes.append(outcome)
        
        return home_outcomes, away_outcomes
    
    @staticmethod
    def minutes_adjustment(
        outcomes: List[Union[int, float]],
        minutes_played: List[float],
        full_game_minutes: float = 90.0
    ) -> List[Union[int, float]]:
        """
        Adjust outcomes based on minutes played (for player props).
        
        Args:
            outcomes: List of outcomes (goals, assists, etc.)
            minutes_played: List of minutes played
            full_game_minutes: Full game duration (default 90 for soccer)
        
        Returns:
            Adjusted outcomes to full game equivalents
        """
        if len(outcomes) != len(minutes_played):
            raise ValueError("Outcomes and minutes must have same length")
        
        adjusted = []
        for outcome, minutes in zip(outcomes, minutes_played):
            if minutes > 0:
                adjusted_value = outcome * (full_game_minutes / minutes)
            else:
                adjusted_value = 0
            adjusted.append(adjusted_value)
        
        return adjusted


class SampleDataGenerator:
    """Generate sample historical data for testing."""
    
    @staticmethod
    def generate_binary_outcomes(
        count: int,
        probability: float = 0.5,
        seed: int = None
    ) -> List[int]:
        """Generate binary outcomes (0/1) with given probability."""
        import random
        if seed is not None:
            random.seed(seed)
        
        return [1 if random.random() < probability else 0 for _ in range(count)]
    
    @staticmethod
    def generate_continuous_outcomes(
        count: int,
        mean: float = 2.5,
        std_dev: float = 1.0,
        seed: int = None
    ) -> List[float]:
        """Generate continuous outcomes (e.g., assist counts) from normal distribution."""
        import random
        if seed is not None:
            random.seed(seed)
        
        return [max(0, random.gauss(mean, std_dev)) for _ in range(count)]
    
    @staticmethod
    def generate_sample_player_data(
        game_count: int = 20,
        goal_probability: float = 0.35,
        seed: int = 42
    ) -> List[Dict]:
        """Generate sample player performance data."""
        import random
        from datetime import datetime, timedelta
        
        if seed is not None:
            random.seed(seed)
        
        data = []
        base_date = datetime.now()
        
        for i in range(game_count):
            game_date = base_date - timedelta(days=game_count - i - 1)
            data.append({
                'date': game_date.strftime("%Y-%m-%d"),
                'opponent': f"Team_{random.choice(['A', 'B', 'C', 'D', 'E'])}",
                'location': random.choice(['home', 'away']),
                'minutes_played': random.randint(45, 90),
                'goals': 1 if random.random() < goal_probability else 0,
                'assists': max(0, random.gauss(0.3, 0.5)),
                'shots': random.randint(0, 6),
                'opponent_strength': round(random.uniform(0.3, 0.9), 2)
            })
        
        return data
