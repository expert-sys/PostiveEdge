"""
Schema Mapping - Handle Dynamic Structure Changes
=================================================
Automatically maps renamed fields and handles missing keys safely.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SchemaMapper:
    """
    Maps response fields to expected schema, handling:
    - Renamed fields
    - Missing keys
    - Type conversions
    - Default values
    """
    
    def __init__(self, schema_file: Optional[Path] = None):
        """
        Initialize schema mapper.
        
        Args:
            schema_file: Optional path to schema mapping file (JSON)
        """
        self.field_mappings: Dict[str, List[str]] = {}
        self.default_values: Dict[str, Any] = {}
        self.type_converters: Dict[str, Callable] = {}
        
        if schema_file and schema_file.exists():
            self.load_mappings(schema_file)
    
    def load_mappings(self, schema_file: Path):
        """Load field mappings from JSON file"""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.field_mappings = data.get('field_mappings', {})
                self.default_values = data.get('default_values', {})
                logger.info(f"Loaded schema mappings from {schema_file}")
        except Exception as e:
            logger.warning(f"Failed to load schema mappings: {e}")
    
    def register_field_mapping(self, expected_field: str, possible_names: List[str], default: Any = None):
        """
        Register a field mapping.
        
        Args:
            expected_field: The expected field name in our schema
            possible_names: List of possible field names in responses
            default: Default value if field not found
        """
        self.field_mappings[expected_field] = possible_names
        if default is not None:
            self.default_values[expected_field] = default
    
    def register_type_converter(self, field: str, converter: Callable):
        """Register a type converter for a field"""
        self.type_converters[field] = converter
    
    def map_field(self, data: Dict, expected_field: str) -> Any:
        """
        Map a field from response data to expected schema.
        
        Args:
            data: Response data dict
            expected_field: Expected field name
        
        Returns:
            Field value or default
        """
        # Check if field exists directly
        if expected_field in data:
            value = data[expected_field]
        else:
            # Try alternative names
            value = None
            possible_names = self.field_mappings.get(expected_field, [])
            
            for name in possible_names:
                if name in data:
                    value = data[name]
                    # Log schema change warning
                    if name != expected_field:
                        logger.warning(
                            f"Schema change detected: '{name}' mapped to '{expected_field}'. "
                            f"Consider updating schema."
                        )
                    break
        
        # Use default if not found
        if value is None:
            value = self.default_values.get(expected_field)
            if value is None:
                logger.debug(f"Field '{expected_field}' not found, using None")
        
        # Apply type converter if registered
        if value is not None and expected_field in self.type_converters:
            try:
                value = self.type_converters[expected_field](value)
            except Exception as e:
                logger.warning(f"Type conversion failed for '{expected_field}': {e}")
                value = self.default_values.get(expected_field)
        
        return value
    
    def map_dict(self, data: Dict, expected_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map entire dict to expected schema.
        
        Args:
            data: Response data dict
            expected_schema: Dict of expected fields with defaults
        
        Returns:
            Mapped dict with all expected fields
        """
        mapped = {}
        
        for field, default in expected_schema.items():
            mapped[field] = self.map_field(data, field)
            if mapped[field] is None:
                mapped[field] = default
        
        return mapped
    
    def safe_get(self, data: Dict, *keys, default: Any = None) -> Any:
        """
        Safely get nested value from dict.
        
        Args:
            data: Dict to search
            *keys: Key path (e.g., 'player', 'stats', 'points')
            default: Default value if path not found
        
        Returns:
            Value or default
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current if current is not None else default


# Common field mappings for DataballR
def get_databallr_schema_mapper() -> SchemaMapper:
    """Get pre-configured schema mapper for DataballR"""
    mapper = SchemaMapper()
    
    # Player stats field mappings
    mapper.register_field_mapping('points', ['points', 'pts', 'PTS', 'Points'], default=0)
    mapper.register_field_mapping('rebounds', ['rebounds', 'reb', 'REB', 'Rebounds', 'total_rebounds'], default=0)
    mapper.register_field_mapping('assists', ['assists', 'ast', 'AST', 'Assists'], default=0)
    mapper.register_field_mapping('steals', ['steals', 'stl', 'STL', 'Steals'], default=0)
    mapper.register_field_mapping('blocks', ['blocks', 'blk', 'BLK', 'Blocks'], default=0)
    mapper.register_field_mapping('turnovers', ['turnovers', 'tov', 'TOV', 'Turnovers'], default=0)
    mapper.register_field_mapping('minutes', ['minutes', 'min', 'MIN', 'Minutes', 'mp'], default=0.0)
    mapper.register_field_mapping('three_pt_made', ['three_pt_made', '3pm', '3PM', 'threes', 'three_pointers_made'], default=0)
    mapper.register_field_mapping('fg_made', ['fg_made', 'fgm', 'FGM', 'field_goals_made'], default=0)
    mapper.register_field_mapping('fg_attempted', ['fg_attempted', 'fga', 'FGA', 'field_goals_attempted'], default=0)
    
    # Date/time mappings
    mapper.register_field_mapping('date', ['date', 'game_date', 'Date', 'GAME_DATE'], default='')
    mapper.register_field_mapping('game_id', ['game_id', 'id', 'ID', 'gameId'], default='')
    
    # Team/opponent mappings
    mapper.register_field_mapping('opponent', ['opponent', 'opp', 'OPP', 'Opponent', 'vs'], default='')
    mapper.register_field_mapping('team', ['team', 'Team', 'TEAM'], default='')
    mapper.register_field_mapping('home_away', ['home_away', 'homeAway', 'location'], default='UNKNOWN')
    
    # Type converters
    mapper.register_type_converter('points', int)
    mapper.register_type_converter('rebounds', int)
    mapper.register_type_converter('assists', int)
    mapper.register_type_converter('steals', int)
    mapper.register_type_converter('blocks', int)
    mapper.register_type_converter('turnovers', int)
    mapper.register_type_converter('minutes', float)
    mapper.register_type_converter('three_pt_made', int)
    
    return mapper

