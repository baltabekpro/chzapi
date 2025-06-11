# 🚨 БЫСТРОЕ РЕШЕНИЕ ОШИБОК TELEGRAM

## Ошибка: JSONDecodeError: Unexpected UTF-8 BOM

### Что произошло?
Файл `telegram_config.json` содержит неправильную кодировку или русские символы в токене.

### ✅ БЫСТРОЕ РЕШЕНИЕ

1. **Проверьте токен:**
   ```bash
   python check_telegram_token.py
   ```

2. **Если токен недействителен, получите новый:**
   - Перейдите к боту @BotFather в Telegram
   - Отправьте команду `/newbot`
   - Создайте нового бота
   - Скопируйте полученный токен

3. **Обновите конфигурацию:**
   Откройте `telegram_config.json` и замените токен:
   ```json
   {
     "token": "1234567890:ВАШТОКЕНЗДЕСЬ",
     "allowed_users": [1419048544],
     "admin_users": [1419048544],
     "error_notification_chat_ids": [1419048544],
     "status_interval_hours": 12,
     "enable_error_notifications": true,
     "enable_status_updates": true,
     "max_retries": 3,
     "retry_delay": 5,
     "connection_timeout": 30,
     "proxy": null,
     "cleanup_on_start": true
   }
   ```

4. **Получите ваш Chat ID:**
   - Отправьте любое сообщение вашему боту
   - Перейдите по ссылке: `https://api.telegram.org/bot[ТОКЕН]/getUpdates`
   - Найдите поле `"id"` в разделе `"chat"` - это ваш Chat ID
   - Обновите поля `allowed_users`, `admin_users` и `error_notification_chat_ids`

5. **Проверьте исправления:**
   ```bash
   python check_telegram_token.py
   ```

## 🔧 Другие возможные ошибки

### Ошибка: AttributeError: 'NoneType' object has no attribute 'text'
**Исправлено!** Добавлена проверка `e.response is not None` во всех местах использования.

### Ошибка: InvalidToken
**Исправлено!** Добавлена детальная обработка с инструкциями по получению нового токена.

## 📞 Получение помощи

Если проблемы продолжаются:
1. Проверьте логи в директории `logs/`
2. Запустите диагностику: `python check_telegram_token.py`
3. См. подробную инструкцию: `TELEGRAM_TOKEN_SETUP.md`
