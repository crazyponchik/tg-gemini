import logging
import os
import time
from telegram import Update
from telegram.ext import ContextTypes
from ai_client import AIClient
from database import (
    get_user, create_or_update_user, add_message,
    add_media, get_chat_history
)
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка сообщений с изображениями"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Создаем или обновляем пользователя
    create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Получаем настройки пользователя
    user_info = get_user(user.id)
    settings = user_info.get('settings', {})
    
    # Отправляем сообщение о начале обработки
    processing_message = await context.bot.send_message(
        chat_id=chat_id,
        text="🖼️ Обрабатываю изображение..."
    )
    
    # Получаем объект фото с максимальным разрешением
    photo = update.message.photo[-1]
    
    # Получаем файл фото
    photo_file = await photo.get_file()
    
    # Создаем директорию для изображений, если её нет
    images_dir = "user_images"
    os.makedirs(images_dir, exist_ok=True)
    
    # Формируем имя файла и путь
    file_name = f"{user.id}_{int(time.time())}_{photo.file_unique_id}.jpg"
    file_path = os.path.join(images_dir, file_name)
    
    # Скачиваем изображение
    await photo_file.download_to_drive(file_path)
    
    # Добавляем медиафайл в базу данных
    media_id = add_media(
        user_id=user.id,
        file_id=photo.file_id,
        file_unique_id=photo.file_unique_id,
        file_path=file_path,
        media_type="image",
        processed_text=file_path
    )
    
    # Извлекаем текст из описания к изображению (если есть)
    caption_text = update.message.caption or "Что на этом изображении?"
    
    # Добавляем сообщение пользователя в историю
    add_message(
        user_id=user.id,
        role="user",
        content=caption_text,
        message_type="image",
        media_id=photo.file_unique_id
    )
    
    # Инициализируем клиент AI
    ai_client = AIClient()
    
    # Формируем URL для изображения (локальный путь, но можно использовать и внешний URL)
    image_url = f"file://{file_path}"
    
    # Обрабатываем изображение
    response = ai_client.process_image(
        user_id=user.id,
        image_url=image_url,
        prompt=caption_text,
        model=settings.get('model', config.DEFAULT_MODEL),
        temperature=settings.get('temperature', config.DEFAULT_TEMP)
    )
    
    # Редактируем сообщение о начале обработки
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=processing_message.message_id
    )
    
    if response:
        # Добавляем ответ в историю
        add_message(
            user_id=user.id,
            role="assistant",
            content=response,
            message_type="text"
        )
        
        # Отправляем ответ пользователю
        await context.bot.send_message(chat_id=chat_id, text=response)
    else:
        # В случае ошибки
        await context.bot.send_message(
            chat_id=chat_id,
            text="😔 Извините, не удалось обработать изображение. Пожалуйста, попробуйте еще раз."
        )
