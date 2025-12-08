"""
Processed Data Storage
======================
Saves cleaned/processed data as Parquet or CSV.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ProcessedDataStorage:
    """Handles storage of processed/cleaned data"""
    
    def __init__(self, base_dir: Path, format: str = 'parquet'):
        """
        Initialize processed data storage.
        
        Args:
            base_dir: Base directory for processed data (e.g., ./data/processed)
            format: Storage format ('parquet' or 'csv')
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.format = format.lower()
        
        if self.format not in ['parquet', 'csv']:
            raise ValueError(f"Unsupported format: {format}. Use 'parquet' or 'csv'")
    
    def save_dataframe(
        self,
        df: pd.DataFrame,
        name: str,
        date: Optional[str] = None,
        append: bool = False
    ) -> Path:
        """
        Save DataFrame to file.
        
        Args:
            df: DataFrame to save
            name: Dataset name (e.g., 'player_stats', 'matchups')
            date: Date string (YYYY-MM-DD) or None for today
            append: If True, append to existing file; if False, overwrite
        
        Returns:
            Path to saved file
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Create date directory
        date_dir = self.base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        extension = 'parquet' if self.format == 'parquet' else 'csv'
        filename = f"{name}.{extension}"
        filepath = date_dir / filename
        
        try:
            if self.format == 'parquet':
                if append and filepath.exists():
                    # Read existing and append
                    existing_df = pd.read_parquet(filepath)
                    df = pd.concat([existing_df, df], ignore_index=True)
                    df = df.drop_duplicates()  # Remove duplicates
                
                df.to_parquet(filepath, index=False, engine='pyarrow')
            else:  # CSV
                mode = 'a' if append and filepath.exists() else 'w'
                header = not (append and filepath.exists())
                df.to_csv(filepath, index=False, mode=mode, header=header)
            
            logger.info(f"Saved processed data to {filepath} ({len(df)} rows)")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save processed data: {e}")
            raise
    
    def save_dict_list(
        self,
        data: List[Dict[str, Any]],
        name: str,
        date: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save list of dicts as DataFrame.
        
        Args:
            data: List of dicts
            name: Dataset name
            date: Date string or None for today
            schema: Optional schema dict for validation
        
        Returns:
            Path to saved file
        """
        if not data:
            logger.warning(f"No data to save for {name}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Apply schema if provided (ensure all columns exist)
        if schema:
            for col, default in schema.items():
                if col not in df.columns:
                    df[col] = default
        
        # Clean data
        df = self._clean_dataframe(df)
        
        return self.save_dataframe(df, name, date)
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame:
        - Remove duplicates
        - Normalize column names
        - Handle missing values
        - Round numeric columns
        """
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Normalize column names (lowercase, replace spaces with underscores)
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Round numeric columns
        numeric_cols = df.select_dtypes(include=['float64', 'float32']).columns
        for col in numeric_cols:
            df[col] = df[col].round(2)
        
        return df
    
    def load_dataframe(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Load DataFrame from file"""
        try:
            if filepath.suffix == '.parquet':
                return pd.read_parquet(filepath)
            else:
                return pd.read_csv(filepath)
        except Exception as e:
            logger.error(f"Failed to load processed data from {filepath}: {e}")
            return None

