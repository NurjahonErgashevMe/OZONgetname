"""
Утилиты для работы с файлами в боте
"""
import os
import zipfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_file_size_mb(file_path: str) -> float:
    """
    Получает размер файла в МБ
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        float: Размер файла в МБ
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0


def compress_file(file_path: str) -> Optional[str]:
    """
    Сжимает файл в ZIP архив
    
    Args:
        file_path: Путь к исходному файлу
        
    Returns:
        str: Путь к сжатому файлу или None при ошибке
    """
    try:
        zip_path = file_path.replace('.xlsx', '.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
        
        logger.info(f"Файл сжат: {file_path} -> {zip_path}")
        return zip_path
        
    except Exception as e:
        logger.error(f"Ошибка сжатия файла: {e}")
        return None


def validate_file_for_telegram(file_path: str) -> tuple[bool, str, float]:
    """
    Проверяет, можно ли отправить файл через Telegram
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        tuple: (can_send, reason, size_mb)
    """
    if not os.path.exists(file_path):
        return False, "Файл не найден", 0
    
    size_mb = get_file_size_mb(file_path)
    max_size_mb = 50  # Лимит Telegram
    
    if size_mb > max_size_mb:
        return False, f"Файл слишком большой ({size_mb:.1f}MB). Максимум: {max_size_mb}MB", size_mb
    
    return True, "OK", size_mb