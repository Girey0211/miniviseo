"""
Logger configuration using loguru
"""
import sys
from pathlib import Path
from loguru import logger

from config import LOG_FILE, LOG_LEVEL, LOGS_DIR


def setup_logger():
    """
    Setup loguru logger with file and console output
    
    Logs are written to:
    - Console (INFO level)
    - File with rotation (DEBUG level)
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler (INFO level)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Add file handler with rotation (DEBUG level)
    logger.add(
        LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress rotated logs
        enqueue=True  # Thread-safe logging
    )
    
    return logger


def get_logger():
    """Get configured logger instance"""
    return logger


# Initialize logger on import
setup_logger()
