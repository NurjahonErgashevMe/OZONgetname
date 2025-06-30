"""
Утилиты для Telegram бота
"""
import re
import os
import asyncio
import logging
from urllib.parse import urlparse
from typing import Tuple, List

from .config import TELEGRAM_CHAT_ID
from src.parser.main_parser import OzonProductParser
from src.config import get_category_name

logger = logging.getLogger(__name__)


def check_access(user_id: int) -> bool:
    """
    Проверяет доступ пользователя к боту
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если доступ разрешен
    """
    return user_id == TELEGRAM_CHAT_ID


def validate_ozon_url(url: str) -> Tuple[bool, str]:
    """
    Валидирует URL категории Ozon
    
    Args:
        url: URL для проверки
        
    Returns:
        Tuple[bool, str]: (валидность, ключ сообщения об ошибке)
    """
    try:
        parsed = urlparse(url)
        
        # Проверяем, что это URL
        if not parsed.scheme or not parsed.netloc:
            return False, 'invalid_url'
        
        # Проверяем, что это Ozon
        if 'ozon.ru' not in parsed.netloc:
            return False, 'not_ozon_url'
        
        # Проверяем, что это категория
        if '/category/' not in parsed.path:
            return False, 'invalid_category_url'
        
        return True, ''
        
    except Exception:
        return False, 'invalid_url'


def validate_product_links(text: str) -> Tuple[bool, str, List[str]]:
    """
    Валидирует ссылки на товары Ozon
    
    Args:
        text: Текст со ссылками (разделенными переносом строки)
        
    Returns:
        Tuple[bool, str, List[str]]: (валидность, ключ сообщения об ошибке, список валидных ссылок)
    """
    lines = text.strip().split('\n')
    valid_links = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Проверяем, что это URL
        try:
            parsed = urlparse(line)
            if not parsed.scheme or not parsed.netloc:
                continue
                
            # Проверяем, что это Ozon
            if 'ozon.ru' not in parsed.netloc:
                continue
                
            # Проверяем, что это товар
            if '/product/' in parsed.path:
                valid_links.append(line)
                
        except Exception:
            continue
    
    # Проверки
    if not valid_links:
        return False, 'no_valid_links', []
    
    if len(valid_links) > 100:
        return False, 'too_many_links', []
    
    return True, '', valid_links


def run_parser_sync(url: str, user_id: int) -> str:
    """
    Синхронная функция для запуска парсера категории
    
    Args:
        url: URL категории для парсинга
        user_id: ID пользователя
        
    Returns:
        str: Путь к созданному файлу или None при ошибке
    """
    try:
        category_name = get_category_name(url)
        parser = OzonProductParser(category_name)
        
        # Запускаем парсер ссылок
        from src.link_parser.main_link_parser import OzonLinkParser
        link_parser = OzonLinkParser(url)
        
        success = link_parser.run()
        if not success:
            logger.error("Ошибка при парсинге ссылок")
            return None
        
        # Читаем ссылки из файла
        from src.config import LINKS_OUTPUT_FILE
        if not os.path.exists(LINKS_OUTPUT_FILE):
            logger.error(f"Файл {LINKS_OUTPUT_FILE} не найден")
            return None
        
        with open(LINKS_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
        
        if not urls:
            logger.error("Не найдено URL для парсинга")
            return None
        
        # Запускаем парсер товаров
        success = parser.run(urls)
        if success:
            return parser.excel_filename
        else:
            return None
            
    except Exception as e:
        logger.exception(f"Ошибка в run_parser_sync: {e}")
        return None


def run_product_parser_sync(links: List[str], user_id: int) -> str:
    """
    Синхронная функция для парсинга конкретных товаров
    
    Args:
        links: Список ссылок на товары
        user_id: ID пользователя
        
    Returns:
        str: Путь к созданному файлу или None при ошибке
    """
    try:
        # Создаем парсер с названием "product_links"
        parser = OzonProductParser("product_links")
        
        # Запускаем парсер товаров
        success = parser.run(links)
        if success:
            return parser.excel_filename
        else:
            return None
            
    except Exception as e:
        logger.exception(f"Ошибка в run_product_parser_sync: {e}")
        return None


async def cleanup_file(file_path: str, delay: int = 300):
    """
    Удаляет файл через заданное время
    
    Args:
        file_path: Путь к файлу
        delay: Задержка в секундах
    """
    try:
        await asyncio.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл удален: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {file_path}: {e}")