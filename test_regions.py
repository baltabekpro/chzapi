import os
from colorama import Fore, Style
import json
from region_manager import RegionManager

def test_ts_to_region_mapping():
    """Test that TCs are correctly mapped to regions"""
    print(f"{Fore.CYAN}Testing TS-to-Region mapping...")
    
    # Load cert_inns.json to get all TCs
    try:
        with open('cert_inns.json', 'r', encoding='utf-8') as f:
            cert_inns = json.load(f)
    except Exception as e:
        print(f"{Fore.RED}Error loading cert_inns.json: {e}")
        return
    
    # Extract all TCs from cert_inns.json
    all_tcs = []
    for cert, tc_pairs in cert_inns.items():
        for pair in tc_pairs:
            for tc in pair.keys():
                if tc not in all_tcs:
                    all_tcs.append(tc)
    
    print(f"{Fore.CYAN}Found {len(all_tcs)} unique TCs in cert_inns.json")
    
    # Initialize RegionManager
    region_manager = RegionManager()
    
    # Check region assignment for each TC
    tcs_with_region = 0
    tcs_without_region = 0
    
    print(f"\n{Fore.CYAN}Testing region assignment for each TC:")
    print(f"{Fore.CYAN}{'TC':<15} | {'Region':<20} | {'Status'}")
    print(f"{Fore.CYAN}{'-'*50}")
    
    for tc in all_tcs:
        region = region_manager.get_region_for_ts(tc)
        if region:
            region_name = region.get('name', 'Unknown')
            print(f"{Fore.GREEN}{tc:<15} | {region_name:<20} | ✓ Assigned")
            tcs_with_region += 1
        else:
            print(f"{Fore.YELLOW}{tc:<15} | {'None':<20} | ⚠ Not assigned")
            tcs_without_region += 1
    
    print(f"\n{Fore.CYAN}Summary:")
    print(f"{Fore.GREEN}{tcs_with_region} TCs assigned to a region")
    print(f"{Fore.YELLOW}{tcs_without_region} TCs not assigned to any region")
    
    print(f"\n{Fore.CYAN}Recommendation:")
    if tcs_without_region > 0:
        print(f"{Fore.YELLOW}Assign the unassigned TCs to regions to ensure proper report grouping.")
    else:
        print(f"{Fore.GREEN}All TCs are properly assigned to regions.")

if __name__ == "__main__":
    test_ts_to_region_mapping()
