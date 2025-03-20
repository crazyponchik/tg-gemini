import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import load_config
from database import get_user, create_or_update_user, update_user_settings, get_user_stats

logger = logging.getLogger(__name__)
config = load_config()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Создаем или обновляем информацию о пользователе
    create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = (
        f"👋 Привет, {user.first_name}! Я OpenRouter AI Telegram Bot.\n\n"
        "Я могу общаться с вами, отвечать на вопросы и даже анализировать изображения!\n\n"
        "🤖 Возможности:\n"
        "• Обработка текстовых сообщений\n"
        "• Анализ изображений\n"
        "• Различные режимы общения\n"
        "• Сохранение истории диалога\n"
        "• Персонализированные настройки\n\n"
        "Команды:\n"
        "/help - Показать справку\n"
        "/settings - Настройки бота\n"
        "/stats - Статистика использования\n"
        "/summary - Суммировать разговор\n"
        "/export - Экспортировать историю чата\n"
        "/clear - Очистить историю чата\n"
        "/mode - Изменить режим общения\n"
        "/schedule - Запланировать сообщение\n"
        "/template - Управление шаблонами\n\n"
        "🚀 Просто напишите мне сообщение или отправьте изображение, и я помогу вам!"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    chat_id = update.effective_chat.id
    
    help_text = (
        "🤖 Список доступных команд:\n\n"
        "/start - Начать диалог с ботом\n"
        "/help - Показать эту справку\n"
        "/settings - Настройки бота\n"
        "/stats - Статистика использования\n"
        "/summary - Суммировать текущий разговор\n"
        "/export - Экспортировать историю чата\n"
        "/clear - Очистить историю чата\n"
        "/mode - Изменить режим общения\n"
        "/template <название> - Использовать шаблон\n"
        "/schedule - Запланировать сообщение\n\n"
        "💡 Особенности:\n"
        "• Отправьте текстовое сообщение для обычного общения\n"
        "• Отправьте изображение для его анализа\n"
        "• Отправьте голосовое сообщение для его обработки\n\n"
        "📝 Режимы общения:\n"
        "• creative - Творческий режим для генерации идей\n"
        "• analytical - Аналитический режим для решения задач\n"
        "• concise - Лаконичный режим для кратких ответов\n"
        "• friendly - Дружелюбный режим для неформального общения\n"
        "• expert - Экспертный режим для подробных объяснений\n\n"
        "✨ Для доступа к шаблонам используйте команду /template list"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=help_text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /settings"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Получаем информацию о пользователе
    user_info = get_user(user.id)
    if not user_info:
        create_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        user_info = get_user(user.id)
    
    settings = user_info.get('settings', {})
    
    # Создаем клавиатуру с настройками
    keyboard = [
        [
            InlineKeyboardButton("Модель", callback_data="settings_model"),
            InlineKeyboardButton("Температура", callback_data="settings_temp")
        ],
        [
            InlineKeyboardButton("Макс. токенов", callback_data="settings_tokens"),
            InlineKeyboardButton("Режим", callback_data="settings_mode")
        ],
        [
            InlineKeyboardButton("Язык", callback_data="settings_language")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_settings = (
        "⚙️ Текущие настройки:\n\n"
        f"🤖 Модель: {settings.get('model', config.DEFAULT_MODEL)}\n"
        f"🌡️ Температура: {settings.get('temperature', config.DEFAULT_TEMP)}\n"
        f"📊 Макс. токенов: {settings.get('max_tokens', config.DEFAULT_MAX_TOKENS)}\n"
        f"🔄 Режим: {settings.get('conversation_mode', 'friendly')}\n"
        f"🌐 Язык: {settings.get('language', 'ru')}\n\n"
        "Выберите параметр для изменения:"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=current_settings,
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /stats"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Получаем статистику пользователя
    stats = get_user_stats(user.id)
    
    if not stats:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Статистика не найдена. Попробуйте пообщаться с ботом сначала."
        )
        return
    
    # Форматируем статистику по моделям
    models_text = "Нет данных"
    if stats.get("tokens_by_model"):
        models_text = "\n".join([
            f"  • {model}: {tokens} токенов" 
            for model, tokens in stats["tokens_by_model"].items()
        ])
    
    # Форматируем статистику по типам запросов
    requests_text = "Нет данных"
    if stats.get("requests_by_type"):
        requests_text = "\n".join([
            f"  • {req_type}: {count} запросов" 
            for req_type, count in stats["requests_by_type"].items()
        ])
    
    # Форматируем статистику по дням недели
    day_map = {
        "0": "Воскресенье",
        "1": "Понедельник",
        "2": "Вторник",
        "3": "Среда",
        "4": "Четверг",
        "5": "Пятница", 
        "6": "Суббота"
    }
    
    activity_text = "Нет данных"
    if stats.get("activity_by_day"):
        activity_text = "\n".join([
            f"  • {day_map.get(day, day)}: {count} сообщений" 
            for day, count in sorted(stats["activity_by_day"].items())
        ])
    
    stats_text = (
        "📊 Статистика использования бота:\n\n"
        f"💬 Всего сообщений: {stats.get('message_count', 0)}\n\n"
        f"🤖 Использование моделей:\n{models_text}\n\n"
        f"🔄 Типы запросов:\n{requests_text}\n\n"
        f"📅 Активность по дням недели:\n{activity_text}\n\n"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=stats_text)
