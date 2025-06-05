import subprocess
import json
import os
from datetime import datetime
from get_token import (
    get_auth_data,
    save_data_to_sign,
    sign_data_with_cryptcp,
    read_signature_file,
    get_token,
    load_certificates,
    load_certificate_inns,
    save_certificate_inns
)

def get_cert_name(thumbprint):
    """Get certificate CN from issuer field"""
    certmgr_path = r"C:\Program Files\Crypto Pro\CSP\certmgr.exe"
    try:
        result = subprocess.run(
            [certmgr_path, "-list", "-thumbprint", thumbprint],
            capture_output=True,
            encoding='cp866'
        )
        
        if result.returncode == 0:
            output = result.stdout
            issuer_line = None
            
            # Find Issuer line
            for line in output.split('\n'):
                if 'Issuer' in line:
                    issuer_line = line.strip()
                    break
            
            if issuer_line:
                # Extract CN from Issuer
                import re
                cn_match = re.search(r'CN=([^,]+)', issuer_line)
                if (cn_match):
                    return cn_match.group(1).strip()
                        
    except Exception as e:
        print(f"Error getting certificate info: {e}")
    
    return thumbprint  # Return thumbprint as last resort

def load_certificates():
    """Load certificates configuration from JSON"""
    try:
        with open('certificates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('certificates', [])
    except FileNotFoundError:
        print("File certificates.json not found")
        return []
    except Exception as e:
        print(f"Error reading certificates: {e}")
        return []

def load_certificate_inns():
    """Load certificate to INN mapping"""
    try:
        with open('cert_inns.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty file if it doesn't exist
        with open('cert_inns.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    except Exception as e:
        print(f"Error loading certificate INNs: {e}")
        return {}

def save_certificate_inns(cert_inns):
    """Save certificate INN mapping"""
    try:
        with open('cert_inns.json', 'w', encoding='utf-8') as f:
            json.dump(cert_inns, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving certificate INNs: {e}")
        return False

def save_mchd_settings(settings):
    """Save МЧДО settings for certificates"""
    try:
        with open('mchd_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving MCHD settings: {e}")
        return False

def load_mchd_settings():
    """Load MCHD settings for certificates"""
    try:
        with open('mchd_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty file if it doesn't exist
        with open('mchd_settings.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    except Exception as e:
        print(f"Error loading MCHD settings: {e}")
        return {}

def get_tokens():
    """Get tokens for all certificates"""
    tokens = {}
    
    try:
        # Load certificates from certificates.json
        certificates = load_certificates()
        
        if not certificates:
            print("No certificates found in certificates.json")
            return {}
        
        # Load saved ТС-ИНН pairs for certificates
        cert_inns = load_certificate_inns()
        
        print(f"Found {len(certificates)} certificates")
        
        for cert in certificates:
            thumbprint = cert.get('thumbprint')
            name = cert.get('name', thumbprint)
            multi_inn = cert.get('multi_inn', False)
            
            if not thumbprint:
                print(f"Skipping certificate without thumbprint: {name}")
                continue
                
            print(f"\nGetting token for: {name}")
            print(f"Thumbprint: {thumbprint}")
            print(f"Multi-INN: {'Yes' if multi_inn else 'No'}")
            
            # Check if we have saved ТС-ИНН pairs for this certificate
            cert_key = name if name else thumbprint
            tc_inn_pairs = cert_inns.get(cert_key, [])
            
            if tc_inn_pairs:
                print(f"Found saved ТС-ИНН pairs:")
                for pair in tc_inn_pairs:
                    for tc, inn in pair.items():
                        # Модификация: обрабатываем ТС с пустым ИНН
                        if inn.strip() == "":
                            print(f"  {tc}: <без ИНН>")
                        else:
                            print(f"  {tc}: {inn}")
            
            # Get auth data and sign
            uuid, data_to_sign = get_auth_data()
            save_data_to_sign(data_to_sign)
            
            signature_path = sign_data_with_cryptcp("data_to_sign.txt", thumbprint)
            if not signature_path:
                print("Could not create signature")
                continue
            
            signed_data = read_signature_file(signature_path)
            if not signed_data:
                continue
            
            # If we have ТС-ИНН pairs, get token for each one, regardless of multi_inn setting
            if tc_inn_pairs:
                # Process each ТС-ИНН pair
                for pair in tc_inn_pairs:
                    for tc, inn in pair.items():
                        print(f"\nGetting token for ТС {tc}")
                        
                        # Модификация: не передаем параметр inn если он пустой
                        if inn.strip() == "":
                            print(f"ТС {tc} используется без ИНН")
                            # Получаем токен без указания ИНН
                            token, status = get_token(uuid, signed_data)
                        else:
                            print(f"ТС {tc} с ИНН {inn}")
                            token, status = get_token(uuid, signed_data, inn=inn)
                        
                        # If we got a token
                        if token and status == "success":
                            print(f"Successfully got token for {name} - {tc}")
                            # Store token with ТС identifier
                            token_key = f"{name} - {tc}"
                            tokens[token_key] = token
            else:
                # If no ТС-ИНН pairs, try without ИНН
                token, status = get_token(uuid, signed_data)
                
                # If we need to provide an ИНН
                if status == "require_inn":
                    tc = input(f"Enter ТС for certificate {name}: ").strip()
                    inn = input(f"Enter ИНН for ТС {tc}: ").strip()
                    
                    if tc and inn:
                        # Save pair for future use
                        cert_inns[cert_key] = [{tc: inn}]
                        save_certificate_inns(cert_inns)
                        print(f"ТС-ИНН pair saved")
                        
                        # Try to get token with ИНН
                        token, status = get_token(uuid, signed_data, inn=inn)
                        
                        if token and status == "success":
                            print(f"Successfully got token for {name} - {tc}")
                            token_key = f"{name} - {tc}"
                            tokens[token_key] = token
                elif status == "success" and token:
                    print(f"Successfully got token for {name}")
                    tokens[name] = token
        
        # Save all tokens in a single file
        if tokens:
            save_tokens(tokens)
            print(f"\nSaved {len(tokens)} tokens to true_api_tokens.json")
        else:
            print("\nCould not get any tokens")
            
    except Exception as e:
        print(f"Error getting tokens: {e}")
    
    return tokens

def save_token(cert_name, token):
    """Save individual token to file"""
    try:
        token_file = f"token_{cert_name.replace(' ', '_')}.txt"
        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(token)
        print(f"Saved token for {cert_name} to {token_file}")
    except Exception as e:
        print(f"Error saving individual token: {e}")

def save_tokens(tokens):
    """Save all tokens to JSON file"""
    try:
        # If file exists, try to merge with existing tokens
        existing_tokens = {}
        try:
            if os.path.exists('true_api_tokens.json'):
                with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_tokens = data.get('tokens', {})
        except:
            pass
            
        # Merge with new tokens
        existing_tokens.update(tokens)
        
        with open('true_api_tokens.json', 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "tokens": existing_tokens,
                    "generated_at": datetime.now().isoformat()
                }, 
                f, 
                indent=2,
                ensure_ascii=False
            )
        return True
    except Exception as e:
        print(f"Error saving tokens: {e}")
        return False

if __name__ == "__main__":
    get_tokens()
