"""
Exponential Backoff and Retry Logic
====================================
Handles retries with exponential backoff and jitter.
"""

import time
import random
import logging
from typing import Callable, Optional, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_errors: Tuple = (403, 429, 500, 502, 503, 504, TimeoutError, ConnectionError)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_errors = retryable_errors


def calculate_backoff_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
    
    Returns:
        Delay in seconds
    """
    # Exponential: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter (random 0-25% of delay)
    if config.jitter:
        jitter_amount = delay * 0.25 * random.random()
        delay = delay + jitter_amount
    
    return delay


def is_retryable_error(error: Exception, config: RetryConfig) -> bool:
    """Check if an error is retryable"""
    error_type = type(error)
    error_code = getattr(error, 'status_code', None) or getattr(error, 'code', None)
    
    # Check error type
    if error_type in config.retryable_errors:
        return True
    
    # Check HTTP status codes
    if error_code in config.retryable_errors:
        return True
    
    # Check error message for common patterns
    error_msg = str(error).lower()
    retryable_patterns = ['timeout', 'connection', '429', '403', '503', '502', '504']
    if any(pattern in error_msg for pattern in retryable_patterns):
        return True
    
    return False


def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable] = None
) -> Any:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        func: Function to retry
        config: Retry configuration (uses default if None)
        on_retry: Optional callback called before each retry
    
    Returns:
        Function result or raises last exception
    """
    if config is None:
        config = RetryConfig()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not is_retryable_error(e, config):
                    # Not retryable - raise immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
                
                if attempt < config.max_attempts - 1:
                    delay = calculate_backoff_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, delay, e)
                    
                    time.sleep(delay)
                else:
                    logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}")
        
        # All attempts exhausted
        raise last_exception
    
    return wrapper


def retry_request(
    request_func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute a request function with retry logic.
    
    Args:
        request_func: Function that makes a request
        *args: Positional arguments for request_func
        config: Retry configuration
        **kwargs: Keyword arguments for request_func
    
    Returns:
        Request result
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return request_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if not is_retryable_error(e, config):
                logger.error(f"Non-retryable error: {e}")
                raise
            
            if attempt < config.max_attempts - 1:
                delay = calculate_backoff_delay(attempt, config)
                logger.warning(
                    f"Request attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {config.max_attempts} request attempts failed")
    
    raise last_exception

