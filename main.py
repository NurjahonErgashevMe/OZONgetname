import logging
import re
import os
import sys
from src.parser.link_parser import OzonLinkParser
from src.parser.main_parser import OzonProductParser
from src.config import *

def setup_logging():
    """Настройка логирования"""
    # Создаем директорию для логов если её нет
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding='utf-8')
        ]
    )

def read_links():
    """Чтение ссылок из файла"""
    try:
        with open(LINKS_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"Файл {LINKS_OUTPUT_FILE} не найден")
        return []
    except Exception as e:
        logging.error(f"Ошибка чтения файла ссылок: {str(e)}")
        return []

def validate_ozon_url(url):
    """Проверяет, является ли ссылка валидным URL Ozon"""
    # Обновленное регулярное выражение для поддержки всех поддоменов
    if not re.search(r'([a-z]+\.)?ozon\.(ru|kz|com|by|uz)', url, re.IGNORECASE):
        return False
    if "/category/" not in url:
        return False
    return True

def get_category_from_url(url):
    """Извлекает имя категории из URL"""
    match = re.search(r'/category/([^/?]+)', url)
    return match.group(1) if match else "unknown_category"

def get_user_input():
    """Получение ссылки от пользователя с валидацией"""
    while True:
        try:
            target_url = input("\nВведите ссылку на категорию Ozon (или 'exit' для выхода): ")
            target_url = target_url.strip()
            
            if target_url.lower() == 'exit':
                print("Выход из программы...")
                sys.exit(0)
            
            if not target_url:
                print("Пожалуйста, введите ссылку!")
                continue
            
            if not validate_ozon_url(target_url):
                print("❌ Некорректная ссылка! Примеры правильных ссылок:")
                print("   - https://www.ozon.ru/category/sistemnye-bloki-15704/")
                print("   - https://uz.ozon.com/category/kompyuternye-i-ofisnye-kresla-38450/")
                continue
            
            category_name = get_category_from_url(target_url)
            print(f"✅ Категория: {category_name}")
            
            return target_url, category_name
            
        except KeyboardInterrupt:
            print("\n\nВыход из программы...")
            sys.exit(0)
        except Exception as e:
            print(f"Ошибка: {str(e)}")
            continue

def print_progress_header():
    """Печать заголовка с информацией о настройках"""
    print("\n" + "="*60)
    print("           НАСТРОЙКИ ПАРСЕРА OZON")
    print("="*60)
    print(f"Целевое количество ссылок: {TOTAL_LINKS}")
    print(f"Количество воркеров: {WORKER_COUNT}")
    print(f"Файл логов: {LOG_FILE}")
    print("="*60)

def main():
    """Основная функция"""
    try:
        setup_logging()
        logger = logging.getLogger('main')
        
        print("🚀 ПАРСЕР OZON ЗАПУЩЕН")
        print_progress_header()
        
        # Запрос ссылки у пользователя
        target_url, category_name = get_user_input()
        
        # Этап 1: Парсинг ссылок
        print(f"\n📡 ЭТАП 1: СБОР ССЫЛОК НА ТОВАРЫ")
        print(f"Цель: собрать {TOTAL_LINKS} ссылок из категории '{category_name}'")
        
        logger.info("=== ЗАПУСК ПАРСЕРА OZON ===")
        logger.info(f"Целевая категория: {target_url}")
        logger.info(f"Целевое количество ссылок: {TOTAL_LINKS}")
        
        link_parser = OzonLinkParser(target_url)
        success, product_urls = link_parser.run()
        
        if not success or not product_urls:
            print("❌ Не удалось собрать ссылки. Завершение работы.")
            logger.error("Не удалось собрать ссылки. Завершение работы.")
            return 1
        
        print(f"✅ Собрано {len(product_urls)} ссылок на товары")
        
        # Этап 2: Парсинг товаров
        print(f"\n🔍 ЭТАП 2: ПАРСИНГ ИНФОРМАЦИИ О ТОВАРАХ")
        print(f"Количество товаров: {len(product_urls)}")
        print(f"Количество воркеров: {WORKER_COUNT}")
        print("Начинаем обработку...")
        
        logger.info("=== ЭТАП 2: ПАРСИНГ ТОВАРОВ ===")
        logger.info(f"Количество товаров: {len(product_urls)}")
        logger.info(f"Количество воркеров: {WORKER_COUNT}")
        
        product_parser = OzonProductParser(category_name)
        
        if product_parser.run(product_urls):
            # Получаем сводку результатов
            summary = product_parser.get_results_summary()
            
            print(f"\n🎉 ПАРСИНГ УСПЕШНО ЗАВЕРШЕН!")
            print(f"📊 СТАТИСТИКА:")
            print(f"   • Всего обработано: {summary['total']}")
            print(f"   • Успешно: {summary['success']}")
            print(f"   • Товар закончился: {summary['out_of_stock']}")
            print(f"   • Ошибки: {summary['error']}")
            print(f"📄 Отчет сохранен: {os.path.abspath(product_parser.excel_filename)}")
            
            logger.info("=== ПАРСИНГ УСПЕШНО ЗАВЕРШЕН ===")
            logger.info(f"Отчет сохранен: {os.path.abspath(product_parser.excel_filename)}")
            
            return 0
        else:
            print("❌ ПАРСИНГ ЗАВЕРШЕН С ОШИБКАМИ")
            logger.error("=== ПАРСИНГ ЗАВЕРШЕН С ОШИБКАМИ ===")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Получен сигнал прерывания!")
        logger.warning("Программа прервана пользователем")
        return 1
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)