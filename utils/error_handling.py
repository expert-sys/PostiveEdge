"""
Error Handling Utilities for NBA Betting System
================================================
Provides consistent error handling patterns for external calls and operations.
"""

import logging
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_call(
    func: Callable[..., T],
    default: T = None,
    log_error: bool = True,
    reraise: bool = False,
    error_context: Optional[str] = None
) -> Optional[T]:
    """
    Safely call a function, catching all exceptions and returning a default value.
    
    Args:
        func: Function to call
        default: Default value to return on error (default: None)
        log_error: Whether to log errors (default: True)
        reraise: Whether to re-raise exceptions after logging (default: False)
        error_context: Additional context string for error messages
    
    Returns:
        Function result or default value on error
    
    Example:
        result = safe_call(lambda: risky_operation(), default={})
    """
    try:
        return func()
    except Exception as e:
        context = f" in {error_context}" if error_context else ""
        if log_error:
            logger.error(f"Error{context}: {e}", exc_info=True)
        if reraise:
            raise
        return default


def safe_scrape(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that wraps scraping functions with error handling.
    Returns None on error instead of raising exceptions.
    
    Args:
        func: Scraping function to wrap
    
    Returns:
        Wrapped function that returns None on error
    
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
            logger.error(
                f"Error in {func.__name__}: {e}",
                exc_info=True,
                extra={'args': args, 'kwargs': kwargs}
            )
            return None
    return wrapper


def safe_api_call(
    func: Callable[..., T],
    default: T = None,
    log_error: bool = True
) -> Optional[T]:
    """
    Safely call an API function, handling network errors gracefully.
    
    Args:
        func: API function to call
        default: Default value to return on error (default: None)
        log_error: Whether to log errors (default: True)
    
    Returns:
        Function result or default value on error
    
    Example:
        result = safe_api_call(lambda: api.get_data(), default=[])
    """
    try:
        return func()
    except ConnectionError as e:
        if log_error:
            logger.error(f"Connection error in API call: {e}")
        return default
    except TimeoutError as e:
        if log_error:
            logger.warning(f"Timeout in API call: {e}")
        return default
    except Exception as e:
        if log_error:
            logger.error(f"Error in API call: {e}", exc_info=True)
        return default


def handle_import_error(module_name: str, fallback: Any = None, error_message: Optional[str] = None):
    """
    Safely import a module with error handling.
    
    Args:
        module_name: Name of module to import
        fallback: Value to return if import fails
        error_message: Custom error message (optional)
    
    Returns:
        Imported module or fallback value
    
    Example:
        scraper = handle_import_error('scrapers.my_scraper', fallback=None)
    """
    try:
        module = __import__(module_name, fromlist=[''])
        return module
    except ImportError as e:
        msg = error_message or f"Could not import {module_name}"
        logger.warning(f"{msg}: {e}")
        return fallback
    except Exception as e:
        logger.error(f"Unexpected error importing {module_name}: {e}")
        return fallback


def validate_result(result: Any, validator: Callable[[Any], bool], error_message: str) -> bool:
    """
    Validate a result using a validator function.
    
    Args:
        result: Result to validate
        validator: Function that returns True if result is valid
        error_message: Message to log if validation fails
    
    Returns:
        True if valid, False otherwise
    
    Example:
        if not validate_result(data, lambda x: x is not None, "Data is None"):
            return None
    """
    try:
        if not validator(result):
            logger.warning(error_message)
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating result: {e}")
        return False


def log_and_continue(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that logs errors and continues execution (returns None).
    Useful for non-critical operations in loops.
    
    Args:
        func: Function to wrap
    
    Returns:
        Wrapped function that returns None on error
    
    Example:
        @log_and_continue
        def process_item(item):
            # process item
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Error in {func.__name__}: {e} (continuing)")
            return None
    return wrapper


def with_error_context(context: str):
    """
    Decorator that adds context to error messages.
    
    Args:
        context: Context string to add to error messages
    
    Returns:
        Decorator function
    
    Example:
        @with_error_context("scraping match data")
        def scrape_match(url):
            # scraping logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error {context}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

