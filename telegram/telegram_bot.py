import asyncio
import atexit
import json
import logging
import os
import socket
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

# Import required telegram libraries with auto-installation if needed
try:
    import telegram.error  # Add this import for error handling
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except ImportError:
    print("Telegram libraries not found. Installing...")
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "python-telegram-bot==20.7"]
    )
    import telegram.error  # Add this import for error handling
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

# Import necessary modules from our application
from logger_config import get_logger, log_exception

# Set up logger
telegram_logger = get_logger("telegram")

# TCP socket for single instance lock (Windows compatible)
LOCK_PORT = 12345
lock_socket = None


def acquire_lock():
    """Acquire a TCP socket lock to ensure only one instance is running"""
    global lock_socket
    try:
        # Try to bind to the lock port
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(("localhost", LOCK_PORT))
        lock_socket.listen(1)
        telegram_logger.info(f"Acquired lock on port {LOCK_PORT}")
        return True
    except socket.error:
        # Port already in use, another instance is running
        lock_socket = None
        telegram_logger.warning(
            f"Another bot instance is already running (port {LOCK_PORT} in use)"
        )
        return False


def release_lock():
    """Release the TCP socket lock when the program exits"""
    global lock_socket
    if lock_socket:
        try:
            lock_socket.close()
            telegram_logger.info("Released lock socket")
        except Exception as e:
            telegram_logger.error(f"Error releasing lock socket: {e}")


# Register lock release to run at exit
atexit.register(release_lock)


class ErrorQueue:
    """Thread-safe error queue with event loop awareness"""

    def __init__(self):
        self._queues = {}  # Store queues per thread/loop
        self._lock = threading.Lock()

    def get_queue(self):
        """Get or create a queue for the current thread"""
        tid = threading.get_ident()
        with self._lock:
            if tid not in self._queues:
                self._queues[tid] = asyncio.Queue(
                    maxsize=100
                )  # Limit size to prevent memory issues
            return self._queues[tid]

    def put(self, item):
        """Add item to the queue"""
        try:
            q = self.get_queue()
            q.put_nowait(item)  # Non-blocking put
            return True
        except asyncio.QueueFull:
            # If queue is full, remove oldest item
            try:
                q.get_nowait()
                q.put_nowait(item)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                return False
        except Exception as e:
            telegram_logger.error(f"Error putting item in queue: {e}")
            return False
        return True

    def get(self):
        """Get item from queue"""
        try:
            q = self.get_queue()
            return q.get_nowait()
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            telegram_logger.error(f"Error getting item from queue: {e}")
            return None

    def empty(self):
        """Check if queue is empty"""
        try:
            q = self.get_queue()
            return q.empty()
        except Exception:
            return True


