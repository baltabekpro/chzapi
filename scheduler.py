import os
import sys
import time
import json
import subprocess
import signal
import atexit
from datetime import datetime, timedelta
import threading
from typing import Optional, List, Dict, Any  # Add Optional import
from logger_config import get_logger, log_exception

# Set up logger
scheduler_logger = get_logger("scheduler")

class Scheduler:
    """
    A simple scheduler to run tasks at specific times.
    Provides functionality to run tasks in background.
    """
    def __init__(self, config_file="scheduler_config.json"):
        self.config_file = config_file
        self.load_config()
        self.running = False
        self.thread = None
        scheduler_logger.info("Scheduler initialized")
    
    def load_config(self):
        """Load scheduler configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    scheduler_logger.info(f"Loaded configuration from {self.config_file}")
            else:
                # Default configuration
                self.config = {
                    "daily_report_time": "04:00",  # Run at 4 AM by default
                    "check_interval": 60,          # Check every minute
                    "token_refresh_time": "03:00", # Refresh tokens at 3 AM
                    "enabled": True,
                    "email_time": "20:04"         # Send email reports at 8:04 PM
                }
                # Save default config
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                scheduler_logger.info(f"Created default configuration in {self.config_file}")
                
            # Load email config time if available
            try:
                with open("email_config.json", 'r', encoding='utf-8') as f:
                    email_config = json.load(f)
                    if "send_time" in email_config:
                        self.config["email_time"] = email_config["send_time"]
                        scheduler_logger.info(f"Using email time from email_config.json: {self.config['email_time']}")
            except Exception as e:
                scheduler_logger.warning(f"Couldn't read email time from email_config.json: {e}")
                
        except Exception as e:
            log_exception(scheduler_logger, e, "Error loading scheduler configuration")
            # Set defaults in case of error
            self.config = {
                "daily_report_time": "04:00",
                "check_interval": 60,
                "token_refresh_time": "03:00",
                "enabled": True,
                "email_time": "20:04"  # Default email time
            }
    
    def save_config(self):
        """Save scheduler configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            scheduler_logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            log_exception(scheduler_logger, e, "Error saving scheduler configuration")
    
    def is_time_to_run(self, task_time):
        """Check if it's time to run a scheduled task"""
        now = datetime.now()
        
        # Parse task time (HH:MM)
        try:
            hour, minute = map(int, task_time.split(':'))
            task_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the task time has already passed today, it's not time yet
            if now.hour > hour or (now.hour == hour and now.minute > minute + 2):
                return False
                
            # Check if current time is within 2 minute window
            time_diff = (now - task_datetime).total_seconds()
            return 0 <= time_diff <= 120
            
        except Exception as e:
            log_exception(scheduler_logger, e, f"Error parsing task time: {task_time}")
            return False
    
    def run_daily_report(self):
        """Run the daily report processing"""
        scheduler_logger.info("Running daily report task")
        try:
            # Import and run the daily process function from main.py
            from main import run_daily_process
            result = run_daily_process()
            
            # Log the result
            if result:
                scheduler_logger.info("Daily report task completed successfully")
                # Send success notification via Telegram
                try:
                    from telegram_bot import send_telegram_notification
                    send_telegram_notification("✅ Ежедневная обработка успешно завершена")
                except ImportError:
                    pass
            else:
                scheduler_logger.error("Daily report task failed")
                # Send error notification via Telegram
                try:
                    from telegram_bot import send_telegram_notification
                    send_telegram_notification("❌ Ежедневная обработка завершилась с ошибкой")
                except ImportError:
                    pass
                
            # Update last run time
            self.update_last_run_time()
            
        except Exception as e:
            log_exception(scheduler_logger, e, "Error running daily report task")
            # Send error notification via Telegram
            try:
                from telegram_bot import send_telegram_notification
                send_telegram_notification(f"❌ Ошибка при выполнении ежедневной обработки: {str(e)}")
            except ImportError:
                pass
    
    def send_email_reports(self):
        """Send daily email reports"""
        scheduler_logger.info("Running email reports task")
        try:
            # Import and run the email sending function
            from send_daily_report import process_and_send_reports
            result = process_and_send_reports()
            
            # Log the result
            if result:
                scheduler_logger.info("Email reports sent successfully")
                # Send success notification via Telegram
                try:
                    from telegram_bot import send_telegram_notification
                    send_telegram_notification("✅ Отчеты по электронной почте успешно отправлены")
                except ImportError:
                    pass
            else:
                scheduler_logger.error("Failed to send email reports")
                # Send error notification via Telegram
                try:
                    from telegram_bot import send_telegram_notification
                    send_telegram_notification("❌ Не удалось отправить отчеты по электронной почте")
                except ImportError:
                    pass
                
            # Update last email run time
            self.update_last_email_run_time()
            
        except ImportError:
            scheduler_logger.error("Could not import process_and_send_reports function")
        except Exception as e:
            log_exception(scheduler_logger, e, "Error sending email reports")
            # Send error notification via Telegram
            try:
                from telegram_bot import send_telegram_notification
                send_telegram_notification(f"❌ Ошибка при отправке отчетов по электронной почте: {str(e)}")
            except ImportError:
                pass
    
    def refresh_tokens(self):
        """Refresh API tokens"""
        scheduler_logger.info("Running token refresh task")
        try:
            # Import and run the token refresh function
            from get_tokens import get_tokens
            tokens = get_tokens()
            
            # Log the result
            if tokens:
                scheduler_logger.info(f"Successfully refreshed {len(tokens)} tokens")
            else:
                scheduler_logger.error("Failed to refresh tokens")
                
        except Exception as e:
            log_exception(scheduler_logger, e, "Error refreshing tokens")
    
    def update_last_run_time(self):
        """Update the last run time in the status file"""
        try:
            last_run = {
                "last_run": datetime.now().isoformat(),
                "data_date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                "scheduler_run": True,
                "next_scheduled_run": (datetime.now() + timedelta(days=1)).replace(
                    hour=int(self.config["daily_report_time"].split(':')[0]),
                    minute=int(self.config["daily_report_time"].split(':')[1]),
                    second=0,
                    microsecond=0
                ).isoformat()
            }
            
            with open('last_run.json', 'w', encoding='utf-8') as f:
                json.dump(last_run, f, indent=2)
                
            scheduler_logger.info("Updated last run time")
            
        except Exception as e:
            log_exception(scheduler_logger, e, "Error updating last run time")
    
    def update_last_email_run_time(self):
        """Update the last email run time"""
        try:
            last_run = {
                "last_run": datetime.now().isoformat(),
                "manual_run": False
            }
            
            with open('last_email_run.json', 'w', encoding='utf-8') as f:
                json.dump(last_run, f, indent=2)
                
            scheduler_logger.info("Updated last email run time")
            
        except Exception as e:
            log_exception(scheduler_logger, e, "Error updating last email run time")
    
    def check_and_run_tasks(self):
        """Check scheduled tasks and run them if it's time"""
        # Check for daily report
        if self.is_time_to_run(self.config["daily_report_time"]):
            scheduler_logger.info(f"It's time to run daily report ({self.config['daily_report_time']})")
            self.run_daily_report()
        
        # Check for token refresh
        if self.is_time_to_run(self.config["token_refresh_time"]):
            scheduler_logger.info(f"It's time to refresh tokens ({self.config['token_refresh_time']})")
            self.refresh_tokens()
        
        # Check for email reports
        if self.is_time_to_run(self.config["email_time"]):
            scheduler_logger.info(f"It's time to send email reports ({self.config['email_time']})")
            self.send_email_reports()
    
    def run_continuously(self):
        """Run the scheduler continuously"""
        self.running = True
        scheduler_logger.info("Scheduler starting continuous operation")
        
        try:
            while self.running:
                # Check if tasks need to be run
                self.check_and_run_tasks()
                
                # Sleep for the configured interval
                time.sleep(self.config.get("check_interval", 60))
                
        except KeyboardInterrupt:
            scheduler_logger.info("Scheduler stopped by user")
            self.running = False
        except Exception as e:
            log_exception(scheduler_logger, e, "Error in scheduler continuous operation")
            self.running = False
    
    def start_in_thread(self):
        """Start scheduler in a background thread"""
        if self.thread and self.thread.is_alive():
            scheduler_logger.warning("Scheduler is already running in a thread")
            return False
            
        self.thread = threading.Thread(target=self.run_continuously)
        self.thread.daemon = True
        self.thread.start()
        scheduler_logger.info("Scheduler started in background thread")
        return True
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        scheduler_logger.info("Scheduler stopped")


