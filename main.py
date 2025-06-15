import os
import sys

# Check for dependencies before importing other modules
if __name__ == "__main__":
    try:
        # First, try to import dependency_manager
        try:
            from dependency_manager import check_and_install_dependencies
            check_and_install_dependencies()
        except ImportError:
            # If dependency_manager.py doesn't exist or can't be imported,
            # install basic requirements first
            print("Dependency manager not found, installing basic requirements...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama", "requests"])
            print("Basic dependencies installed.")
            
            # Now create the dependency manager file
            dm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dependency_manager.py")
            with open(dm_path, "w", encoding="utf-8") as f:
                f.write('''import importlib
import subprocess
import sys
import os
import time
from typing import List, Dict, Set

def check_and_install_dependencies():
    """
    Check for and install all required dependencies
    """
    # Dictionary of required packages and their import names (if different)    required_packages = {
        "requests": "requests",
        "colorama": "colorama", 
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
    if (missing_packages):
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
''')
            print("Created dependency manager.")
            
            # Now import and run the dependency checker
            from dependency_manager import check_and_install_dependencies
            check_and_install_dependencies()
    except Exception as e:        
        print(f"Error setting up dependencies: {e}")
        print("Please install required packages manually using:")
        print("pip install colorama requests pandas chardet")
        input("Press Enter to exit...")
        sys.exit(1)

# Now import the rest of the modules after dependencies are installed
import time
import json
import shutil
import colorama
from colorama import Fore, Back, Style
from datetime import datetime, timedelta
from get_violations import ViolationsReport, PRODUCT_GROUPS
from get_report import ReportDownloader
from process_report import process_reports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from get_tokens import get_tokens
from logger_config import get_logger, log_exception
from file_viewer import view_file_with_menu
from token_manager import show_tokens_management_menu

# Import utilities from the new modules
from email_utils import load_email_config
from file_utils import (
    list_files_in_directory, 
    delete_file, 
    add_file, 
    check_last_run_info,  # Make sure this is imported
    get_reports_list
)
from report_processor import (
    process_reports_for_token,
    view_report
)
from file_viewer import view_file_with_menu
from token_manager import show_tokens_management_menu
from token_utils import get_any_valid_token
from scheduler import Scheduler

# Initialize colorama
colorama.init(autoreset=True)

# Set up main logger
logger = get_logger("main")

# Module-specific loggers
tokens_logger = get_logger("tokens")
violations_logger = get_logger("violations")
reports_logger = get_logger("reports")
email_logger = get_logger("email")
files_logger = get_logger("files")

