#!/usr/bin/env python
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import load_config
from handlers.command_handler import start_command, help_command, settings_command, stats_command
from handlers.text_handler import handle_text_message
from handlers.image_handler import handle_image_message
from handlers.callback_handler import handle_callback_query
from database import init_db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("summary", lambda update, context: handle_text_message(update, context, summarize=True)))
    application.add_handler(CommandHandler("export", lambda update, context: handle_text_message(update, context, export=True)))
    application.add_handler(CommandHandler("clear", lambda update, context: handle_text_message(update, context, clear=True)))
    application.add_handler(CommandHandler("mode", lambda update, context: handle_text_message(update, context, change_mode=True)))
    application.add_handler(CommandHandler("template", lambda update, context: handle_text_message(update, context, template=True)))
    application.add_handler(CommandHandler("schedule", lambda update, context: handle_text_message(update, context, schedule=True)))
    
    # Обработчик callback-запросов (для inline-кнопок)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))
    application.add_handler(MessageHandler(filters.VOICE, lambda update, context: handle_text_message(update, context, voice=True)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
