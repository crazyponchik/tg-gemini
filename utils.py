import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()

def ensure_directories():
    """Создание необходимых директорий"""
    directories = [
        "user_images",  # Директория для хранения изображений
        "exports",      # Директория для экспорта чатов
        "logs",         # Директория для логов
        "temp"          # Временная директория
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Директория {directory} создана или уже существует")

def format_timestamp(timestamp: int) -> str:
    """Форматирование временной метки в читаемый формат"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_file_size(file_path: str) -> str:
    """Получение размера файла в читаемом формате"""
    if not os.path.exists(file_path):
        return "0 B"
    
    size_bytes = os.path.getsize(file_path)
    
    # Конвертация в читаемый формат
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} PB"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Сокращение текста до указанной длины"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def estimate_tokens(text: str) -> int:
    """Примерная оценка количества токенов в тексте"""
    # Очень приблизительная оценка: ~4 символа на токен для латиницы,
    # ~2 символа для кириллицы и других нелатинских символов
    
    latin_chars = sum(1 for c in text if ord(c) < 128)
    other_chars = len(text) - latin_chars
    
    return latin_chars // 4 + other_chars // 2

def create_backup(backup_dir: str = "backups") -> str:
    """Создание резервной копии базы данных"""
    import sqlite3
    import shutil
    from datetime import datetime
    
    # Создаем директорию для резервных копий, если она не существует
    os.makedirs(backup_dir, exist_ok=True)
    
    # Формируем имя файла резервной копии
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")
    
    # Копируем файл базы данных
    try:
        shutil.copy2(config.DB_PATH, backup_file)
        logger.info(f"Резервная копия базы данных создана: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")
        return None

def rate_limit(user_id: int, action: str, limit_per_minute: int = 10) -> bool:
    """Ограничение частоты запросов для пользователя"""
    # Имя файла для хранения информации о запросах
    rate_limit_file = "rate_limits.json"
    
    # Загружаем текущие ограничения
    if os.path.exists(rate_limit_file):
        with open(rate_limit_file, "r") as f:
            try:
                rate_limits = json.load(f)
            except json.JSONDecodeError:
                rate_limits = {}
    else:
        rate_limits = {}
    
    # Ключ для пользователя и действия
    key = f"{user_id}_{action}"
    current_time = time.time()
    
    # Удаляем устаревшие запросы (старше 1 минуты)
    if key in rate_limits:
        rate_limits[key] = [t for t in rate_limits[key] if current_time - t < 60]
    else:
        rate_limits[key] = []
    
    # Проверяем, не превышен ли лимит
    if len(rate_limits[key]) >= limit_per_minute:
        return False
    
    # Добавляем текущий запрос
    rate_limits[key].append(current_time)
    
    # Сохраняем обновленные ограничения
    with open(rate_limit_file, "w") as f:
        json.dump(rate_limits, f)
    
    return True

def parse_time_string(time_str: str) -> Optional[int]:
    """Парсинг строки времени в UNIX-время"""
    formats = [
        "%H:%M",           # ЧЧ:ММ
        "%H:%M:%S",        # ЧЧ:ММ:СС
        "%d.%m.%Y %H:%M",  # ДД.ММ.ГГГГ ЧЧ:ММ
        "%Y-%m-%d %H:%M",  # ГГГГ-ММ-ДД ЧЧ:ММ
        "%d-%m-%Y %H:%M",  # ДД-ММ-ГГГГ ЧЧ:ММ
        "%d/%m/%Y %H:%M"   # ДД/ММ/ГГГГ ЧЧ:ММ
    ]
    
    # Текущая дата
    now = datetime.now()
    
    for fmt in formats:
        try:
            # Пытаемся распарсить время
            dt = datetime.strptime(time_str, fmt)
            
            # Если формат не содержит дату, используем текущую дату
            if "%d" not in fmt:
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            
            # Если время уже прошло, добавляем 1 день
            if dt < now and "%d" not in fmt:
                dt = dt.replace(day=dt.day + 1)
            
            # Возвращаем UNIX-время
            return int(dt.timestamp())
        except ValueError:
            continue
    
    return None

def sanitize_filename(filename: str) -> str:
    """Санитизация имени файла"""
    # Заменяем недопустимые символы
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ограничиваем длину
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext) - 3] + "..."
        filename = name + ext
    
    return filename
