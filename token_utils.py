"""
Utility functions for token management
"""

import os
import json
import datetime
import jwt
from typing import Dict, List, Tuple, Optional, Any
import colorama
from colorama import Fore
import logging
from logger_config import get_logger, log_exception
import random

# Initialize colorama
colorama.init(autoreset=True)

# Set up logger
tokens_logger = get_logger("tokens")

logger = logging.getLogger(__name__)

def load_tokens() -> List[Tuple[str, str]]:
    """
    Load tokens from true_api_tokens.json
    
    Returns:
        List of tuples containing certificate IDs and tokens
    """
    try:
        with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            tokens = [(cert_id, token) for cert_id, token in data.get('tokens', {}).items()]
            tokens_logger.info(f"Loaded {len(tokens)} tokens from true_api_tokens.json")
            return tokens
    except FileNotFoundError:
        tokens_logger.error("File true_api_tokens.json not found")
        return []
    except Exception as e:
        log_exception(tokens_logger, e, "Error loading tokens")
        return []

def get_any_valid_token() -> Optional[str]:
    """
    Get any valid token from the loaded tokens
    
    Returns:
        A token string or None if no valid tokens found
    """
    tokens = load_tokens()
    
    if tokens:
        cert_name, token = random.choice(tokens)
        tokens_logger.info(f"Selected token for: {cert_name}")
        return token
    
    tokens_logger.warning("No valid tokens found")
    return None

def get_token_for_certificate(cert_name: str) -> Optional[str]:
    """
    Get token for a specific certificate
    
    Args:
        cert_name: Certificate name or identifier
        
    Returns:
        Token string or None if not found
    """
    tokens = load_tokens()
    
    for name, token in tokens:
        if name == cert_name:
            return token
    
    tokens_logger.warning(f"No token found for certificate: {cert_name}")
    return None

def save_tokens(tokens_dict: Dict[str, str]) -> bool:
    """
    Save tokens to JSON file
    
    Args:
        tokens_dict: Dictionary of certificate IDs to tokens
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        with open('true_api_tokens.json', 'w', encoding='utf-8') as f:
            json.dump({
                'tokens': tokens_dict,
                'generated_at': datetime.datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        tokens_logger.info(f"Saved {len(tokens_dict)} tokens to true_api_tokens.json")
        return True
    except Exception as e:
        log_exception(tokens_logger, e, "Error saving tokens")
        return False

def list_available_tokens() -> List[str]:
    """
    List all available tokens
    
    Returns:
        List of certificate names that have tokens
    """
    tokens = load_tokens()
    return [cert_name for cert_name, _ in tokens]

def get_token_for_tc(tc: str) -> Optional[str]:
    """Get token for specific ТС"""
    tokens = load_tokens()
    
    if not tokens:
        return None
    
    # Look for tokens with ТС in their name
    for name, token in tokens:
        if f" - {tc}" in name and is_token_valid(token):
            print(f"Found valid token for ТС {tc}")
            return token
    
    print(f"No valid token found for ТС {tc}")
    return None

def is_token_valid(token: str) -> bool:
    """Check if token is valid and not expired"""
    try:
        # Decode without verification to check expiration
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Check expiration
        if 'exp' in decoded:
            expiration = datetime.datetime.fromtimestamp(decoded['exp'])
            now = datetime.datetime.now()
            
            if expiration > now:
                return True
        
        return False
    except Exception:
        return False

def get_token_info(token: str) -> Dict[str, Any]:
    """Get information from token"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Extract basic info
        info = {
            "user": decoded.get('full_name', 'Unknown'),
            "inn": decoded.get('inn', 'Unknown'),
            "organization_status": decoded.get('organisation_status', 'Unknown'),
            "product_groups": [],
            "expires_at": datetime.datetime.fromtimestamp(decoded.get('exp', 0)).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract product group info if available
        if 'product_group_info' in decoded:
            for group in decoded['product_group_info']:
                info["product_groups"].append({
                    "name": group.get('name', 'Unknown'),
                    "status": group.get('status', 'Unknown'),
                    "types": group.get('types', [])
                })
        
        return info
    except Exception as e:
        print(f"{Fore.RED}Error extracting token info: {str(e)}")
        return None

def update_token(cert_name, token):
    """
    Update a specific token in the JSON file
    """
    try:
        tokens = {}
        if os.path.exists('true_api_tokens.json'):
            with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                tokens = data.get('tokens', {})
        
        tokens[cert_name] = token
        
        with open('true_api_tokens.json', 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "tokens": tokens,
                    "generated_at": datetime.datetime.now().isoformat()
                }, 
                f, 
                indent=2,
                ensure_ascii=False
            )
        return True
    except Exception as e:
        print(f"{Fore.RED}Error updating token: {str(e)}")
        return False

