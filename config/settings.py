"""
Configuration Settings for NBA Betting System
=============================================
Centralized configuration management using environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, use environment variables only
    pass


class Config:
    """Centralized configuration for NBA Betting System"""
    
    # ========================================================================
    # Betting Thresholds
    # ========================================================================
    MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', '40.0'))
    """Minimum confidence score for initial recommendations (default: 40.0)
    
    Note: This is a relaxed threshold to let more bets through to enhanced filtering.
    The enhanced filtering script will apply stricter quality filters (B-Tier or better).
    """
    
    MIN_EDGE_PERCENTAGE = float(os.getenv('MIN_EDGE_PERCENTAGE', '3.0'))
    """Minimum edge percentage for value bets (default: 3.0)"""
    
    # Confidence thresholds for recommendation strength
    VERY_HIGH_CONFIDENCE = float(os.getenv('VERY_HIGH_CONFIDENCE', '75.0'))
    HIGH_CONFIDENCE = float(os.getenv('HIGH_CONFIDENCE', '65.0'))
    MEDIUM_CONFIDENCE = float(os.getenv('MEDIUM_CONFIDENCE', '55.0'))
    
    # Edge thresholds for recommendation strength
    VERY_HIGH_EDGE = float(os.getenv('VERY_HIGH_EDGE', '8.0'))
    HIGH_EDGE = float(os.getenv('HIGH_EDGE', '5.0'))
    MEDIUM_EDGE = float(os.getenv('MEDIUM_EDGE', '3.0'))
    
    # ========================================================================
    # Scraping Configuration
    # ========================================================================
    SCRAPER_TIMEOUT = int(os.getenv('SCRAPER_TIMEOUT', '30000'))  # milliseconds
    """Timeout for web scraping operations in milliseconds (default: 30000)"""
    
    SCRAPER_PAGE_LOAD_TIMEOUT = int(os.getenv('SCRAPER_PAGE_LOAD_TIMEOUT', '60000'))  # milliseconds
    """Page load timeout for Playwright (default: 60000)"""
    
    HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
    """Run browser in headless mode (default: true)"""
    
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '3'))
    """Maximum concurrent scraping requests (default: 3)"""
    
    # ========================================================================
    # Retry Configuration
    # ========================================================================
    RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
    """Maximum retry attempts for failed operations (default: 3)"""
    
    RETRY_MIN_WAIT = float(os.getenv('RETRY_MIN_WAIT', '2.0'))
    """Minimum wait time between retries in seconds (default: 2.0)"""
    
    RETRY_MAX_WAIT = float(os.getenv('RETRY_MAX_WAIT', '10.0'))
    """Maximum wait time between retries in seconds (default: 10.0)"""
    
    # ========================================================================
    # API Configuration
    # ========================================================================
    DATABALLR_BASE_URL = os.getenv('DATABALLR_BASE_URL', 'https://www.databallr.com')
    """Base URL for DataBallr API"""
    
    DATABALLR_API_KEY = os.getenv('DATABALLR_API_KEY', '')
    """API key for DataBallr (if required)"""
    
    SPORTSBET_BASE_URL = os.getenv('SPORTSBET_BASE_URL', 'https://www.sportsbet.com.au')
    """Base URL for Sportsbet"""
    
    # ========================================================================
    # Caching Configuration
    # ========================================================================
    CACHE_TTL = int(os.getenv('CACHE_TTL', '86400'))  # 24 hours in seconds
    """Time-to-live for cached data in seconds (default: 86400 = 24 hours)"""
    
    USE_CACHE = os.getenv('USE_CACHE', 'true').lower() == 'true'
    """Enable caching for player stats (default: true)"""
    
    # Cache TTLs by data type (hours)
    CACHE_TTL_MINUTES = int(os.getenv('CACHE_TTL_MINUTES', '24'))
    """TTL for minutes data (hours, default: 24)"""
    
    CACHE_TTL_INJURIES = int(os.getenv('CACHE_TTL_INJURIES', '6'))
    """TTL for injury data (hours, default: 6)"""
    
    CACHE_TTL_ROLE = int(os.getenv('CACHE_TTL_ROLE', '48'))
    """TTL for role data (hours, default: 48)"""
    
    # Market-specific tier thresholds
    MARKET_TIER_THRESHOLDS = {
        "player_prop": {"A": 65, "B": 50, "C": 35},
        "team_sides": {"A": 65, "B": 50, "C": 40},
        "totals": {"A": 65, "B": 50, "C": 45}
    }
    
    # Market weights for soft floor
    MARKET_WEIGHTS = {
        "player_prop": 0.92,
        "team_sides": 1.0,
        "totals": 1.05
    }
    
    # CLV tracking
    ENABLE_CLV_TRACKING = os.getenv('ENABLE_CLV_TRACKING', 'true').lower() == 'true'
    """Enable CLV tracking (default: true)"""
    
    CLV_DB_PATH = os.getenv('CLV_DB_PATH', 'data/clv_tracking.db')
    """Path to CLV tracking database (default: data/clv_tracking.db)"""
    
    # ========================================================================
    # Statistical Model Configuration
    # ========================================================================
    MODEL_CONFIDENCE_WEIGHT = float(os.getenv('MODEL_CONFIDENCE_WEIGHT', '0.70'))
    """Weight for model confidence in final score (default: 0.70 = 70%)"""
    
    HISTORICAL_WEIGHT = float(os.getenv('HISTORICAL_WEIGHT', '0.30'))
    """Weight for historical data in final score (default: 0.30 = 30%)"""
    
    # Sample size thresholds for confidence boosts
    SAMPLE_SIZE_LARGE = int(os.getenv('SAMPLE_SIZE_LARGE', '15'))
    """Large sample size threshold (default: 15)"""
    
    SAMPLE_SIZE_MEDIUM = int(os.getenv('SAMPLE_SIZE_MEDIUM', '10'))
    """Medium sample size threshold (default: 10)"""
    
    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    """Logging level (DEBUG, INFO, WARNING, ERROR) (default: INFO)"""
    
    LOG_FILE = os.getenv('LOG_FILE', 'logs/nba_betting_system.log')
    """Path to log file (default: logs/nba_betting_system.log)"""
    
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
    """Maximum log file size before rotation (default: 10MB)"""
    
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    """Number of backup log files to keep (default: 5)"""
    
    # ========================================================================
    # Data Processing Configuration
    # ========================================================================
    MAX_GAMES_TO_ANALYZE = int(os.getenv('MAX_GAMES_TO_ANALYZE', '10'))
    """Maximum number of games to analyze in a single run (default: 10)"""
    
    MAX_PLAYER_PROPS_PER_GAME = int(os.getenv('MAX_PLAYER_PROPS_PER_GAME', '50'))
    """Maximum player props to analyze per game (default: 50)"""
    
    # ========================================================================
    # File Paths
    # ========================================================================
    DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
    """Base directory for data files"""
    
    CACHE_DIR = Path(os.getenv('CACHE_DIR', 'data/cache'))
    """Directory for cache files"""
    
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'data/outputs'))
    """Directory for output files"""
    
    LOGS_DIR = Path(os.getenv('LOGS_DIR', 'logs'))
    """Directory for log files"""
    
    # ========================================================================
    # Validation
    # ========================================================================
    @classmethod
    def validate(cls) -> list:
        """
        Validate configuration values.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        if cls.MIN_CONFIDENCE < 0 or cls.MIN_CONFIDENCE > 100:
            errors.append(f"MIN_CONFIDENCE must be between 0 and 100, got {cls.MIN_CONFIDENCE}")
        
        if cls.RETRY_MAX_ATTEMPTS < 1:
            errors.append(f"RETRY_MAX_ATTEMPTS must be at least 1, got {cls.RETRY_MAX_ATTEMPTS}")
        
        if cls.SCRAPER_TIMEOUT < 1000:
            errors.append(f"SCRAPER_TIMEOUT must be at least 1000ms, got {cls.SCRAPER_TIMEOUT}")
        
        if cls.MODEL_CONFIDENCE_WEIGHT + cls.HISTORICAL_WEIGHT != 1.0:
            errors.append(
                f"MODEL_CONFIDENCE_WEIGHT ({cls.MODEL_CONFIDENCE_WEIGHT}) + "
                f"HISTORICAL_WEIGHT ({cls.HISTORICAL_WEIGHT}) must equal 1.0"
            )
        
        return errors
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("=" * 60)
        print("NBA Betting System Configuration")
        print("=" * 60)
        print(f"MIN_CONFIDENCE: {cls.MIN_CONFIDENCE}")
        print(f"MIN_EDGE_PERCENTAGE: {cls.MIN_EDGE_PERCENTAGE}")
        print(f"SCRAPER_TIMEOUT: {cls.SCRAPER_TIMEOUT}ms")
        print(f"HEADLESS_MODE: {cls.HEADLESS_MODE}")
        print(f"RETRY_MAX_ATTEMPTS: {cls.RETRY_MAX_ATTEMPTS}")
        print(f"CACHE_TTL: {cls.CACHE_TTL}s ({cls.CACHE_TTL / 3600:.1f} hours)")
        print(f"LOG_LEVEL: {cls.LOG_LEVEL}")
        print(f"MAX_GAMES_TO_ANALYZE: {cls.MAX_GAMES_TO_ANALYZE}")
        print("=" * 60)


# Validate configuration on import
validation_errors = Config.validate()
if validation_errors:
    import warnings
    for error in validation_errors:
        warnings.warn(f"Configuration error: {error}", UserWarning)

