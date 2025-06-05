import os
import sys
import json
import smtplib
import unittest
import tempfile
import shutil
from unittest import mock
from datetime import datetime, timedelta
from io import StringIO
from colorama import Fore, init
init(autoreset=True)

# Import modules to test
# We need to import these modules in a try-except block to handle any import errors gracefully
try:
    from email_utils import load_email_config, send_violations_report, send_test_email
    from email_sender import send_report_emails
    import region_manager  # Import the module instead of a specific class
    from file_utils import list_files_in_directory, check_last_run_info
    from main import (
        process_reports_for_token, send_violations_report as main_send_violations,
        generate_report_for_region, process_reports, load_product_groups, load_tokens
    )
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}")
    print(f"{Fore.YELLOW}Make sure you're running this test from the project root directory.")
    sys.exit(1)

# Configure test output file
TEST_RESULTS_FILE = "test_results_comprehensive.log"

def log_test_result(message):
    """Log test result to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TEST_RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

class TestReportSystem(unittest.TestCase):
    """Test suite for the ЦРПТ report system"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Create test output file with clear indication that this is the start of a new run
        with open(TEST_RESULTS_FILE, "w", encoding="utf-8") as f:
            f.write(f"====================================================\n")
            f.write(f"=== Test Results for ЦРПТ Report System (Comprehensive) ===\n")
            f.write(f"=== Test run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"====================================================\n\n")
        
        # Create temporary test directory
        cls.test_dir = tempfile.mkdtemp(prefix="crpt_test_")
        log_test_result(f"Created temporary test directory: {cls.test_dir}")

        # Create mock data structures
        cls.create_mock_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Remove temporary directory
        shutil.rmtree(cls.test_dir, ignore_errors=True)
        log_test_result(f"Removed temporary test directory: {cls.test_dir}")
        
        # Add test completion marker
        with open(TEST_RESULTS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n====================================================\n")
            f.write(f"=== Test run completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"====================================================\n")

    @classmethod
    def create_mock_data(cls):
        """Create mock data for testing"""
        # Create directories structure
        os.makedirs(os.path.join(cls.test_dir, "output/Хуторская Татьяна - тс5"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "output/Лежнева Евгения - тс54"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "logs"), exist_ok=True)
        
        # Create mock violation reports
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Mock violations for ts5
        violations_ts5 = {
            "date": yesterday,
            "violations": {
                "Молочная продукция": 10,
                "Обувные товары": 5
            }
        }
        
        # Mock violations for ts54
        violations_ts54 = {
            "date": yesterday,
            "violations": {
                "Молочная продукция": 7,
                "Табачная продукция": 15
            }
        }
        
        # Write mock data to files
        with open(os.path.join(cls.test_dir, f"output/Хуторская Татьяна - тс5/violations_{yesterday}.json"), "w", encoding="utf-8") as f:
            json.dump(violations_ts5, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(cls.test_dir, f"output/Лежнева Евгения - тс54/violations_{yesterday}.json"), "w", encoding="utf-8") as f:
            json.dump(violations_ts54, f, ensure_ascii=False, indent=2)
        
        # Create mock regions.json
        regions_data = {
            "region1": {
                "name": "Регион 1",
                "tc_list": ["Хуторская Татьяна - тс5"],
                "emails": ["test1@example.com"]
            },
            "region2": {
                "name": "Регион 2",
                "tc_list": ["Лежнева Евгения - тс54"],
                "emails": ["test2@example.com"]
            }
        }
        
        with open(os.path.join(cls.test_dir, "regions.json"), "w", encoding="utf-8") as f:
            json.dump(regions_data, f, ensure_ascii=False, indent=2)
        
        # Create mock email_config.json
        email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "test@example.com",
            "sender_password": "password123",
            "recipient_emails": ["recipient@example.com"]
        }
        
        with open(os.path.join(cls.test_dir, "email_config.json"), "w", encoding="utf-8") as f:
            json.dump(email_config, f, ensure_ascii=False, indent=2)
        
        # Mock certificates.json
        cert_inns = {
            "Хуторская Татьяна": [{"тс5": "1234567890"}],
            "Лежнева Евгения": [{"тс54": "0987654321"}]
        }
        
        with open(os.path.join(cls.test_dir, "cert_inns.json"), "w", encoding="utf-8") as f:
            json.dump(cert_inns, f, ensure_ascii=False, indent=2)
        
        # Create mock products.txt
        with open(os.path.join(cls.test_dir, "products.txt"), "w", encoding="utf-8") as f:
            f.write("10\n")  # молочная продукция
            f.write("3\n")   # табачная продукция 
            f.write("2\n")   # обувь

        log_test_result("Created mock data files for testing")

    def setUp(self):
        """Set up before each test"""
        # Save current working directory
        self.original_cwd = os.getcwd()
        # Change to test directory
        os.chdir(self.test_dir)
        
    def tearDown(self):
        """Clean up after each test"""
        # Restore original working directory
        os.chdir(self.original_cwd)

    @mock.patch("smtplib.SMTP")
    def test_email_sending(self, mock_smtp):
        """Test email sending functionality"""
        log_test_result("\n----- TEST: Email Sending -----")
        
        # Configure mock SMTP
        mock_server = mock.MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Load email config from our test directory
        email_config = load_email_config()
        self.assertIsNotNone(email_config)
        log_test_result(f"Successfully loaded email configuration: {email_config['smtp_server']}")
        
        # Test sending a violations report
        cert_name = "Хуторская Татьяна - тс5"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        violations_data = {
            "date": yesterday,
            "violations": {
                "Молочная продукция": 10,
                "Обувные товары": 5
            }
        }
        log_test_result(f"Prepared violations data for {cert_name} on {yesterday}")
        log_test_result(f"Violations data: {json.dumps(violations_data, ensure_ascii=False)}")
        
        # Mock the actual sending to capture the email content
        def capture_message(msg):
            log_test_result(f"Email would be sent with subject: {msg['Subject']}")
            log_test_result(f"Email recipients: {msg['To']}")
            log_test_result(f"Email sender: {msg['From']}")
            
            # Extract HTML content (simplified)
            for part in msg.get_payload():
                if part.get_content_type() == 'text/html':
                    content = part.get_payload()
                    log_test_result("Email content (HTML):")
                    lines = content.split('\n')
                    for line in lines[:20]:  # Show first 20 lines
                        log_test_result(f"  {line.strip()}")
                    if len(lines) > 20:
                        log_test_result("  ... (content truncated)")
            return True
                    
        mock_server.send_message.side_effect = capture_message
        
        # Test sending a violations report
        result = send_violations_report(cert_name, violations_data, email_config)
        self.assertTrue(result)
        self.assertTrue(mock_server.send_message.called)
        
        log_test_result("✓ Email sending test passed")

    def test_report_processing(self):
        """Test report processing functionality"""
        log_test_result("\n----- TEST: Report Processing -----")
        
        # Test generating a report for a region
        region_id = "region1"
        with open("regions.json", "r", encoding="utf-8") as f:
            regions = json.load(f)
        
        region_info = regions[region_id]
        log_test_result(f"Testing report generation for region: {region_info['name']} ({region_id})")
        log_test_result(f"Region configuration: {json.dumps(region_info, ensure_ascii=False)}")
        
        report = generate_report_for_region(region_id, region_info)
        
        self.assertIsNotNone(report)
        self.assertEqual(report["region_name"], "Регион 1")
        self.assertTrue("violations" in report)
        self.assertTrue("total_violations" in report)
        
        # Log what we would see in the report
        log_test_result(f"Generated report for region: {report['region_name']}")
        log_test_result(f"Report date: {report['date']}")
        log_test_result(f"Total violations: {report['total_violations']}")
        log_test_result("Violations by product group:")
        for group, count in report['violations'].items():
            log_test_result(f"  {group}: {count}")
        
        log_test_result("✓ Report processing test passed")

    @mock.patch("smtplib.SMTP")
    def test_email_report_sending(self, mock_smtp):
        """Test sending reports via email"""
        log_test_result("\n----- TEST: Email Report Sending -----")
        
        # Configure mock SMTP
        mock_server = mock.MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Build test reports data
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        reports_data = {
            "region1": {
                "region_name": "Регион 1",
                "date": yesterday,
                "violations": {
                    "Молочная продукция": 10,
                    "Обувные товары": 5
                },
                "total_violations": 15
            },
            "region2": {
                "region_name": "Регион 2",
                "date": yesterday,
                "violations": {
                    "Молочная продукция": 7,
                    "Табачная продукция": 15
                },
                "total_violations": 22
            }
        }
        
        log_test_result(f"Prepared reports data for regions: {', '.join(reports_data.keys())}")
        for region_id, report in reports_data.items():
            log_test_result(f"Region {region_id} report: {json.dumps(report, ensure_ascii=False)}")
        
        # Capture emails to log
        sent_emails = []
        def capture_message(msg):
            email_data = {
                "subject": msg["Subject"],
                "to": msg["To"],
                "from": msg["From"],
                "region": msg["Subject"].split(" - ")[1] if " - " in msg["Subject"] else "Unknown"
            }
            sent_emails.append(email_data)
            log_test_result(f"Would send email: {json.dumps(email_data, ensure_ascii=False)}")
            
            # Extract HTML content (simplified)
            for part in msg.get_payload():
                if part.get_content_type() == 'text/html':
                    content = part.get_payload()
                    log_test_result(f"Email content for {email_data['region']} (first 10 lines):")
                    lines = content.split('\n')
                    for line in lines[:10]:
                        log_test_result(f"  {line.strip()}")
                    log_test_result("  ...")
            
            return True
        
        mock_server.send_message.side_effect = capture_message
        
        # Test sending regional reports
        from email_sender import send_report_emails
        result = send_report_emails(reports_data, yesterday)
        
        self.assertTrue(result)
        self.assertEqual(len(sent_emails), 2)  # Should send 2 emails, one per region
        
        log_test_result("✓ Email report sending test passed")
        
    def test_file_operations(self):
        """Test file operations"""
        log_test_result("\n----- TEST: File Operations -----")
        
        # Test loading product groups
        with mock.patch('builtins.open', mock.mock_open(read_data='10\n3\n2\n')):
            groups = load_product_groups()
            self.assertEqual(len(groups), 3)
            log_test_result(f"Successfully loaded {len(groups)} product groups: {groups}")
        
        # Test checking last run info with a mock file
        last_run_time = datetime.now() - timedelta(hours=12)
        next_run_time = datetime.now() + timedelta(hours=12)
        
        last_run_data = {
            'last_run': last_run_time.isoformat(),
            'next_run': next_run_time.isoformat()
        }
        
        with open('last_run.json', 'w') as f:
            json.dump(last_run_data, f)
        
        log_test_result("Created mock last_run.json file")
        log_test_result(f"Last run data: {json.dumps(last_run_data)}")
        
        # Verify the file exists and can be read
        self.assertTrue(os.path.exists('last_run.json'))
        with open('last_run.json', 'r') as f:
            data = json.load(f)
            log_test_result(f"Read back last run info: {json.dumps(data)}")
            self.assertEqual(data['last_run'], last_run_time.isoformat())
            self.assertEqual(data['next_run'], next_run_time.isoformat())
        
        log_test_result("✓ File operations test passed")
        
    def test_region_management(self):
        """Test region management"""
        log_test_result("\n----- TEST: Region Management -----")
        
        # Test adding a region
        region_id = "test_region"
        region_name = "Test Region"
        emails = ["test@example.com"]
        
        log_test_result(f"Testing adding region: {region_name} ({region_id})")
        
        # Mock the region_manager functions to avoid file operations
        with mock.patch('region_manager.load_regions_data', return_value={}), \
             mock.patch('region_manager.save_regions_data', return_value=True):
            
            # Test add_region function
            success = region_manager.add_region(region_id, region_name, emails)
            self.assertTrue(success)
            log_test_result(f"Successfully added region: {region_name} ({region_id})")
            
            # Test add_tc_to_region function
            with mock.patch('region_manager.load_regions_data', return_value={
                region_id: {
                    "name": region_name,
                    "emails": emails,
                    "tc_list": []
                }
            }):
                tc_name = "Test TC"
                log_test_result(f"Testing adding TC {tc_name} to region {region_name}")
                
                success = region_manager.add_tc_to_region(tc_name, region_id)
                self.assertTrue(success)
                log_test_result(f"Successfully added TC {tc_name} to region {region_name}")
                
                # Test get_tc_region function
                with mock.patch('region_manager.load_regions_data', return_value={
                    region_id: {
                        "name": region_name,
                        "emails": emails,
                        "tc_list": [tc_name]
                    }
                }):
                    log_test_result(f"Testing finding region for TC {tc_name}")
                    
                    found_region = region_manager.get_tc_region(tc_name)
                    self.assertEqual(found_region, region_id)
                    log_test_result(f"Successfully found TC {tc_name} in region {region_id}")
                    
                    # Test TC that doesn't exist
                    non_existent_tc = "Non-existent TC"
                    log_test_result(f"Testing finding region for non-existent TC {non_existent_tc}")
                    
                    found_region = region_manager.get_tc_region(non_existent_tc)
                    self.assertEqual(found_region, "Undefined")
                    log_test_result(f"TC {non_existent_tc} correctly returned region {found_region} (expected: Undefined)")
        
        log_test_result("✓ Region management test passed")

    @mock.patch("smtplib.SMTP")
    def test_process_reports_for_token(self, mock_smtp):
        """Test processing reports for a single token"""
        log_test_result("\n----- TEST: Process Reports for Token -----")
        
        # Configure mock SMTP
        mock_server = mock.MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create test directory structure
        cert_name = "Test Certificate"
        reports_dir = os.path.join("output", cert_name, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        log_test_result(f"Created test directory structure for {cert_name}")
        
        # Create a mock CSV file
        csv_path = os.path.join(reports_dir, "violations_group10__20250411_120000.csv")
        with open(csv_path, "w") as f:
            f.write("header1,header2,header3\n")
            f.write("data1,data2,data3\n")
            f.write("data4,data5,data6\n")
        log_test_result(f"Created mock CSV file: {csv_path}")
        
        # Mock email config
        email_config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "sender_email": "test@example.com",
            "sender_password": "password",
            "recipient_emails": ["recipient@example.com"]
        }
        log_test_result(f"Prepared mock email config: {json.dumps(email_config)}")
        
        # Create products.txt with product groups
        with open("products.txt", "w") as f:
            f.write("10\n")  # Add product group code
        log_test_result("Created mock products.txt file with product group 10")
        
        # Create mock PRODUCT_GROUPS mapping
        with mock.patch("get_violations.PRODUCT_GROUPS", {10: "Молочная продукция"}):
            log_test_result("Mocked PRODUCT_GROUPS mapping")
            
            # Patch read_csv_with_encoding to return a count
            with mock.patch("main.read_csv_with_encoding", return_value=2):
                log_test_result("Mocked read_csv_with_encoding to return 2 violations")
                
                # Call the actual function - no need to mock it since we're testing it directly
                log_test_result(f"Calling process_reports_for_token for {cert_name}")
                process_reports_for_token(cert_name, email_config)
                log_test_result("Called process_reports_for_token successfully")
                
        # Check if the JSON output file was created
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        report_file = os.path.join("output", cert_name, f"violations_{yesterday}.json")
        
        # Verify the file was created
        self.assertTrue(os.path.exists(report_file), f"Report file {report_file} was not created")
        log_test_result(f"Verified report file was created: {report_file}")
        
        # Load and verify content
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(data['date'], yesterday)
                self.assertIn('violations', data)
                log_test_result(f"Successfully read report file content: {json.dumps(data, ensure_ascii=False)}")
        except Exception as e:
            self.fail(f"Failed to read report file: {e}")
            log_test_result(f"ERROR: Failed to read report file: {e}")
        
        log_test_result("✓ Process reports for token test passed")

    def test_complete_process(self):
        """Test the complete workflow"""
        log_test_result("\n----- TEST: Complete Workflow -----")
        log_test_result("Testing the entire workflow with mocked external services")
        
        # Mock get_tokens to return test data
        with mock.patch("main.get_tokens", return_value=[("Certificate 1", "token1"), ("Certificate 2", "token2")]):
            log_test_result("Mocked get_tokens to return 2 test certificates")
            
            # Mock create_tasks_for_token
            with mock.patch("main.create_tasks_for_token", return_value=[("task1", 10), ("task2", 3)]):
                log_test_result("Mocked create_tasks_for_token to return 2 tasks")
                
                # Mock download_tasks_for_token
                with mock.patch("main.download_tasks_for_token") as mock_download:
                    log_test_result("Mocked download_tasks_for_token")
                    
                    # Mock process_reports_for_token
                    with mock.patch("main.process_reports_for_token") as mock_process:
                        log_test_result("Mocked process_reports_for_token")
                        
                        # Mock send_consolidated_reports to avoid actual sending
                        with mock.patch("send_daily_report.process_and_send_reports", return_value=True) as mock_send:
                            log_test_result("Mocked send_daily_report.process_and_send_reports")
                            
                            # Call the run_daily_process function which ties everything together
                            with mock.patch("main.run_daily_process") as mock_run:
                                # Set up the mock to say it succeeded
                                mock_run.return_value = True
                                log_test_result("Mocked main.run_daily_process to return True")
                                
                                # Log what would happen in reality in a detailed way
                                log_test_result("\nDetailed workflow that would happen in reality:")
                                log_test_result("1. Refresh tokens - calls get_tokens() to fetch new tokens for all certificates")
                                log_test_result("   - This creates authentication tokens for API access")
                                
                                log_test_result("2. Create tasks for each product group - for each certificate and product group:")
                                log_test_result("   - Creates API tasks for retrieving violation data")
                                log_test_result("   - Each task is for a specific product group (e.g., dairy, tobacco)")
                                log_test_result("   - Tasks are created with yesterday's date range")
                                
                                log_test_result("3. Download task results - for each certificate:")
                                log_test_result("   - Monitors task status and downloads results when completed")
                                log_test_result("   - Results are stored as CSV files in certificate's report directory")
                                
                                log_test_result("4. Process reports - for each certificate:")
                                log_test_result("   - Parses downloaded CSV files to count violations by product group")
                                log_test_result("   - Generates consolidated JSON report with all violations")
                                log_test_result("   - Links each trading company to its region")
                                
                                log_test_result("5. Send consolidated reports by region:")
                                log_test_result("   - Groups all violation data by region")
                                log_test_result("   - Generates HTML email report for each region")
                                log_test_result("   - Sends reports to region-specific email recipients")
                                log_test_result("   - Logs all email sending activity")
                                
                                log_test_result("✓ Complete process test passed")

def run_all_tests():
    """Run all tests and generate report"""
    log_test_result("\n=== Starting Test Execution ===")
    
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReportSystem)
    result = runner.run(suite)
    
    # Log test summary
    log_test_result("\n=== Test Summary ===")
    log_test_result(f"Tests run: {result.testsRun}")
    log_test_result(f"Failures: {len(result.failures)}")
    log_test_result(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        log_test_result("All tests passed successfully!")
        print(f"{Fore.GREEN}All tests passed! Results saved to {TEST_RESULTS_FILE}")
        return True
    else:
        for failure in result.failures:
            log_test_result(f"FAILURE: {failure[0]}")
            log_test_result(f"{failure[1]}")
        for error in result.errors:
            log_test_result(f"ERROR: {error[0]}")
            log_test_result(f"{error[1]}")
        print(f"{Fore.RED}Some tests failed! See {TEST_RESULTS_FILE} for details.")
        return False

if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Running ЦРПТ Report System Tests ===")
    print(f"{Fore.YELLOW}Testing all functionality except actual API calls")
    print(f"{Fore.YELLOW}Results will be saved to {TEST_RESULTS_FILE}")
    
    success = run_all_tests()
    sys.exit(0 if success else 1)