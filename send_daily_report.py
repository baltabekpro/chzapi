import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from logger_config import get_logger, log_exception
from email_utils import load_email_config, send_violations_report
from region_manager import load_regions_data

# Set up logger
email_logger = get_logger("email")

def get_yesterday_date():
    """Get yesterday's date in YYYY-MM-DD format"""
    return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

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
    
    for region, region_data in regions_data.items():
        for tc in region_data.get('tc_list', []):
            cert_to_region[tc] = region
    
    # Initialize regional reports
    regional_reports = defaultdict(lambda: {
        'date': get_yesterday_date(),
        'certificates': [],
        'cert_reports': {},  # individual reports per certificate
        'violations': defaultdict(int),
        'total': 0
    })
    
    # Consolidate reports by region
    for report in all_reports:
        cert_name = report['certificate']
        region = cert_to_region.get(cert_name, "Undefined")
        # Store individual certificate report
        regional_reports[region]['cert_reports'][cert_name] = report['data'].get('violations', {})
         
        regional_reports[region]['certificates'].append(cert_name)
        
        for product_group, count in report['data'].get('violations', {}).items():
            # Explicitly convert to integer to make sure we're dealing with numbers
            try:
                count_value = int(count)
                regional_reports[region]['violations'][product_group] += count_value
                regional_reports[region]['total'] += count_value
                
                # Debug log to see what values we're getting
                email_logger.debug(f"Product: {product_group}, Count: {count_value}, Type: {type(count_value)}")
            except (ValueError, TypeError) as e:
                email_logger.warning(f"Invalid count value for {product_group}: {count} ({type(count)})")
    
    # Convert defaultdicts to regular dicts for serialization
    result = {}
    for region, data in regional_reports.items():
        result[region] = {
            'date': data['date'],
            'certificates': data['certificates'],
            'violations': dict(data['violations']),
            'total': data['total']
        }
    
    return result

def send_regional_reports() -> bool:
    """
    Send consolidated regional reports
    
    Returns:
        bool: True if all reports were sent successfully, False otherwise
    """
    email_config = load_email_config()
    if not email_config:
        email_logger.error("Failed to load email configuration")
        return False
    
    regional_reports = generate_consolidated_report_by_region()
    regions_data = load_regions_data()
    
    if not regional_reports:
        email_logger.warning("No reports to send")
        return False
    
    success = True
    
    # Debug log to help diagnose issues
    email_logger.info(f"Found {len(regional_reports)} regional reports: {', '.join(regional_reports.keys())}")
    email_logger.info(f"Region data contains {len(regions_data)} regions: {', '.join(regions_data.keys())}")
    
    for region, report_data in regional_reports.items():
        # Don't skip Undefined regions - this was causing region2 to be skipped
        # if region == "Undefined" and len(regional_reports) > 1:
        #     continue
        
        try:
            # Get region name, defaulting to region key if not found
            region_name = regions_data.get(region, {}).get('name', region)
            email_logger.info(f"Processing report for region: {region} (display name: {region_name})")
            
            # Create email HTML content with individual tables per certificate
            html = f"""
            <h2>Отчет о нарушениях маркировки по региону {region_name}</h2>
            <h3>Дата: {report_data['date']} (данные за вчерашний день)</h3>
            """
            # For each certificate, add its own table
            for cert in report_data.get('cert_reports', {}):
                cert_violations = report_data['cert_reports'][cert]
                html += f"""
                <h4>Торговая точка: {cert}</h4>
                <table border=\"1\" style=\"border-collapse: collapse; width: 100%; margin-bottom:20px;\">
                    <tr style=\"background-color: #f2f2f2;\">
                        <th style=\"padding: 8px;\">Товарная группа</th>
                        <th style=\"padding: 8px;\">Количество нарушений</th>
                    </tr>
                """
                # Add rows for each product group in this certificate
                for product_group, count in sorted(
                    cert_violations.items(), key=lambda x: x[1], reverse=True
                ):
                    html += f"""
                    <tr>
                        <td style=\"padding: 8px;\">{product_group}</td>
                        <td style=\"padding: 8px; text-align: center;\">{count}</td>
                    </tr>
                    """
                # Add total row for this certificate
                total_count = sum(cert_violations.values())
                html += f"""
                    <tr style=\"background-color: #f2f2f2; font-weight: bold;\">
                        <td style=\"padding: 8px;\">Всего нарушений:</td>
                        <td style=\"padding: 8px; text-align: center;\">{total_count}</td>
                    </tr>
                </table>
                <br/>
                """
            # End for each certificate table
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Отчет о нарушениях маркировки - Регион {region_name} - {report_data['date']}"
            msg['From'] = email_config['sender_email']
            
            # Get recipients for this region
            recipients = regions_data.get(region, {}).get('emails', email_config['recipient_emails'])
            if not recipients:
                recipients = email_config['recipient_emails']
                
            msg['To'] = ', '.join(recipients)
            msg.attach(MIMEText(html, 'html'))
            
            email_logger.info(f"Sending email for region {region_name} to {len(recipients)} recipients")
            
            # Send email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
                
            email_logger.info(f"Email report sent successfully for region {region_name}")
            
        except Exception as e:
            log_exception(email_logger, e, f"Error sending email report for region {region}")
            success = False
    
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
        # Log debug info about what reports we're finding
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
