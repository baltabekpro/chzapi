import os
import json
import sys
import re  # Add missing import for regular expressions
import csv  # Add import for CSV handling
import pandas as pd  # Add pandas for Excel processing
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
                # Return number of violations (rows minus header)
                return max(0, len(rows) - 1)  # Subtract header row
                
        except UnicodeDecodeError:
            continue
        except Exception as e:
            reports_logger.warning(f"Error with {encoding} encoding: {e}")
            continue
    
    reports_logger.error(f"Could not read file {file_path} with any encoding")
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
    
    # Find CSV and Excel files to process
    report_files = [f for f in os.listdir(reports_dir) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
    reports_logger.info(f"Found {len(report_files)} report files to process (CSV/Excel)")
    
    # Process violations data - no changes to this part
    encodings = ['cp1251', 'utf-8-sig', 'utf-8', 'windows-1251', 'latin1']
    
    for report_file in report_files:
        try:
            input_path = os.path.join(reports_dir, report_file)
            reports_logger.info(f"Processing file: {report_file}")
            
            # Extract group code from filename (e.g. violations_group1__20250303_235139.csv or .xlsx)
            group_code = None
            match = re.search(r'group(\d+)', report_file)
            if match:
                group_code = int(match.group(1))
            if group_code is None:
                reports_logger.warning(f"No group code found in filename: {report_file}")
                continue
              
            # Get product group name
            product_name = PRODUCT_GROUPS.get(group_code)
            if not product_name:
                reports_logger.warning(f"Unknown product group code: {group_code}")
                continue
            
            # Read count based on file type
            ext = os.path.splitext(report_file)[1].lower()
            if ext in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(input_path, engine='openpyxl')
                    violation_count = len(df)
                except Exception as e:
                    reports_logger.error(f"Error reading Excel file {report_file}: {e}")
                    violation_count = 0
            else:
                violation_count = read_csv_with_encoding(input_path)
            
            violations_data['violations'][product_name] = violation_count
            reports_logger.info(f"Found {violation_count} violations for {product_name}")
            
            # os.remove(input_path)  # Закомментировано: сохраняем CSV файлы для дополнительного анализа
            reports_logger.info(f"Processed {report_file}")
            
        except Exception as e:
            log_exception(reports_logger, e, f"Error processing {report_file}")
    
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
