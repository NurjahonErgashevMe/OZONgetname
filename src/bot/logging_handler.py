"""
Обработчик логирования для Telegram бота
"""
import asyncio
import logging
import queue
import time
from typing import Optional

from aiogram import Bot
from aiogram.types import Message

from .config import LOG_BUFFER_SIZE, LOG_UPDATE_INTERVAL
from .keywords import is_significant_log


logger = logging.getLogger(__name__)

# Очередь для передачи логов между потоками
log_queue = queue.Queue()


class QueueLogHandler(logging.Handler):
    """Кастомный обработчик логов для записи в очередь"""
    
    def emit(self, record):
        """
        Записывает лог в очередь
        
        Args:
            record: Запись лога
        """
        log_entry = self.format(record)
        log_queue.put(log_entry)


def setup_queue_logging():
    """Настраивает кастомный обработчик логов"""
    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logging.getLogger().addHandler(handler)


class LogUpdater:
    """Класс для обновления логов в Telegram"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.message: Optional[Message] = None
        self.log_buffer = []
        self.last_update = 0
    
    async def start(self, chat_id: int):
        """
        Запускает обновление логов в Telegram
        
        Args:
            chat_id: ID чата для отправки логов
        """
        while True:
            try:
                await self._process_logs(chat_id)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка обновления логов: {e}")
                await asyncio.sleep(5)
    
    async def _process_logs(self, chat_id: int):
        """
        Обрабатывает новые логи
        
        Args:
            chat_id: ID чата
        """
        # Собираем новые логи
        new_logs = []
        while not log_queue.empty():
            try:
                log_entry = log_queue.get_nowait()
                if is_significant_log(log_entry):
                    new_logs.append(log_entry)
                log_queue.task_done()
            except queue.Empty:
                break
        
        # Добавляем новые логи в буфер
        if new_logs:
            self.log_buffer.extend(new_logs)
            await self._update_message(chat_id)
    
    async def _update_message(self, chat_id: int):
        """
        Обновляет сообщение с логами
        
        Args:
            chat_id: ID чата
        """
        # Ограничиваем буфер
        if len(self.log_buffer) > LOG_BUFFER_SIZE:
            self.log_buffer = self.log_buffer[-LOG_BUFFER_SIZE:]
        
        # Формируем текст сообщения
        log_text = "\n".join(self.log_buffer)
        message_text = f"```\n{log_text}\n```"
        
        # Обновляем или создаем сообщение
        current_time = time.time()
        if self.message and current_time - self.last_update > LOG_UPDATE_INTERVAL:
            try:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=self.message.message_id,
                    text=message_text,
                    parse_mode="Markdown"
                )
                self.last_update = current_time
            except Exception:
                # Если не удалось обновить, создаем новое сообщение
                self.message = None
        
        if not self.message:
            self.message = await self.bot.send_message(
                chat_id, 
                message_text, 
                parse_mode="Markdown"
            )
            self.last_update = current_time