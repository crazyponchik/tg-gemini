import logging
import os
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ai_client import AIClient
from database import (
    get_user, create_or_update_user, add_message, get_chat_history,
    clear_chat_history, export_chat_history, add_scheduled_message
)
from config import load_config, config

logger = logging.getLogger(__name__)
config = load_config()

async def handle_text_message(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    summarize: bool = False,
    export: bool = False,
    clear: bool = False,
    change_mode: bool = False,
    template: bool = False,
    schedule: bool = False,
    voice: bool = False
) -> None:
    """Обработка текстовых сообщений"""
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
    
    # Обработка специальных команд
    if summarize:
        await handle_summary(update, context)
        return
    elif export:
        await handle_export(update, context)
        return
    elif clear:
        await handle_clear_history(update, context)
        return
    elif change_mode:
        await handle_change_mode(update, context)
        return
    elif template:
        await handle_template(update, context)
        return
    elif schedule:
        await handle_schedule(update, context)
        return
    
    # Если это голосовое сообщение, сначала его нужно преобразовать в текст
    if voice:
        voice_file = await update.message.voice.get_file()
        voice_path = f"temp_voice_{user.id}_{int(time.time())}.ogg"
        await voice_file.download_to_drive(voice_path)
        
        # Здесь должен быть код для преобразования голоса в текст
        # Можно использовать библиотеку SpeechRecognition или Whisper API
        # Для примера просто сообщаем, что функция в разработке
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎤 Получено голосовое сообщение. Функция преобразования голоса в текст находится в разработке."
        )
        
        # Удаляем временный файл
        if os.path.exists(voice_path):
            os.remove(voice_path)
        
        return
    
    # Получаем текст сообщения
    message_text = update.message.text
    
    # Отправляем индикатор набора текста
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Добавляем сообщение пользователя в историю
    add_message(
        user_id=user.id,
        role="user",
        content=message_text,
        message_type="text"
    )
    
    # Получаем историю чата для контекста
    chat_history = get_chat_history(user.id, limit=10)
    
    # Инициализируем клиент AI
    ai_client = AIClient()
    
    # Получаем системный промпт для текущего режима разговора
    conversation_mode = settings.get('conversation_mode', 'friendly')
    system_prompt = config.CONVERSATION_MODES[conversation_mode]["system_prompt"]
    
    # Добавляем системное сообщение в начало истории
    system_message = {
        "role": "system",
        "content": [{"type": "text", "text": system_prompt}]
    }
    
    messages = [system_message] + chat_history
    
    # Генерируем ответ от AI
    response = ai_client.generate_response(
        user_id=user.id,
        messages=messages,
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

async def handle_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /summary"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Получаем историю чата
    chat_history = get_chat_history(user.id, limit=20)
    
    if not chat_history:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Нет истории чата для суммирования."
        )
        return
    
    # Отправляем индикатор набора текста
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Получаем настройки пользователя
    user_info = get_user(user.id)
    settings = user_info.get('settings', {})
    
    # Преобразуем историю в текст для суммирования
    history_text = ""
    for msg in chat_history:
        role = msg.get("role", "")
        content = msg.get("content", [])
        
        if role == "user":
            author = "Пользователь"
        elif role == "assistant":
            author = "Ассистент"
        else:
            continue
        
        # Извлекаем текст из содержимого
        text = ""
        for item in content:
            if item.get("type") == "text":
                text += item.get("text", "")
        
        history_text += f"{author}: {text}\n\n"
    
    # Формируем промпт для суммирования
    summary_prompt = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Ты аналитический ассистент. Твоя задача - кратко суммировать ключевые моменты разговора."}]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": f"Пожалуйста, суммируй следующий разговор:\n\n{history_text}"}]
        }
    ]
    
    # Инициализируем клиент AI
    ai_client = AIClient()
    
    # Генерируем суммирование
    summary = ai_client.generate_response(
        user_id=user.id,
        messages=summary_prompt,
        model=settings.get('model', config.DEFAULT_MODEL),
        temperature=0.3,  # Используем низкую температуру для точности
        max_tokens=500  # Ограничиваем длину суммирования
    )
    
    if summary:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 *Суммирование разговора:*\n\n{summary}",
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="😔 Извините, не удалось суммировать разговор. Пожалуйста, попробуйте еще раз."
        )

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /export"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Создаем клавиатуру с форматами экспорта
    keyboard = [
        [
            InlineKeyboardButton("Текст (TXT)", callback_data="export_text"),
            InlineKeyboardButton("JSON", callback_data="export_json")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Выберите формат для экспорта истории чата:",
        reply_markup=reply_markup
    )

async def handle_clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /clear"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, очистить", callback_data="clear_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="⚠️ Вы уверены, что хотите очистить всю историю чата? Это действие нельзя отменить.",
        reply_markup=reply_markup
    )

