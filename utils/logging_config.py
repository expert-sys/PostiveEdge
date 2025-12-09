"""
Centralized Logging Configuration
==================================
Provides a reusable logging setup with rotation to prevent large log files.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup logger with rotation to prevent large log files.
    
    Args:
        name: Logger name (typically __name__)
        log_file: Path to log file (optional). If None, only console logging.
        level: Logging level (default: INFO)
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        format_string: Custom format string (optional)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = setup_logger(__name__, 'logs/app.log')
        >>> logger.info("This will be logged")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Default format
    if format_string is None:
        format_string = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (if log_file provided)
    if log_file:
        log_path = Path(log_file)
        # Create parent directories if they don't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # If no handlers, set up with defaults
        return setup_logger(name)
    return logger

