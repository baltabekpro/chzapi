import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from logger_config import get_logger, log_exception
from email_utils import load_email_config

# Set up logger
email_logger = get_logger("email")

def get_yesterday_date():
    """Get yesterday's date in YYYY-MM-DD format"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

def load_all_reports(base_dir='output') -> List[Dict]:
    """
    Load all violation reports for yesterday from all certificates
    
    Returns:
        List of report objects with certificate and violation data
    """
    if not os.path.exists(base_dir):
        email_logger.warning(f"Report directory not found: {base_dir}")
        return []
    
    yesterday = get_yesterday_date()
    email_logger.info(f"Looking for reports from date: {yesterday}")
    
    all_reports = []
    
    for cert_dir in os.listdir(base_dir):
        cert_path = os.path.join(base_dir, cert_dir)
        if not os.path.isdir(cert_path):
            continue
            
        # Look for yesterday's report
        report_file = os.path.join(cert_path, f'violations_{yesterday}.json')
        
        if os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    
                all_reports.append({
                    'certificate': cert_dir,
                    'data': report_data
                })
                
                email_logger.info(f"Loaded report for {cert_dir}")
                
            except Exception as e:
                log_exception(email_logger, e, f"Error loading report for {cert_dir}")
    
    email_logger.info(f"Loaded {len(all_reports)} reports in total")
    return all_reports

def load_regions_data() -> Dict:
    """Load regions configuration"""
    try:
        with open('regions.json', 'r', encoding='utf-8') as f:
            regions = json.load(f)
            email_logger.info(f"Loaded {len(regions)} regions from configuration")
            return regions
    except Exception as e:
        log_exception(email_logger, e, "Failed to load regions configuration")
        return {}

def generate_consolidated_report_by_region() -> Dict[str, Dict]:
    """
    Generate consolidated report by region
    
    Returns:
        Dictionary with region as key and report data as value
    """
    all_reports = load_all_reports()
    regions_data = load_regions_data()
    
    # Map certificate names to regions
    cert_to_region = {}
    
    for region_id, region_info in regions_data.items():
        region_name = region_info.get('name', f'Регион {region_id}')
        email_logger.debug(f"Processing region {region_id} ({region_name})")
        
        for tc in region_info.get('tc_list', []):
            cert_to_region[tc] = region_id
    
    # Initialize regional reports
    regional_reports = defaultdict(lambda: {
        'date': get_yesterday_date(),
        'region_name': 'Неизвестный регион',  # Will be replaced with actual region name
        'certificates': [],
        'violations': defaultdict(int),
        'total_violations': 0
    })
    
    # Consolidate reports by region
    import re
    for report in all_reports:
        cert_name = report['certificate']
        
        # Extract TC ID from certificate name (format: "Имя Фамилия - тсXXX")
        tc_match = re.search(r'(тс\d+)', cert_name)
        tc_id = tc_match.group(1) if tc_match else cert_name
        
        # Log the extraction
        email_logger.debug(f"Extracted TC ID '{tc_id}' from certificate name '{cert_name}'")
        
        # Get region ID, defaulting to "unassigned" if not mapped
        region_id = cert_to_region.get(tc_id, "unassigned")
        
        email_logger.info(f"Mapping certificate '{cert_name}' with TC ID '{tc_id}' to region '{region_id}'")
        
        # Get region name from config
        if region_id in regions_data:
            region_name = regions_data[region_id].get('name', f'Регион {region_id}')
            regional_reports[region_id]['region_name'] = region_name
        else:
            # Handle unassigned certificates
            regional_reports[region_id]['region_name'] = "Нераспределенные ТС"
        
        regional_reports[region_id]['certificates'].append(cert_name)
        
        # Add violations data
        for product_group, count in report['data'].get('violations', {}).items():
            try:
                count_value = int(count)
                regional_reports[region_id]['violations'][product_group] += count_value
                regional_reports[region_id]['total_violations'] += count_value
            except (ValueError, TypeError) as e:
                email_logger.warning(f"Invalid count value for {product_group}: {count} ({type(count)})")
    
    # Convert defaultdicts to regular dicts for serialization
    result = {}
    for region_id, data in regional_reports.items():
        result[region_id] = {
            'date': data['date'],
            'region_name': data['region_name'],
            'certificates': data['certificates'],
            'violations': dict(data['violations']),
            'total_violations': data['total_violations']
        }
        email_logger.info(f"Region {data['region_name']} has {data['total_violations']} violations across {len(data['certificates'])} certificates")
    
    return result

def send_regional_reports() -> bool:
    """
    Send consolidated regional reports
    
    Returns:
        bool: True if all reports were sent successfully, False otherwise
    """
    from email_sender import send_report_emails
    
    # Generate consolidated reports
    regional_reports = generate_consolidated_report_by_region()
    
    if not regional_reports:
        email_logger.warning("No reports to send")
        return False
    
    # Send emails using the updated email_sender module
    success = send_report_emails(regional_reports)
    
    # Update last email run time
    try:
        last_run = {
            "last_run": datetime.now().isoformat(),
            "manual_run": False
        }
        
        with open('last_email_run.json', 'w', encoding='utf-8') as f:
            json.dump(last_run, f, indent=2)
            
        email_logger.info("Updated last email run time")
        
    except Exception as e:
        log_exception(email_logger, e, "Error updating last email run time")
    
    return success

def process_and_send_reports() -> bool:
    """
    Main function to process and send reports
    
    Returns:
        bool: True if successful, False otherwise
    """
    email_logger.info("Starting report processing and email sending")
    
    try:
        # Debug log what reports we're finding
        base_dir = 'output'
        if os.path.exists(base_dir):
            for cert_dir in os.listdir(base_dir):
                cert_path = os.path.join(base_dir, cert_dir)
                if os.path.isdir(cert_path):
                    email_logger.debug(f"Checking directory: {cert_path}")
                    for file in os.listdir(cert_path):
                        if file.startswith('violations_'):
                            email_logger.debug(f"Found report file: {file}")
        
        # Send regional reports
        result = send_regional_reports()
        
        if result:
            email_logger.info("Successfully processed and sent all reports")
        else:
            email_logger.warning("Some issues occurred while processing and sending reports")
        
        return result
        
    except Exception as e:
        log_exception(email_logger, e, "Error processing and sending reports")
        return False

if __name__ == "__main__":
    process_and_send_reports()
