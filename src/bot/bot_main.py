"""
Основной модуль Telegram бота
"""
import logging
import sys
import os

# Добавляем корневую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aiogram import Bot, Dispatcher

from .config import BOT_TOKEN
from .register_handlers import register_handlers
from .logging_handler import setup_queue_logging
from src.config import LOG_FILE


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_bot')


async def main():
    """Главная функция для запуска бота"""
    logger.info("Запуск Telegram бота...")
    
    # Настраиваем логирование в очередь
    setup_queue_logging()
    
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем обработчики
    register_handlers(dp, bot)
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Критическая ошибка бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")