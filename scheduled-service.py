#!/usr/bin/env python
"""
Сервис для обработки запланированных сообщений.
Может быть запущен как отдельный процесс для проверки и отправки
запланированных сообщений даже когда основной бот не активен.
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

def get_db_connection():
    """Подключение к базе данных"""
    import sqlite3
    from config import load_config
    
    config = load_config()
    return sqlite3.connect(config.DB_PATH)

def get_pending_messages():
    """Получение запланированных сообщений, которые нужно отправить"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute("""
    SELECT id, user_id, content, scheduled_time 
    FROM scheduled_messages 
    WHERE scheduled_time <= ? AND is_sent = 0
    """, (current_time,))
    
    messages = cursor.fetchall()
    conn.close()
    
    # Преобразуем в список словарей
    result = []
    for msg in messages:
        msg_id, user_id, content, scheduled_time = msg
        result.append({
            "id": msg_id,
            "user_id": user_id,
            "content": content,
            "scheduled_time": scheduled_time
        })
    
    return result

def mark_message_sent(message_id):
    """Отметить сообщение как отправленное"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE scheduled_messages 
    SET is_sent = 1
    WHERE id = ?
    """, (message_id,))
    
    conn.commit()
    conn.close()

def send_telegram_message(chat_id, text):
    """Отправка сообщения через Telegram Bot API"""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"⏰ *Запланированное сообщение*\n\n{text}",
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return False

def process_scheduled_messages():
    """Обработка запланированных сообщений"""
    logger.info("Проверка запланированных сообщений")
    
    # Получаем список сообщений для отправки
    messages = get_pending_messages()
    
    if not messages:
        logger.info("Нет запланированных сообщений для отправки")
        return
    
    logger.info(f"Найдено {len(messages)} сообщений для отправки")
    
    # Отправляем каждое сообщение
    for message in messages:
        user_id = message["user_id"]
        content = message["content"]
        message_id = message["id"]
        
        logger.info(f"Отправка сообщения #{message_id} пользователю {user_id}")
        
        # Пытаемся отправить сообщение
        if send_telegram_message(user_id, content):
            # Если успешно отправлено, отмечаем как отправленное
            mark_message_sent(message_id)
            logger.info(f"Сообщение #{message_id} успешно отправлено и отмечено")
        else:
            logger.error(f"Не удалось отправить сообщение #{message_id}")

def main():
    """Основная функция"""
    logger.info("Запуск сервиса запланированных сообщений")
    
    check_interval = 60  # Проверка каждую минуту
    
    try:
        while True:
            process_scheduled_messages()
            time.sleep(check_interval)
    except KeyboardInterrupt:
        logger.info("Сервис остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка в работе сервиса: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