async def handle_change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /mode"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Создаем клавиатуру с режимами
    keyboard = []
    row = []
    
    for i, (mode_name, mode_info) in enumerate(config.CONVERSATION_MODES.items()):
        if i > 0 and i % 2 == 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(
            mode_info["description"], 
            callback_data=f"mode_{mode_name}"
        ))
    
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Получаем текущий режим
    user_info = get_user(user.id)
    settings = user_info.get('settings', {})
    current_mode = settings.get('conversation_mode', 'friendly')
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Текущий режим: *{config.CONVERSATION_MODES[current_mode]['description']}*\n\nВыберите новый режим общения:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /template"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверяем, есть ли аргументы
    args = context.args
    
    if not args:
        # Отображаем список доступных шаблонов
        template_list = "\n".join([
            f"• *{name}*: {template[:50]}..." 
            for name, template in config.TEMPLATES.items()
        ])
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 Доступные шаблоны:\n\n{template_list}\n\nИспользование: /template [название]",
            parse_mode="Markdown"
        )
        return
    
    template_name = args[0].lower()
    
    if template_name == "list":
        # Отображаем полный список шаблонов
        template_list = "\n\n".join([
            f"*{name}*:\n{template}" 
            for name, template in config.TEMPLATES.items()
        ])
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 Шаблоны:\n\n{template_list}",
            parse_mode="Markdown"
        )
        return
    
    # Проверяем, существует ли такой шаблон
    if template_name not in config.TEMPLATES:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Шаблон '{template_name}' не найден. Используйте /template list для просмотра доступных шаблонов."
        )
        return
    
    # Создаем клавиатуру для ввода текста
    keyboard = [
        [
            InlineKeyboardButton("Отмена", callback_data=f"template_cancel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Сохраняем выбранный шаблон в контексте
    context.user_data["selected_template"] = template_name
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Выбран шаблон '*{template_name}*'.\n\nВведите текст для обработки:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /schedule"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверяем, есть ли аргументы
    args = context.args
    
    if not args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ *Планирование сообщений*\n\n"
                 "Вы можете запланировать сообщение, указав время и текст.\n\n"
                 "Формат: /schedule [время в формате ЧЧ:ММ] [текст сообщения]\n\n"
                 "Пример: /schedule 15:30 Напомни про встречу",
            parse_mode="Markdown"
        )
        return
    
    # Если передан только один аргумент (время), то ожидаем ввод текста
    if len(args) == 1:
        time_str = args[0]
        
        # Проверяем формат времени
        try:
            scheduled_time = datetime.strptime(time_str, "%H:%M")
            
            # Получаем текущее время и устанавливаем нужные часы и минуты
            now = datetime.now()
            scheduled_datetime = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=scheduled_time.hour,
                minute=scheduled_time.minute
            )
            
            # Если время уже прошло, добавляем 1 день
            if scheduled_datetime < now:
                scheduled_datetime = scheduled_datetime.replace(day=scheduled_datetime.day + 1)
            
            # Сохраняем время в контексте пользователя
            context.user_data["scheduled_time"] = int(scheduled_datetime.timestamp())
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Время установлено на *{time_str}*. Теперь введите текст сообщения:",
                parse_mode="Markdown"
            )
            
        except ValueError:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Неверный формат времени. Используйте формат ЧЧ:ММ, например, 15:30"
            )
        
        return
    
    # Если передано время и текст сообщения
    time_str = args[0]
    message_text = " ".join(args[1:])
    
    # Проверяем формат времени
    try:
        scheduled_time = datetime.strptime(time_str, "%H:%M")
        
        # Получаем текущее время и устанавливаем нужные часы и минуты
        now = datetime.now()
        scheduled_datetime = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=scheduled_time.hour,
            minute=scheduled_time.minute
        )
        
        # Если время уже прошло, добавляем 1 день
        if scheduled_datetime < now:
            scheduled_datetime = scheduled_datetime.replace(day=scheduled_datetime.day + 1)
        
        # Добавляем запланированное сообщение
        scheduled_time_unix = int(scheduled_datetime.timestamp())
        
        message_id = add_scheduled_message(
            user_id=user.id,
            content=message_text,
            scheduled_time=scheduled_time_unix
        )
        
        local_time_str = scheduled_datetime.strftime("%H:%M")
        date_str = scheduled_datetime.strftime("%d.%m.%Y")
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Сообщение запланировано на *{date_str}* в *{local_time_str}*.\n\n"
                 f"Текст сообщения: {message_text}",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Неверный формат времени. Используйте формат ЧЧ:ММ, например, 15:30"
        )
