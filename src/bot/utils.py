"""
Утилиты для Telegram бота
"""
import re
import os
import logging
import asyncio
from datetime import datetime
from typing import Optional

from .config import TELEGRAM_CHAT_ID
from src.config import RESULTS_DIR, get_category_name


logger = logging.getLogger(__name__)


def check_access(user_id: int) -> bool:
    """
    Проверяет доступ пользователя к боту
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        bool: True если доступ разрешен
    """
    return user_id == TELEGRAM_CHAT_ID


def validate_ozon_url(url: str) -> tuple[bool, str]:
    """
    Валидирует URL Ozon
    
    Args:
        url: URL для проверки
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not re.search(r'([a-z]+\.)?ozon\.(ru|kz|com|by|uz)', url, re.IGNORECASE):
        return False, "invalid_url"
    
    if "/category/" not in url:
        return False, "invalid_category"
    
    return True, ""


def run_parser_sync(url: str, user_id: int) -> Optional[str]:
    """
    Синхронная функция для запуска парсера
    
    Args:
        url: URL категории Ozon
        user_id: ID пользователя
        
    Returns:
        str: Путь к файлу результатов или None при ошибке
    """
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        from src.parser.link_parser import OzonLinkParser
        from src.parser.main_parser import OzonProductParser
        
        # Этап 1: Парсинг ссылок
        logger.info(f"Начало парсинга ссылок для {url}")
        link_parser = OzonLinkParser(url)
        success, product_urls = link_parser.run()
        
        if not success or not product_urls:
            logger.error("Не удалось собрать ссылки")
            return None
        
        # Этап 2: Парсинг товаров
        category_name = get_category_name(url)
        logger.info(f"Начало парсинга {len(product_urls)} товаров")
        
        # Создаем уникальное имя файла с ID пользователя
        timestamp = datetime.now().strftime("%d.%m.%Y-%H_%M_%S")
        filename = f"{category_name}_{timestamp}.xlsx"
        excel_path = os.path.join(RESULTS_DIR, filename)
        
        # Модифицируем парсер для использования нового пути
        product_parser = OzonProductParser(category_name)
        product_parser.excel_filename = excel_path
        
        if product_parser.run(product_urls):
            logger.info(f"Файл результатов создан: {excel_path}")
            return excel_path
        return None
        
    except Exception as e:
        logger.exception(f"Критическая ошибка парсера: {e}")
        return None


async def cleanup_file(file_path: str, delay: int = 10):
    """
    Удаляет файл через указанное время
    
    Args:
        file_path: Путь к файлу
        delay: Задержка в секундах
    """
    await asyncio.sleep(delay)
    try:
        os.remove(file_path)
        logger.info(f"Файл удален: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка удаления файла: {e}")