"""
Logger configuration using loguru
"""
import sys
from pathlib import Path
from loguru import logger

from config import LOG_FILE, LOG_LEVEL, LOGS_DIR


# Store handler IDs for dynamic level changes
_console_handler_id = None
_file_handler_id = None


def setup_logger(console_level="WARNING"):
    """
    Setup loguru logger with file and console output
    
    Logs are written to:
    - Console (WARNING level by default, INFO in debug mode)
    - File with rotation (DEBUG level)
    
    Args:
        console_level: Log level for console output (default: WARNING)
    """
    global _console_handler_id, _file_handler_id
    
    # Remove default handler
    logger.remove()
    
    # Add console handler (WARNING level by default)
    _console_handler_id = logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=console_level,
        colorize=True
    )
    
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Add file handler with rotation (DEBUG level)
    _file_handler_id = logger.add(
        LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress rotated logs
        enqueue=True  # Thread-safe logging
    )
    
    return logger


def set_console_level(level: str):
    """
    Change console log level dynamically
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    global _console_handler_id
    
    if _console_handler_id is not None:
        logger.remove(_console_handler_id)
    
    _console_handler_id = logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )


def get_logger():
    """Get configured logger instance"""
    return logger


# Initialize logger on import with WARNING level
setup_logger()
