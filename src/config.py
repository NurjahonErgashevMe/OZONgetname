import os
import re
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()

# Общие настройки
LOG_FILE = "ozon_parser.log"
WORKER_COUNT = 20  # Количество воркеров
TABS_PER_WORKER = 1  # Количество вкладок на каждого воркера

# Настройки для парсера ссылок
LINKS_OUTPUT_FILE = "links.json"
TOTAL_LINKS = 500  # Целевое количество ссылок
MAX_IDLE_SCROLLS = 5  # Максимум скроллов без новых ссылок
SCROLL_DELAY = 1.5  # Задержка между скроллами
LOAD_TIMEOUT = 15
TELEGRAM_CHAT_ID= os.getenv('TELEGRAM_CHAT_ID')  # ID чата для отправки сообщений

# Папка для результатов
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Текущая дата и время
def get_timestamp():
    return datetime.now().strftime("%d.%m.%Y-%H_%M_%S")

# Получение имени категории из URL
def get_category_name(url):
    match = re.search(r'/category/([^/?]+)', url)
    return match.group(1) if match else "unknown_category"