# Инструкция по настройке токена Telegram бота

## Проблема
Ваш токен Telegram бота недействителен. Ошибка: `telegram.error.InvalidToken: The token was rejected by the server.`

## Решение

### 1. Создание нового бота
1. Откройте Telegram и найдите бота **@BotFather**
2. Отправьте команду `/start`
3. Отправьте команду `/newbot`
4. Введите название для вашего бота (например: "ЦРПТ Мониторинг")
5. Введите уникальное имя пользователя (должно заканчиваться на "bot", например: "crpt_monitoring_bot")

### 2. Получение токена
После создания бота @BotFather отправит вам сообщение с токеном в формате:
```
Use this token to access the HTTP API:
1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
```

### 3. Обновление конфигурации
1. Откройте файл `telegram_config.json`
2. Замените значение поля `"token"` на новый токен:
```json
{
  "token": "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ",
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

### 4. Получение Chat ID
Для получения вашего Chat ID:
1. Отправьте любое сообщение вашему новому боту
2. Перейдите по ссылке: `https://api.telegram.org/bot[ВАШ_ТОКЕН]/getUpdates`
3. Найдите поле `"id"` в разделе `"chat"` - это ваш Chat ID
4. Обновите значения `allowed_users`, `admin_users` и `error_notification_chat_ids` в конфигурации

### 5. Запуск бота
После обновления токена перезапустите приложение:
```bash
python main.py
```

## Дополнительные команды @BotFather

- `/mybots` - список ваших ботов
- `/token` - получить токен существующего бота
- `/revoke` - отозвать токен бота
- `/deletebot` - удалить бота

## Безопасность
⚠️ **Важно**: Никогда не публикуйте токен вашего бота! Храните его в безопасности.

## Проверка токена
Для проверки валидности токена можете использовать:
```bash
curl "https://api.telegram.org/bot[ВАШ_ТОКЕН]/getMe"
```

Если токен действителен, вы получите ответ с информацией о боте:
```json
{
  "ok": true,
  "result": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "Ваш Бот",
    "username": "your_bot_username"
  }
}
```

Если токен недействителен, вы получите ошибку:
```json
{
  "ok": false,
  "error_code": 401,
  "description": "Unauthorized"
}
```

## Устранение неполадок

### Ошибка "InvalidToken"
- **Причина**: Токен был отозван или удален
- **Решение**: Создайте нового бота и получите новый токен

### Ошибка "Conflict"
- **Причина**: Другой экземпляр бота уже запущен
- **Решение**: Остановите все процессы и перезапустите

### Ошибка "AttributeError: 'NoneType' object has no attribute 'text'"
- **Причина**: Проблемы с сетевым подключением
- **Решение**: Проверьте интернет-соединение и повторите попытку
