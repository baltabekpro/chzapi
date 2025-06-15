import json
import os
import sys
from datetime import datetime, timedelta  # Add timedelta import

import colorama
from colorama import Fore, Style
from logger_config import get_logger, log_exception

# Initialize colorama
colorama.init(autoreset=True)

# Set up logger
token_logger = get_logger("tokens")


def mask_token(token, visible_chars=4):
    """Mask token for display, showing only first and last few characters"""
    if not token or len(token) <= visible_chars * 2:
        return "***"

    return (
        token[:visible_chars]
        + "*" * (len(token) - visible_chars * 2)
        + token[-visible_chars:]
    )


def load_tokens_file():
    """Load tokens from JSON file"""
    try:
        file_path = "true_api_tokens.json"
        if not os.path.exists(file_path):
            return {"tokens": {}, "generated_at": datetime.now().isoformat()}

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        token_logger.error(f"Ошибка при загрузке токенов: {str(e)}")
        return {"tokens": {}, "generated_at": datetime.now().isoformat()}


def save_tokens_file(data):
    """Save tokens to JSON file"""
    try:
        file_path = "true_api_tokens.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        token_logger.error(f"Ошибка при сохранении токенов: {str(e)}")
        return False


def load_certificates_file():
    """Load certificates from JSON file"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        file_path = os.path.join(base_dir, 'config', 'certificates.json')
        if not os.path.exists(file_path):
            return {"certificates": []}

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        token_logger.error(f"Ошибка при загрузке сертификатов: {str(e)}")
        return {"certificates": []}


def save_certificates_file(data):
    """Save certificates to JSON file"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        file_path = os.path.join(base_dir, 'config', 'certificates.json')
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        token_logger.error(f"Ошибка при сохранении сертификатов: {str(e)}")
        return False


