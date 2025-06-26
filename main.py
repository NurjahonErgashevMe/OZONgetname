import logging
import re
import os
from link_parser import OzonLinkParser
from product_parser import OzonProductParser
from config import *

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE)
        ]
    )

def read_links():
    try:
        with open(LINKS_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Ошибка чтения файла ссылок: {str(e)}")
        return []

def validate_ozon_url(url):
    """Проверяет, является ли ссылка валидным URL Ozon"""
    # Обновленное регулярное выражение для поддержки всех поддоменов
    if not re.match(r'^https?://([a-z]+\.)?ozon\.(ru|kz|com|by|uz)', url, re.IGNORECASE):
        return False
    if "/category/" not in url:
        return False
    return True

def get_category_from_url(url):
    """Извлекает имя категории из URL"""
    match = re.search(r'/category/([^/?]+)', url)
    return match.group(1) if match else "unknown_category"

def main():
    setup_logging()
    logger = logging.getLogger('main')
    
    logger.info("=== ЗАПУСК ПАРСЕРА OZON ===")
    
    # Запрос ссылки у пользователя
    while True:
        target_url = input("\nВведите ссылку на категорию Ozon (например: https://www.ozon.ru/category/sistemnye-bloki-15704/): ")
        
        # Нормализация URL (удаление пробелов)
        target_url = target_url.strip()
        
        if not validate_ozon_url(target_url):
            logger.error("Некорректная ссылка! Пример правильной ссылки: https://www.ozon.ru/category/sistemnye-bloki-15704/")
            logger.error("Или: https://uz.ozon.com/category/kompyuternye-i-ofisnye-kresla-38450/")
            continue
        
        # Извлекаем имя категории
        category_name = get_category_from_url(target_url)
        logger.info(f"Категория: {category_name}")
        break
    
    # Этап 1: Парсинг ссылок
    logger.info("\n=== ЭТАП 1: ПАРСИНГ ССЫЛОК ===")
    link_parser = OzonLinkParser(target_url)
    success, product_urls = link_parser.run()
    
    if not success or not product_urls:
        logger.error("Не удалось собрать ссылки. Завершение работы.")
        return
    
    # Этап 2: Чтение ссылок
    logger.info("\n=== ЭТАП 2: ЧТЕНИЕ ССЫЛОК ===")
    logger.info(f"Прочитано ссылок: {len(product_urls)}")
    
    # Этап 3: Парсинг товаров
    logger.info("\n=== ЭТАП 3: ПАРСИНГ ТОВАРОВ ===")
    logger.info(f"Количество воркеров: {WORKER_COUNT}")
    
    product_parser = OzonProductParser(category_name)
    if product_parser.run(product_urls):
        logger.info("\n=== ПАРСИНГ УСПЕШНО ЗАВЕРШЕН ===")
        logger.info(f"Отчет сохранен: {os.path.abspath(product_parser.excel_filename)}")
    else:
        logger.error("\n=== ПАРСИНГ ЗАВЕРШЕН С ОШИБКАМИ ===")

if __name__ == "__main__":
    main()