def get_pid_file_path():
    """Get path to PID file"""
    return os.path.join(os.getcwd(), "scheduler.pid")

def check_if_running() -> Optional[int]:
    """
    Check if the scheduler process is running
    
    Returns:
        int or None: PID of the scheduler process if running, None otherwise
    """
    try:
        # On Windows
        if os.name == 'nt':
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if this is a Python process
                    if 'python' in proc.info['name'].lower():
                        # Check the command line arguments
                        if proc.info['cmdline'] and len(proc.info['cmdline']) > 1:
                            cmdline = ' '.join(proc.info['cmdline'])
                            # Look for our scheduler arguments
                            if '--scheduler' in cmdline and os.path.basename(__file__) in cmdline:
                                return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        # On Unix-like systems
        else:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", f"python.*{os.path.basename(__file__)}.*--scheduler"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
                
        # Alternative check for Windows if psutil approach fails
        if os.name == 'nt':
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"WINDOWTITLE eq *{os.path.basename(__file__)}*", "/FO", "CSV"],
                capture_output=True, text=True
            )
            if "python" in result.stdout.lower():
                for line in result.stdout.splitlines():
                    if "python" in line.lower() and "--scheduler" in line.lower():
                        parts = line.split(',')
                        if len(parts) > 1:
                            pid_part = parts[1].strip('"')
                            if pid_part.isdigit():
                                return int(pid_part)
        
        return None
    except Exception as e:
        scheduler_logger.error(f"Error checking if scheduler is running: {e}")
        return None

