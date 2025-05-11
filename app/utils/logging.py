"""
Logging utilities for the application.
"""

import logging
import sys
from typing import Optional

from app.config.settings import settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the given name and level.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (default: from settings)
        
    Returns:
        A configured logger
    """
    logger = logging.getLogger(name)
    
    # Set level from parameter or settings
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level))
    
    # Add handler if not already added
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger