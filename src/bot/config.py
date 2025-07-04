"""
Конфигурация Telegram бота
"""
import os

def load_config_from_file():
    config_path = os.path.join(os.getcwd(), "config.txt")
    if not os.path.exists(config_path):
        raise FileNotFoundError("❌ config.txt не найден рядом с .exe")
    
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Загружаем переменные из config.txt
load_config_from_file()

# Получаем значения
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', "0"))

if not BOT_TOKEN:
    raise ValueError("❌ Не указан TELEGRAM_BOT_TOKEN в config.txt")

if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ Не указан TELEGRAM_CHAT_ID в config.txt")


# Настройки логирования
LOG_BUFFER_SIZE = 15
LOG_UPDATE_INTERVAL = 2  # секунды