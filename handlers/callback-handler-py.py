import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, update_user_settings, clear_chat_history, export_chat_history
)
from config import load_config, config

logger = logging.getLogger(__name__)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-запросов от inline-кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    callback_data = query.data
    
    # Обработка настроек
    if callback_data.startswith("settings_"):
        setting_type = callback_data.split("_")[1]
        await handle_settings_callback(update, context, setting_type)
    
    # Обработка выбора модели
    elif callback_data.startswith("model_"):
        model_name = callback_data.replace("model_", "")
        await handle_model_selection(update, context, model_name)
    
    # Обработка выбора температуры
    elif callback_data.startswith("temp_"):
        temp_value = float(callback_data.replace("temp_", ""))
        await handle_temperature_selection(update, context, temp_value)
    
    # Обработка выбора максимального количества токенов
    elif callback_data.startswith("tokens_"):
        tokens_value = int(callback_data.replace("tokens_", ""))
        await handle_tokens_selection(update, context, tokens_value)
    
    # Обработка выбора режима разговора
    elif callback_data.startswith("mode_"):
        mode_name = callback_data.replace("mode_", "")
        await handle_mode_selection(update, context, mode_name)
    
    # Обработка выбора языка
    elif callback_data.startswith("lang_"):
        lang_code = callback_data.replace("lang_", "")
        await handle_language_selection(update, context, lang_code)
    
    # Обработка экспорта истории чата
    elif callback_data.startswith("export_"):
        format_type = callback_data.replace("export_", "")
        await handle_export_confirmation(update, context, format_type)
    
    # Обработка подтверждения очистки истории
    elif callback_data == "clear_confirm":
        await handle_clear_confirmation(update, context)
    
    # Обработка отмены очистки истории
    elif callback_data == "clear_cancel":
        await query.edit_message_text(text="❌ Очистка истории отменена.")
    
    # Обработка отмены шаблона
    elif callback_data == "template_cancel":
        if "selected_template" in context.user_data:
            del context.user_data["selected_template"]
        await query.edit_message_text(text="❌ Использование шаблона отменено.")
    
    # Вернуться в меню настроек
    elif callback_data == "back_to_settings":
        await handle_back_to_settings(update, context)

async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, setting_type: str) -> None:
    """Обработка callback-запросов для настроек"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if setting_type == "model":
        # Отображаем доступные модели
        keyboard = []
        for model in config.AVAILABLE_MODELS:
            # Делаем короткие имена для моделей
            model_short = model.split("/")[-1].split(":")[0]
            keyboard.append([InlineKeyboardButton(model_short, callback_data=f"model_{model}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите модель:",
            reply_markup=reply_markup
        )
    
    elif setting_type == "temp":
        # Отображаем варианты температуры
        keyboard = [
            [
                InlineKeyboardButton("0.1", callback_data="temp_0.1"),
                InlineKeyboardButton("0.3", callback_data="temp_0.3"),
                InlineKeyboardButton("0.5", callback_data="temp_0.5")
            ],
            [
                InlineKeyboardButton("0.7", callback_data="temp_0.7"),
                InlineKeyboardButton("0.9", callback_data="temp_0.9"),
                InlineKeyboardButton("1.0", callback_data="temp_1.0")
            ],
            [InlineKeyboardButton("Назад", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите температуру (низкая - более точные ответы, высокая - более творческие):",
            reply_markup=reply_markup
        )
    
    elif setting_type == "tokens":
        # Отображаем варианты максимального количества токенов
        keyboard = [
            [
                InlineKeyboardButton("500", callback_data="tokens_500"),
                InlineKeyboardButton("1000", callback_data="tokens_1000"),
                InlineKeyboardButton("1500", callback_data="tokens_1500")
            ],
            [
                InlineKeyboardButton("2000", callback_data="tokens_2000"),
                InlineKeyboardButton("3000", callback_data="tokens_3000"),
                InlineKeyboardButton("4000", callback_data="tokens_4000")
            ],
            [InlineKeyboardButton("Назад", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите максимальное количество токенов (влияет на длину ответа):",
            reply_markup=reply_markup
        )
    
    elif setting_type == "mode":
        # Отображаем варианты режимов разговора
        keyboard = []
        for mode_name, mode_info in config.CONVERSATION_MODES.items():
            keyboard.append([InlineKeyboardButton(mode_info["description"], callback_data=f"mode_{mode_name}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите режим разговора:",
            reply_markup=reply_markup
        )
    
    elif setting_type == "language":
        # Отображаем варианты языков
        keyboard = [
            [
                InlineKeyboardButton("Русский", callback_data="lang_ru"),
                InlineKeyboardButton("English", callback_data="lang_en")
            ],
            [
                InlineKeyboardButton("Español", callback_data="lang_es"),
                InlineKeyboardButton("Français", callback_data="lang_fr")
            ],
            [
                InlineKeyboardButton("Deutsch", callback_data="lang_de"),
                InlineKeyboardButton("中文", callback_data="lang_zh")
            ],
            [InlineKeyboardButton("Назад", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите язык интерфейса:",
            reply_markup=reply_markup
        )

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, model_name: str) -> None:
    """Обработка выбора модели"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Обновляем настройки пользователя
    update_user_settings(user_id, {"model": model_name})
    
    # Получаем короткое имя модели для отображения
    model_short = model_name.split("/")[-1].split(":")[0]
    
    await query.edit_message_text(
        text=f"✅ Модель изменена на: {model_short}"
    )

