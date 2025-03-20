import os
import json
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class Config:
    TELEGRAM_TOKEN: str
    OPENROUTER_API_KEY: str
    DEFAULT_MODEL: str = "google/gemini-2.0-pro-exp-02-05:free"
    DEFAULT_TEMP: float = 0.7
    DEFAULT_MAX_TOKENS: int = 1000
    DB_PATH: str = "bot_data.db"
    
    # Конфигурация для дополнительных функций
    AVAILABLE_MODELS: list = None
    CONVERSATION_MODES: dict = None
    TEMPLATES: dict = None
    
    def __post_init__(self):
        self.AVAILABLE_MODELS = [
            "google/gemini-2.0-pro-exp-02-05:free",
            "anthropic/claude-3-haiku:free",
            "anthropic/claude-3-opus:free",
            "anthropic/claude-3-sonnet:free",
            "meta-llama/llama-3-70b-instruct:free",
            "mistralai/mistral-large:free"
        ]
        
        self.CONVERSATION_MODES = {
            "creative": {
                "description": "Творческий режим для генерации идей",
                "system_prompt": "Ты креативный ассистент. Предлагай необычные и оригинальные идеи.",
                "temperature": 0.9
            },
            "analytical": {
                "description": "Аналитический режим для решения задач",
                "system_prompt": "Ты аналитический ассистент. Анализируй информацию глубоко и точно.",
                "temperature": 0.2
            },
            "concise": {
                "description": "Лаконичный режим для кратких ответов",
                "system_prompt": "Ты лаконичный ассистент. Отвечай кратко и по существу.",
                "temperature": 0.5
            },
            "friendly": {
                "description": "Дружелюбный режим для неформального общения",
                "system_prompt": "Ты дружелюбный ассистент. Общаешься в неформальном тоне, используешь эмодзи.",
                "temperature": 0.8
            },
            "expert": {
                "description": "Экспертный режим для глубоких знаний",
                "system_prompt": "Ты эксперт. Предоставляешь подробные и глубокие объяснения.",
                "temperature": 0.3
            }
        }
        
        self.TEMPLATES = {
            "summary": "Кратко изложи основные моменты следующего текста: {text}",
            "explain": "Объясни простыми словами: {text}",
            "code_review": "Проанализируй этот код и предложи улучшения: {text}",
            "translate_en": "Переведи на английский: {text}",
            "translate_ru": "Переведи на русский: {text}",
            "brainstorm": "Предложи 5 идей на тему: {text}"
        }

def load_config():
    """Загрузка конфигурации из переменных окружения и файлов"""
    load_dotenv()
    
    config = Config(
        TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN"),
        OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
    )
    
    # Загрузка пользовательских настроек из файла если он существует
    user_config_path = "user_config.json"
    if os.path.exists(user_config_path):
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            
            if "DEFAULT_MODEL" in user_config:
                config.DEFAULT_MODEL = user_config["DEFAULT_MODEL"]
            if "DEFAULT_TEMP" in user_config:
                config.DEFAULT_TEMP = user_config["DEFAULT_TEMP"]
            if "DEFAULT_MAX_TOKENS" in user_config:
                config.DEFAULT_MAX_TOKENS = user_config["DEFAULT_MAX_TOKENS"]
                
            # Загрузка пользовательских шаблонов
            if "TEMPLATES" in user_config:
                config.TEMPLATES.update(user_config["TEMPLATES"])
    
    return config

def save_user_config(updated_config):
    """Сохранение пользовательских настроек в файл"""
    user_config = {
        "DEFAULT_MODEL": updated_config.DEFAULT_MODEL,
        "DEFAULT_TEMP": updated_config.DEFAULT_TEMP,
        "DEFAULT_MAX_TOKENS": updated_config.DEFAULT_MAX_TOKENS,
        "TEMPLATES": updated_config.TEMPLATES
    }
    
    with open("user_config.json", "w", encoding="utf-8") as f:
        json.dump(user_config, f, ensure_ascii=False, indent=2)
