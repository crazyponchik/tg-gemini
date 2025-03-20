import sqlite3
import json
import time
from config import load_config
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

config = load_config()

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        settings TEXT,
        created_at INTEGER,
        last_active INTEGER
    )
    ''')
    
    # Таблица сообщений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp INTEGER,
        message_type TEXT,
        media_id TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица для хранения файлов/изображений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_id TEXT,
        file_unique_id TEXT,
        file_path TEXT,
        media_type TEXT,
        processed_text TEXT,
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица для запланированных сообщений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        scheduled_time INTEGER,
        is_sent INTEGER DEFAULT 0,
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица для статистики использования
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        model TEXT,
        tokens_used INTEGER,
        request_type TEXT,
        timestamp INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Dict:
    """Получить информацию о пользователе"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    conn.close()
    
    if not user_data:
        return None
    
    columns = ['user_id', 'username', 'first_name', 'last_name', 'settings', 'created_at', 'last_active']
    user_dict = dict(zip(columns, user_data))
    
    if user_dict['settings']:
        user_dict['settings'] = json.loads(user_dict['settings'])
    else:
        user_dict['settings'] = {
            "model": config.DEFAULT_MODEL,
            "temperature": config.DEFAULT_TEMP,
            "max_tokens": config.DEFAULT_MAX_TOKENS,
            "conversation_mode": "friendly",
            "language": "ru"
        }
    
    return user_dict

def create_or_update_user(user_id: int, username: str, first_name: str, last_name: str) -> None:
    """Создать или обновить пользователя"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    if exists:
        # Обновляем информацию о пользователе
        cursor.execute("""
        UPDATE users 
        SET username = ?, first_name = ?, last_name = ?, last_active = ? 
        WHERE user_id = ?
        """, (username, first_name, last_name, current_time, user_id))
    else:
        # Создаем нового пользователя с настройками по умолчанию
        default_settings = {
            "model": config.DEFAULT_MODEL,
            "temperature": config.DEFAULT_TEMP,
            "max_tokens": config.DEFAULT_MAX_TOKENS,
            "conversation_mode": "friendly",
            "language": "ru"
        }
        
        cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, settings, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, json.dumps(default_settings), current_time, current_time))
    
    conn.commit()
    conn.close()

def update_user_settings(user_id: int, settings: Dict) -> None:
    """Обновить настройки пользователя"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    # Получаем текущие настройки
    cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        current_settings = json.loads(result[0])
    else:
        current_settings = {
            "model": config.DEFAULT_MODEL,
            "temperature": config.DEFAULT_TEMP,
            "max_tokens": config.DEFAULT_MAX_TOKENS,
            "conversation_mode": "friendly",
            "language": "ru"
        }
    
    # Обновляем настройки
    current_settings.update(settings)
    
    # Сохраняем обновленные настройки
    cursor.execute("""
    UPDATE users 
    SET settings = ?, last_active = ? 
    WHERE user_id = ?
    """, (json.dumps(current_settings), int(time.time()), user_id))
    
    conn.commit()
    conn.close()

def add_message(user_id: int, role: str, content: str, message_type: str = "text", media_id: str = None) -> int:
    """Добавить сообщение в историю"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute("""
    INSERT INTO messages (user_id, role, content, timestamp, message_type, media_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, role, content, current_time, message_type, media_id))
    
    message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return message_id

def get_chat_history(user_id: int, limit: int = 10) -> List[Dict]:
    """Получить историю чата пользователя"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT m.role, m.content, m.timestamp, m.message_type, m.media_id, med.processed_text 
    FROM messages m
    LEFT JOIN media med ON m.media_id = med.file_unique_id
    WHERE m.user_id = ?
    ORDER BY m.timestamp DESC
    LIMIT ?
    """, (user_id, limit))
    
    messages = cursor.fetchall()
    conn.close()
    
    # Преобразуем сообщения в формат для OpenRouter API
    chat_messages = []
    
    for msg in reversed(messages):
        role, content, timestamp, message_type, media_id, processed_text = msg
        
        if role not in ["user", "assistant", "system"]:
            continue
        
        # Формируем содержимое сообщения в зависимости от типа
        message_content = []
        
        if message_type == "text":
            message_content.append({
                "type": "text",
                "text": content
            })
        elif message_type == "image" and processed_text:
            # Если есть изображение и оно было обработано
            message_content.append({
                "type": "text",
                "text": content or "Что на этом изображении?"
            })
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"file://{processed_text}"  # Путь к файлу изображения
                }
            })
        
        if message_content:
            chat_messages.append({
                "role": role,
                "content": message_content
            })
    
    return chat_messages

def add_media(user_id: int, file_id: str, file_unique_id: str, 
              file_path: str, media_type: str, processed_text: str = None) -> int:
    """Добавить медиафайл в базу данных"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute("""
    INSERT INTO media (user_id, file_id, file_unique_id, file_path, media_type, processed_text, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, file_id, file_unique_id, file_path, media_type, processed_text, current_time))
    
    media_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return media_id

def get_media(file_unique_id: str) -> Dict:
    """Получить информацию о медиафайле"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM media WHERE file_unique_id = ?", (file_unique_id,))
    media_data = cursor.fetchone()
    
    conn.close()
    
    if not media_data:
        return None
    
    columns = ['id', 'user_id', 'file_id', 'file_unique_id', 'file_path', 'media_type', 'processed_text', 'created_at']
    media_dict = dict(zip(columns, media_data))
    
    return media_dict

def add_usage_stats(user_id: int, model: str, tokens_used: int, request_type: str) -> None:
    """Добавить статистику использования"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute("""
    INSERT INTO usage_stats (user_id, model, tokens_used, request_type, timestamp)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, model, tokens_used, request_type, current_time))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id: int) -> Dict:
    """Получить статистику использования для пользователя"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    # Общее количество сообщений
    cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
    message_count = cursor.fetchone()[0]
    
    # Количество токенов по моделям
    cursor.execute("""
    SELECT model, SUM(tokens_used) 
    FROM usage_stats 
    WHERE user_id = ? 
    GROUP BY model
    """, (user_id,))
    tokens_by_model = {model: tokens for model, tokens in cursor.fetchall()}
    
    # Статистика по типам запросов
    cursor.execute("""
    SELECT request_type, COUNT(*) 
    FROM usage_stats 
    WHERE user_id = ? 
    GROUP BY request_type
    """, (user_id,))
    requests_by_type = {req_type: count for req_type, count in cursor.fetchall()}
    
    # Активность по дням недели
    cursor.execute("""
    SELECT strftime('%w', datetime(timestamp, 'unixepoch')) as day, COUNT(*)
    FROM messages
    WHERE user_id = ?
    GROUP BY day
    """, (user_id,))
    activity_by_day = {day: count for day, count in cursor.fetchall()}
    
    conn.close()
    
    return {
        "message_count": message_count,
        "tokens_by_model": tokens_by_model,
        "requests_by_type": requests_by_type,
        "activity_by_day": activity_by_day
    }

def add_scheduled_message(user_id: int, content: str, scheduled_time: int) -> int:
    """Добавить запланированное сообщение"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    cursor.execute("""
    INSERT INTO scheduled_messages (user_id, content, scheduled_time, created_at)
    VALUES (?, ?, ?, ?)
    """, (user_id, content, scheduled_time, current_time))
    
    message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return message_id

def get_pending_scheduled_messages() -> List[Dict]:
    """Получить запланированные сообщения, которые нужно отправить"""
    conn = sqlite3.connect(config.DB_PATH)
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

def mark_scheduled_message_sent(message_id: int) -> None:
    """Отметить запланированное сообщение как отправленное"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE scheduled_messages 
    SET is_sent = 1
    WHERE id = ?
    """, (message_id,))
    
    conn.commit()
    conn.close()

def clear_chat_history(user_id: int) -> None:
    """Очистить историю чата пользователя"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()

def export_chat_history(user_id: int, format_type: str = "text") -> str:
    """Экспортировать историю чата в выбранном формате"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT m.role, m.content, m.timestamp, m.message_type
    FROM messages m
    WHERE m.user_id = ?
    ORDER BY m.timestamp ASC
    """, (user_id,))
    
    messages = cursor.fetchall()
    conn.close()
    
    if format_type == "text":
        output = []
        for msg in messages:
            role, content, timestamp, message_type = msg
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            if role == "user":
                output.append(f"[{time_str}] Вы: {content}")
            elif role == "assistant":
                output.append(f"[{time_str}] Бот: {content}")
        
        return "\n\n".join(output)
    
    elif format_type == "json":
        output = []
        for msg in messages:
            role, content, timestamp, message_type = msg
            output.append({
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "time": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                "type": message_type
            })
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    return "Неподдерживаемый формат экспорта"