async def handle_temperature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_value: float) -> None:
    """Обработка выбора температуры"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Обновляем настройки пользователя
    update_user_settings(user_id, {"temperature": temp_value})
    
    await query.edit_message_text(
        text=f"✅ Температура изменена на: {temp_value}"
    )

async def handle_tokens_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, tokens_value: int) -> None:
    """Обработка выбора максимального количества токенов"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Обновляем настройки пользователя
    update_user_settings(user_id, {"max_tokens": tokens_value})
    
    await query.edit_message_text(
        text=f"✅ Максимальное количество токенов изменено на: {tokens_value}"
    )

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, mode_name: str) -> None:
    """Обработка выбора режима разговора"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Обновляем настройки пользователя
    update_user_settings(user_id, {"conversation_mode": mode_name})
    
    mode_description = config.CONVERSATION_MODES[mode_name]["description"]
    
    await query.edit_message_text(
        text=f"✅ Режим разговора изменен на: {mode_description}"
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str) -> None:
    """Обработка выбора языка"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Обновляем настройки пользователя
    update_user_settings(user_id, {"language": lang_code})
    
    lang_names = {
        "ru": "Русский",
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "zh": "中文"
    }
    
    lang_name = lang_names.get(lang_code, lang_code)
    
    await query.edit_message_text(
        text=f"✅ Язык изменен на: {lang_name}"
    )

async def handle_back_to_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат к меню настроек"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Получаем информацию о пользователе
    user_info = get_user(user_id)
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
    
    await query.edit_message_text(
        text=current_settings,
        reply_markup=reply_markup
    )

async def handle_export_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str) -> None:
    """Обработка подтверждения экспорта истории чата"""
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Экспортируем историю чата
    history_text = export_chat_history(user_id, format_type)
    
    # Формируем имя файла
    file_name = f"chat_history_{user_id}_{format_type}.{'txt' if format_type == 'text' else format_type}"
    
    # Сохраняем историю в файл
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(history_text)
    
    # Отправляем файл пользователю
    with open(file_name, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id,
            document=f,
            filename=file_name,
            caption="📤 Экспорт истории чата"
        )
    
    # Удаляем временный файл
    import os
    os.remove(file_name)
    
    await query.edit_message_text(
        text=f"✅ История чата успешно экспортирована в формате {format_type.upper()}"
    )

async def handle_clear_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка подтверждения очистки истории чата"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Очищаем историю чата
    clear_chat_history(user_id)
    
    await query.edit_message_text(
        text="✅ История чата успешно очищена"
    )
