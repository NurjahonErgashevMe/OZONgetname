"""
Конфигурация Telegram бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', 0))

if not BOT_TOKEN:
    raise ValueError("Не указан TELEGRAM_BOT_TOKEN в переменных окружения")

if not TELEGRAM_CHAT_ID:
    raise ValueError("Не указан TELEGRAM_CHAT_ID в переменных окружения")

# Настройки логирования
LOG_BUFFER_SIZE = 15
LOG_UPDATE_INTERVAL = 2  # секунды