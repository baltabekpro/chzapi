"""
Region Management Module

This module provides functionality for managing regions and their TC assignments.
"""
import os
import json
import colorama
from colorama import Fore, Style
from typing import Dict, List, Any
from logger_config import get_logger, log_exception

# Initialize colorama
colorama.init(autoreset=True)

# Set up logger
region_logger = get_logger("regions")

def load_regions_data() -> Dict[str, Any]:
    """
    Load regions data from regions.json
    
    Returns:
        Dictionary with region data
    """
    try:
        if not os.path.exists('regions.json'):
            region_logger.warning("Regions file not found: regions.json")
            return {}
            
        with open('regions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            region_logger.info(f"Loaded {len(data)} regions from regions.json")
            return data
    except Exception as e:
        log_exception(region_logger, e, "Error loading regions data")
        return {}

def save_regions_data(regions_data: Dict[str, Any]) -> bool:
    """
    Save regions data to regions.json
    
    Args:
        regions_data: Dictionary with region data
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        with open('regions.json', 'w', encoding='utf-8') as f:
            json.dump(regions_data, f, indent=2, ensure_ascii=False)
        
        region_logger.info(f"Saved {len(regions_data)} regions to regions.json")
        return True
    except Exception as e:
        log_exception(region_logger, e, "Error saving regions data")
        return False

def get_tc_region(tc_name: str) -> str:
    """
    Get region for a TC
    
    Args:
        tc_name: TC identifier
        
    Returns:
        Region identifier or 'Undefined' if not found
    """
    regions_data = load_regions_data()
    
    for region_id, region_data in regions_data.items():
        tc_list = region_data.get('tc_list', [])
        if tc_name in tc_list:
            return region_id
    
    return "Undefined"

def add_region(region_id: str, region_name: str, emails: List[str] = None) -> bool:
    """
    Add or update a region
    
    Args:
        region_id: Region identifier
        region_name: Display name for the region
        emails: List of email addresses for the region
        
    Returns:
        True if added successfully, False otherwise
    """
    regions_data = load_regions_data()
    
    # Default values
    if emails is None:
        emails = []
    
    # Add or update region
    regions_data[region_id] = {
        'name': region_name,
        'emails': emails,
        'tc_list': regions_data.get(region_id, {}).get('tc_list', [])
    }
    
    return save_regions_data(regions_data)

def add_tc_to_region(tc_name: str, region_id: str) -> bool:
    """
    Add a TC to a region
    
    Args:
        tc_name: TC identifier
        region_id: Region identifier
        
    Returns:
        True if added successfully, False otherwise
    """
    regions_data = load_regions_data()
    
    # Check if region exists
    if region_id not in regions_data:
        region_logger.warning(f"Region not found: {region_id}")
        return False
    
    # Get TC list for region
    tc_list = regions_data[region_id].get('tc_list', [])
    
    # Add TC if not already in the list
    if tc_name not in tc_list:
        tc_list.append(tc_name)
        regions_data[region_id]['tc_list'] = tc_list
        
        # Remove from other regions
        for other_region_id, other_region_data in regions_data.items():
            if other_region_id != region_id:
                other_tc_list = other_region_data.get('tc_list', [])
                if tc_name in other_tc_list:
                    other_tc_list.remove(tc_name)
                    regions_data[other_region_id]['tc_list'] = other_tc_list
        
        return save_regions_data(regions_data)
    
    return True  # TC already in the region

def remove_tc_from_region(tc_name: str, region_id: str) -> bool:
    """
    Remove a TC from a region
    
    Args:
        tc_name: TC identifier
        region_id: Region identifier
        
    Returns:
        True if removed successfully, False otherwise
    """
    regions_data = load_regions_data()
    
    # Check if region exists
    if region_id not in regions_data:
        region_logger.warning(f"Region not found: {region_id}")
        return False
    
    # Get TC list for region
    tc_list = regions_data[region_id].get('tc_list', [])
    
    # Remove TC if in the list
    if tc_name in tc_list:
        tc_list.remove(tc_name)
        regions_data[region_id]['tc_list'] = tc_list
        return save_regions_data(regions_data)
    
    return True  # TC not in the region

def delete_region(region_id: str) -> bool:
    """
    Delete a region
    
    Args:
        region_id: Region identifier
        
    Returns:
        True if deleted successfully, False otherwise
    """
    regions_data = load_regions_data()
    
    # Check if region exists
    if region_id not in regions_data:
        region_logger.warning(f"Region not found: {region_id}")
        return False
    
    # Delete region
    del regions_data[region_id]
    return save_regions_data(regions_data)

def list_regions():
    """Print all regions with their TCs"""
    regions_data = load_regions_data()
    
    if not regions_data:
        print(f"{Fore.YELLOW}No regions defined")
        return
    
    print(f"\n{Fore.CYAN}=== Available Regions ===")
    for region_id, region_data in regions_data.items():
        name = region_data.get('name', region_id)
        tc_list = region_data.get('tc_list', [])
        emails = region_data.get('emails', [])
        
        print(f"\n{Fore.GREEN}Region: {name} ({region_id})")
        print(f"{Fore.YELLOW}Emails: {', '.join(emails) if emails else 'None'}")
        print(f"{Fore.YELLOW}TCs:")
        
        if tc_list:
            for tc in tc_list:
                print(f"  - {tc}")
        else:
            print("  No TCs assigned")

def manage_regions():
    """Interactive region management"""
    while True:
        print(f"\n{Fore.CYAN}=== Region Management ===")
        print(f"{Fore.YELLOW}1. List regions")
        print(f"{Fore.YELLOW}2. Add/Update region")
        print(f"{Fore.YELLOW}3. Add TC to region")
        print(f"{Fore.YELLOW}4. Remove TC from region")
        print(f"{Fore.YELLOW}5. Delete region")
        print(f"{Fore.RED}0. Back")
        
        choice = input(f"\n{Fore.GREEN}Enter choice: ")
        
        if choice == '0':
            break
        elif choice == '1':
            list_regions()
        elif choice == '2':
            region_id = input(f"{Fore.YELLOW}Enter region ID: ")
            region_name = input(f"{Fore.YELLOW}Enter region name: ")
            emails_str = input(f"{Fore.YELLOW}Enter email addresses (comma separated): ")
            emails = [email.strip() for email in emails_str.split(',') if email.strip()]
            
            if add_region(region_id, region_name, emails):
                print(f"{Fore.GREEN}Region added/updated successfully")
            else:
                print(f"{Fore.RED}Failed to add/update region")
        elif choice == '3':
            # List regions first
            regions_data = load_regions_data()
            print(f"\n{Fore.CYAN}Available regions:")
            for i, (region_id, region_data) in enumerate(regions_data.items(), 1):
                print(f"{i}. {region_data.get('name', region_id)} ({region_id})")
            
            region_index = input(f"{Fore.YELLOW}Select region (number): ")
            try:
                region_keys = list(regions_data.keys())
                region_id = region_keys[int(region_index) - 1]
                
                tc_name = input(f"{Fore.YELLOW}Enter TC name: ")
                
                if add_tc_to_region(tc_name, region_id):
                    print(f"{Fore.GREEN}TC added to region successfully")
                else:
                    print(f"{Fore.RED}Failed to add TC to region")
            except (ValueError, IndexError):
                print(f"{Fore.RED}Invalid region selection")
        elif choice == '4':
            # List regions with TCs
            regions_data = load_regions_data()
            print(f"\n{Fore.CYAN}Regions with TCs:")
            
            for i, (region_id, region_data) in enumerate(regions_data.items(), 1):
                tc_list = region_data.get('tc_list', [])
                if tc_list:
                    print(f"{i}. {region_data.get('name', region_id)} ({region_id}) - {len(tc_list)} TCs")
            
            region_index = input(f"{Fore.YELLOW}Select region (number): ")
            try:
                region_keys = list(regions_data.keys())
                region_id = region_keys[int(region_index) - 1]
                
                # List TCs in the region
                region_data = regions_data[region_id]
                tc_list = region_data.get('tc_list', [])
                
                print(f"\n{Fore.CYAN}TCs in {region_data.get('name', region_id)}:")
                for i, tc in enumerate(tc_list, 1):
                    print(f"{i}. {tc}")
                
                tc_index = input(f"{Fore.YELLOW}Select TC to remove (number): ")
                try:
                    tc_name = tc_list[int(tc_index) - 1]
                    
                    if remove_tc_from_region(tc_name, region_id):
                        print(f"{Fore.GREEN}TC removed from region successfully")
                    else:
                        print(f"{Fore.RED}Failed to remove TC from region")
                except (ValueError, IndexError):
                    print(f"{Fore.RED}Invalid TC selection")
            except (ValueError, IndexError):
                print(f"{Fore.RED}Invalid region selection")
        elif choice == '5':
            # List regions
            regions_data = load_regions_data()
            print(f"\n{Fore.CYAN}Available regions:")
            for i, (region_id, region_data) in enumerate(regions_data.items(), 1):
                print(f"{i}. {region_data.get('name', region_id)} ({region_id})")
            
            region_index = input(f"{Fore.YELLOW}Select region to delete (number): ")
            try:
                region_keys = list(regions_data.keys())
                region_id = region_keys[int(region_index) - 1]
                
                confirm = input(f"{Fore.RED}Are you sure you want to delete {regions_data[region_id].get('name', region_id)}? (y/n): ")
                if confirm.lower() == 'y':
                    if delete_region(region_id):
                        print(f"{Fore.GREEN}Region deleted successfully")
                    else:
                        print(f"{Fore.RED}Failed to delete region")
            except (ValueError, IndexError):
                print(f"{Fore.RED}Invalid region selection")
        else:
            print(f"{Fore.RED}Invalid choice")

if __name__ == "__main__":
    manage_regions()
