"""
Utility for managing certificates with multiple INNs and ТС
"""

import json
import os
from colorama import Fore, Style
import colorama

# Initialize colorama
colorama.init(autoreset=True)

def load_certificates():
    """Load certificates from certificates.json"""
    try:
        with open('certificates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('certificates', [])
    except FileNotFoundError:
        print(f"{Fore.RED}File certificates.json not found")
        return []
    except Exception as e:
        print(f"{Fore.RED}Error reading certificates: {e}")
        return []

def load_certificate_inns():
    """Load certificate to ТС-ИНН mapping"""
    try:
        if not os.path.exists('cert_inns.json'):
            # Create empty file if it doesn't exist
            with open('cert_inns.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}
            
        with open('cert_inns.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"{Fore.RED}Error loading certificate INNs: {e}")
        return {}

def save_certificate_inns(cert_inns):
    """Save certificate ТС-ИНН mapping"""
    try:
        with open('cert_inns.json', 'w', encoding='utf-8') as f:
            json.dump(cert_inns, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"{Fore.RED}Error saving certificate INNs: {e}")
        return False

def add_tc_inn_to_certificate():
    """Add a TC-INN pair to a certificate"""
    certificates = load_certificates()
    cert_inns = load_certificate_inns()
    
    if not certificates:
        print(f"{Fore.RED}No certificates found")
        return False
        
    # Display certificates
    print(f"{Fore.CYAN}Available certificates:")
    for i, cert in enumerate(certificates):
        name = cert.get('name', cert.get('thumbprint', f'Certificate {i+1}'))
        multi_inn = cert.get('multi_inn', False)
        print(f"{i+1}. {name} {'(Multi-INN)' if multi_inn else ''}")
    
    # Select certificate
    try:
        choice = int(input(f"{Fore.YELLOW}Select certificate number: ")) - 1
        if choice < 0 or choice >= len(certificates):
            print(f"{Fore.RED}Invalid selection")
            return False
            
        selected_cert = certificates[choice]
        cert_name = selected_cert.get('name', selected_cert.get('thumbprint'))
        
        # Check if certificate is set for multi-INN
        is_multi = selected_cert.get('multi_inn', False)
        if not is_multi:
            print(f"{Fore.YELLOW}This certificate is not set for multiple INNs.")
            make_multi = input(f"{Fore.YELLOW}Do you want to enable multiple INNs for this certificate? (y/n): ").lower() == 'y'
            if make_multi:
                # Update certificates.json
                selected_cert['multi_inn'] = True
                try:
                    with open('certificates.json', 'w', encoding='utf-8') as f:
                        json.dump({"certificates": certificates}, f, ensure_ascii=False, indent=2)
                    print(f"{Fore.GREEN}Certificate updated to support multiple INNs")
                except Exception as e:
                    print(f"{Fore.RED}Error updating certificate: {e}")
                    return False
            else:
                return False
        
        # Get existing ТС-ИНН pairs
        existing_pairs = cert_inns.get(cert_name, [])
        
        if existing_pairs:
            print(f"{Fore.CYAN}Existing ТС-ИНН pairs for {cert_name}:")
            for i, pair in enumerate(existing_pairs, 1):
                for tc, inn in pair.items():
                    print(f"{i}. ТС: {tc}, ИНН: {inn}")
        else:
            print(f"{Fore.CYAN}No ТС-ИНН pairs found for {cert_name}")
        
        # Add new ТС-ИНН pair
        tc = input(f"{Fore.YELLOW}Enter ТС identifier: ").strip()
        if not tc:
            print(f"{Fore.RED}No ТС entered")
            return False
            
        inn = input(f"{Fore.YELLOW}Enter ИНН for ТС {tc}: ").strip()
        if not inn:
            print(f"{Fore.RED}No ИНН entered")
            return False
            
        # Add new pair
        new_pair = {tc: inn}
        
        # Check if ТС already exists
        for pair in existing_pairs:
            if tc in pair:
                update = input(f"{Fore.YELLOW}ТС {tc} already exists. Update it? (y/n): ").lower() == 'y'
                if update:
                    pair[tc] = inn
                    if save_certificate_inns(cert_inns):
                        print(f"{Fore.GREEN}ТС-ИНН pair updated. Now ТС {tc} has ИНН: {inn}")
                        return True
                    else:
                        return False
                else:
                    return False
        
        # Add new pair if ТС doesn't exist
        existing_pairs.append(new_pair)
        cert_inns[cert_name] = existing_pairs
        
        if save_certificate_inns(cert_inns):
            print(f"{Fore.GREEN}ТС-ИНН pair added successfully. Certificate {cert_name} now has ТС {tc} with ИНН {inn}")
            return True
        else:
            return False
            
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number")
        return False
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

def add_multiple_tc_inns_to_certificate():
    """Add multiple TC-INN pairs to a certificate at once"""
    certificates = load_certificates()
    cert_inns = load_certificate_inns()
    
    if not certificates:
        print(f"{Fore.RED}No certificates found")
        return False
        
    # Display certificates
    print(f"{Fore.CYAN}Available certificates:")
    for i, cert in enumerate(certificates):
        name = cert.get('name', cert.get('thumbprint', f'Certificate {i+1}'))
        multi_inn = cert.get('multi_inn', False)
        print(f"{i+1}. {name} {'(Multi-INN)' if multi_inn else ''}")
    
    # Select certificate
    try:
        choice = int(input(f"{Fore.YELLOW}Select certificate number: ")) - 1
        if choice < 0 or choice >= len(certificates):
            print(f"{Fore.RED}Invalid selection")
            return False
            
        selected_cert = certificates[choice]
        cert_name = selected_cert.get('name', selected_cert.get('thumbprint'))
        
        # Check if certificate is set for multi-INN
        is_multi = selected_cert.get('multi_inn', False)
        if not is_multi:
            print(f"{Fore.YELLOW}This certificate is not set for multiple INNs.")
            make_multi = input(f"{Fore.YELLOW}Do you want to enable multiple INNs for this certificate? (y/n): ").lower() == 'y'
            if make_multi:
                # Update certificates.json
                selected_cert['multi_inn'] = True
                try:
                    with open('certificates.json', 'w', encoding='utf-8') as f:
                        json.dump({"certificates": certificates}, f, ensure_ascii=False, indent=2)
                    print(f"{Fore.GREEN}Certificate updated to support multiple INNs")
                except Exception as e:
                    print(f"{Fore.RED}Error updating certificate: {e}")
                    return False
            else:
                return False
        
        # Get existing ТС-ИНН pairs
        existing_pairs = cert_inns.get(cert_name, [])
        
        if existing_pairs:
            print(f"{Fore.CYAN}Existing ТС-ИНН pairs for {cert_name}:")
            for i, pair in enumerate(existing_pairs, 1):
                for tc, inn in pair.items():
                    print(f"{i}. ТС: {tc}, ИНН: {inn}")
        else:
            print(f"{Fore.CYAN}No ТС-ИНН pairs found for {cert_name}")
        
        # Add multiple ТС-ИНН pairs at once
        print(f"{Fore.YELLOW}Enter TC-INN pairs (one per line, format: TC,INN)")
        print(f"{Fore.YELLOW}Leave empty line to finish")
        
        new_pairs = []
        while True:
            line = input().strip()
            if not line:
                break
                
            parts = line.split(',')
            if len(parts) != 2:
                print(f"{Fore.RED}Invalid format. Use TC,INN format")
                continue
                
            tc = parts[0].strip()
            inn = parts[1].strip()
            
            if not tc or not inn:
                print(f"{Fore.RED}TC and INN cannot be empty")
                continue
                
            # Check if ТС already exists
            tc_exists = False
            for pair in existing_pairs:
                if tc in pair:
                    print(f"{Fore.YELLOW}TC {tc} already exists, will be updated")
                    pair[tc] = inn
                    tc_exists = True
                    break
                    
            if not tc_exists:
                new_pairs.append({tc: inn})
        
        # Add new pairs
        if new_pairs:
            existing_pairs.extend(new_pairs)
            cert_inns[cert_name] = existing_pairs
            
            if save_certificate_inns(cert_inns):
                print(f"{Fore.GREEN}Added {len(new_pairs)} new TC-INN pairs to certificate {cert_name}")
                return True
            else:
                print(f"{Fore.RED}Error saving TC-INN pairs")
                return False
        else:
            print(f"{Fore.YELLOW}No new TC-INN pairs added")
            return False
            
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number")
        return False
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

def remove_tc_inn_from_certificate():
    """Remove a ТС-ИНН pair from a certificate"""
    certificates = load_certificates()
    cert_inns = load_certificate_inns()
    
    if not certificates:
        print(f"{Fore.RED}No certificates found")
        return False
        
    # Display certificates with ТС-ИНН pairs
    print(f"{Fore.CYAN}Certificates with ТС-ИНН pairs:")
    certs_with_inns = []
    for i, cert in enumerate(certificates):
        name = cert.get('name', cert.get('thumbprint', f'Certificate {i+1}'))
        if name in cert_inns and cert_inns[name]:
            print(f"{len(certs_with_inns)+1}. {name}")
            certs_with_inns.append((name, cert_inns[name]))
    
    if not certs_with_inns:
        print(f"{Fore.YELLOW}No certificates with ТС-ИНН pairs found")
        return False
        
    # Select certificate
    try:
        choice = int(input(f"{Fore.YELLOW}Select certificate number: ")) - 1
        if choice < 0 or choice >= len(certs_with_inns):
            print(f"{Fore.RED}Invalid selection")
            return False
            
        cert_name, tc_inn_pairs = certs_with_inns[choice]
        
        # Display ТС-ИНН pairs for removal
        print(f"{Fore.CYAN}ТС-ИНН pairs for {cert_name}:")
        for i, pair in enumerate(tc_inn_pairs, 1):
            for tc, inn in pair.items():
                print(f"{i}. ТС: {tc}, ИНН: {inn}")
        
        # Select pair to remove
        pair_choice = int(input(f"{Fore.YELLOW}Select ТС-ИНН pair number to remove (0 to cancel): "))
        if pair_choice == 0:
            return False
        pair_choice -= 1
        
        if pair_choice < 0 or pair_choice >= len(tc_inn_pairs):
            print(f"{Fore.RED}Invalid selection")
            return False
            
        removed_pair = tc_inn_pairs.pop(pair_choice)
        removed_tc = list(removed_pair.keys())[0]
        
        # Update cert_inns.json
        if tc_inn_pairs:
            cert_inns[cert_name] = tc_inn_pairs
        else:
            cert_inns[cert_name] = []
            
        if save_certificate_inns(cert_inns):
            print(f"{Fore.GREEN}ТС {removed_tc} removed from certificate {cert_name}")
            return True
        else:
            return False
            
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number")
        return False
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

def manage_multi_inn():
    """Main function to manage certificates with multiple INNs"""
    print(f"{Fore.CYAN}===== Multi-INN Certificate Manager =====")
    
    while True:
        print(f"\n{Fore.CYAN}Options:")
        print("1. Add ТС-ИНН pair to a certificate")
        print("2. Add multiple ТС-ИНН pairs at once")
        print("3. Remove ТС-ИНН pair from a certificate")
        print("4. Show all certificates with ТС-ИНН pairs")
        print("0. Exit")
        
        try:
            choice = int(input(f"{Fore.YELLOW}Enter your choice: "))
            
            if choice == 0:
                break
            elif choice == 1:
                add_tc_inn_to_certificate()
            elif choice == 2:
                add_multiple_tc_inns_to_certificate()
            elif choice == 3:
                remove_tc_inn_from_certificate()
            elif choice == 4:
                # Display all certificates with their ТС-ИНН pairs
                certificates = load_certificates()
                cert_inns = load_certificate_inns()
                
                print(f"\n{Fore.CYAN}Certificates and their ТС-ИНН pairs:")
                for cert in certificates:
                    name = cert.get('name', cert.get('thumbprint'))
                    multi_inn = cert.get('multi_inn', False)
                    pairs = cert_inns.get(name, [])
                    
                    print(f"- {name} {'(Multi-INN)' if multi_inn else ''}")
                    if pairs:
                        for pair in pairs:
                            for tc, inn in pair.items():
                                print(f"  ТС: {tc}, ИНН: {inn}")
                    else:
                        print("  No ТС-ИНН pairs defined")
            else:
                print(f"{Fore.RED}Invalid choice")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number")
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")

if __name__ == "__main__":
    manage_multi_inn()
