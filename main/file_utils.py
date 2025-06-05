import os
import shutil
import json
from datetime import datetime, timedelta
from logger_config import get_logger, log_exception

# Set up logger
files_logger = get_logger("files")

def list_files_in_directory(directory=None):
    """Lists files in a directory"""
    if directory is None:
        directory = os.getcwd()
    
    if not os.path.exists(directory):
        print("Директория не найдена.")
        files_logger.warning(f"Attempted to list non-existent directory: {directory}")
        return []
    
    files_logger.info(f"Listing files in directory: {directory}")
    
    try:
        files = os.listdir(directory)
        for i, fname in enumerate(files, 1):
            path = os.path.join(directory, fname)
            file_type = 'Файл' if os.path.isfile(path) else 'Папка'
            size = os.path.getsize(path) if os.path.isfile(path) else '-'
            modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{i:3d}. {fname:<50} | {file_type:<6} | {size:<10} | {modified}")
        
        files_logger.info(f"Listed {len(files)} files/directories")
        return files
    except Exception as e:
        log_exception(files_logger, e, f"Error listing directory {directory}")
        return []

def delete_file(file_path=None):
    """Delete a file or directory"""
    if file_path is None:
        file_path = input("Введите полный путь к файлу для удаления: ").strip()
        
    if not os.path.exists(file_path):
        print("Указанный файл/папка не существует.")
        files_logger.warning(f"Attempted to delete non-existent file/directory: {file_path}")
        return False
        
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            print("Файл удалён.")
            files_logger.info(f"Deleted file: {file_path}")
            return True
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            print("Папка удалена.")
            files_logger.info(f"Deleted directory: {file_path}")
            return True
    except Exception as e:
        log_exception(files_logger, e, f"Error deleting file/directory: {file_path}")
        return False

def add_file(src=None, dest_dir=None):
    """Copy a file to another location"""
    if src is None:
        src = input("Введите путь к исходному файлу, который нужно добавить: ").strip()
        
    if not os.path.isfile(src):
        print("Исходный файл не найден.")
        files_logger.warning(f"Attempted to add non-existent file: {src}")
        return False
        
    if dest_dir is None:
        dest_dir = input("Введите путь к директории для копирования (или Enter для текущей): ").strip()
        if not dest_dir:
            dest_dir = os.getcwd()
            
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    
    try:
        shutil.copy2(src, dest)
        print(f"Файл скопирован в {dest}")
        files_logger.info(f"Copied file from {src} to {dest}")
        return True
    except Exception as e:
        log_exception(files_logger, e, f"Error copying file from {src} to {dest}")
        return False

def check_last_run_info():
    """Check information about last and next run"""
    last_run_file = "last_run.json"
    if not os.path.exists(last_run_file):
        print("Файл last_run.json не найден. Следующий запуск неизвестен.")
        files_logger.warning("File last_run.json not found")
        return None
        
    try:
        with open(last_run_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_run = datetime.fromisoformat(data.get('last_run'))
            certs_processed = data.get('certificates_processed', 0)
            manual_run = data.get('manual_run', False)
            
            # Next run at midnight of next day
            next_run = (last_run.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            
            # Calculate time until next run
            now = datetime.now()
            time_until = next_run - now if next_run > now else timedelta(0)
            
            run_info = {
                'last_run': last_run,
                'next_run': next_run,
                'certificates_processed': certs_processed,
                'manual_run': manual_run,
                'time_until': time_until
            }
            
            # Print information
            print("\n=== Информация о запусках ===")
            print(f"Последний запуск: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Следующий запуск: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Обработано сертификатов: {certs_processed}")
            print(f"{'Ручной' if manual_run else 'Автоматический'} запуск")
            
            if time_until.total_seconds() > 0:
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"Времени до следующего запуска: {time_until.days} дней, {hours} часов, {minutes} минут")
            else:
                print("Время следующего запуска уже наступило")
                
            files_logger.info(f"Checked run information: next run at {next_run}")
            return run_info
            
    except Exception as e:
        log_exception(files_logger, e, f"Error reading file {last_run_file}")
        return None

def get_reports_list(base_dir='output'):
    """Get list of available reports by certificate"""
    if not os.path.exists(base_dir):
        print("Папка с отчетами не найдена.")
        files_logger.warning(f"Reports directory not found: {base_dir}")
        return {}
        
    reports = {}
    certificates = os.listdir(base_dir)
    
    for cert in certificates:
        cert_path = os.path.join(base_dir, cert)
        if os.path.isdir(cert_path):
            json_reports = [f for f in os.listdir(cert_path) if f.startswith('violations_') and f.endswith('.json')]
            if json_reports:
                reports[cert] = [
                    {
                        'filename': report,
                        'date': report.split('_')[1].split('.')[0],
                        'path': os.path.join(cert_path, report)
                    }
                    for report in json_reports
                ]
    
    return reports

if __name__ == "__main__":
    # If run directly, show file management capabilities
    print("=== File Management Utilities ===")
    print("\nCurrent directory contents:")
    list_files_in_directory()
    
    print("\nRun information:")
    check_last_run_info()