class TelegramBot:
    """
    Telegram bot for controlling and monitoring the application
    """

    def __init__(self):
        self.config = self.load_config()
        self.token = self.config.get("token")
        self.allowed_users = self.config.get("allowed_users", [])
        self.admin_users = self.config.get("admin_users", [])
        self.error_notification_chat_ids = self.config.get(
            "error_notification_chat_ids", []
        )
        self.proxy = self.config.get("proxy", None)  # Add proxy support
        self.max_retries = self.config.get("max_retries", 3)  # Number of retry attempts
        self.retry_delay = self.config.get("retry_delay", 5)  # Seconds between retries
        self.connection_timeout = self.config.get(
            "connection_timeout", 60
        )  # Increased from 30 to 60 seconds
        self.cleanup_on_start = self.config.get(
            "cleanup_on_start", True
        )  # Whether to clean up existing sessions
        self.application = None
        self.running = False
        self.initialized = False
        self.thread = None
        self.command_registry = {}  # Registry of commands and their descriptions

        # Error notification queue
        self.error_queue = ErrorQueue()

        # Register commands with descriptions for help menu
        self.register_command("start", "Начать работу с ботом")
        self.register_command("help", "Показать список команд")
        self.register_command("status", "Проверить статус системы")
        self.register_command("reports", "Показать доступные отчеты")
        self.register_command("errors", "Показать последние ошибки")
        self.register_command("restart", "Перезапустить планировщик заданий")
        self.register_command("run", "Запустить ежедневную обработку")
        self.register_command("tokens", "Проверить токены API")

    def register_command(self, command: str, description: str):
        """Register a command with its description for the help menu"""
        self.command_registry[command] = description

    def load_config(self) -> Dict[str, Any]:
        """Load the Telegram bot configuration"""
        try:
            if os.path.exists("telegram_config.json"):
                with open("telegram_config.json", "r", encoding="utf-8-sig") as f:
                    config = json.load(f)
                    telegram_logger.info("Telegram configuration loaded successfully")
                    return config
            else:
                # Create default config file
                default_config = {
                    "token": "YOUR_TELEGRAM_BOT_TOKEN",
                    "allowed_users": [],
                    "admin_users": [],
                    "error_notification_chat_ids": [],
                    "status_interval_hours": 12,
                }
                with open("telegram_config.json", "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                telegram_logger.warning(
                    "Created default telegram_config.json. Please update with your bot token."
                )
                return default_config
        except Exception as e:
            log_exception(telegram_logger, e, "Error loading Telegram configuration")
            return {
                "token": None,
                "allowed_users": [],
                "admin_users": [],
                "error_notification_chat_ids": [],
            }

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send a message when the command /start is issued."""
        user_id = update.effective_user.id
        username = update.effective_user.username

        # Log the user interaction
        telegram_logger.info(f"Start command from user {username} (ID: {user_id})")

        if user_id not in self.allowed_users and str(user_id) not in self.allowed_users:
            await update.message.reply_text(
                f"Привет, {username}! У вас нет доступа к этому боту. "
                f"ID пользователя: {user_id}. "
                f"Обратитесь к администратору, чтобы получить доступ."
            )
            telegram_logger.warning(
                f"Unauthorized access attempt from {username} (ID: {user_id})"
            )
            return

        # User is authorized
        admin_status = (
            "Администратор"
            if user_id in self.admin_users or str(user_id) in self.admin_users
            else "Пользователь"
        )

        await update.message.reply_text(
            f"Привет, {username}! Добро пожаловать в систему управления ЦРПТ.\n\n"
            f"Статус: {admin_status}\n\n"
            f"Используйте /help чтобы увидеть список доступных команд."
        )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send a message when the command /help is issued."""
        user_id = update.effective_user.id

        if not await self.check_authorization(update, context):
            return

        # Build help message from command registry
        help_text = "Доступные команды:\n\n"

        for command, description in self.command_registry.items():
            # Skip admin commands for non-admin users
            if command in ["restart", "run"] and (
                user_id not in self.admin_users and str(user_id) not in self.admin_users
            ):
                continue

            help_text += f"/{command} - {description}\n"

        await update.message.reply_text(help_text)

    async def status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Check and report system status."""
        if not await self.check_authorization(update, context):
            return

        await update.message.reply_text("⏳ Проверка статуса системы...")

        try:
            # Check scheduler status with more robust error handling
            from scheduler import check_if_running

            try:
                scheduler_pid = check_if_running()
                # Add a delay to allow the scheduler status to update
                if not scheduler_pid:
                    # Try checking up to 3 times with a short delay
                    for _ in range(3):
                        await asyncio.sleep(1)
                        scheduler_pid = check_if_running()
                        if scheduler_pid:
                            break

                scheduler_status = "🟢 Работает" if scheduler_pid else "🔴 Не запущен"
                telegram_logger.info(
                    f"Scheduler status check: PID={scheduler_pid}, Status={scheduler_status}"
                )
            except Exception as e:
                log_exception(telegram_logger, e, "Error checking scheduler status")
                scheduler_pid = None
                scheduler_status = "⚠️ Ошибка проверки"

            # Check last run information
            from file_utils import check_last_run_info

            last_run_info = check_last_run_info()

            if last_run_info:
                last_run = last_run_info.get("last_run").strftime("%Y-%m-%d %H:%M:%S")
                next_run = last_run_info.get("next_run").strftime("%Y-%m-%d %H:%M:%S")
                certificates_processed = last_run_info.get("certificates_processed", 0)
                run_type = (
                    "Ручной"
                    if last_run_info.get("manual_run", False)
                    else "Автоматический"
                )
                time_until_next = last_run_info.get("time_until", timedelta(0))

                # Format time until next run
                days = time_until_next.days
                hours, remainder = divmod(time_until_next.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                time_until_str = f"{days} дней, {hours} часов, {minutes} минут"

                status_message = (
                    f"📊 *Статус системы:*\n\n"
                    f"Планировщик: {scheduler_status}\n"
                    f"PID: {scheduler_pid}\n\n"
                    f"Последний запуск: {last_run}\n"
                    f"Тип запуска: {run_type}\n"
                    f"Обработано сертификатов: {certificates_processed}\n\n"
                    f"Следующий запуск: {next_run}\n"
                    f"Времени до запуска: {time_until_str}\n"
                )
            else:
                status_message = (
                    f"📊 *Статус системы:*\n\n"
                    f"Планировщик: {scheduler_status}\n"
                    f"PID: {scheduler_pid}\n\n"
                    f"❌ Информация о последнем запуске не найдена"
                )

            # Check token status
            from token_utils import load_tokens

            tokens = load_tokens()
            token_count = len(tokens)
            token_status = (
                f"🟢 Имеется {token_count} токенов"
                if token_count > 0
                else "🔴 Токены не найдены"
            )

            status_message += f"\n*Токены API:*\n{token_status}\n"

            # Check available reports
            from file_utils import get_reports_list

            reports = get_reports_list()
            report_count = (
                sum(len(certs) for certs in reports.values()) if reports else 0
            )
            cert_count = len(reports) if reports else 0

            status_message += (
                f"\n*Отчеты:*\n{cert_count} сертификатов, {report_count} отчетов"
            )

            # Send message with markdown formatting
            await update.message.reply_text(status_message, parse_mode="Markdown")

        except Exception as e:
            log_exception(telegram_logger, e, "Error in status command")
            await update.message.reply_text(f"❌ Ошибка при получении статуса: {str(e)}")

    async def restart_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Restart the scheduler service."""
        user_id = update.effective_user.id

        # Check if user is admin
        if user_id not in self.admin_users and str(user_id) not in self.admin_users:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для выполнения этой команды"
            )
            telegram_logger.warning(
                f"Unauthorized restart attempt from user ID: {user_id}"
            )
            return

        await update.message.reply_text("🔄 Перезапуск планировщика...")

        try:
            # Import necessary modules
            from scheduler import check_if_running, ensure_scheduler_running

            # Kill existing scheduler if running
            pid = check_if_running()
            if pid:
                try:
                    # For Windows
                    if os.name == "nt":
                        import subprocess

                        subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    else:
                        # For Linux/Unix
                        import signal

                        os.kill(pid, signal.SIGKILL)
                    telegram_logger.info(f"Killed scheduler process with PID {pid}")
                    # Add a small delay to ensure process is fully terminated
                    await asyncio.sleep(2)
                except Exception as e:
                    log_exception(telegram_logger, e, "Error killing scheduler process")

            # Start a new scheduler
            new_pid = ensure_scheduler_running()

            # Additional verification of scheduler start
            if not new_pid:
                # Try checking a few times with delay
                for _ in range(3):
                    await asyncio.sleep(2)
                    new_pid = check_if_running()
                    if new_pid:
                        break

            if new_pid:
                await update.message.reply_text(
                    f"✅ Планировщик успешно перезапущен. Новый PID: {new_pid}"
                )
                telegram_logger.info(
                    f"Scheduler restarted with PID {new_pid} by user ID: {user_id}"
                )
            else:
                await update.message.reply_text("❌ Ошибка при перезапуске планировщика")
                telegram_logger.error(
                    f"Failed to restart scheduler, requested by user ID: {user_id}"
                )

        except Exception as e:
            log_exception(telegram_logger, e, "Error in restart command")
            await update.message.reply_text(
                f"❌ Ошибка при перезапуске планировщика: {str(e)}"
            )

    async def reports_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show available reports."""
        if not await self.check_authorization(update, context):
            return

        try:
            from file_utils import get_reports_list

            reports = get_reports_list()

            if not reports:
                await update.message.reply_text("❌ Отчеты не найдены")
                return

            # Create list of certificates with inline buttons
            keyboard = []
            for cert_name in reports.keys():
                cert_reports = reports[cert_name]
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{cert_name} ({len(cert_reports)} отчетов)",
                            callback_data=f"cert_{cert_name}",
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📊 Выберите сертификат для просмотра отчетов:",
                reply_markup=reply_markup,
            )

        except Exception as e:
            log_exception(telegram_logger, e, "Error in reports command")
            await update.message.reply_text(f"❌ Ошибка при получении отчетов: {str(e)}")

    async def button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle button callbacks from inline keyboards."""
        query = update.callback_query
        await query.answer()  # Acknowledge the button press

        callback_data = query.data
        user_id = update.effective_user.id

        # Check authorization
        if user_id not in self.allowed_users and str(user_id) not in self.allowed_users:
            await query.edit_message_text("❌ У вас нет доступа к этой функции")
            return

        try:
            # Handle token refresh
            if callback_data == "refresh_tokens":
                # Check if user is admin
                if (
                    user_id not in self.admin_users
                    and str(user_id) not in self.admin_users
                ):
                    await query.edit_message_text(
                        "❌ У вас нет прав администратора для обновления токенов"
                    )
                    return

                await query.edit_message_text("🔄 Обновление токенов API...")

                try:
                    # Import and run the token refresh function
                    from get_tokens import get_tokens

                    tokens = get_tokens()

                    if tokens:
                        await query.edit_message_text(
                            f"✅ Токены API успешно обновлены. Получено {len(tokens)} токенов."
                        )
                        telegram_logger.info(f"Tokens refreshed by user ID: {user_id}")
                    else:
                        await query.edit_message_text(
                            "❌ Не удалось обновить токены API"
                        )
                        telegram_logger.error(
                            f"Token refresh failed, requested by user ID: {user_id}"
                        )
                except Exception as e:
                    log_exception(telegram_logger, e, "Error refreshing tokens")
                    await query.edit_message_text(
                        f"❌ Ошибка при обновлении токенов: {str(e)}"
                    )

                return

            # Handle certificate selection
            elif callback_data.startswith("cert_"):
                cert_name = callback_data[5:]  # Remove "cert_" prefix
                from file_utils import get_reports_list

                reports = get_reports_list()

                if cert_name in reports:
                    cert_reports = reports[cert_name]

                    # Create list of reports for this certificate with shortened callback data
                    keyboard = []
                    # Create a mapping from short IDs to report paths
                    if not hasattr(self, "_report_path_map"):
                        self._report_path_map = {}

                    for i, report in enumerate(cert_reports):
                        report_date = report["date"]
                        # Create a short ID for the report
                        short_id = f"{cert_name[:10]}_{i}"  # Limit to 10 chars + index
                        self._report_path_map[short_id] = report["path"]

                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    f"Отчет от {report_date}",
                                    callback_data=f"rep_{short_id}",
                                )
                            ]
                        )

                    # Add back button
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                "« Назад к сертификатам", callback_data="back_to_certs"
                            )
                        ]
                    )

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        f"📄 Отчеты для сертификата {cert_name}:",
                        reply_markup=reply_markup,
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Отчеты для сертификата {cert_name} не найдены"
                    )

            # Handle shortened report selection
            elif callback_data.startswith("rep_"):
                short_id = callback_data[4:]  # Remove "rep_" prefix
                if (
                    hasattr(self, "_report_path_map")
                    and short_id in self._report_path_map
                ):
                    report_path = self._report_path_map[short_id]

                    try:
                        with open(report_path, "r", encoding="utf-8") as f:
                            report_data = json.load(f)

                        date = report_data.get("date", "Неизвестная дата")
                        violations = report_data.get("violations", {})

                        # Build report message
                        message = f"📊 *Отчет о нарушениях за {date}*\n\n"
                        message += "*Нарушения по товарным группам:*\n"

                        total = 0
                        for group, count in violations.items():
                            total += count
                            message += f"• {group}: {count}\n"

                        message += f"\n*Всего нарушений:* {total}"

                        # Send message with markdown formatting
                        await query.edit_message_text(message, parse_mode="Markdown")

                    except Exception as e:
                        log_exception(
                            telegram_logger, e, f"Error reading report {report_path}"
                        )
                        await query.edit_message_text(
                            f"❌ Ошибка при чтении отчета: {str(e)}"
                        )
                else:
                    await query.edit_message_text("❌ Отчет не найден")

            # Handle back button
            elif callback_data == "back_to_certs":
                from file_utils import get_reports_list

                reports = get_reports_list()

                keyboard = []
                for cert_name in reports.keys():
                    cert_reports = reports[cert_name]
                    # Ensure cert_name is not too long for callback_data
                    safe_cert_name = (
                        cert_name[:50] if len(cert_name) > 50 else cert_name
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                f"{cert_name} ({len(cert_reports)} отчетов)",
                                callback_data=f"cert_{safe_cert_name}",
                            )
                        ]
                    )

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📊 Выберите сертификат для просмотра отчетов:",
                    reply_markup=reply_markup,
                )

        except Exception as e:
            log_exception(telegram_logger, e, "Error handling button callback")
            await query.edit_message_text(f"❌ Ошибка при обработке запроса: {str(e)}")

    async def errors_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show recent error logs."""
        if not await self.check_authorization(update, context):
            return

        # Check for error logs
        logs_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(logs_dir):
            await update.message.reply_text("❌ Директория логов не найдена")
            return

        error_logs = []
        for filename in os.listdir(logs_dir):
            if filename.endswith(".log"):
                filepath = os.path.join(logs_dir, filename)
                try:
                    # Read last 20 lines from each log file
                    with open(filepath, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        error_lines = [line for line in lines if "ERROR" in line]
                        if error_lines:
                            # Take the 5 most recent error lines
                            recent_errors = error_lines[-5:]
                            error_logs.append(
                                {"file": filename, "errors": recent_errors}
                            )
                except Exception as e:
                    log_exception(
                        telegram_logger, e, f"Error reading log file {filepath}"
                    )

        if not error_logs:
            await update.message.reply_text("✅ Ошибок не найдено")
            return

        # Build error message
        message = "🔴 *Последние ошибки:*\n\n"

        for log in error_logs:
            message += f"*{log['file']}*:\n"
            for line in log["errors"]:
                # Trim and clean up error lines
                clean_line = line.strip()
                if len(clean_line) > 100:
                    clean_line = clean_line[:97] + "..."
                message += f"- {clean_line}\n"
            message += "\n"

        # Send message with markdown formatting
        if len(message) > 4000:  # Telegram message length limit
            message = message[:3997] + "..."

        await update.message.reply_text(message, parse_mode="Markdown")

    async def run_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Run the daily process manually."""
        user_id = update.effective_user.id

        # Check if user is admin
        if user_id not in self.admin_users and str(user_id) not in self.admin_users:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для выполнения этой команды"
            )
            telegram_logger.warning(f"Unauthorized run attempt from user ID: {user_id}")
            return

        await update.message.reply_text("🔄 Запуск ежедневной обработки...")

        # Run the process in a separate thread to avoid blocking
        def run_process():
            try:
                # Import main module function
                from main import run_daily_process

                # Run the process
                result = run_daily_process()

                # Send result as a message
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if result:
                    loop.run_until_complete(
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="✅ Ежедневная обработка успешно завершена",
                        )
                    )
                    telegram_logger.info(
                        f"Daily process completed successfully, requested by user ID: {user_id}"
                    )
                else:
                    loop.run_until_complete(
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="❌ Ошибка при выполнении ежедневной обработки",
                        )
                    )
                    telegram_logger.error(
                        f"Daily process failed, requested by user ID: {user_id}"
                    )

                loop.close()

            except Exception as e:
                log_exception(telegram_logger, e, "Error running daily process")

                # Send error message
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    error_message = (
                        f"❌ Ошибка при выполнении ежедневной обработки: {str(e)}"
                    )
                    loop.run_until_complete(
                        context.bot.send_message(
                            chat_id=update.effective_chat.id, text=error_message
                        )
                    )

                    loop.close()
                except:
                    telegram_logger.error("Failed to send error message to Telegram")

        # Start the process in a separate thread
        process_thread = threading.Thread(target=run_process)
        process_thread.daemon = True
        process_thread.start()

        telegram_logger.info(f"Daily process started by user ID: {user_id}")

    async def tokens_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Check API tokens status."""
        if not await self.check_authorization(update, context):
            return

        await update.message.reply_text("⏳ Проверка статуса токенов API...")

        try:
            # Import token utilities
            from token_utils import load_tokens

            # Load tokens
            tokens = load_tokens()
            if not tokens:
                await update.message.reply_text("❌ Токены API не найдены")
                return

            # Build tokens message
            message = f"🔑 *Статус токенов API:*\n\n"
            message += f"Всего токенов: {len(tokens)}\n\n"

            # Group tokens by certificate - handle different possible structures
            cert_tokens = {}

            # Check the structure of the tokens and handle accordingly
            if isinstance(tokens, dict):
                # If tokens is already a dictionary
                for cert_name, token_value in tokens.items():
                    if cert_name not in cert_tokens:
                        cert_tokens[cert_name] = []
                    cert_tokens[cert_name].append(token_value)
            elif isinstance(tokens, list):
                # If tokens is a list, check the element structure
                for item in tokens:
                    if isinstance(item, tuple) and len(item) == 2:
                        # Standard tuple format (cert_name, token)
                        cert_name, token = item
                        if cert_name not in cert_tokens:
                            cert_tokens[cert_name] = []
                        cert_tokens[cert_name].append(token)
                    elif isinstance(item, dict):
                        # Handle case where items are dictionaries
                        for cert_name, token in item.items():
                            if cert_name not in cert_tokens:
                                cert_tokens[cert_name] = []
                            cert_tokens[cert_name].append(token)
                    else:
                        telegram_logger.warning(f"Unexpected token format: {item}")
            else:
                telegram_logger.warning(f"Unexpected tokens structure: {type(tokens)}")
                cert_tokens = {"Unknown": ["Structure not supported"]}

            # Add information about each certificate
            for cert_name, token_list in cert_tokens.items():
                message += f"*{cert_name}*: {len(token_list)} токен(ов)\n"

            # Find token file info
            token_file = "true_api_tokens.json"
            if os.path.exists(token_file):
                mod_time = datetime.fromtimestamp(os.path.getmtime(token_file))
                message += (
                    f"\nПоследнее обновление: {mod_time.strftime('%Y-%m-%d %H:%М:%S')}"
                )

            # Add option to refresh tokens
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Обновить токены", callback_data="refresh_tokens"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send message with markdown formatting
            await update.message.reply_text(
                message, parse_mode="Markdown", reply_markup=reply_markup
            )

        except Exception as e:
            log_exception(telegram_logger, e, "Error in tokens command")
            await update.message.reply_text(f"❌ Ошибка при проверке токенов: {str(e)}")

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle non-command messages."""
        user_id = update.effective_user.id

        # Check authorization
        if user_id not in self.allowed_users and str(user_id) not in self.allowed_users:
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return

        # Handle text messages
        message_text = update.message.text

        # Respond to simple queries
        if message_text.lower() in ["привет", "здравствуйте", "hi", "hello"]:
            await update.message.reply_text(
                f"Здравствуйте! Используйте /help для списка команд."
            )
        elif "статус" in message_text.lower():
            await self.status_command(update, context)
        elif "отчет" in message_text.lower():
            await self.reports_command(update, context)
        else:
            await update.message.reply_text(
                "Для взаимодействия с ботом используйте команды. Отправьте /help для списка команд."
            )

    async def check_authorization(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Check if user is authorized to use the bot."""
        user_id = update.effective_user.id

        if user_id not in self.allowed_users and str(user_id) not in self.allowed_users:
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            telegram_logger.warning(
                f"Unauthorized access attempt from user ID: {user_id}"
            )
            return False

        return True

    async def send_error_notification(self, error_message: str) -> None:
        """Send error notification to configured chat IDs."""
        if not self.application or not self.error_notification_chat_ids:
            return

        # Add timestamp to error message
        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )  # Fixed format string here
        full_message = f"⚠️ *ОШИБКА* ⚠️\n{timestamp}\n\n{error_message}"

        for chat_id in self.error_notification_chat_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id, text=full_message, parse_mode="Markdown"
                )
                telegram_logger.info(f"Sent error notification to chat ID: {chat_id}")
            except Exception as e:
                log_exception(
                    telegram_logger,
                    e,
                    f"Failed to send error notification to chat ID: {chat_id}",
                )

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors in the telegram bot."""
        # Log the error
        telegram_logger.error(f"Exception while handling an update: {context.error}")

        try:
            # Get traceback info
            tb_list = traceback.format_exception(
                None, context.error, context.error.__traceback__
            )
            tb_string = "".join(tb_list)

            # Log the traceback
            telegram_logger.error(f"Traceback: {tb_string}")

            # Notify user if possible
            if update and hasattr(update, "effective_chat"):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка при обработке запроса. Администратор уведомлен.",
                )

            # Notify admins about the error
            for admin_id in self.admin_users:
                try:
                    error_message = f"Ошибка бота:\n{str(context.error)}"
                    await context.bot.send_message(chat_id=admin_id, text=error_message)
                except:
                    pass

        except Exception as e:
            telegram_logger.error(f"Error in error handler: {e}")

    def start_error_monitor(self) -> None:
        """Start the error monitoring thread"""

        def monitor_errors():
            """Monitor error queue and send notifications"""
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while True:
                try:
                    # Only process errors if bot is initialized
                    if self.initialized and not self.error_queue.empty():
                        error = self.error_queue.get()
                        if error:
                            # Instead of directly calling coroutine, use run_coroutine_threadsafe
                            if self.application is not None and hasattr(
                                self.application, "bot"
                            ):
                                for chat_id in self.error_notification_chat_ids:
                                    self._send_message_sync(chat_id, error)
                            else:
                                telegram_logger.debug(
                                    "Cannot send error - bot not fully initialized"
                                )

                    # Sleep to avoid busy waiting
                    time.sleep(1)
                except Exception as e:
                    # Don't use error_queue here to avoid recursion
                    telegram_logger.error(f"Error in error monitoring task: {e}")
                    time.sleep(5)  # Longer delay after error

        # Start error monitor in daemon thread
        thread = threading.Thread(target=monitor_errors, daemon=True)
        thread.start()
        telegram_logger.info("Error monitoring thread started")

    def _send_message_sync(self, chat_id: int, message: str) -> None:
        """Send a message synchronously from a different thread"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"⚠️ *ALERT* ⚠️\n{now}\n\n```\n{message}\n```"

            # Don't use asyncio in this thread, use telegram's synchronous methods
            import requests

            api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown",
            }
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                telegram_logger.info(f"Sent notification to {chat_id}")
            else:
                telegram_logger.error(
                    f"Failed to send message: {response.status_code}, {response.text}"
                )
        except Exception as e:
            telegram_logger.error(f"Error sending message to {chat_id}: {e}")

    async def send_error_notification(self, error: str) -> None:
        """Send error notification to configured chat IDs - use this from async context"""
        if not self.application or not self.initialized:
            telegram_logger.debug(
                "Cannot send error notification - bot not initialized"
            )
            return

        for chat_id in self.error_notification_chat_ids:
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"⚠️ *ERROR ALERT* ⚠️\n{now}\n\n```\n{error}\n```"
                await self.application.bot.send_message(
                    chat_id=chat_id, text=message, parse_mode="Markdown"
                )
                telegram_logger.info(f"Sent error notification to {chat_id}")
            except Exception as e:
                telegram_logger.error(
                    f"Failed to send error notification to {chat_id}: {e}"
                )

    async def cleanup_telegram_session(self) -> None:
        """Clean up Telegram session to allow for a clean restart"""
        try:
            telegram_logger.info("Cleaning up Telegram session...")
            import requests

            reset_url = f"https://api.telegram.org/bot{self.token}/deleteWebhook?drop_pending_updates=true"
            response = requests.get(reset_url, timeout=10)
            telegram_logger.info(
                f"Cleanup response: {response.status_code}, {response.text}"
            )

            # Also try to close the application if it exists
            if self.application:
                try:
                    await self.application.stop()
                    await self.application.shutdown()
                    telegram_logger.info("Successfully stopped application")
                except Exception as e:
                    telegram_logger.error(f"Error stopping application: {e}")

            # Release lock
            release_lock()
            telegram_logger.info("Released lock")

            # Wait to allow system to reset
            await asyncio.sleep(3)

            return True
        except Exception as e:
            telegram_logger.error(f"Error during cleanup: {e}")
            return False

    async def start_bot(self) -> None:
        """Start the Telegram bot with retry mechanism and conflict handling."""
        # Validate token format and value
        if (
            not self.token
            or self.token == "YOUR_TELEGRAM_BOT_TOKEN"
            or self.token == "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ"
        ):
            telegram_logger.error("❌ ОШИБКА: Недействительный токен Telegram бота!")
            telegram_logger.error("📝 Для получения токена:")
            telegram_logger.error("1. Перейдите к @BotFather в Telegram")
            telegram_logger.error("2. Создайте нового бота командой /newbot")
            telegram_logger.error("3. Обновите токен в telegram_config.json")
            telegram_logger.error(
                "4. См. подробную инструкцию в TELEGRAM_TOKEN_SETUP.md"
            )
            return

        # Basic token format validation
        if not self.token.count(":") == 1 or len(self.token.split(":")[0]) < 8:
            telegram_logger.error("❌ ОШИБКА: Неверный формат токена!")
            telegram_logger.error(
                "Токен должен быть в формате: 123456789:ABCDEFGHijklmnop"
            )
            telegram_logger.error("📝 См. инструкцию в TELEGRAM_TOKEN_SETUP.md")
            return

        # Acquire lock to prevent multiple instances
        if not acquire_lock():
            telegram_logger.error(
                "Cannot start bot: Another bot instance is already running"
            )

            # Try a more aggressive cleanup approach
            try:
                telegram_logger.info(
                    "Attempting forced cleanup of any existing sessions..."
                )
                import requests

                # Make a direct API call to delete webhook and reset getUpdates state
                reset_url = f"https://api.telegram.org/bot{self.token}/deleteWebhook?drop_pending_updates=true"
                response = requests.get(reset_url, timeout=10)
                telegram_logger.info(
                    f"Forced cleanup response: {response.status_code}, {response.text}"
                )

                # Wait to ensure Telegram servers have time to reset
                await asyncio.sleep(5)

                # Try to acquire lock again
                if not acquire_lock():
                    telegram_logger.error(
                        "Still cannot acquire lock. Exiting bot initialization."
                    )
                    return
            except Exception as e:
                telegram_logger.error(f"Error during forced cleanup: {e}")
                return

        try:
            # If configured, try to clean up any existing sessions
            if self.cleanup_on_start:
                try:
                    # Make a direct API call to delete webhook and reset getUpdates state
                    telegram_logger.info("Cleaning up any existing bot sessions...")
                    import requests

                    reset_url = f"https://api.telegram.org/bot{self.token}/deleteWebhook?drop_pending_updates=true"
                    response = requests.get(reset_url, timeout=10)
                    telegram_logger.info(
                        f"Cleanup response: {response.status_code}, {response.text}"
                    )
                    # Sleep briefly to allow Telegram servers to reset
                    await asyncio.sleep(2)
                except Exception as e:
                    telegram_logger.warning(f"Error during cleanup: {e}")

            # Initialize the Application with proxy and timeout settings if configured
            builder = Application.builder().token(self.token)

            # Apply proxy if configured
            if self.proxy:
                telegram_logger.info(f"Using proxy: {self.proxy}")
                from telegram.request import HTTPXRequest

                request = HTTPXRequest(
                    proxy=self.proxy,
                    connection_pool_size=8,
                    read_timeout=self.connection_timeout,
                    write_timeout=self.connection_timeout,
                    connect_timeout=self.connection_timeout,
                )
                builder = builder.request(request)
            else:
                # Set timeouts even without proxy
                from telegram.request import HTTPXRequest

                request = HTTPXRequest(
                    connection_pool_size=8,
                    read_timeout=self.connection_timeout,
                    write_timeout=self.connection_timeout,
                    connect_timeout=self.connection_timeout,
                )
                builder = builder.request(request)

            # Build the application
            self.application = builder.build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(
                CommandHandler("reports", self.reports_command)
            )
            self.application.add_handler(CommandHandler("errors", self.errors_command))
            self.application.add_handler(
                CommandHandler("restart", self.restart_command)
            )
            self.application.add_handler(CommandHandler("run", self.run_command))
            self.application.add_handler(CommandHandler("tokens", self.tokens_command))

            # Add button callback handler
            self.application.add_handler(CallbackQueryHandler(self.button_callback))

            # Add message handler
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )

            # Add error handler
            self.application.add_error_handler(self.error_handler)

            # Mark as running
            self.running = True

            # Start error monitoring task
            self.start_error_monitor()

            # Initialize the bot with retry mechanism
            for attempt in range(1, self.max_retries + 1):
                try:
                    telegram_logger.info(
                        f"Starting Telegram bot (attempt {attempt}/{self.max_retries})"
                    )

                    # Add a longer timeout for initialization
                    await asyncio.wait_for(
                        self.application.initialize(),
                        timeout=self.connection_timeout
                        * 3,  # Increased multiplier from 2 to 3
                    )

                    await self.application.start()
                    await self.application.updater.start_polling(
                        drop_pending_updates=True,  # Very important to ignore old updates
                        allowed_updates=[
                            "message",
                            "callback_query",
                            "edited_message",
                        ],  # Limit update types
                    )

                    # Mark as initialized if we get here
                    self.initialized = True
                    telegram_logger.info("Telegram bot started successfully")

                    # Implement a heartbeat mechanism to verify bot is still responsive
                    heartbeat_counter = 0
                    while self.running:
                        await asyncio.sleep(30)  # Check every 30 seconds
                        heartbeat_counter += 1
                        if heartbeat_counter >= 10:  # Log heartbeat every 5 minutes
                            telegram_logger.debug(
                                "Telegram bot heartbeat: still running"
                            )
                            heartbeat_counter = 0

                    # Proper shutdown
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                    break  # Exit retry loop on success

                except asyncio.TimeoutError:
                    telegram_logger.error(
                        f"Timeout initializing bot (attempt {attempt}/{self.max_retries})"
                    )
                    if attempt < self.max_retries:
                        # Use exponential backoff for retries
                        wait_time = self.retry_delay * (2 ** (attempt - 1))
                        telegram_logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        telegram_logger.error(
                            "Maximum retry attempts reached. Failed to start Telegram bot."
                        )
                        self.running = False
                        break

                except telegram.error.InvalidToken as e:
                    telegram_logger.error(f"Invalid token error: {e}")
                    telegram_logger.error(
                        "❌ КРИТИЧЕСКАЯ ОШИБКА: Токен Telegram бота недействителен!"
                    )
                    telegram_logger.error("Возможные причины:")
                    telegram_logger.error("1. Токен был отозван в @BotFather")
                    telegram_logger.error("2. Токен неправильно скопирован")
                    telegram_logger.error("3. Бот был удален")
                    telegram_logger.error("📝 Инструкция по получению нового токена:")
                    telegram_logger.error("1. Перейдите в Telegram к @BotFather")
                    telegram_logger.error("2. Отправьте команду /newbot")
                    telegram_logger.error("3. Следуйте инструкциям для создания бота")
                    telegram_logger.error(
                        "4. Скопируйте новый токен в telegram_config.json"
                    )
                    telegram_logger.error(f"Текущий токен: {self.token}")
                    self.running = False
                    break  # Не retry для недействительного токена

                except telegram.error.Conflict as e:
                    telegram_logger.error(
                        f"Conflict error: {e} (attempt {attempt}/{self.max_retries})"
                    )
                    # This is a special error - another instance is already using the token
                    # We need to fix this by resetting the connection
                    try:
                        # Try to clean up directly with API call
                        import requests

                        telegram_logger.info("Attempting to reset bot connection...")
                        reset_url = f"https://api.telegram.org/bot{self.token}/deleteWebhook?drop_pending_updates=true"
                        response = requests.get(reset_url, timeout=10)
                        telegram_logger.info(
                            f"Reset response: {response.status_code}, {response.text}"
                        )

                        # Wait longer before retry for conflict errors
                        wait_time = self.retry_delay * 3
                        telegram_logger.info(
                            f"Waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)

                        if attempt >= self.max_retries:
                            telegram_logger.error(
                                "Maximum retry attempts reached. Failed to start Telegram bot."
                            )
                            self.running = False
                            break
                    except Exception as cleanup_error:
                        telegram_logger.error(
                            f"Error during connection reset: {cleanup_error}"
                        )
                        self.running = False
                        break

                except telegram.error.TimedOut:
                    telegram_logger.error(
                        f"Telegram API timed out (attempt {attempt}/{self.max_retries})"
                    )
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** (attempt - 1))
                        telegram_logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        telegram_logger.error(
                            "Maximum retry attempts reached. Failed to start Telegram bot."
                        )
                        self.running = False
                        break

                except telegram.error.NetworkError as e:
                    telegram_logger.error(
                        f"Network error starting bot: {e} (attempt {attempt}/{self.max_retries})"
                    )
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** (attempt - 1))
                        telegram_logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        telegram_logger.error(
                            "Maximum retry attempts reached. Failed to start Telegram bot."
                        )
                        self.running = False
                        break

                except Exception as e:
                    log_exception(
                        telegram_logger,
                        e,
                        f"Error starting Telegram bot (attempt {attempt}/{self.max_retries})",
                    )
                    self.running = False
                    break

        except Exception as e:
            self.running = False
            log_exception(telegram_logger, e, "Error setting up Telegram bot")
        finally:
            # Always release the lock when we're done
            if not self.running:
                release_lock()

    def start(self) -> None:
        """Start the bot in a separate thread with non-blocking behavior."""
        if self.thread and self.thread.is_alive():
            telegram_logger.warning("Bot is already running")
            return

        def run_bot():
            """Run the bot in an event loop."""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Set a timeout for the overall bot startup
                try:
                    # Start the bot with a much longer timeout for the entire startup process
                    loop.run_until_complete(
                        asyncio.wait_for(
                            self.start_bot(),
                            timeout=600,  # Increase timeout from 300 to 600 seconds (10 minutes)
                        )
                    )
                except asyncio.TimeoutError:
                    telegram_logger.error("Overall timeout starting Telegram bot")
                    self.running = False
                    # Attempt to restart the bot on timeout
                    telegram_logger.info("Attempting to restart bot after timeout...")
                    time.sleep(5)  # Wait 5 seconds before restart attempt
                    loop.run_until_complete(self.cleanup_telegram_session())
                    # Schedule a restart in the main application thread
                    threading.Timer(10.0, self.start).start()
                except KeyboardInterrupt:
                    telegram_logger.info("Bot thread interrupted by user")
                    self.running = False
                except Exception as e:
                    log_exception(telegram_logger, e, "Error running Telegram bot")
                    self.running = False
                finally:
                    # Clean up
                    release_lock()
                    loop.close()
            except Exception as e:
                log_exception(telegram_logger, e, "Fatal error in Telegram bot thread")
                self.running = False
                release_lock()

        # Start the bot in a daemon thread so it doesn't block program exit
        self.thread = threading.Thread(target=run_bot)
        self.thread.daemon = True
        self.thread.start()
        telegram_logger.info("Telegram bot thread started")

    def stop(self) -> None:
        """Stop the bot and release resources."""
        self.running = False
        telegram_logger.info("Stopping Telegram bot")

        # Release the lock
        release_lock()

    def queue_error(self, error_message: str) -> None:
        """Add an error to the notification queue."""
        if not self.running or not self.initialized:
            telegram_logger.warning(
                "Bot is not running or not initialized, error notification queued but won't be sent"
            )
            return

        try:
            # If we're in the same thread as the bot's event loop
            if threading.current_thread() == self.thread:
                asyncio.run_coroutine_threadsafe(
                    self.error_queue.put(error_message), asyncio.get_event_loop()
                )
            else:
                # We're in a different thread, create a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.error_queue.put(error_message), loop
                    )
                    future.result(timeout=1)  # Wait for 1 second
                finally:
                    loop.close()

            telegram_logger.info(f"Error queued for notification: {error_message}")
        except Exception as e:
            telegram_logger.error(f"Failed to queue error: {e}")


# Global bot instance for access from other modules
_bot_instance = None


def get_bot_instance() -> TelegramBot:
    """Get or create the global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    return _bot_instance