def display_all_tokens_info():
    """
    Display information about all available tokens.
    """
    try:
        if os.path.exists('true_api_tokens.json'):
            with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
                tokens_data = json.load(f)
                tokens = tokens_data.get('tokens', {})
                
            if not tokens:
                print(f"{Fore.YELLOW}No tokens found in token file.")
                return
                
            print(f"\n{Fore.CYAN}=== Available Tokens ===")
            for i, (cert_name, token) in enumerate(tokens.items(), 1):
                print(f"\n{Fore.CYAN}Token {i}: {cert_name}")
                
                # Check validity
                is_valid = is_token_valid(token)
                status = f"{Fore.GREEN}VALID" if is_valid else f"{Fore.RED}EXPIRED"
                print(f"Status: {status}")
                
                # Get token info
                info = get_token_info(token)
                if info:
                    print(f"User: {info['user']}")
                    print(f"INN: {info['inn']}")
                    print(f"Expires: {info['expires_at']}")
                    
                    if info['product_groups']:
                        print("Product groups:")
                        for group in info['product_groups'][:5]:  # Show first 5 groups
                            print(f"  - {group['name']}")
                        if len(info['product_groups']) > 5:
                            print(f"  - ... and {len(info['product_groups'])-5} more")
        else:
            print(f"{Fore.YELLOW}Token file not found.")
                
    except Exception as e:
        print(f"{Fore.RED}Error displaying token info: {str(e)}")

def is_token_expired(token_data):
    """Check if token is expired or will expire soon"""
    if 'generated_at' not in token_data:
        # If no timestamp, assume it's expired
        return True
        
    try:
        gen_time = datetime.fromisoformat(token_data['generated_at'])
        # Tokens are valid for approximately 10 hours, but we'll use 8 to be safe
        expiry_time = gen_time + datetime.timedelta(hours=8)
        return datetime.datetime.now() > expiry_time
    except Exception:
        # If can't parse time, assume expired
        return True

def get_token_status():
    """Get status of tokens (valid, expired, etc.)"""
    try:
        if not os.path.exists('true_api_tokens.json'):
            return {"status": "missing", "message": "Token file not found"}
            
        with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Check if we have tokens and when they were generated
        if 'tokens' not in data or not data['tokens']:
            return {"status": "empty", "message": "No tokens found"}
            
        if 'generated_at' not in data:
            return {"status": "unknown", "message": "Token generation time unknown"}
            
        # Check if tokens are expired
        gen_time = datetime.datetime.fromisoformat(data['generated_at'])
        now = datetime.datetime.now()
        time_diff = now - gen_time
        
        # Tokens are valid for approximately 10 hours
        if time_diff.total_seconds() > 10 * 3600:  # 10 hours
            return {
                "status": "expired",
                "message": "Tokens expired",
                "age_hours": round(time_diff.total_seconds() / 3600, 1)
            }
        else:
            hours_left = 10 - (time_diff.total_seconds() / 3600)
            return {
                "status": "valid",
                "message": "Tokens are valid",
                "age_hours": round(time_diff.total_seconds() / 3600, 1),
                "hours_left": round(hours_left, 1)
            }
    except Exception as e:
        return {"status": "error", "message": f"Error checking token status: {e}"}

def load_regions_mapping():
    """Load the mapping of regions to TCs from regions.json"""
    try:
        if not os.path.exists('regions.json'):
            logger.warning("regions.json file not found")
            return {}
            
        with open('regions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading regions mapping: {e}")
        return {}

def get_tc_to_region_mapping():
    """Create a reverse mapping of TC to region"""
    regions = load_regions_mapping()
    tc_to_region = {}
    
    for region, tc_list in regions.items():
        for tc in tc_list:
            tc_to_region[tc] = region
            
    return tc_to_region

def get_region_for_tc(tc_name):
    """Get the region for a specific TC"""
    tc_to_region = get_tc_to_region_mapping()
    return tc_to_region.get(tc_name, "Неопределенный регион")

def group_violations_by_region(all_violations):
    """
    Group violation data by region
    
    Args:
        all_violations: Dictionary mapping TC names to their violation data
        
    Returns:
        Dictionary mapping regions to grouped violation data
    """
    regions_mapping = load_regions_mapping()
    tc_to_region = get_tc_to_region_mapping()
    region_violations = {}
    
    # Initialize region data
    for region in regions_mapping:
        region_violations[region] = {
            "date": next(iter(all_violations.values()))["date"] if all_violations else datetime.datetime.now().strftime("%Y-%m-%d"),
            "tc_data": {},
            "total_violations": 0
        }
    
    # Add "Другие" region for TCs without a defined region
    region_violations["Другие"] = {
        "date": next(iter(all_violations.values()))["date"] if all_violations else datetime.datetime.now().strftime("%Y-%m-%d"),
        "tc_data": {},
        "total_violations": 0
    }
    
    # Group violations data by region
    for tc, violations_data in all_violations.items():
        region = tc_to_region.get(tc, "Другие")
        
        region_violations[region]["tc_data"][tc] = violations_data
        
        # Add to total violations count for this region
        total_violations = sum(violations_data.get("violations", {}).values())
        region_violations[region]["total_violations"] += total_violations
    
    # Remove empty regions
    empty_regions = [r for r in region_violations if not region_violations[r]["tc_data"]]
    for region in empty_regions:
        del region_violations[region]
    
    return region_violations

if __name__ == "__main__":
    # When run directly, display info about all tokens
    token = get_any_valid_token()
    if token:
        print(f"\n{Fore.GREEN}Found valid token!")
        info = get_token_info(token)
        if info:
            print(f"\n{Fore.CYAN}Token Information:")
            print(f"User: {info['user']}")
            print(f"INN: {info['inn']}")
            print(f"Expires: {info['expires_at']}")
            print(f"Product Groups: {len(info['product_groups'])}")
    else:
        print(f"\n{Fore.RED}No valid tokens found.")

    # Test token utilities
    print("Available tokens:")
    tokens = load_tokens()
    for cert_name, token in tokens:
        print(f"- {cert_name}: {token[:10]}...")
