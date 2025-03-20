import os
import logging
import tempfile
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, add_message
from ai_client import AIClient
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()

async def process_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Обработка голосового сообщения и преобразование его в текст
    
    Args:
        update: Объект Update из Telegram
        context: Контекст бота
    
    Returns:
        Распознанный текст или None в случае ошибки
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Получаем голосовое сообщение
        voice = update.message.voice
        voice_file = await voice.get_file()
        
        # Создаем временный файл для голосового сообщения
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
            ogg_file_path = temp_ogg.name
        
        # Скачиваем голосовое сообщение
        await voice_file.download_to_drive(ogg_file_path)
        
        # Конвертируем ogg в wav для распознавания
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wav_file_path = temp_wav.name
        
        # Используем pydub для конвертации
        audio = AudioSegment.from_ogg(ogg_file_path)
        audio.export(wav_file_path, format="wav")
        
        # Инициализируем распознаватель
        recognizer = sr.Recognizer()
        
        # Получаем настройки пользователя
        user_info = get_user(user.id)
        settings = user_info.get('settings', {})
        language = settings.get('language', 'ru')
        
        # Карта языковых кодов для распознавания речи
        language_map = {
            'ru': 'ru-RU',
            'en': 'en-US',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'de': 'de-DE',
            'zh': 'zh-CN'
        }
        
        speech_lang = language_map.get(language, 'ru-RU')
        
        # Распознаем речь
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=speech_lang)
        
        # Очистка временных файлов
        os.remove(ogg_file_path)
        os.remove(wav_file_path)
        
        logger.info(f"Голосовое сообщение от пользователя {user.id} распознано: {text}")
        
        return text
    
    except sr.UnknownValueError:
        logger.warning(f"Не удалось распознать речь от пользователя {user.id}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎤 Извините, не удалось распознать речь. Пожалуйста, попробуйте снова."
        )
    except sr.RequestError as e:
        logger.error(f"Ошибка при запросе к сервису распознавания речи: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎤 Извините, возникла ошибка при обращении к сервису распознавания речи."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎤 Произошла ошибка при обработке голосового сообщения."
        )
    finally:
        # Удаляем временные файлы, если они существуют
        for file_path in [ogg_file_path, wav_file_path]:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
    
    return None

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Основной обработчик голосовых сообщений
    
    Args:
        update: Объект Update из Telegram
        context: Контекст бота
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Отправляем сообщение о начале обработки
    processing_message = await context.bot.send_message(
        chat_id=chat_id,
        text="🎤 Распознаю голосовое сообщение..."
    )
    
    # Преобразуем голосовое сообщение в текст
    recognized_text = await process_voice_message(update, context)
    
    if not recognized_text:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_message.message_id,
            text="❌ Не удалось распознать голосовое сообщение."
        )
        return
    
    # Удаляем сообщение о распознавании
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=processing_message.message_id
    )
    
    # Отправляем распознанный текст
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎤 Распознанный текст: {recognized_text}"
    )
    
    # Добавляем текст в историю сообщений
    add_message(
        user_id=user.id,
        role="user",
        content=recognized_text,
        message_type="voice"
    )
    
    # Отправляем индикатор набора текста
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Получаем настройки пользователя
    user_info = get_user(user.id)
    settings = user_info.get('settings', {})
    
    # Инициализируем клиент AI
    ai_client = AIClient()
    
    # Генерируем ответ от AI
    response = ai_client.generate_response(
        user_id=user.id,
        messages=[{
            "role": "user",
            "content": [{"type": "text", "text": recognized_text}]
        }],
        model=settings.get('model', config.DEFAULT_MODEL),
        temperature=settings.get('temperature', config.DEFAULT_TEMP),
        max_tokens=settings.get('max_tokens', config.DEFAULT_MAX_TOKENS)
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
            text="😔 Извините, произошла ошибка при генерации ответа. Пожалуйста, попробуйте еще раз."
        )
