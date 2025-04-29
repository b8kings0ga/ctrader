"""Logging utility for ctrader."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.utils.config import config_manager


def setup_logger(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """Set up the logger with the specified configuration.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to the log file
    """
    # Get configuration from config manager
    if log_level is None:
        log_level = config_manager.get("general", "log_level", "INFO")
        
    logs_dir = config_manager.get("general", "logs_dir", "logs")
    
    if log_file is None:
        log_file = Path(logs_dir) / "ctrader.log"
    else:
        log_file = Path(logs_dir) / log_file
        
    # Create logs directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    # Add file logger
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",  # Rotate when file reaches 10 MB
        retention="1 week",  # Keep logs for 1 week
        compression="zip",  # Compress rotated logs
    )
    
    logger.info(f"Logger initialized with level {log_level}")


# Initialize logger with default configuration
setup_logger()


def get_logger(name: str):
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)