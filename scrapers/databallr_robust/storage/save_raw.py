"""
Raw Data Storage
================
Saves raw scraped data as JSON files.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RawDataStorage:
    """Handles storage of raw scraped data"""
    
    def __init__(self, base_dir: Path):
        """
        Initialize raw data storage.
        
        Args:
            base_dir: Base directory for raw data (e.g., ./data/raw)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        data: Dict[str, Any],
        date: Optional[str] = None,
        source: str = "databallr",
        filename: Optional[str] = None
    ) -> Path:
        """
        Save raw data to JSON file.
        
        Args:
            data: Data dict to save
            date: Date string (YYYY-MM-DD) or None for today
            source: Data source name (e.g., 'databallr', 'gameplay')
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Create date directory
        date_dir = self.base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"{source}_{timestamp}.json"
        
        filepath = date_dir / filename
        
        # Add metadata
        data_with_meta = {
            'scraped_at': datetime.now().isoformat(),
            'source': source,
            'date': date,
            'data': data
        }
        
        # Save JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_with_meta, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved raw data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save raw data: {e}")
            raise
    
    def load(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Load raw data from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load raw data from {filepath}: {e}")
            return None

