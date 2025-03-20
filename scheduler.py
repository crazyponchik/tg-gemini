import logging
import time
import threading
from telegram.ext import Application
from database import get_pending_scheduled_messages, mark_scheduled_message_sent
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()

class MessageScheduler:
    """Планировщик сообщений"""
    
    def __init__(self, application: Application, check_interval: int = 60):
        """Инициализация планировщика"""
        self.application = application
        self.check_interval = check_interval
        self.is_running = False
        self.thread = None
    
    def start(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Планировщик сообщений запущен")
    
    def stop(self):
        """Остановка планировщика"""
        if not self.is_running:
            logger.warning("Планировщик не запущен")
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Планировщик сообщений остановлен")
    
    def _run(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                self._process_scheduled_messages()
            except Exception as e:
                logger.error(f"Ошибка при обработке запланированных сообщений: {e}")
            
            # Пауза перед следующей проверкой
            time.sleep(self.check_interval)
    
    def _process_scheduled_messages(self):
        """Обработка запланированных сообщений"""
        # Получаем список запланированных сообщений, которые нужно отправить
        pending_messages = get_pending_scheduled_messages()
        
        for message in pending_messages:
            try:
                # Отправляем сообщение
                self.application.create_task(
                    self._send_scheduled_message(
                        user_id=message["user_id"],
                        content=message["content"]
                    )
                )
                
                # Отмечаем сообщение как отправленное
                mark_scheduled_message_sent(message["id"])
                
                logger.info(f"Запланированное сообщение #{message['id']} отправлено пользователю {message['user_id']}")
            except Exception as e:
                logger.error(f"Ошибка при отправке запланированного сообщения #{message['id']}: {e}")
    
    async def _send_scheduled_message(self, user_id: int, content: str):
        """Отправка запланированного сообщения"""
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"⏰ *Запланированное сообщение*\n\n{content}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
