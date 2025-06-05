import importlib
import subprocess
import sys
import os
import time
from typing import List, Dict, Set

def check_and_install_dependencies():
    """
    Check for and install all required dependencies
    """
    # Dictionary of required packages and their import names (if different)
    required_packages = {
        "requests": "requests",
        "colorama": "colorama", 
        "python-telegram-bot": "telegram",
        "pandas": "pandas",
        "chardet": "chardet",
        "cryptography": "cryptography",
        "pytz": "pytz",
        "python-docx": "docx",
        "markdown": "markdown",
        "pywin32": "win32com",  # For Windows-specific functionality
    }
    
    missing_packages = []
    
    # Check which packages are missing
    print("Checking required dependencies...")
    for package, import_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            # Successfully imported
        except ImportError:
            missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        print(f"Installing missing dependencies: {', '.join(missing_packages)}")
        for package in missing_packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--upgrade"])
                print(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
            except Exception as e:
                print(f"Error installing {package}: {e}")
        
        # Give a moment for installations to complete
        time.sleep(2)
        
        # Verify installations
        still_missing = []
        for package, import_name in required_packages.items():
            if package in missing_packages:
                try:
                    importlib.import_module(import_name)
                    print(f"Successfully verified {package} installation")
                except ImportError:
                    still_missing.append(package)
        
        if still_missing:
            print(f"Warning: Some packages could not be installed: {', '.join(still_missing)}")
            return False
        else:
            print("All dependencies installed successfully!")
            return True
    else:
        print("All required dependencies are already installed.")
        return True

if __name__ == "__main__":
    # When run directly, check and install dependencies
    check_and_install_dependencies()
