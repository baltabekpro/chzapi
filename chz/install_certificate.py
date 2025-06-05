import os
import subprocess
import shutil
from getpass import getpass

def extract_archive(rar_path: str, extract_path: str, password: str = None) -> bool:
    """Extract archive using 7-Zip or WinRAR"""
    try:
        # Try 7-Zip first
        sevenzip_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            r"C:\Users\workb\AppData\Local\Programs\7-Zip\7z.exe"  # Common user installation path
        ]
        
        # Find 7-Zip
        archiver_path = None
        for path in sevenzip_paths:
            if os.path.exists(path):
                archiver_path = path
                print(f"Found 7-Zip at: {path}")
                break

        if not archiver_path:
            print("7-Zip not found")
            return False

        # Build command
        cmd = [
            archiver_path,
            'x',               # extract with full paths
            '-y',              # yes to all
            '-aoa',           # overwrite all existing files
            f'-o{extract_path}'  # output directory
        ]
        if password:
            cmd.append(f'-p{password}')
        cmd.append(rar_path)

        # Execute command with timeout
        print(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 seconds timeout
        )
        
        # Print detailed output
        print("\n=== Command Output ===")
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            # Verify files were extracted
            if os.path.exists(extract_path) and os.listdir(extract_path):
                print("Files successfully extracted:")
                for file in os.listdir(extract_path):
                    print(f"- {file}")
                return True
            else:
                print("Error: Output directory is empty")
                return False
        else:
            print("Extraction failed")
            return False

    except subprocess.TimeoutExpired:
        print("Error: Command timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        return False

def get_masked_input(prompt: str) -> str:
    """Get password input with asterisk feedback"""
    import msvcrt
    print(prompt, end='', flush=True)
    password = ""
    while True:
        char = msvcrt.getch()
        # Fix Enter key detection
        if char in [b'\r', b'\n']:  # Enter key
            print()
            break
        elif char == b'\x08':  # Backspace
            if password:
                password = password[:-1]
                print('\b \b', end='', flush=True)
        elif char == b'\x03':  # Ctrl+C
            raise KeyboardInterrupt
        else:
            try:
                # Ensure we can decode the character
                char_str = char.decode('utf-8')
                password += char_str
                print('*', end='', flush=True)
            except UnicodeDecodeError:
                # Skip characters we can't decode
                continue

    return password

def install_certificate(cert_path: str) -> bool:
    """Install certificate using certmgr.exe"""
    try:
        certmgr_path = r"C:\Program Files\Crypto Pro\CSP\certmgr.exe"
        if not os.path.exists(certmgr_path):
            print("CryptoPro CSP not found. Please install it first.")
            return False

        is_pfx = cert_path.lower().endswith(('.pfx', '.p12'))
        if is_pfx:
            print("\nPFX/P12 certificate detected - requires password")
            cert_password = get_masked_input("Enter certificate password: ")
            # Use -instpfx; supply the PFX file as a positional argument
            cmd = [
                certmgr_path,
                "-instpfx",
                cert_path,             # PFX file passed without a flag
                "-store", "uMy",
                "-pin", cert_password,  # Use -pin for password
                "-keep_exportable"
            ]
        else:
            cmd = [
                certmgr_path,
                "-inst",
                "-store", "uMy",
                "-file", cert_path
            ]

        print("\nInstalling certificate...")
        print(f"Command: {' '.join(cmd)}")  # Debug output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='cp866',
            timeout=60
        )
        
        if result.returncode == 0:
            print("Certificate installed successfully")
            return True
        else:
            print("Error installing certificate:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            stderr_lower = result.stderr.lower()
            if is_pfx and any(x in stderr_lower for x in ["пароль", "password", "неверн", "pin"]):
                print("\nIncorrect certificate password. Try again?")
                if input("(y/n): ").lower() == 'y':
                    return install_certificate(cert_path)
            return False
    except Exception as e:
        print(f"Error during installation: {e}")
        return False

def main():
    print("=== Certificate Installation Tool ===")
    
    # Get RAR file path
    rar_path = input("Enter path to RAR file with certificate: ").strip('"')
    if not os.path.exists(rar_path):
        print("RAR file not found!")
        return

    # Create temp directory for extraction
    temp_dir = os.path.join(os.getcwd(), "temp_cert")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Ask for password if needed
        password = getpass("Enter password for RAR file (press Enter if no password): ")
        if not password.strip():
            password = None

        # Extract archive
        if not extract_archive(rar_path, temp_dir, password):
            print("Failed to extract archive")
            return

        # Find certificate file
        cert_file = None
        for file in os.listdir(temp_dir):
            if file.lower().endswith(('.cer', '.p12', '.pfx')):
                cert_file = os.path.join(temp_dir, file)
                break

        if not cert_file:
            print("No certificate file found in archive!")
            return

        # Install certificate
        if install_certificate(cert_file):
            print("\nCertificate installation completed successfully")
        else:
            print("\nFailed to install certificate")

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            print("Warning: Could not remove temporary directory")

if __name__ == "__main__":
    main()
