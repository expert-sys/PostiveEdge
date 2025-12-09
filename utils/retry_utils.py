"""
Retry Utilities for NBA Betting System
=======================================
Provides retry decorators with exponential backoff for resilient API calls and scraping.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    before_sleep_log,
    after_log
)
import logging
import requests
from typing import Callable, Type, Any, Optional
from functools import wraps

# Import config for default values
try:
    from config import Config
    DEFAULT_MAX_ATTEMPTS = Config.RETRY_MAX_ATTEMPTS
    DEFAULT_MIN_WAIT = Config.RETRY_MIN_WAIT
    DEFAULT_MAX_WAIT = Config.RETRY_MAX_WAIT
except ImportError:
    # Fallback if config not available
    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_MIN_WAIT = 2.0
    DEFAULT_MAX_WAIT = 10.0

logger = logging.getLogger(__name__)


def retry_api_call(
    max_attempts: int = None,
    min_wait: float = None,
    max_wait: float = None,
    exceptions: tuple = (requests.RequestException, ConnectionError, TimeoutError)
):
    """
    Decorator for API calls with exponential backoff retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from Config)
        min_wait: Minimum wait time between retries in seconds (default: from Config)
        max_wait: Maximum wait time between retries in seconds (default: from Config)
        exceptions: Tuple of exception types to retry on
    
    Example:
        @retry_api_call(max_attempts=3)
        def fetch_player_stats(player_id):
            response = requests.get(f"https://api.example.com/player/{player_id}")
            response.raise_for_status()
            return response.json()
    """
    # Use config defaults if not provided
    max_attempts = max_attempts or DEFAULT_MAX_ATTEMPTS
    min_wait = min_wait or DEFAULT_MIN_WAIT
    max_wait = max_wait or DEFAULT_MAX_WAIT
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def retry_scraper_call(
    max_attempts: int = None,
    min_wait: float = None,
    max_wait: float = None,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for web scraping functions with exponential backoff.
    
    More lenient than API calls - retries on any exception by default.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from Config)
        min_wait: Minimum wait time between retries in seconds (default: from Config)
        max_wait: Maximum wait time between retries in seconds (default: from Config)
        exceptions: Tuple of exception types to retry on (default: all exceptions)
    
    Example:
        @retry_scraper_call(max_attempts=3)
        def scrape_match_data(url):
            # scraping logic
            return data
    """
    # Use config defaults if not provided
    max_attempts = max_attempts or DEFAULT_MAX_ATTEMPTS
    min_wait = min_wait or DEFAULT_MIN_WAIT
    max_wait = max_wait or DEFAULT_MAX_WAIT
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def retry_if_none(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 5.0):
    """
    Decorator that retries if function returns None.
    
    Useful for scraping functions that might not find data on first try.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time between retries in seconds (default: 1.0)
        max_wait: Maximum wait time between retries in seconds (default: 5.0)
    
    Example:
        @retry_if_none(max_attempts=3)
        def find_element(page):
            element = page.query_selector('.target')
            return element  # Retries if None
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_result(lambda result: result is None),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=False
    )


def safe_scrape(func: Callable) -> Callable:
    """
    Wrapper that adds error handling to scraping functions.
    Returns None on error instead of raising exceptions.
    
    Use this when you want graceful failure rather than retries.
    
    Example:
        @safe_scrape
        def scrape_data(url):
            # scraping logic
            return data
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper


# Convenience decorators with common configurations
retry_3_times = retry_api_call(max_attempts=3)
retry_5_times = retry_api_call(max_attempts=5)
retry_scraper_3_times = retry_scraper_call(max_attempts=3)
retry_scraper_5_times = retry_scraper_call(max_attempts=5)

