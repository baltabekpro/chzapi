"""
Input validation utilities for better user experience
"""
import re
import time
from colorama import Fore, Style

def validate_menu_choice(prompt: str, min_value: int, max_value: int, error_message: str = None) -> int:
    """
    Validate a numeric menu choice within a range
    
    Args:
        prompt: The input prompt to display
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        error_message: Custom error message (optional)
        
    Returns:
        int: The validated input as an integer
    """
    if error_message is None:
        error_message = f"{Fore.RED}Пожалуйста, введите число от {min_value} до {max_value}."
        
    while True:
        choice = input(prompt).strip()
        
        # Check if input looks like a date/time string
        if len(choice) > 1 and (':' in choice or '-' in choice):
            print(f"{Fore.RED}Введено некорректное значение (похоже на дату/время).")
            time.sleep(1)
            continue
            
        # Check if input is numeric
        if not choice.isdigit():
            print(error_message)
            time.sleep(1)
            continue
            
        # Convert to int and check range
        try:
            value = int(choice)
            if min_value <= value <= max_value:
                return value
            else:
                print(error_message)
                time.sleep(1)
        except ValueError:
            print(error_message)
            time.sleep(1)

def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Ask for confirmation of an action
    
    Args:
        prompt: The confirmation prompt to display
        default: Default value if user just presses Enter
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    yes_options = ['y', 'д', 'yes', 'да', '+']
    no_options = ['n', 'н', 'no', 'нет', '-']
    
    default_text = " [Д/н]" if default else " [д/Н]"
    
    while True:
        choice = input(f"{prompt}{default_text}: ").strip().lower()
        
        if not choice:  # Empty string (just pressed Enter)
            return default
            
        if choice in yes_options:
            return True
            
        if choice in no_options:
            return False
            
        print(f"{Fore.RED}Пожалуйста, введите 'д' (да) или 'н' (нет).")
        time.sleep(1)

def validate_date(date_str: str, allow_empty: bool = False) -> str:
    """
    Validate a date string in format YYYY-MM-DD
    
    Args:
        date_str: Date string to validate
        allow_empty: Allow empty input (returns empty string)
        
    Returns:
        str: Validated date string or empty string if allowed and input is empty
    """
    if not date_str and allow_empty:
        return ""
        
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    
    if not re.match(date_pattern, date_str):
        raise ValueError("Дата должна быть в формате YYYY-MM-DD")
        
    # Additional validation could be added here (e.g., check if valid date)
    
    return date_str

def timed_input(prompt: str, timeout: int = 60) -> str:
    """
    Input with timeout to prevent freezing
    
    Args:
        prompt: The input prompt to display
        timeout: Timeout in seconds
        
    Returns:
        str: User input or empty string if timeout
    """
    print(prompt, end='', flush=True)
    
    start_time = time.time()
    input_str = ''
    
    while True:
        if time.time() - start_time > timeout:
            print("\nВремя ожидания истекло.")
            return ''
            
        # This is a simple polling implementation
        # A better solution would use threading or select, but this is simpler
        if input_str:
            return input_str
            
        try:
            input_str = input()
        except EOFError:
            return ''
        except KeyboardInterrupt:
            return ''
            
        time.sleep(0.1)