def send_telegram_notification(message: str) -> None:
    """Send a notification message via Telegram (can be called from any module)."""
    try:
        bot = get_bot_instance()
        bot.queue_error(message)
    except Exception as e:
        telegram_logger.error(f"Error sending notification: {e}")


def start_telegram_bot() -> TelegramBot:
    """Start the Telegram bot (called from main) with failure handling."""
    telegram_logger.info("Starting Telegram bot from main application")
    try:
        # First try to reset any existing bot sessions
        try:
            import requests

            with open("telegram_config.json", "r", encoding="utf-8-sig") as f:
                config = json.load(f)
            token = config.get("token")

            if token and token not in [
                "YOUR_TELEGRAM_BOT_TOKEN",
                "YOUR_NEW_TOKEN_HERE",
                "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ",
            ]:
                telegram_logger.info("Resetting any existing bot sessions...")
                reset_url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
                response = requests.get(
                    reset_url, timeout=10
                )  # Increased from 5 to 10 seconds
                telegram_logger.info(f"Reset response: {response.status_code}")
                # Sleep briefly to ensure reset is complete
                time.sleep(3)  # Added sleep to ensure reset is complete
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            telegram_logger.error(f"❌ Ошибка чтения telegram_config.json: {e}")
            telegram_logger.error(
                "📝 Проверьте кодировку файла и исправьте JSON синтаксис"
            )
            telegram_logger.error("Подробная инструкция: TELEGRAM_TOKEN_SETUP.md")
            return get_bot_instance()  # Return non-initialized instance
        except Exception as e:
            telegram_logger.warning(f"Error resetting bot session: {e}")

        # Start the bot
        bot = get_bot_instance()
        bot.start()

        # Wait a bit to see if initialization succeeds
        time.sleep(5)  # Added to check initial startup

        # Return the bot instance even if it fails to initialize
        # This allows the main application to continue running
        return bot
    except Exception as e:
        telegram_logger.error(f"Error initializing bot: {e}")
        # Return a non-initialized bot so the application can continue
        return get_bot_instance()


if __name__ == "__main__":
    # Start the bot when run directly
    telegram_logger.info("Starting Telegram bot from script")
    bot = start_telegram_bot()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        telegram_logger.info("Keyboard interrupt, stopping bot")
        bot.stop()