def load_thumbprints_file():
    """Load certificate thumbprints from file"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        file_path = os.path.join(base_dir, 'config', 'cert_thumbprints.txt')
        if not os.path.exists(file_path):
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            thumbprints = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            return thumbprints
    except Exception as e:
        token_logger.error(f"Ошибка при загрузке отпечатков сертификатов: {str(e)}")
        return []


def save_thumbprints_file(thumbprints):
    """Save certificate thumbprints to file"""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        file_path = os.path.join(base_dir, 'config', 'cert_thumbprints.txt')
        with open(file_path, "w", encoding="utf-8") as f:
            for tp in thumbprints:
                f.write(f"{tp}\n")
        return True
    except Exception as e:
        token_logger.error(f"Ошибка при сохранении отпечатков сертификатов: {str(e)}")
        return False


def update_last_run_time(new_date=None, manual=True):
    """Update the last_run.json file with new date"""
    try:
        file_path = "last_run.json"

        # Load existing data if available
        data = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Use provided date or current time
        if new_date:
            if isinstance(new_date, str):
                # Try to parse the date string
                new_date = datetime.fromisoformat(new_date)
        else:
            new_date = datetime.now()

        # Format the new date
        date_str = new_date.isoformat()

        # Update the data
        data["last_run"] = date_str
        data["manual_run"] = manual

        # Save the file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        token_logger.info(f"Дата последнего запуска обновлена: {date_str}")
        return True
    except Exception as e:
        token_logger.error(f"Ошибка при обновлении даты запуска: {str(e)}")
        return False


def show_tokens_management_menu():
    """Display tokens management menu"""
    menu = f"""
{Fore.CYAN}================ УПРАВЛЕНИЕ ТОКЕНАМИ И СЕРТИФИКАТАМИ ================
{Fore.YELLOW}1. Просмотр токенов
{Fore.YELLOW}2. Добавить токен
{Fore.YELLOW}3. Редактировать токен
{Fore.YELLOW}4. Удалить токен
{Fore.YELLOW}5. Просмотр сертификатов
{Fore.YELLOW}6. Добавить сертификат
{Fore.YELLOW}7. Редактировать сертификат
{Fore.YELLOW}8. Удалить сертификат
{Fore.YELLOW}9. Изменить дату последнего запуска
{Fore.YELLOW}0. Выход в главное меню
{Fore.CYAN}=================================================================
"""
    while True:
        print(menu)
        choice = input(f"{Fore.GREEN}Выберите действие (0-9): ").strip()

        if choice == "1":
            view_tokens()
        elif choice == "2":
            add_token()
        elif choice == "3":
            edit_token()
        elif choice == "4":
            delete_token()
        elif choice == "5":
            view_certificates()
        elif choice == "6":
            add_certificate()
        elif choice == "7":
            edit_certificate()
        elif choice == "8":
            delete_certificate()
        elif choice == "9":
            change_last_run_date()
        elif choice == "0":
            return
        else:
            print(f"{Fore.RED}Неверный выбор. Пожалуйста, повторите.")


def view_tokens():
    """Display all available tokens"""
    tokens_data = load_tokens_file()
    tokens = tokens_data.get("tokens", {})
    generated_at = tokens_data.get("generated_at", "")

    if not tokens:
        print(f"{Fore.RED}Токены не найдены")
        return

    print(f"\n{Fore.CYAN}=== Доступные токены (сгенерированы: {generated_at}) ===\n")

    for i, (name, token) in enumerate(tokens.items(), 1):
        masked = mask_token(token)
        print(f"{Fore.GREEN}{i}. {Fore.WHITE}{name}: {Fore.YELLOW}{masked}")

    print()
    input(f"{Fore.CYAN}Нажмите Enter для продолжения...")


def add_token():
    """Add a new token"""
    tokens_data = load_tokens_file()
    tokens = tokens_data.get("tokens", {})

    print(f"\n{Fore.CYAN}=== Добавление нового токена ===\n")

    name = input(f"{Fore.GREEN}Введите имя для токена: ").strip()
    if not name:
        print(f"{Fore.RED}Имя не может быть пустым")
        return

    if name in tokens:
        print(f"{Fore.RED}Токен с именем {name} уже существует. Выберите другое имя.")
        return

    token = input(f"{Fore.GREEN}Введите значение токена: ").strip()
    if not token:
        print(f"{Fore.RED}Значение токена не может быть пустым")
        return

    # Add the new token
    tokens[name] = token
    tokens_data["tokens"] = tokens
    tokens_data["generated_at"] = datetime.now().isoformat()

    if save_tokens_file(tokens_data):
        token_logger.info(f"Добавлен новый токен: {name}")
        print(f"{Fore.GREEN}Токен успешно добавлен")
    else:
        print(f"{Fore.RED}Ошибка при сохранении токена")


def edit_token():
    """Edit an existing token"""
    tokens_data = load_tokens_file()
    tokens = tokens_data.get("tokens", {})

    if not tokens:
        print(f"{Fore.RED}Нет доступных токенов для редактирования")
        return

    print(f"\n{Fore.CYAN}=== Редактирование токена ===\n")

    # Display available tokens
    names = list(tokens.keys())
    for i, name in enumerate(names, 1):
        masked = mask_token(tokens[name])
        print(f"{Fore.GREEN}{i}. {Fore.WHITE}{name}: {Fore.YELLOW}{masked}")

    # Select token to edit
    try:
        choice = input(
            f"\n{Fore.GREEN}Выберите номер токена для редактирования (или 0 для отмены): "
        )
        if choice == "0":
            return

        index = int(choice) - 1
        if index < 0 or index >= len(names):
            print(f"{Fore.RED}Неверный номер")
            return

        selected_name = names[index]
        original_token = tokens[selected_name]

        # What to edit
        print(f"\n{Fore.CYAN}Редактирование токена: {selected_name}\n")
        print(f"{Fore.YELLOW}1. Изменить имя токена")
        print(f"{Fore.YELLOW}2. Изменить значение токена")
        print(f"{Fore.YELLOW}0. Отмена")

        edit_choice = input(f"\n{Fore.GREEN}Выберите действие: ")

        if edit_choice == "0":
            return
        elif edit_choice == "1":
            # Change token name
            new_name = input(f"{Fore.GREEN}Введите новое имя: ").strip()
            if not new_name:
                print(f"{Fore.RED}Имя не может быть пустым")
                return

            if new_name in tokens and new_name != selected_name:
                print(f"{Fore.RED}Токен с таким именем уже существует")
                return

            # Delete old key and add with new name
            tokens.pop(selected_name)
            tokens[new_name] = original_token
            tokens_data["tokens"] = tokens
            tokens_data["generated_at"] = datetime.now().isoformat()

            if save_tokens_file(tokens_data):
                token_logger.info(f"Переименован токен: {selected_name} -> {new_name}")
                print(f"{Fore.GREEN}Имя токена успешно изменено")
            else:
                print(f"{Fore.RED}Ошибка при сохранении изменений")

        elif edit_choice == "2":
            # Change token value
            new_token = input(f"{Fore.GREEN}Введите новое значение токена: ").strip()
            if not new_token:
                print(f"{Fore.RED}Значение не может быть пустым")
                return

            tokens[selected_name] = new_token
            tokens_data["tokens"] = tokens
            tokens_data["generated_at"] = datetime.now().isoformat()

            if save_tokens_file(tokens_data):
                token_logger.info(f"Изменено значение токена: {selected_name}")
                print(f"{Fore.GREEN}Значение токена успешно изменено")
            else:
                print(f"{Fore.RED}Ошибка при сохранении изменений")

        else:
            print(f"{Fore.RED}Неверный выбор")

    except ValueError:
        print(f"{Fore.RED}Некорректный ввод")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {str(e)}")


def delete_token():
    """Delete a token"""
    tokens_data = load_tokens_file()
    tokens = tokens_data.get("tokens", {})

    if not tokens:
        print(f"{Fore.RED}Нет доступных токенов для удаления")
        return

    print(f"\n{Fore.CYAN}=== Удаление токена ===\n")

    # Display available tokens
    names = list(tokens.keys())
    for i, name in enumerate(names, 1):
        masked = mask_token(tokens[name])
        print(f"{Fore.GREEN}{i}. {Fore.WHITE}{name}: {Fore.YELLOW}{masked}")

    # Select token to delete
    try:
        choice = input(
            f"\n{Fore.GREEN}Выберите номер токена для удаления (или 0 для отмены): "
        )
        if choice == "0":
            return

        index = int(choice) - 1
        if index < 0 or index >= len(names):
            print(f"{Fore.RED}Неверный номер")
            return

        selected_name = names[index]

        # Confirm deletion
        confirm = input(
            f"{Fore.RED}Вы уверены, что хотите удалить токен {selected_name}? (д/н): "
        )
        if confirm.lower() not in ["д", "y", "да", "yes"]:
            print(f"{Fore.YELLOW}Отмена удаления")
            return

        # Delete the token
        tokens.pop(selected_name)
        tokens_data["tokens"] = tokens
        tokens_data["generated_at"] = datetime.now().isoformat()

        if save_tokens_file(tokens_data):
            token_logger.info(f"Удален токен: {selected_name}")
            print(f"{Fore.GREEN}Токен успешно удален")
        else:
            print(f"{Fore.RED}Ошибка при сохранении изменений")

    except ValueError:
        print(f"{Fore.RED}Некорректный ввод")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {str(e)}")


def view_certificates():
    """Display all certificates"""
    # Load thumbprints
    thumbprints = load_thumbprints_file()

    # Load certificate names
    cert_data = load_certificates_file()
    certificates = cert_data.get("certificates", [])

    # Create mapping of thumbprint to certificate object
    cert_map = {
        cert.get("thumbprint"): cert for cert in certificates if cert.get("thumbprint")
    }

    print(f"\n{Fore.CYAN}=== Доступные сертификаты ===\n")

    # First show certificates from certificates.json
    for i, thumbprint in enumerate(thumbprints, 1):
        cert = cert_map.get(thumbprint, {"name": "Без имени"})
        name = cert.get("name", "Без имени")
        print(
            f"{Fore.GREEN}{i}. {Fore.WHITE}{name}\n   {Fore.YELLOW}Отпечаток: {thumbprint}"
        )

    print()
    input(f"{Fore.CYAN}Нажмите Enter для продолжения...")


def add_certificate():
    """Add a new certificate"""
    # Load existing data
    thumbprints = load_thumbprints_file()
    cert_data = load_certificates_file()
    certificates = cert_data.get("certificates", [])

    print(f"\n{Fore.CYAN}=== Добавление нового сертификата ===\n")

    name = input(f"{Fore.GREEN}Введите имя сертификата (владельца): ").strip()
    thumbprint = (
        input(f"{Fore.GREEN}Введите отпечаток сертификата (SHA1): ").strip().lower()
    )

    if not thumbprint:
        print(f"{Fore.RED}Отпечаток не может быть пустым")
        return

    # Check if thumbprint already exists
    if thumbprint in thumbprints:
        print(f"{Fore.RED}Сертификат с таким отпечатком уже существует")
        return

    # Add to thumbprints.txt
    thumbprints.append(thumbprint)
    save_thumbprints_file(thumbprints)

    # Add to certificates.json if name provided
    if name:
        certificates.append({"name": name, "thumbprint": thumbprint})
        cert_data["certificates"] = certificates
        save_certificates_file(cert_data)

    token_logger.info(f"Добавлен новый сертификат: {name} ({thumbprint})")
    print(f"{Fore.GREEN}Сертификат успешно добавлен")


def edit_certificate():
    """Edit a certificate"""
    # Load existing data
    thumbprints = load_thumbprints_file()
    cert_data = load_certificates_file()
    certificates = cert_data.get("certificates", [])

    # Create mapping of thumbprint to certificate object and index
    cert_map = {}
    for i, cert in enumerate(certificates):
        if "thumbprint" in cert:
            cert_map[cert["thumbprint"]] = (i, cert)

    if not thumbprints:
        print(f"{Fore.RED}Нет доступных сертификатов для редактирования")
        return

    print(f"\n{Fore.CYAN}=== Редактирование сертификата ===\n")

    # Display available certificates
    for i, thumbprint in enumerate(thumbprints, 1):
        if thumbprint in cert_map:
            _, cert = cert_map[thumbprint]
            name = cert.get("name", "Без имени")
        else:
            name = "Без имени"

        print(
            f"{Fore.GREEN}{i}. {Fore.WHITE}{name}\n   {Fore.YELLOW}Отпечаток: {thumbprint}"
        )

    # Select certificate to edit
    try:
        choice = input(
            f"\n{Fore.GREEN}Выберите номер сертификата для редактирования (или 0 для отмены): "
        )
        if choice == "0":
            return

        index = int(choice) - 1
        if index < 0 or index >= len(thumbprints):
            print(f"{Fore.RED}Неверный номер")
            return

        selected_thumbprint = thumbprints[index]

        # What to edit
        print(
            f"\n{Fore.CYAN}Редактирование сертификата с отпечатком: {selected_thumbprint}\n"
        )
        print(f"{Fore.YELLOW}1. Изменить имя сертификата")
        print(f"{Fore.YELLOW}2. Изменить отпечаток сертификата")
        print(f"{Fore.YELLOW}0. Отмена")

        edit_choice = input(f"\n{Fore.GREEN}Выберите действие: ")

        if edit_choice == "0":
            return
        elif edit_choice == "1":
            # Change certificate name
            if selected_thumbprint in cert_map:
                cert_index, cert = cert_map[selected_thumbprint]
                current_name = cert.get("name", "Без имени")
                print(f"{Fore.YELLOW}Текущее имя: {current_name}")
            else:
                # Certificate not in certificates.json yet
                cert_index = None
                current_name = "Без имени"
                print(f"{Fore.YELLOW}У сертификата нет имени")

            new_name = input(f"{Fore.GREEN}Введите новое имя: ").strip()
            if not new_name:
                print(f"{Fore.RED}Имя не может быть пустым")
                return

            if cert_index is not None:
                # Update existing certificate
                certificates[cert_index]["name"] = new_name
            else:
                # Add new certificate
                certificates.append(
                    {"name": new_name, "thumbprint": selected_thumbprint}
                )

            cert_data["certificates"] = certificates
            if save_certificates_file(cert_data):
                token_logger.info(
                    f"Изменено имя сертификата: {current_name} -> {new_name}"
                )
                print(f"{Fore.GREEN}Имя сертификата успешно изменено")
            else:
                print(f"{Fore.RED}Ошибка при сохранении изменений")

        elif edit_choice == "2":
            # Change certificate thumbprint
            new_thumbprint = (
                input(f"{Fore.GREEN}Введите новый отпечаток сертификата: ")
                .strip()
                .lower()
            )
            if not new_thumbprint:
                print(f"{Fore.RED}Отпечаток не может быть пустым")
                return

            if new_thumbprint in thumbprints:
                print(f"{Fore.RED}Сертификат с таким отпечатком уже существует")
                return

            # Update thumbprints.txt
            thumbprints[index] = new_thumbprint
            if save_thumbprints_file(thumbprints):
                # Update certificates.json if present
                if selected_thumbprint in cert_map:
                    cert_index, _ = cert_map[selected_thumbprint]
                    certificates[cert_index]["thumbprint"] = new_thumbprint
                    cert_data["certificates"] = certificates
                    save_certificates_file(cert_data)

                token_logger.info(
                    f"Изменен отпечаток сертификата: {selected_thumbprint} -> {new_thumbprint}"
                )
                print(f"{Fore.GREEN}Отпечаток сертификата успешно изменен")
            else:
                print(f"{Fore.RED}Ошибка при сохранении изменений")

        else:
            print(f"{Fore.RED}Неверный выбор")

    except ValueError:
        print(f"{Fore.RED}Некорректный ввод")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {str(e)}")


def delete_certificate():
    """Delete a certificate"""
    # Load existing data
    thumbprints = load_thumbprints_file()
    cert_data = load_certificates_file()
    certificates = cert_data.get("certificates", [])

    # Create mapping of thumbprint to certificate object and index
    cert_map = {}
    for i, cert in enumerate(certificates):
        if "thumbprint" in cert:
            cert_map[cert["thumbprint"]] = (i, cert)

    if not thumbprints:
        print(f"{Fore.RED}Нет доступных сертификатов для удаления")
        return

    print(f"\n{Fore.CYAN}=== Удаление сертификата ===\n")

    # Display available certificates
    for i, thumbprint in enumerate(thumbprints, 1):
        if thumbprint in cert_map:
            _, cert = cert_map[thumbprint]
            name = cert.get("name", "Без имени")
        else:
            name = "Без имени"

        print(
            f"{Fore.GREEN}{i}. {Fore.WHITE}{name}\n   {Fore.YELLOW}Отпечаток: {thumbprint}"
        )

    # Select certificate to delete
    try:
        choice = input(
            f"\n{Fore.GREEN}Выберите номер сертификата для удаления (или 0 для отмены): "
        )
        if choice == "0":
            return

        index = int(choice) - 1
        if index < 0 or index >= len(thumbprints):
            print(f"{Fore.RED}Неверный номер")
            return

        selected_thumbprint = thumbprints[index]

        # Get name if available
        if selected_thumbprint in cert_map:
            cert_name = cert_map[selected_thumbprint][1].get("name", "Без имени")
        else:
            cert_name = "Без имени"

        # Confirm deletion
        confirm = input(
            f"{Fore.RED}Вы уверены, что хотите удалить сертификат '{cert_name}'? (д/н): "
        )
        if confirm.lower() not in ["д", "y", "да", "yes"]:
            print(f"{Fore.YELLOW}Отмена удаления")
            return

        # Delete from thumbprints.txt
        thumbprints.pop(index)
        save_thumbprints_file(thumbprints)

        # Delete from certificates.json if present
        if selected_thumbprint in cert_map:
            cert_index, _ = cert_map[selected_thumbprint]
            certificates.pop(cert_index)
            cert_data["certificates"] = certificates
            save_certificates_file(cert_data)

        token_logger.info(f"Удален сертификат: {cert_name} ({selected_thumbprint})")
        print(f"{Fore.GREEN}Сертификат успешно удален")

    except ValueError:
        print(f"{Fore.RED}Некорректный ввод")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {str(e)}")


def change_last_run_date():
    """Change the last run date"""
    # Load current date from last_run.json
    last_run = None
    try:
        if os.path.exists("last_run.json"):
            with open("last_run.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data.get("last_run", ""))
                print(
                    f"{Fore.YELLOW}Текущая дата последнего запуска: {last_run.strftime('%Y-%м-%д %H:%M:%S')}"
                )
        else:
            print(
                f"{Fore.YELLOW}Файл last_run.json не найден. Будет создан новый файл."
            )
            last_run = datetime.now()
    except:
        last_run = datetime.now()
        print(
            f"{Fore.YELLOW}Не удалось прочитать дату из файла. Используется текущая дата."
        )

    print(f"\n{Fore.CYAN}=== Изменение даты последнего запуска ===\n")

    # Menu options for date update
    print(f"{Fore.YELLOW}1. Использовать текущую дату и время")
    print(f"{Fore.YELLOW}2. Ввести конкретную дату и время")
    print(f"{Fore.YELLOW}3. Установить время в прошлом (например, 2 дня назад)")
    print(f"{Fore.YELLOW}0. Отмена")

    choice = input(f"\n{Fore.GREEN}Выберите действие: ")

    if choice == "0":
        return
    elif choice == "1":
        # Use current date/time
        if update_last_run_time():
            print(f"{Fore.GREEN}Дата последнего запуска установлена на текущее время")
    elif choice == "2":
        # Enter specific date/time
        try:
            date_str = input(
                f"{Fore.GREEN}Введите дату в формате ГГГГ-ММ-ДД (например 2025-03-21): "
            )
            time_str = input(
                f"{Fore.GREEN}Введите время в формате ЧЧ:ММ (например 14:30): "
            )

            # Parse date and time
            date_parts = date_str.split("-")
            year, month, day = map(int, date_parts)

            # Parse time if provided
            hour, minute = 0, 0
            if time_str:
                time_parts = time_str.split(":")
                hour, minute = map(int, time_parts)

            # Create datetime object
            new_date = datetime(year, month, day, hour, minute)

            # Update the file
            if update_last_run_time(new_date):
                print(f"{Fore.GREEN}Дата последнего запуска установлена на {new_date}")

        except Exception as e:
            print(f"{Fore.RED}Ошибка при установке даты: {e}")
    elif choice == "3":
        # Set date in the past
        try:
            days = int(input(f"{Fore.GREEN}Сколько дней назад (например, 2): "))

            # Calculate the date
            new_date = datetime.now() - timedelta(days=days)

            # Update the file
            if update_last_run_time(new_date):
                print(f"{Fore.GREEN}Дата последнего запуска установлена на {new_date}")

        except ValueError:
            print(f"{Fore.RED}Некорректное число дней")
        except Exception as e:
            print(f"{Fore.RED}Ошибка при установке даты: {e}")
    else:
        print(f"{Fore.RED}Неверный выбор")


if __name__ == "__main__":
    show_tokens_management_menu()  # Fix the function name
