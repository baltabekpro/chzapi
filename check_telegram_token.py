#!/usr/bin/env python3
"""
Скрипт для проверки токена Telegram бота
"""

import json
import requests
import sys
import os

def check_token_format(token: str) -> bool:
    """Проверяет формат токена Telegram"""
    if not token:
        return False
    
    if token in ["YOUR_TELEGRAM_BOT_TOKEN", "YOUR_NEW_TOKEN_HERE", "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ"]:
        return False
    
    # Проверка формата токена (должен содержать ровно одно двоеточие)
    if token.count(':') != 1:
        return False
    
    parts = token.split(':')
    # Первая часть должна быть числом (bot ID)
    if not parts[0].isdigit() or len(parts[0]) < 8:
        return False
    
    # Вторая часть - secret token (должна быть достаточно длинной)
    if len(parts[1]) < 20:
        return False
    
    return True

def check_token_validity(token: str) -> tuple[bool, str]:
    """Проверяет валидность токена через API Telegram"""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                username = bot_info.get('username', 'Unknown')
                first_name = bot_info.get('first_name', 'Unknown')
                return True, f"✅ Токен действителен! Бот: {first_name} (@{username})"
            else:
                return False, f"❌ API вернул ошибку: {data.get('description', 'Unknown error')}"
        elif response.status_code == 401:
            return False, "❌ Токен недействителен (401 Unauthorized)"
        elif response.status_code == 404:
            return False, "❌ Бот не найден (404 Not Found)"
        else:
            return False, f"❌ HTTP ошибка: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "❌ Превышено время ожидания ответа от API"
    except requests.exceptions.ConnectionError:
        return False, "❌ Ошибка подключения к API Telegram"
    except Exception as e:
        return False, f"❌ Ошибка при проверке токена: {str(e)}"

def load_config():
    """Загружает конфигурацию из файла"""
    config_file = 'telegram_config.json'
    
    if not os.path.exists(config_file):
        print(f"❌ Файл {config_file} не найден")
        return None
    
    try:
        # Пробуем с utf-8-sig для обработки BOM
        with open(config_file, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
            return config
    except UnicodeDecodeError:
        try:
            # Fallback к обычному utf-8
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"❌ Ошибка кодировки файла {config_file}: {e}")
            return None
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка JSON в файле {config_file}: {e}")
        return None
    except Exception as e:
        print(f"❌ Ошибка при чтении файла {config_file}: {e}")
        return None

def main():
    print("🤖 Проверка токена Telegram бота")
    print("=" * 40)
    
    # Загружаем конфигурацию
    config = load_config()
    if not config:
        print("\n📝 Создайте файл telegram_config.json с действительным токеном")
        print("Инструкция: TELEGRAM_TOKEN_SETUP.md")
        sys.exit(1)
    
    token = config.get('token')
    
    print(f"Токен из конфигурации: {token[:20]}..." if token and len(token) > 20 else f"Токен: {token}")
    
    # Проверяем формат токена
    print("\n🔍 Проверка формата токена...")
    if not check_token_format(token):
        print("❌ Неверный формат токена!")
        print("Токен должен быть в формате: 123456789:ABCDEFGHIJKLMNOP...")
        print("📝 См. инструкцию в TELEGRAM_TOKEN_SETUP.md")
        sys.exit(1)
    
    print("✅ Формат токена корректный")
    
    # Проверяем валидность через API
    print("\n🌐 Проверка валидности через API Telegram...")
    is_valid, message = check_token_validity(token)
    print(message)
    
    if is_valid:
        print("\n🎉 Все проверки пройдены успешно!")
        print("Бот готов к использованию.")
        
        # Проверяем дополнительные настройки
        print("\n⚙️ Дополнительные настройки:")
        allowed_users = config.get('allowed_users', [])
        admin_users = config.get('admin_users', [])
        chat_ids = config.get('error_notification_chat_ids', [])
        
        print(f"- Разрешенные пользователи: {len(allowed_users)}")
        print(f"- Администраторы: {len(admin_users)}")
        print(f"- Chat ID для уведомлений: {len(chat_ids)}")
        
        if not allowed_users:
            print("⚠️ Предупреждение: Список разрешенных пользователей пуст")
        
        sys.exit(0)
    else:
        print("\n❌ Токен недействителен!")
        print("📝 Получите новый токен согласно инструкции в TELEGRAM_TOKEN_SETUP.md")
        sys.exit(1)

if __name__ == "__main__":
    main()
