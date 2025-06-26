import os
import re
from datetime import datetime

# Общие настройки
CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver.exe"
LOG_FILE = "ozon_parser.log"
WORKER_COUNT = 3

# Настройки для парсера ссылок
LINKS_OUTPUT_FILE = "links.txt"
TOTAL_LINKS = 100  # Целевое количество ссылок
MAX_IDLE_SCROLLS = 5  # Максимум скроллов без новых ссылок
SCROLL_DELAY = 1.5  # Задержка между скроллами
LOAD_TIMEOUT = 15

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