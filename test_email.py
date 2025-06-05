import os
import json
import smtplib
import unittest
from unittest import mock
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from colorama import Fore, init
init(autoreset=True)

# Import email modules
try:
    from email_utils import load_email_config, send_violations_report, send_test_email
    from email_sender import send_report_emails
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}")
    print(f"{Fore.YELLOW}Make sure you're running this test from the project root directory.")
    exit(1)

# Configure test output file
TEST_LOG_FILE = "test_email_results.log"

def log_result(message):
    """Log a message to the test log file"""
    with open(TEST_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def clear_log():
    """Clear the test log file"""
    with open(TEST_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== Email Functionality Test Results ===\n")
        f.write(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")


class EmailTest(unittest.TestCase):
    """Test the email functionality"""

    @mock.patch("smtplib.SMTP")
    def test_single_email(self, mock_smtp):
        """Test sending a single email"""
        clear_log()
        log_result("Testing individual email sending")

        # Set up mock
        mock_server = mock.MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Create a test email config
        email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "test@example.com",
            "sender_password": "password123",
            "recipient_emails": ["recipient1@example.com", "recipient2@example.com"]
        }
        
        log_result(f"Using email configuration:")
        log_result(f"  SMTP Server: {email_config['smtp_server']}")
        log_result(f"  SMTP Port: {email_config['smtp_port']}")
        log_result(f"  Sender: {email_config['sender_email']}")
        log_result(f"  Recipients: {', '.join(email_config['recipient_emails'])}")

        # Prepare test data
        cert_name = "Test Certificate"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        violations_data = {
            "date": yesterday,
            "violations": {
                "Молочная продукция": 10,
                "Обувные товары": 5,
                "Табачная продукция": 15
            }
        }
        
        log_result(f"Created test violations data for {cert_name} on {yesterday}:")
        log_result(f"  Молочная продукция: {violations_data['violations']['Молочная продукция']} violations")
        log_result(f"  Обувные товары: {violations_data['violations']['Обувные товары']} violations")
        log_result(f"  Табачная продукция: {violations_data['violations']['Табачная продукция']} violations")

        # Define email capture function
        def capture_email(msg):
            log_result(f"Email would be sent with:")
            log_result(f"  Subject: {msg['Subject']}")
            log_result(f"  From: {msg['From']}")
            log_result(f"  To: {msg['To']}")
            
            # Extract HTML content
            for part in msg.get_payload():
                if part.get_content_type() == 'text/html':
                    content = part.get_payload()
                    log_result("\nEmail HTML content (excerpt):")
                    lines = content.split('\n')
                    for line in lines[:30]:  # First 30 lines
                        if line.strip():  # Only non-empty lines
                            log_result(f"  {line.strip()}")
                    if len(lines) > 30:
                        log_result("  ...")
            return True
        
        # Set up the mock to capture the email
        mock_server.send_message.side_effect = capture_email

        # Send the violations report
        log_result("\nAttempting to send violations report...")
        result = send_violations_report(cert_name, violations_data, email_config)
        
        # Check result
        self.assertTrue(result)
        self.assertTrue(mock_server.send_message.called)
        log_result(f"Email sending result: {'SUCCESS' if result else 'FAILED'}")

    @mock.patch("smtplib.SMTP")
    def test_regional_emails(self, mock_smtp):
        """Test sending regional emails"""
        log_result("\n" + "="*50)
        log_result("Testing regional email reports")

        # Set up mock
        mock_server = mock.MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Create test regions data
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        reports_data = {
            "region1": {
                "region_name": "Москва и МО",
                "date": yesterday,
                "violations": {
                    "Молочная продукция": 10,
                    "Обувные товары": 5
                },
                "total_violations": 15
            },
            "region2": {
                "region_name": "Санкт-Петербург",
                "date": yesterday,
                "violations": {
                    "Молочная продукция": 7,
                    "Табачная продукция": 15
                },
                "total_violations": 22
            }
        }
        
        log_result(f"Created test data for {len(reports_data)} regions:")
        for region_id, data in reports_data.items():
            log_result(f"  Region: {data['region_name']} ({region_id})")
            log_result(f"    Date: {data['date']}")
            log_result(f"    Total violations: {data['total_violations']}")
            for group, count in data['violations'].items():
                log_result(f"      {group}: {count}")

        # Create mock regions.json content
        regions_data = {
            "region1": {
                "name": "Москва и МО",
                "tc_list": ["ТС1", "ТС2"],
                "emails": ["moscow@example.com"]
            },
            "region2": {
                "name": "Санкт-Петербург",
                "tc_list": ["ТС3", "ТС4"],
                "emails": ["spb@example.com"]
            }
        }
        
        # Save regions.json
        with open('regions.json', 'w', encoding='utf-8') as f:
            json.dump(regions_data, f, ensure_ascii=False, indent=2)
        log_result("\nCreated regions.json with region configurations")

        # Create email_config.json
        email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "reports@example.com",
            "sender_password": "password123",
            "recipient_emails": ["default@example.com"]
        }
        
        # Save email_config.json
        with open('email_config.json', 'w', encoding='utf-8') as f:
            json.dump(email_config, f, ensure_ascii=False, indent=2)
        log_result("Created email_config.json with email settings")

        # Define email capture function
        emails_sent = []
        def capture_email(msg):
            email_info = {
                "subject": msg['Subject'],
                "from": msg['From'],
                "to": msg['To'],
                "region": next((region_data["region_name"] for region_id, region_data in regions_data.items() 
                              if region_data["name"] in msg['Subject']), "Unknown")
            }
            emails_sent.append(email_info)
            
            log_result(f"\nWould send email for {email_info['region']}:")
            log_result(f"  Subject: {email_info['subject']}")
            log_result(f"  From: {email_info['from']}")
            log_result(f"  To: {email_info['to']}")
            
            # Extract HTML content
            for part in msg.get_payload():
                if part.get_content_type() == 'text/html':
                    content = part.get_payload()
                    log_result("\n  Email HTML content (excerpt):")
                    lines = content.split('\n')
                    for line in lines[:20]:  # First 20 lines
                        if line.strip():  # Only non-empty lines
                            log_result(f"    {line.strip()}")
                    if len(lines) > 20:
                        log_result("    ...")
            return True
        
        # Set up the mock to capture the email
        mock_server.send_message.side_effect = capture_email

        # Send the regional reports
        log_result("\nAttempting to send regional reports...")
        result = send_report_emails(reports_data, yesterday)
        
        # Check result
        self.assertTrue(result)
        self.assertEqual(len(emails_sent), 2)  # Should send 2 emails, one per region
        log_result(f"Regional email sending result: {'SUCCESS' if result else 'FAILED'}")
        log_result(f"Number of emails sent: {len(emails_sent)}")

# Run the tests
if __name__ == '__main__':
    print(f"{Fore.CYAN}=== Running Email Tests ===")
    print(f"{Fore.YELLOW}Testing email functionality with detailed logging")
    print(f"{Fore.YELLOW}Results will be saved to {TEST_LOG_FILE}")
    
    # Run the tests
    unittest.main(verbosity=2)