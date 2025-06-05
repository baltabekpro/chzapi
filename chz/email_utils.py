import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from logger_config import get_logger, log_exception

# Set up logger
email_logger = get_logger("email")

def load_email_config():
    """Load email configuration from file"""
    try:
        with open('email_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            email_logger.info("Email configuration loaded successfully")
            return config
    except Exception as e:
        log_exception(email_logger, e, "Error loading email config")
        return None

def send_violations_report(cert_name: str, violations_data: dict, email_config: dict) -> bool:
    """Send email with violations report
    
    Args:
        cert_name: Certificate name/ID
        violations_data: Dictionary with violation data
        email_config: Email configuration dictionary
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        email_logger.info(f"Preparing email report for {cert_name} on {violations_data['date']}")
        
        # Create HTML content
        html = f"""
        <h2>Отчет о нарушениях маркировки за {violations_data['date']}</h2>
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

def send_test_email(email_config=None):
    """Send a test email to verify configuration"""
    if not email_config:
        email_config = load_email_config()
        if not email_config:
            print("Failed to load email configuration")
            return False
    
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['Subject'] = f"Test email from ЦРПТ processor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        msg['From'] = email_config['sender_email']
        recipients = email_config['recipient_emails']
        msg['To'] = ', '.join(recipients)
        
        # Add text content
        text = "Это тестовое сообщение от системы обработки отчетов ЦРПТ. Если вы видите это сообщение, значит настройки email работают корректно."
        msg.attach(MIMEText(text, 'plain'))
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
            
        print("Test email sent successfully")
        email_logger.info(f"Test email sent to {', '.join(recipients)}")
        return True
        
    except Exception as e:
        print(f"Error sending test email: {e}")
        log_exception(email_logger, e, "Error sending test email")
        return False

if __name__ == "__main__":
    # If run directly, send a test email
    send_test_email()
