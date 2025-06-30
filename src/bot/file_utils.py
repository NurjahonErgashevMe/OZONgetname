"""
Утилиты для работы с файлами в Telegram боте
"""
import os
import zipfile
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Максимальный размер файла для Telegram (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_file_for_telegram(file_path: str) -> Tuple[bool, str, float]:
    """
    Проверяет, можно ли отправить файл через Telegram
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Tuple[bool, str, float]: (можно отправить, причина, размер в MB)
    """
    try:
        if not os.path.exists(file_path):
            return False, "файл не найден", 0.0
        
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        
        if file_size > MAX_FILE_SIZE:
            return False, f"слишком большой ({size_mb:.1f}MB, максимум 50MB)", size_mb
        
        return True, "", size_mb
        
    except Exception as e:
        logger.error(f"Ошибка при проверке файла {file_path}: {e}")
        return False, f"ошибка проверки: {str(e)}", 0.0


def compress_file(file_path: str) -> str:
    """
    Сжимает файл в ZIP архив
    
    Args:
        file_path: Путь к файлу для сжатия
        
    Returns:
        str: Путь к ZIP файлу или None при ошибке
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл для сжатия не найден: {file_path}")
            return None
        
        # Создаем имя ZIP файла
        base_name = os.path.splitext(file_path)[0]
        zip_path = f"{base_name}.zip"
        
        # Создаем ZIP архив
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
        
        logger.info(f"Файл сжат: {file_path} -> {zip_path}")
        return zip_path
        
    except Exception as e:
        logger.error(f"Ошибка при сжатии файла {file_path}: {e}")
        return None