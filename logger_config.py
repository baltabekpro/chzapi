import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.getcwd(), "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Removed Telegram bot functionality

def setup_logger(name=None, log_level=logging.INFO):
    """
    Configure and return a logger that logs to both console and file
    
    Args:
        name: Logger name (defaults to root logger if None)
        log_level: Logging level (INFO by default)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.handlers = []  # Clear any existing handlers
    
    # Log format with timestamps
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # File handler (automatic rotation, max 10MB, keep 10 backup files)
    if name is None:
        log_filename = "app.log"
    else:
        log_filename = f"{name}.log"
        
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, log_filename),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name=None):
    """Get a configured logger instance"""
    return setup_logger(name)

def log_exception(logger, exc, additional_info=None):
    """
    Log an exception with detailed information and optionally send to Telegram
    
    Args:
        logger: Logger instance
        exc: Exception object
        additional_info: Optional additional context information
    """
    import traceback
    
    if additional_info:
        error_message = f"{additional_info}: {type(exc).__name__}: {str(exc)}"
        logger.error(error_message)
    else:
        error_message = f"Exception: {type(exc).__name__}: {str(exc)}"
        logger.error(error_message)
        
    # Log traceback
    tb_string = traceback.format_exc()
    logger.error(f"Traceback: {tb_string}")
    
    # Send to Telegram if it's a critical error
    if is_critical_error(error_message, tb_string):
        try:
            send_to_telegram(error_message)
        except:
            # Avoid recursion if sending to Telegram fails
            logger.error("Failed to send error to Telegram")

def is_critical_error(error_message, traceback):
    """
    Determine if an error is critical enough to send to Telegram
    
    Args:
        error_message: The error message
        traceback: The exception traceback
    
    Returns:
        bool: True if the error is critical
    """
    # Check for critical keywords in error message or traceback
    critical_keywords = [
        "connection refused", "timeout", "failed to", "permission denied",
        "access denied", "disk full", "out of memory", "certificate expired",
        "token expired", "database error", "critical error"
    ]
    
    # Check if any critical keyword is in the error message or traceback
    for keyword in critical_keywords:
        if keyword.lower() in error_message.lower() or keyword.lower() in traceback.lower():
            return True
    
    return False

def send_to_telegram(message):
    """
    Send an error message to Telegram (функция отключена)
    
    Args:
        message: The error message to send
    """
    # Функционал Telegram бота удален
    pass
