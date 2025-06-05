import asyncio
import concurrent.futures
import threading
from typing import Callable, Any, Awaitable, Optional
from logger_config import get_logger

# Set up logger
handlers_logger = get_logger("telegram_handlers")

def run_async_safely(coro_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Optional[Any]:
    """
    Safely run an async function from a synchronous context
    
    Args:
        coro_func: The async function to run
        *args: Arguments to pass to the async function
        **kwargs: Keyword arguments to pass to the async function
        
    Returns:
        The result of the async function, or None if an error occurred
    """
    try:
        # Create the coroutine
        coro = coro_func(*args, **kwargs)
        
        # Get the current event loop if one exists
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            should_close_loop = True
        else:
            should_close_loop = False
            
        # Run the coroutine
        if loop.is_running():
            # If loop is running, use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            try:
                return future.result(timeout=30)  # 30 second timeout
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                handlers_logger.error("Timeout running async function")
                return None
        else:
            # If loop is not running, use run_until_complete
            return loop.run_until_complete(coro)
            
        # Clean up if we created a new loop
        if should_close_loop:
            loop.close()
            
    except Exception as e:
        handlers_logger.error(f"Error running async function: {e}")
        return None

def send_notification(message: str) -> bool:
    """
    Send a notification via Telegram (safe wrapper)
    
    Args:
        message: The message to send
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        from telegram_bot import send_telegram_notification
        
        # Use the run_async_safely function to handle async properly
        return run_async_safely(send_telegram_notification, message)
    except Exception as e:
        handlers_logger.error(f"Failed to send notification: {e}")
        return False
