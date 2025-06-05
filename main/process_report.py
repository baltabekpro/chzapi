from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from logger_config import get_logger, log_exception

# Try to import pandas and chardet, install if missing
try:
    import pandas as pd
except ImportError:
    import subprocess
    import sys
    print("Installing pandas...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

try:
    import chardet
except ImportError:
    import subprocess
    import sys
    print("Installing chardet...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chardet"])
    import chardet

# Try to import other required modules
try:
    import os
    import zipfile
    import json
    import tempfile
    import shutil
except ImportError:
    print("Missing standard library modules. Please check your Python installation.")

# Set up logger
reports_logger = get_logger("reports")

def detect_encoding(file_path: str) -> str:
    """
    Определяет кодировку файла
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024*1024)  # Read up to 1MB
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            reports_logger.info(f"Detected encoding: {encoding} (confidence: {result['confidence']})")
            return encoding
    except Exception as e:
        log_exception(reports_logger, e, f"Error detecting encoding for {file_path}")
        return 'utf-8'  # Default to UTF-8

def process_violations_report(zip_file_path: str) -> None:
    """Обрабатывает ZIP-файл с отчетом о нарушениях и сохраняет результаты в JSON"""
    extract_dir = "report_" + datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        # Распаковываем архив
        reports_logger.info(f"Extracting {zip_file_path}...")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Ищем CSV файл
        csv_files = [f for f in os.listdir(extract_dir) if f.endswith('.csv')]
        if not csv_files:
            reports_logger.error(f"No CSV files found in {zip_file_path}")
            shutil.rmtree(extract_dir)
            return
        
        csv_file = os.path.join(extract_dir, csv_files[0])
        reports_logger.info(f"Found file: {csv_files[0]}")
        
        # Подготавливаем структуру для JSON
        result = {
            "meta": {
                "generated": datetime.now().isoformat(),
                "source_file": zip_file_path,
                "report_date": datetime.now().strftime('%Y-%m-%d')
            },
            "statistics": defaultdict(int),
            "violations": []
        }
        
        # Читаем и анализируем CSV
        df, encoding, separator = try_read_file_with_encodings(csv_file)
        
        if df is not None:
            # Count violations by product group
            product_group_col = None
            
            # Try to find product group column
            potential_columns = [
                'Товарная группа', 'Группа товаров', 'Product Group',
                'ТГ', 'Товарная_группа', 'Группа_товаров'
            ]
            
            for col in potential_columns:
                if col in df.columns:
                    product_group_col = col
                    break
            
            if product_group_col:
                # Count violations by product group
                group_counts = df[product_group_col].value_counts().to_dict()
                
                for group, count in group_counts.items():
                    result["statistics"][group] = int(count)
                
                # Add all violations to the result
                for _, row in df.iterrows():
                    violation = {}
                    for col in df.columns:
                        violation[col] = str(row[col])
                    result["violations"].append(violation)
            else:
                reports_logger.warning(f"Product group column not found in {csv_file}")
                
                # Try to infer product group from filename
                if 'group' in zip_file_path.lower():
                    import re
                    match = re.search(r'group(\d+)', zip_file_path.lower())
                    if match:
                        group_code = int(match.group(1))
                        from get_violations import PRODUCT_GROUPS
                        group_name = PRODUCT_GROUPS.get(group_code, f"Unknown Group {group_code}")
                        
                        # Count all rows as this group
                        result["statistics"][group_name] = len(df)
                        
                        # Add all violations to the result
                        for _, row in df.iterrows():
                            violation = {'Товарная группа': group_name}
                            for col in df.columns:
                                violation[col] = str(row[col])
                            result["violations"].append(violation)
            
            # Save results
            output_dir = os.path.join('reports', 'json')
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(
                output_dir, 
                f"violations_{os.path.basename(zip_file_path).split('.')[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            reports_logger.info(f"Violations report saved to {output_file}")
        
    except Exception as e:
        log_exception(reports_logger, e, f"Error processing violations report: {zip_file_path}")
    finally:
        # Clean up
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)

def try_read_file_with_encodings(file_path: str) -> tuple[pd.DataFrame, str, str]:
    """
    Пытается прочитать файл с разными кодировками и разделителями
    
    Returns:
        tuple[DataFrame, encoding, separator]
    """
    encodings = ['cp1251', 'utf-8', 'windows-1251', 'ascii', 'iso-8859-1']
    separators = [';', ',', '\t', '|']
    errors = []

    # Сначала пробуем определить кодировку через chardet
    try:
        detected_encoding = detect_encoding(file_path)
        encodings.insert(0, detected_encoding)  # Try the detected encoding first
    except Exception as e:
        reports_logger.warning(f"Error detecting encoding: {e}")

    # Пробуем все комбинации кодировок и разделителей
    for encoding in encodings:
        for separator in separators:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=separator, low_memory=False)
                if len(df.columns) > 1:
                    reports_logger.info(f"Successfully read file with encoding: {encoding}, separator: {separator}")
                    return df, encoding, separator
            except Exception as e:
                errors.append(f"Encoding: {encoding}, Separator: {separator}, Error: {e}")
    
    # Если все попытки не удались, пробуем прочитать как текстовый файл
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
                
                if len(lines) > 0:
                    # Try to determine separator from first line
                    first_line = lines[0].strip()
                    for sep in separators:
                        if sep in first_line:
                            # Manually create dataframe
                            data = []
                            header = first_line.split(sep)
                            
                            for line in lines[1:]:
                                row = line.strip().split(sep)
                                if len(row) == len(header):
                                    data.append(row)
                            
                            df = pd.DataFrame(data, columns=header)
                            reports_logger.info(f"Manually parsed file with encoding: {encoding}, separator: {sep}")
                            return df, encoding, sep
        except Exception as e:
            errors.append(f"Manual parsing with encoding {encoding} failed: {e}")

    reports_logger.error(f"Could not read file {file_path}. Tried combinations:\n" + "\n".join(errors))
    return None, None, None

def process_reports(input_path: str) -> list:
    """
    Process CSV file and return list of dictionaries
    
    Args:
        input_path: Path to input CSV file
    Returns:
        List of dictionaries containing the processed data
    """
    temp_dir = None
    try:
        # Check if input is a ZIP file
        if input_path.lower().endswith('.zip'):
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            
            # Extract ZIP
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find CSV file
            csv_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith('.csv')]
            
            if not csv_files:
                reports_logger.error(f"No CSV files found in ZIP: {input_path}")
                return []
            
            input_path = csv_files[0]
        
        # Process CSV file
        df, encoding, separator = try_read_file_with_encodings(input_path)
        
        if df is None:
            reports_logger.error(f"Could not read file: {input_path}")
            return []
        
        # Convert to list of dictionaries
        records = df.to_dict('records')
        
        # Clean up any NaN values
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = ""
        
        reports_logger.info(f"Processed {len(records)} records from {input_path}")
        return records
    
    except Exception as e:
        log_exception(reports_logger, e, f"Error processing file: {input_path}")
        return []
    
    finally:
        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def process_multiple_reports(input_files: List[str], output_dir: str = None) -> Dict[str, Any]:
    """
    Обрабатывает несколько CSV файлов и объединяет их в один JSON
    
    Args:
        input_files: Список путей к CSV файлам
        output_dir: Директория для сохранения результата (если None, используется reports/json)
    Returns:
        Dict с результатами обработки
    """
    # Создаем директории если не указан output_dir
    if output_dir is None:
        output_dir = os.path.join('reports', 'json')
    
    os.makedirs(output_dir, exist_ok=True)
    
    all_records = []
    results = {
        "processed_files": 0,
        "total_records": 0,
        "output_file": "",
        "errors": []
    }
    
    try:
        # Process each file
        for input_file in input_files:
            try:
                records = process_reports(input_file)
                all_records.extend(records)
                results["processed_files"] += 1
                results["total_records"] += len(records)
                reports_logger.info(f"Added {len(records)} records from {input_file}")
            except Exception as e:
                error_msg = f"Error processing {input_file}: {str(e)}"
                results["errors"].append(error_msg)
                log_exception(reports_logger, e, f"Error processing {input_file}")
        
        # Save combined results
        if all_records:
            # Create result with proper structure
            output = {
                "meta": {
                    "generated": datetime.now().isoformat(),
                    "source_files": len(input_files),
                    "total_records": len(all_records)
                },
                "statistics": {},
                "violations": all_records
            }
            
            # Count violations by product group
            product_groups = defaultdict(int)
            
            for record in all_records:
                # Look for product group field with various possible names
                group = None
                for field in ['Товарная группа', 'Группа товаров', 'Product Group', 'ТГ']:
                    if field in record and record[field]:
                        group = record[field]
                        break
                
                if group:
                    product_groups[group] += 1
                else:
                    product_groups["Unknown"] += 1
            
            output["statistics"] = dict(product_groups)
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(output_dir, f"combined_violations_{timestamp}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            results["output_file"] = output_file
            reports_logger.info(f"Combined results saved to {output_file}")
        
    except Exception as e:
        error_msg = f"Error combining reports: {str(e)}"
        results["errors"].append(error_msg)
        log_exception(reports_logger, e, "Error combining reports")
    
    return results

def main():
    """Main function"""
    # Создаем базовую структуру директорий
    reports_dir = 'reports'
    json_dir = os.path.join(reports_dir, 'json')
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    # Ищем CSV файлы в директории reports
    csv_files = [f for f in os.listdir(reports_dir) if f.endswith('.csv')]
    if not csv_files:
        reports_logger.warning("No CSV files found in reports directory")
        return
    
    # Process each CSV file
    for csv_file in csv_files:
        input_path = os.path.join(reports_dir, csv_file)
        try:
            process_reports(input_path)
        except Exception as e:
            log_exception(reports_logger, e, f"Error processing {csv_file}")

if __name__ == "__main__":
    main()