def load_product_groups():
    """Load product groups from products.txt"""
    try:
        groups = []
        with open('products.txt', 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    code = int(line.strip())
                    groups.append(code)
                except ValueError:
                    continue
        logger.info(f"Loaded {len(groups)} product groups from products.txt")
        return groups
    except FileNotFoundError:
        logger.error("File products.txt not found")
        return []
    except Exception as e:
        log_exception(logger, e, "Error loading product groups")
        return []

def load_tokens():
    """Load tokens from true_api_tokens.json"""
    try:
        with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            tokens = [(cert_id, token) for cert_id, token in data['tokens'].items()]
            tokens_logger.info(f"Loaded {len(tokens)} tokens from true_api_tokens.json")
            return tokens
    except FileNotFoundError:
        tokens_logger.error("File true_api_tokens.json not found")
        return []
    except Exception as e:
        log_exception(tokens_logger, e, "Error reading tokens")
        return []

def read_csv_with_encoding(file_path: str) -> int:
    """Read CSV file and return number of violations"""
    encodings = ['cp1251', 'utf-8-sig', 'utf-8', 'windows-1251', 'latin1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Read all lines first
                lines = f.readlines()
                
                # Skip empty file
                if not lines:
                    return 0
                    
                # Find header line
                header = None
                for line in lines:
                    if line.strip():
                        header = line
                        break
                
                if not header:
                    return 0
                
                # Count non-empty lines after header
                count = sum(1 for line in lines if line.strip() and line != header)
                reports_logger.info(f"Successfully read file with {encoding} encoding, found {count} violations")
                return count
                
        except UnicodeDecodeError:
            continue
        except Exception as e:
            reports_logger.warning(f"Error with {encoding} encoding: {e}")
            continue
    
    reports_logger.error(f"Could not read file {file_path} with any encoding")
    return 0

def create_tasks_for_token(cert_name: str, token: str) -> list:
    """Create tasks for all product groups and return task IDs"""
    violations_logger.info(f"Creating tasks for certificate: {cert_name}")
    
    task_ids = []
    base_dir = os.path.join('output', cert_name)
    os.makedirs(base_dir, exist_ok=True)
    
    # Use yesterday's date instead of current date
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    violations_logger.info(f"Using date range: {yesterday} to {yesterday} (yesterday's data)")
    
    for group_code in load_product_groups():
        try:
            violations_logger.info(f"Creating task for group {group_code} ({PRODUCT_GROUPS.get(group_code, 'Unknown')})")
            result = ViolationsReport(token).create_violations_task(
                start_date=yesterday,
                end_date=yesterday,  # Use yesterday for both start and end dates
                product_group_code=group_code
            )
            
            if result and result.get('id'):
                task_id = result['id']
                task_ids.append((task_id, group_code))
                violations_logger.info(f"Created task: {task_id}")
                
        except Exception as e:
            log_exception(violations_logger, e, f"Error creating task for group {group_code}")
            continue
    
    # Save task IDs for this certificate
    if task_ids:
        tasks_file = os.path.join(base_dir, 'pending_tasks.txt')
        with open(tasks_file, 'w') as f:
            for task_id, group_code in task_ids:
                f.write(f"{task_id},{group_code}\n")
        violations_logger.info(f"Saved {len(task_ids)} tasks to {tasks_file}")
    
    return task_ids

def download_tasks_for_token(cert_name: str, token: str):
    """Download all pending tasks for a certificate"""
    reports_logger.info(f"Downloading tasks for certificate: {cert_name}")
    
    base_dir = os.path.join('output', cert_name)
    reports_dir = os.path.join(base_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    tasks_file = os.path.join(base_dir, 'pending_tasks.txt')
    if not os.path.exists(tasks_file):
        reports_logger.info("No pending tasks found")
        return
        
    with open(tasks_file, 'r') as f:
        tasks = [line.strip().split(',') for line in f if line.strip()]
    
    reports_logger.info(f"Found {len(tasks)} pending tasks")
    
    remaining_tasks = []
    for task_id, group_code in tasks:
        try:
            group_code = int(group_code)
            client = ReportDownloader(token, group_code)
            reports_logger.info(f"Downloading task {task_id} for group {group_code}")
            
            if client.monitor_and_download(task_id, reports_dir):
                reports_logger.info(f"Successfully downloaded task {task_id}")
            else:
                reports_logger.warning(f"Failed to download task {task_id}, will retry later")
                remaining_tasks.append((task_id, group_code))
                
        except Exception as e:
            log_exception(reports_logger, e, f"Error downloading task {task_id}")
            remaining_tasks.append((task_id, group_code))
    
    # Update pending tasks file
    if remaining_tasks:
        with open(tasks_file, 'w') as f:
            for task_id, group_code in remaining_tasks:
                f.write(f"{task_id},{group_code}\n")
        reports_logger.info(f"Updated pending tasks, {len(remaining_tasks)} tasks remaining")
    else:
        os.remove(tasks_file)
        reports_logger.info("All tasks completed, removed pending tasks file")

def load_email_config():
    """Load email configuration"""
    try:
        with open('email_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            email_logger.info("Email configuration loaded successfully")
            return config
    except Exception as e:
        log_exception(email_logger, e, "Error loading email config")
        return None

def send_violations_report(cert_name: str, violations_data: dict, email_config: dict) -> bool:
    """Send email with violations report"""
    try:
        email_logger.info(f"Preparing email report for {cert_name} on {violations_data['date']}")
        
        # Create HTML content with clear indication that this is yesterday's data
        html = f"""
        <h2>Отчет о нарушениях маркировки за {violations_data['date']} (данные за вчерашний день)</h2>
        <h3>Сертификат: {cert_name}</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px;">Товарная группа</th>
                <th style="padding: 8px;">Количество нарушений</th>
            </tr>
        """
        
        total_violations = 0
        for group, count in violations_data['violations'].items():
            total_violations += count
            html += f"""
            <tr>
                <td style="padding: 8px;">{group}</td>
                <td style="padding: 8px; text-align: center;">{count}</td>
            </tr>
            """
        
        html += f"""
            <tr style="background-color: #f2f2f2; font-weight: bold;">
                <td style="padding: 8px;">Всего нарушений:</td>
                <td style="padding: 8px; text-align: center;">{total_violations}</td>
            </tr>
        </table>
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Отчет о нарушениях маркировки - {cert_name} - {violations_data['date']}"
        msg['From'] = email_config['sender_email']
        recipients = email_config['recipient_emails']
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html, 'html'))
        
        email_logger.info(f"Sending email to {len(recipients)} recipients")
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
            
        email_logger.info(f"Email report sent successfully for {cert_name}")
        return True
        
    except Exception as e:
        log_exception(email_logger, e, f"Error sending email report for {cert_name}")
        return False

def process_reports_for_token(cert_name: str, email_config: dict = None):
    """Process all reports into single JSON file and send email"""
    reports_logger.info(f"Processing reports for certificate: {cert_name}")
    
    base_dir = os.path.join('output', cert_name)
    reports_dir = os.path.join(base_dir, 'reports')
    
    if not os.path.exists(reports_dir):
        reports_logger.warning("No reports directory found")
        return
        
    # Use yesterday's date for the report label
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    violations_data = {
        'date': yesterday,  # Use yesterday's date in the report
        'violations': {}
    }
    
    csv_files = [f for f in os.listdir(reports_dir) if f.endswith('.csv')]
    reports_logger.info(f"Found {len(csv_files)} CSV files to process")
    
    for csv_file in csv_files:
        try:
            input_path = os.path.join(reports_dir, csv_file)
            reports_logger.info(f"Processing file: {csv_file}")
            
            # Extract group code from filename using improved parsing
            # Example filename: violations_group1__20250303_235139.csv
            group_code = None
            try:
                # Find the number after 'group' in the filename
                import re
                match = re.search(r'group(\d+)', csv_file)
                if match:
                    group_code = int(match.group(1))
            except ValueError:
                reports_logger.warning(f"Could not extract group code from filename: {csv_file}")
                continue
            
            if group_code is None:
                reports_logger.warning(f"No group code found in filename: {csv_file}")
                continue
              # Get product group name
            product_name = PRODUCT_GROUPS.get(group_code)
            if not product_name:
                reports_logger.warning(f"Unknown product group code: {group_code}")
                continue
            
            violation_count = read_csv_with_encoding(input_path)
            violations_data['violations'][product_name] = violation_count
            reports_logger.info(f"Found {violation_count} violations for {product_name}")
            
            # os.remove(input_path)  # Закомментировано: сохраняем CSV файлы для дополнительного анализа
            reports_logger.info(f"Processed {csv_file}")
            
        except Exception as e:
            log_exception(reports_logger, e, f"Error processing {csv_file}")
    
    # Save consolidated JSON
    if violations_data['violations']:
        output_file = os.path.join(base_dir, f'violations_{yesterday}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(violations_data, f, ensure_ascii=False, indent=2)
        reports_logger.info(f"Saved consolidated data to {output_file}")
        
        # Remove individual email sending - this is now handled at the end of daily processing
        reports_logger.info("Report processed and saved. Consolidated emails will be sent later.")

def refresh_daily_tokens() -> bool:
    """Refresh tokens daily"""
    try:
        tokens_logger.info("Refreshing tokens...")
        tokens = get_tokens()
        if not tokens:
            tokens_logger.error("Failed to get new tokens")
            return False
        tokens_logger.info("Tokens successfully refreshed")
        return True
    except Exception as e:
        log_exception(tokens_logger, e, "Error refreshing tokens")
        return False

def show_file_menu():
    """Displays file management menu"""
    menu = f"""
{Fore.CYAN}╔══════════════════ УПРАВЛЕНИЕ ФАЙЛАМИ ══════════════════╗
{Fore.YELLOW}║ 1. Просмотр файлов и директорий                       ║
{Fore.YELLOW}║ 2. Текстовый редактор                                 ║
{Fore.YELLOW}║ 3. Удалить файл или папку                             ║
{Fore.YELLOW}║ 4. Скопировать файл в другую директорию               ║
{Fore.YELLOW}║ 5. Информация о следующем запуске                     ║
{Fore.YELLOW}║ 6. Просмотр журналов работы                           ║
{Fore.GREEN}║ 0. ◄ Вернуться в главное меню                         ║
{Fore.CYAN}╚═══════════════════════════════════════════════════════╝
"""
    while True:
        print(menu)
        choice = input(f"{Fore.GREEN}Выберите пункт меню: ")
        if choice == '1':
            directory = input("Введите путь к директории (Enter для текущей): ").strip()
            list_files_in_directory(directory if directory else None)
        elif choice == '2':
            view_file_with_menu()  # Use the new file viewer
        elif choice == '3':
            delete_file()
        elif choice == '4':
            add_file()
        elif choice == '5':
            check_last_run_info()
        elif choice == '6':
            view_logs()
        elif choice == '0':
            logger.info("Возврат в главное меню")
            break
        else:
            print(f"{Fore.RED}Неверный выбор. Повторите попытку.")

def view_logs():
    """Display available log files and view selected log"""
    files_logger.info("Просмотр журналов")
    logs_dir = os.path.join(os.getcwd(), "logs")
    
    if not os.path.exists(logs_dir):
        print(f"{Fore.RED}Директория журналов не найдена")
        return
    
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
    if not log_files:
        print(f"{Fore.RED}Журналы не найдены")
        return
    
    print(f"\n{Fore.CYAN}╔═══════════ ДОСТУПНЫЕ ЖУРНАЛЫ ═══════════╗")
    for i, log_file in enumerate(log_files, 1):
        # Color code log files by type
        if 'error' in log_file.lower():
            print(f"{Fore.RED}{i}. {log_file}")
        elif 'warning' in log_file.lower():
            print(f"{Fore.YELLOW}{i}. {log_file}")
        elif 'token' in log_file.lower():
            print(f"{Fore.BLUE}{i}. {log_file}")
        elif 'main' in log_file.lower():
            print(f"{Fore.GREEN}{i}. {log_file}")
        else:
            print(f"{Fore.WHITE}{i}. {log_file}")
    print(f"{Fore.CYAN}╚═══════════════════════════════════════════╝")
    
    choice = input(f"{Fore.GREEN}Выберите журнал (номер) или 0 для возврата: ")
    try:
        index = int(choice)
        if index == 0:
            return
        
        log_file = log_files[index-1]
        log_path = os.path.join(logs_dir, log_file)
        view_file_with_menu(log_path)  # Use advanced file viewer
                
    except (ValueError, IndexError):
        print(f"{Fore.RED}Неверный выбор")

def list_files_in_directory():
    """Lists files in a directory"""
    directory = input("Введите путь к директории (или Enter для текущей): ").strip()
    if not directory:
        directory = os.getcwd()
    if not os.path.exists(directory):
        print("Директория не найдена.")
        files_logger.warning(f"Attempted to list non-existent directory: {directory}")
        return
    
    files_logger.info(f"Listing files in directory: {directory}")
    print(f"\nСодержимое директории {directory}:")
    
    try:
        files = os.listdir(directory)
        for fname in files:
            path = os.path.join(directory, fname)
            print(f"{fname} - {'Файл' if os.path.isfile(path) else 'Папка'}")
        files_logger.info(f"Listed {len(files)} files/directories")
    except Exception as e:
        log_exception(files_logger, e, f"Error listing directory {directory}")

def view_file_content():
    """View the content of a file"""
    file_path = input("Введите полный путь к файлу для просмотра: ").strip()
    if not os.path.isfile(file_path):
        print("Файл не найден.")
        files_logger.warning(f"Attempted to view non-existent file: {file_path}")
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("\n--- Содержимое файла ---")
            print(content)
            print("--- Конец файла ---\n")
        files_logger.info(f"Viewed content of file: {file_path}")
    except Exception as e:
        log_exception(files_logger, e, f"Error reading file: {file_path}")

def delete_file():
    """Delete a file or directory"""
    file_path = input("Введите полный путь к файлу для удаления: ").strip()
    if not os.path.exists(file_path):
        print("Указанный файл/папка не существует.")
        files_logger.warning(f"Attempted to delete non-existent file/directory: {file_path}")
        return
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            print("Файл удалён.")
            files_logger.info(f"Deleted file: {file_path}")
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            print("Папка удалена.")
            files_logger.info(f"Deleted directory: {file_path}")
    except Exception as e:
        log_exception(files_logger, e, f"Error deleting file/directory: {file_path}")

def add_file():
    """Copy a file to another location"""
    src = input("Введите путь к исходному файлу, который нужно добавить: ").strip()
    if not os.path.isfile(src):
        print("Исходный файл не найден.")
        files_logger.warning(f"Attempted to add non-existent file: {src}")
        return
    dest_dir = input("Введите путь к директории для копирования (или Enter для текущей): ").strip()
    if not dest_dir:
        dest_dir = os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    try:
        shutil.copy2(src, dest)
        print(f"Файл скопирован в {dest}")
        files_logger.info(f"Copied file from {src} to {dest}")
    except Exception as e:
        log_exception(files_logger, e, f"Error copying file from {src} to {dest}")

def next_run_time():
    """Check when the next run is scheduled"""
    last_run_file = "last_run.json"
    if os.path.exists(last_run_file):
        try:
            with open(last_run_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data.get('last_run'))
                # Next run at midnight of next day
                next_run = (last_run.replace(hour=0, minute=0, second=0, microsecond=0)
                            + timedelta(days=1))
                print(f"Последний запуск: {last_run}")
                print(f"Следующий запуск: {next_run}")
                
                # Calculate time until next run
                now = datetime.now()
                if next_run > now:
                    time_until = next_run - now
                    hours, remainder = divmod(time_until.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    print(f"Времени до следующего запуска: {time_until.days} дней, {hours} часов, {minutes} минут")
            files_logger.info(f"Next run time checked: {next_run}")
        except Exception as e:
            log_exception(files_logger, e, f"Error reading file {last_run_file}")
    else:
        print("Файл last_run.json не найден. Следующий запуск неизвестен.")
        files_logger.warning("File last_run.json not found")

def show_main_menu():
    """Displays main menu"""
    menu = f"""
{Fore.CYAN}╔══════════════════ ЦРПТ МАРКИРОВКА ══════════════════╗
{Fore.YELLOW}║ 1. Запустить ежедневную обработку                  ║
{Fore.YELLOW}║ 2. Управление файлами                              ║
{Fore.YELLOW}║ 3. Управление токенами и сертификатами             ║
{Fore.YELLOW}║ 4. Просмотреть отчеты о нарушениях                 ║
{Fore.YELLOW}║ 5. Отправить отчет по email                        ║
{Fore.YELLOW}║ 6. Обновить токены                                 ║
{Fore.YELLOW}║ 7. Установить сертификат из файла                  ║
{Fore.YELLOW}║ 8. Запустить планировщик                           ║
{Fore.YELLOW}║ 9. Управление регионами                            ║
{Fore.RED}║ 0. Выход из программы                              ║
{Fore.CYAN}╚═════════════════════════════════════════════════════╝
"""
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Show header with current time 
        now = datetime.now()
        print(f"{Fore.CYAN}╔═══ ЦРПТ Процессор ═══ {now.strftime('%Y-%m-%d %H:%M:%S')} ═══╗")
        
        print(menu)
        
        # Improved input handling to prevent misinterpreting date/time as menu option
        choice = input(f"{Fore.GREEN}Выберите пункт меню (0-9): ")
        
        # Check if the input looks like a date/time string (more than 1 character and contains ':' or '-')
        if len(choice) > 1 and (':' in choice or '-' in choice):
            print(f"{Fore.RED}Некорректный ввод. Введите число от 0 до 9.")
            time.sleep(2)
            continue
        
        # Validate that input is a single digit
        if not choice.isdigit() or len(choice) != 1:
            print(f"{Fore.RED}Некорректный ввод. Введите число от 0 до 9.")
            time.sleep(2)
            continue
            
        choice = choice.strip()
        
        if choice == '1':
            run_daily_process()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '2':
            show_file_menu()
        elif choice == '3':
            show_tokens_management_menu()  # Added token management menu
        elif choice == '4':
            view_reports()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '5':
            send_report_manually()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '6':
            refresh_tokens_manually()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '7':
            install_certificate()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '8':
            start_scheduler()
            input(f"\n{Fore.GREEN}Нажмите Enter для продолжения...")
        elif choice == '9':
            from region_manager import manage_regions
            manage_regions()
        elif choice == '0':
            # Add confirmation dialog to prevent accidental exit
            confirm = input(f"{Fore.YELLOW}Вы уверены, что хотите выйти? (д/н): ").lower()
            if confirm in ['д', 'y', 'да', 'yes']:
                logger.info("Выход из программы")
                print(f"{Fore.CYAN}Выход из программы...")
                sys.exit(0)
            else:
                logger.info("Отмена выхода из программы")
                continue
        else:
            print(f"{Fore.RED}Неверный выбор. Повторите попытку.")
            time.sleep(1)

def install_certificate():
    """Install certificate from file"""
    try:
        # Import the certificate installer
        from install_certificate import main as install_cert_main
        print(f"{Fore.CYAN}╔══════════════ УСТАНОВКА СЕРТИФИКАТА ═══════════════╗")
        install_cert_main()
        
    except ImportError:
        print(f"{Fore.RED}Модуль установки сертификатов не найден")
        logger.error("Certificate installation module not found")
    except Exception as e:
        log_exception(logger, e, "Error during certificate installation")

def run_daily_process():
    """Run the daily processing routine"""
    logger.info("Запуск ежедневной обработки...")
    logger.info("Будут обработаны данные за вчерашний день")
    
    # Load email configuration
    email_config = load_email_config()
    if not email_config:
        logger.warning("Email configuration not loaded, reports won't be sent")
        
    try:
        # First refresh tokens - ALWAYS refresh tokens before running daily process
        # This ensures we always have fresh tokens
        logger.info("Refreshing tokens before daily processing...")
        if not refresh_daily_tokens():
            logger.error("Failed to refresh tokens. Retrying once...")
            # Wait a moment and try again
            time.sleep(10)
            if not refresh_daily_tokens():
                logger.error("Failed to refresh tokens after retry.")
                return False

        # Load newly generated tokens
        tokens = load_tokens()
        if not tokens:
            logger.error("No tokens found in true_api_tokens.json")
            return False
        
        # Process each certificate
        for cert_id, token in tokens:
            logger.info(f"Processing certificate: {cert_id}")
            
            # Phase 1: Create tasks
            tasks = create_tasks_for_token(cert_id, token)
            
            # Phase 2: Download reports
            download_tasks_for_token(cert_id, token)
            
            # Phase 3: Process reports - but don't send emails yet
            process_reports_for_token(cert_id, None)
        
        # Now send consolidated reports by region
        logger.info("Processing complete. Sending consolidated regional reports...")
        
        # Import and use function from send_daily_report.py
        from send_daily_report import process_and_send_reports
        process_and_send_reports()
        
        # Update last run time
        current_time = datetime.now()
        with open('last_run.json', 'w') as f:
            json.dump({
                'last_run': current_time.isoformat(),
                'certificates_processed': len(tokens),
                'next_run': (current_time + timedelta(days=1)).replace(
                    hour=0, minute=5, second=0
                ).isoformat()
            }, f, indent=2)
        
        logger.info("Daily processing completed successfully")
        return True
        
    except Exception as e:
        log_exception(logger, e, "Error during processing")
        return False

def refresh_tokens_manually():
    """Manually refresh tokens"""
    logger.info("Обновление токенов...")
    if refresh_daily_tokens():
        logger.info("Токены успешно обновлены")
    else:
        logger.error("Не удалось обновить токены")

def view_reports():
    """View available reports"""
    logger.info("Доступные отчеты:")
    
    base_dir = 'output'
    if not os.path.exists(base_dir):
        logger.warning("Папка с отчетами не найдена.")
        return
        
    certificates = os.listdir(base_dir)
    if not certificates:
        logger.warning("Отчеты не найдены.")
        return
        
    for i, cert in enumerate(certificates, 1):
        print(f"{i}. {cert}")
        
    choice = input("\nВыберите сертификат (номер) или 0 для возврата: ")
    try:
        index = int(choice)
        if index == 0:
            return
            
        cert_dir = certificates[index-1]
        cert_path = os.path.join(base_dir, cert_dir)
        
        # Список JSON-файлов с отчетами
        reports = [f for f in os.listdir(cert_path) if f.startswith('violations_') and f.endswith('.json')]
        if not reports:
            logger.warning("Для этого сертификата отчеты не найдены.")
            return
            
        print(f"\nОтчеты для сертификата {cert_dir}:")
        for i, report in enumerate(reports, 1):
            date = report.split('_')[1].split('.')[0]  # Extract date from filename
            print(f"{i}. Отчет за {date}")
            
        report_choice = input("\nВыберите отчет (номер) или 0 для возврата: ")
        try:
            report_index = int(report_choice)
            if report_index == 0:
                return
                
            report_file = reports[report_index-1]
            report_path = os.path.join(cert_path, report_file)
            
            # Отображаем содержимое отчета
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    date = data.get('date', 'Неизвестная дата')
                    print(f"\n=== Отчет о нарушениях за {date} ===")
                    print(f"Сертификат: {cert_dir}")
                    print("\nНарушения по товарным группам:")
                    total = 0
                    for group, count in data.get('violations', {}).items():
                        total += count
                        print(f"- {group}: {count}")
                    print(f"\nВсего нарушений: {total}")
                logger.info(f"Viewed report: {report_file}")
            except Exception as e:
                log_exception(logger, e, f"Ошибка чтения отчета: {report_file}")
                
        except (ValueError, IndexError):
            logger.warning("Неверный выбор отчета")
            
    except (ValueError, IndexError):
        logger.warning("Неверный выбор сертификата")

def send_report_manually():
    """Manually send a report by email"""
    logger.info("Отправка отчета по email:")
    
    # Load email config
    email_config = load_email_config()
    if not email_config:
        logger.error("Не удалось загрузить конфигурацию email")
        return
        
    # Select certificate
    base_dir = 'output'
    if not os.path.exists(base_dir):
        logger.warning("Папка с отчетами не найдена.")
        return
        
    certificates = os.listdir(base_dir)
    if not certificates:
        logger.warning("Отчеты не найдены.")
        return
        
    for i, cert in enumerate(certificates, 1):
        print(f"{i}. {cert}")
        
    choice = input("\nВыберите сертификат (номер) или 0 для возврата: ")
    try:
        index = int(choice)
        if index == 0:
            return
            
        cert_dir = certificates[index-1]
        cert_path = os.path.join(base_dir, cert_dir)
        
        # List JSON report files
        reports = [f for f in os.listdir(cert_path) if f.startswith('violations_') and f.endswith('.json')]
        if not reports:
            logger.warning("Для этого сертификата отчеты не найдены.")
            return
            
        print(f"\nОтчеты для сертификата {cert_dir}:")
        for i, report in enumerate(reports, 1):
            date = report.split('_')[1].split('.')[0]  # Extract date from filename
            print(f"{i}. Отчет за {date}")
            
        report_choice = input("\nВыберите отчет (номер) или 0 для возврата: ")
        try:
            report_index = int(report_choice)
            if report_index == 0:
                return
                
            report_file = reports[report_index-1]
            report_path = os.path.join(cert_path, report_file)
            
            # Load and send the report
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    violations_data = json.load(f)
                    
                if send_violations_report(cert_dir, violations_data, email_config):
                    logger.info("Отчет успешно отправлен")
                else:
                    logger.error("Не удалось отправить отчет")
                    
            except Exception as e:
                log_exception(logger, e, f"Ошибка при отправке отчета: {report_file}")
                
        except (ValueError, IndexError):
            logger.warning("Неверный выбор отчета")
            
    except (ValueError, IndexError):
        logger.warning("Неверный выбор сертификата")

def start_scheduler():
    """Start the task scheduler"""
    print(f"\n{Fore.CYAN}=== Запуск планировщика задач ===")
    
    try:
        from scheduler import ensure_scheduler_running
        ensure_scheduler_running()
        print(f"{Fore.GREEN}Планировщик успешно запущен в фоновом режиме")
        print(f"{Fore.YELLOW}Задачи будут выполняться автоматически каждый день")
        return True
    except Exception as e:
        print(f"{Fore.RED}Ошибка при запуске планировщика: {e}")
        logger.error(f"Error starting scheduler: {e}")
        return False

def main():
    logger.info("=== Запуск ЦРПТ Маркировка ===")
    
    # Check for command line argument to run in scheduler mode
    if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
        logger.info("Запуск в режиме планировщика")
        # Run the scheduler without UI
        scheduler = Scheduler()
        # Run continuously - this is a blocking call that runs forever
        scheduler.run_continuously()
        return
    
    # Check for daemon mode - this starts the scheduler and exits
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        logger.info("Запуск в фоновом режиме")
        from scheduler import ensure_scheduler_running
        pid = ensure_scheduler_running()
        if pid:
            print(f"Scheduler started successfully with PID {pid}")
            print("The program will continue running in the background.")
            print("Daily tasks will run automatically.")
        else:
            print("Failed to start scheduler.")
        return
        
    # For normal mode (with UI), also ensure the scheduler is running
    from scheduler import ensure_scheduler_running
    ensure_scheduler_running()
    logger.info("Автоматический планировщик запущен")
    print(f"{Fore.GREEN}Планировщик задач запущен в фоновом режиме")
    print(f"{Fore.CYAN}Программа будет автоматически выполняться каждый день")
    
    # Show interactive menu
    logger.info("Запуск в интерактивном режиме")
    show_main_menu()

def run_daemon_mode():
    """Run in daemon mode without interactive menu"""
    logger.info("=== True API ЦРПТ Daily Processor (Daemon Mode) ===")
    
    # Use the scheduler for consistent scheduling
    scheduler = Scheduler()
    scheduler.run_continuously()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем (Ctrl+C)")
        print(f"\n{Fore.YELLOW}Остановка программы...")
        sys.exit(0)
    except Exception as e:
        log_exception(logger, e, "Непредвиденная ошибка в программе")
        print(f"{Fore.RED}Критическая ошибка: {str(e)}")
        print(f"{Fore.YELLOW}Подробная информация сохранена в журнале")
        sys.exit(1)