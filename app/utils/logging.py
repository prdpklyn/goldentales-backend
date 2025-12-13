# app/utils/logging.py
"""
GoldenTales Logging
===================
Centralized logging configuration.
"""

import logging
import sys
from typing import Optional
from functools import lru_cache

from app.config import settings


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). 
               Defaults based on environment.
    """
    if level is None:
        level = "DEBUG" if settings.debug else "INFO"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


@lru_cache()
def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    return logger


# Convenience instances for common loggers
app_logger = get_logger("goldentales")
api_logger = get_logger("goldentales.api")
ai_logger = get_logger("goldentales.ai")
