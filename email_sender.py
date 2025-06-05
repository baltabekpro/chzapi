import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from logger_config import get_logger, log_exception

# Configure logger
logger = get_logger("email_sender")

def load_email_config():
    """Load email configuration from file"""
    try:
        with open('email_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info("Email configuration loaded successfully")
            return config
    except FileNotFoundError:
        logger.error("Email configuration file not found")
        return None
    except Exception as e:
        log_exception(logger, e, "Error loading email configuration")
        return None

def send_report_emails(reports_data, date_str=None):
    """
    Send reports via email to configured recipients per region
    
    Args:
        reports_data: Dictionary of reports data by region
        date_str: Optional date string for the report
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Preparing to send email reports for date: {date_str}")
    
    # Load region configurations
    regions = {}
    try:
        with open('regions.json', 'r', encoding='utf-8') as f:
            regions = json.load(f)
        logger.info(f"Loaded {len(regions)} region configurations")
    except Exception as e:
        log_exception(logger, e, "Failed to load regions configuration")
        return False
    
    # Load email configuration
    email_config = load_email_config()
    if not email_config:
        logger.error("Failed to load email configuration")
        return False
    
    # Track success for each region
    success_count = 0
    total_regions = 0
    
    # Process each region that has reports
    for region_id, report_data in reports_data.items():
        # Skip undefined region if we have others (except when it's the only one)
        if region_id == "Undefined" and len(reports_data) > 1:
            logger.info(f"Skipping undefined region as other regions are available")
            continue
            
        if not report_data:
            logger.warning(f"No report data for region {region_id}, skipping")
            continue
        
        # Get region info - ensure we have the name
        region_info = regions.get(region_id, {})
        # Use the name from report_data first, then from region_info, finally fallback to region_id
        region_name = report_data.get('region_name', region_info.get('name', f"Регион {region_id}"))
        logger.debug(f"Processing region: {region_id}, name: {region_name}")
        
        # Get recipient emails for this region
        recipients = region_info.get('emails', [])
        # If region has no emails configured, use default from email_config
        if not recipients:
            recipients = email_config.get('recipient_emails', [])
            logger.info(f"No recipients for region {region_name}, using default recipients")
            
        if not recipients:
            logger.warning(f"No recipients configured for region {region_name}, skipping")
            continue
        
        logger.info(f"Sending report for region: {region_id} ({region_name}) to {len(recipients)} recipients")
        total_regions += 1
        
        # Construct email subject with proper region name
        subject = f"Отчет по маркировке товаров - {region_name} - {date_str}"
        
        # Construct email body
        body = f"""
        <html>
        <body>
        <h2>Отчет по маркировке товаров</h2>
        <p><b>Регион:</b> {region_name}</p>
        <p><b>Дата отчета:</b> {date_str}</p>
        <hr/>
        <h3>Результаты проверки:</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px;">Товарная группа</th>
                <th style="padding: 8px;">Количество нарушений</th>
            </tr>
        """
        
        # Add report content
        total_violations = report_data.get('total_violations', 0)
        for group, count in report_data.get('violations', {}).items():
            body += f"""
            <tr>
                <td style="padding: 8px;">{group}</td>
                <td style="padding: 8px; text-align: center;">{count}</td>
            </tr>
            """
        
        body += f"""
            <tr style="background-color: #f2f2f2; font-weight: bold;">
                <td style="padding: 8px;">Всего нарушений:</td>
                <td style="padding: 8px; text-align: center;">{total_violations}</td>
            </tr>
        </table>
        <p>Этот отчет содержит данные за вчерашний день.</p>
        </body>
        </html>
        """
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = email_config['sender_email']
            msg['To'] = ', '.join(recipients)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
            
            logger.info(f"Email report sent successfully for region {region_name}")
            success_count += 1
            
        except Exception as e:
            log_exception(logger, e, f"Error sending email for region {region_name}")
    
    # Return overall success
    logger.info(f"Email sending complete: {success_count}/{total_regions} regions processed successfully")
    return success_count > 0

if __name__ == "__main__":
    # Test function when run directly
    print("This module is not meant to be run directly.")