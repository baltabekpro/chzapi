import os
import json
import sys
import re  # Add missing import for regular expressions
import csv  # Add import for CSV handling
from datetime import datetime
from logger_config import get_logger, log_exception
from token_utils import load_regions_mapping, get_tc_to_region_mapping, group_violations_by_region
from send_daily_report import process_and_send_reports, load_email_config  # Fix import error - use the correct function name
from get_violations import PRODUCT_GROUPS  # Import PRODUCT_GROUPS dictionary

# Set up logger
reports_logger = get_logger("reports")

def read_csv_with_encoding(file_path: str) -> int:
    """Read CSV file with different encodings and return number of violations
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Number of violations (rows in the CSV minus header)
    """
    encodings = ['cp1251', 'utf-8-sig', 'utf-8', 'windows-1251', 'latin1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                csv_reader = csv.reader(f)
                rows = list(csv_reader)
                row_count = max(0, len(rows) - 1)  # Subtract header row
                
                # Проверяем, что файл не пустой и содержит строки данных
                if row_count > 0:
                    reports_logger.info(f"Успешно прочитан файл {file_path} с кодировкой {encoding}: найдено {row_count} строк")
                else:
                    reports_logger.warning(f"Файл {file_path} содержит только заголовок или пустой")
                    
                return row_count
                
        except UnicodeDecodeError:
            continue
        except Exception as e:
            reports_logger.warning(f"Ошибка при чтении файла {file_path} с кодировкой {encoding}: {e}")
            continue
    
    reports_logger.error(f"Не удалось прочитать файл {file_path} ни с одной из кодировок")
    return 0

def load_violations_data(base_dir='output'):
    """
    Load all violation data from JSON files
    
    Args:
        base_dir: Base directory where violation reports are stored
        
    Returns:
        Dictionary mapping TC names to their violation data
    """
    all_violations = {}
    
    if not os.path.exists(base_dir):
        reports_logger.warning(f"Base directory {base_dir} not found")
        return all_violations
        
    # Collect all violation data
    for cert_dir in os.listdir(base_dir):
        cert_path = os.path.join(base_dir, cert_dir)
        if not os.path.isdir(cert_path):
            continue
            
        # Parse certificate name to extract TC name (assuming format "Name - TC")
        if " - " in cert_dir:
            tc_name = cert_dir.split(" - ")[1].strip()
        else:
            tc_name = cert_dir.strip()
            
        # Find the violation report JSON files
        json_files = [f for f in os.listdir(cert_path) if f.startswith('violations_') and f.endswith('.json')]
        if not json_files:
            continue
            
        # Use the most recent report
        json_file = sorted(json_files)[-1]
        json_path = os.path.join(cert_path, json_file)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                violations_data = json.load(f)
                all_violations[tc_name] = violations_data
                reports_logger.info(f"Loaded violations data for {tc_name}")
        except Exception as e:
            log_exception(reports_logger, e, f"Error loading violations data for {tc_name}")
    
    return all_violations

def process_reports_for_token(cert_name: str, email_config: dict = None):
    """Process all reports into single JSON file and send email"""
    reports_logger.info(f"Processing reports for certificate: {cert_name}")
    
    base_dir = os.path.join('output', cert_name)
    reports_dir = os.path.join(base_dir, 'reports')
    
    if not os.path.exists(reports_dir):
        reports_logger.warning("No reports directory found")
        return
        
    # Use yesterday's date for the report label
    from datetime import timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    violations_data = {
        'date': yesterday,
        'violations': {}
    }
    
    csv_files = [f for f in os.listdir(reports_dir) if f.endswith('.csv')]
    reports_logger.info(f"Найдено {len(csv_files)} CSV файлов для обработки")
    
    # Сортируем файлы по имени, чтобы обеспечить стабильную обработку
    csv_files.sort()
    
    # Словарь для хранения временных результатов обработки для каждой группы товаров
    # Это позволяет избежать перезаписи данных, если есть несколько файлов для одной группы
    temp_violations = {}
    
    # Обрабатываем каждый CSV-файл
    for csv_file in csv_files:
        try:
            input_path = os.path.join(reports_dir, csv_file)
            reports_logger.info(f"Обработка файла: {csv_file}")
            
            # Извлекаем код группы из имени файла
            # Пример имени файла: violations_group1__20250303_235139.csv
            group_code = None
            try:
                # Ищем число после 'group' в имени файла
                match = re.search(r'group(\d+)', csv_file)
                if match:
                    group_code = int(match.group(1))
                    reports_logger.info(f"Извлечен код группы товаров: {group_code}")
                else:
                    reports_logger.warning(f"Не удалось извлечь код группы товаров из имени файла: {csv_file}")
            except ValueError as ve:
                reports_logger.warning(f"Ошибка при извлечении кода группы товаров: {ve}")
                continue
            
            if group_code is None:
                reports_logger.warning(f"Код группы товаров не найден в имени файла: {csv_file}")
                continue
                
            # Проверяем, что код группы существует в словаре PRODUCT_GROUPS
            if group_code not in PRODUCT_GROUPS:
                reports_logger.warning(f"Неизвестный код группы товаров в файле: {csv_file}, код: {group_code}")
                continue
            
            # Получаем название товарной группы
            product_name = PRODUCT_GROUPS.get(group_code)
            reports_logger.info(f"Товарная группа: {product_name} (код {group_code})")
            
            # Считаем нарушения в файле
            violation_count = read_csv_with_encoding(input_path)
            
            # Сохраняем количество нарушений для данной товарной группы
            # Если для группы уже есть данные, суммируем их
            if product_name in temp_violations:
                temp_violations[product_name] += violation_count
                reports_logger.info(f"Добавлено {violation_count} нарушений к существующим {temp_violations[product_name] - violation_count} для группы {product_name}")
            else:
                temp_violations[product_name] = violation_count
                reports_logger.info(f"Найдено {violation_count} нарушений для группы {product_name}")
            
            # Удаляем обработанный файл
            os.remove(input_path)
            reports_logger.info(f"Файл {csv_file} обработан и удален")
            
        except Exception as e:
            log_exception(reports_logger, e, f"Ошибка при обработке файла {csv_file}")
    
    # Переносим обработанные данные в итоговый отчет
    violations_data['violations'] = temp_violations
    
    # Выводим суммарную статистику
    reports_logger.info(f"Итоговая статистика нарушений по товарным группам:")
    for product, count in temp_violations.items():
        reports_logger.info(f"  {product}: {count} нарушений")
    
    # Save consolidated JSON
    if violations_data['violations']:
        output_file = os.path.join(base_dir, f'violations_{yesterday}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(violations_data, f, ensure_ascii=False, indent=2)
        reports_logger.info(f"Saved consolidated data to {output_file}")
        
        # Individual emails are now handled by the consolidated email sender
        reports_logger.info("Report processed and saved. Consolidated emails will be sent later.")

def view_report(report_path=None):
    """View a violation report by region"""
    if not report_path:
        # Show available reports
        all_violations = load_violations_data()
        if not all_violations:
            print("No violation reports found")
            return
            
        # Group by region
        region_violations = group_violations_by_region(all_violations)
        
        # Display report
        print("Violations by Region:")
        for region, data in region_violations.items():
            print(f"\nRegion: {region}")
            print(f"Total violations: {data['total_violations']}")
            
            for tc, tc_data in data["tc_data"].items():
                print(f"\n  TC: {tc}")
                tc_total = sum(tc_data.get('violations', {}).values())
                print(f"  Total violations: {tc_total}")
                
                for group, count in tc_data.get('violations', {}).items():
                    print(f"    {group}: {count}")
    else:
        # View specific report
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"Report date: {data.get('date', 'Unknown')}")
            violations = data.get('violations', {})
            total = sum(violations.values())
            
            print(f"Total violations: {total}")
            for group, count in violations.items():
                print(f"  {group}: {count}")
                
        except Exception as e:
            print(f"Error viewing report: {e}")

def process_and_send_all_reports():
    """Process all reports and send consolidated emails by region"""
    reports_logger.info("Processing all reports and sending consolidated emails")
    
    # Load all violation data
    all_violations = load_violations_data()
    
    if not all_violations:
        reports_logger.warning("No violation data found")
        return False
        
    # Load email configuration
    email_config = load_email_config()
    if not email_config:
        reports_logger.error("Failed to load email configuration")
        return False
        
    # Send consolidated reports by region
    result = process_and_send_reports(all_violations, email_config)
    
    reports_logger.info(f"Consolidated email sending {'succeeded' if result else 'failed'}")
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        process_and_send_all_reports()
    else:
        view_report()
