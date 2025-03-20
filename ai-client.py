import requests
import json
import logging
from typing import List, Dict, Any, Optional
from config import load_config
from database import add_usage_stats

logger = logging.getLogger(__name__)
config = load_config()

class AIClient:
    """Клиент для работы с OpenRouter API"""
    
    def __init__(self, api_key: str = None):
        """Инициализация клиента"""
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
    
    def generate_response(self, 
                         user_id: int,
                         messages: List[Dict], 
                         model: str = None, 
                         temperature: float = None,
                         max_tokens: int = None) -> Optional[str]:
        """
        Генерация ответа на основе сообщений
        
        Args:
            user_id: ID пользователя для статистики
            messages: Список сообщений
            model: Модель для генерации ответа
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов
            
        Returns:
            Сгенерированный ответ или None в случае ошибки
        """
        model = model or config.DEFAULT_MODEL
        temperature = temperature if temperature is not None else config.DEFAULT_TEMP
        max_tokens = max_tokens or config.DEFAULT_MAX_TOKENS
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Сохраняем статистику использования
            if "usage" in result and "total_tokens" in result["usage"]:
                add_usage_stats(
                    user_id=user_id,
                    model=model,
                    tokens_used=result["usage"]["total_tokens"],
                    request_type="chat"
                )
            
            # Извлекаем текст ответа
            if "choices" in result and len(result["choices"]) > 0:
                if "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                    return result["choices"][0]["message"]["content"]
            
            logger.error(f"Неожиданный формат ответа: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса к OpenRouter API: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при декодировании ответа от OpenRouter API: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при генерации ответа: {e}")
            return None
    
    def process_image(self, 
                     user_id: int,
                     image_url: str, 
                     prompt: str = "Что на этом изображении?",
                     model: str = None, 
                     temperature: float = None) -> Optional[str]:
        """
        Обработка изображения
        
        Args:
            user_id: ID пользователя для статистики
            image_url: URL изображения
            prompt: Текстовый запрос к изображению
            model: Модель для обработки изображения
            temperature: Температура генерации (0.0-1.0)
            
        Returns:
            Текстовый результат обработки изображения или None в случае ошибки
        """
        model = model or config.DEFAULT_MODEL
        temperature = temperature if temperature is not None else config.DEFAULT_TEMP
        
        # Проверяем, поддерживает ли модель работу с изображениями
        # Для примера: модели Gemini, Claude поддерживают мультимодальные входы
        if not self._model_supports_images(model):
            logger.warning(f"Модель {model} не поддерживает обработку изображений. Используем gemini-pro-vision")
            model = "google/gemini-2.0-pro-exp-02-05:free"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Сохраняем статистику использования
            if "usage" in result and "total_tokens" in result["usage"]:
                add_usage_stats(
                    user_id=user_id,
                    model=model,
                    tokens_used=result["usage"]["total_tokens"],
                    request_type="image"
                )
            
            # Извлекаем текст ответа
            if "choices" in result and len(result["choices"]) > 0:
                if "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                    return result["choices"][0]["message"]["content"]
            
            logger.error(f"Неожиданный формат ответа: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса к OpenRouter API: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при декодировании ответа от OpenRouter API: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке изображения: {e}")
            return None
    
    def _model_supports_images(self, model: str) -> bool:
        """Проверка поддержки обработки изображений моделью"""
        # Примерный список моделей, которые поддерживают обработку изображений
        vision_models = [
            "google/gemini-2.0-pro-exp-02-05",
            "google/gemini-pro-vision",
            "anthropic/claude-3",
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet"
        ]
        
        return any(model.startswith(vm) for vm in vision_models)
