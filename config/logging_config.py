"""
Centralized Logging Configuration
==================================
Provides clean, consistent logging across the application with support for
quiet/verbose modes and easy copy-paste diagnostics.

Default: INFO level (shows progress like "Starting", "Found X games")
Quiet: WARNING level (errors and warnings only)
Debug: DEBUG level (includes cache hits, scraping details)
"""

import logging
import os
import sys
from typing import Optional


# Default log level from environment variable (INFO shows progress, WARNING only shows errors)
_DEFAULT_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
_LOG_LEVEL_MAP = {
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}


def get_log_level(level_name: Optional[str] = None) -> int:
    """
    Get logging level from name or environment variable.
    
    Args:
        level_name: Level name (ERROR, WARNING, INFO, DEBUG) or None to use env/default
    
    Returns:
        Logging level constant
    """
    if level_name:
        return _LOG_LEVEL_MAP.get(level_name.upper(), logging.WARNING)
    return _LOG_LEVEL_MAP.get(_DEFAULT_LOG_LEVEL, logging.WARNING)


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        level: Log level (ERROR, WARNING, INFO, DEBUG) - overrides env/quiet/verbose
        format_string: Custom format string (default: clean [LEVEL] message)
        quiet: If True, only ERROR level
        verbose: If True, INFO level (overrides quiet)
    """
    # Determine log level
    if quiet and not verbose:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.INFO
    elif level:
        log_level = get_log_level(level)
    else:
        log_level = get_log_level()  # Use default from env
    
    # Default format: clean [LEVEL] message (no timestamps for easy copy-paste)
    if format_string is None:
        format_string = "[%(levelname)s] %(message)s"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler with clean format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set level for common loggers to prevent noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with centralized configuration.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If root logger hasn't been configured, set it up with defaults
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        setup_logging()
    
    return logger


# Auto-setup on import if LOG_LEVEL is set
if _DEFAULT_LOG_LEVEL in _LOG_LEVEL_MAP:
    setup_logging()
