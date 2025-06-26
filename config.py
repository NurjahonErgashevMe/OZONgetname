import os
from datetime import datetime
import re

# Общие настройки
CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver.exe"
LOG_FILE = "ozon_parser.log"
WORKER_COUNT = 3

# Настройки для парсера ссылок
LINKS_OUTPUT_FILE = "links.txt"
TOTAL_LINKS = 100
BATCH_SIZE = 10
MAX_SCROLL_ATTEMPTS = 20
SCROLL_DELAY = 3
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