def write_pid_file():
    """Write current PID to file"""
    pid_file = get_pid_file_path()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid_file():
    """Remove PID file on exit"""
    pid_file = get_pid_file_path()
    if os.path.exists(pid_file):
        os.remove(pid_file)

def ensure_scheduler_running() -> Optional[int]:
    """
    Ensure the scheduler is running, starting it if necessary
    
    Returns:
        int or None: PID of the scheduler process if running, None otherwise
    """
    # First check if it's already running
    pid = check_if_running()
    if pid:
        scheduler_logger.info(f"Scheduler already running with PID {pid}")
        return pid
        
    # Start the scheduler as a background process
    try:
        # Get the path to the current Python executable
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Create a detached process
        if os.name == 'nt':  # Windows
            import subprocess
            # Use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS flags to detach
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                [python_exe, script_path, "--scheduler"],
                close_fds=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                startupinfo=startupinfo
            )
            # Give Windows a moment to register the process
            time.sleep(2)
            
        else:  # Unix/Linux
            import subprocess
            process = subprocess.Popen(
                [python_exe, script_path, "--scheduler"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True
            )
            
        # Check if it started successfully
        pid = process.pid if process else None
        if pid:
            scheduler_logger.info(f"Started scheduler process with PID {pid}")
            # Double-check the process is really running
            time.sleep(1)
            if check_if_running():
                return pid
                
        # If we didn't successfully start it, or validate it running
        scheduler_logger.error("Failed to start scheduler process")
        return None
        
    except Exception as e:
        scheduler_logger.error(f"Error ensuring scheduler is running: {e}")
        return None

def start_daemon():
    """Start the scheduler as a daemon process"""
    pid = check_if_running()
    
    if pid:
        print(f"Scheduler is already running with PID {pid}")
        return pid
    
    # Register clean up function
    atexit.register(remove_pid_file)
    
    # Write PID file
    write_pid_file()
    
    # Start scheduler
    scheduler = Scheduler()
    scheduler.run_continuously()
    
    return os.getpid()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        start_daemon()
    else:
        scheduler = Scheduler()
        scheduler.run_continuously()
