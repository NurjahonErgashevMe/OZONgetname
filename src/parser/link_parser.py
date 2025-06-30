import logging
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.config import *
from src.utils.driver_manager import DriverManager

class OzonLinkParser:
    def __init__(self, target_url):
        self.target_url = target_url
        self.driver = None
        self.driver_manager = DriverManager()
        self.unique_links = set()
        self.ordered_links = []
        self.idle_scrolls = 0  # Счетчик скроллов без новых ссылок
        self.logger = logging.getLogger('link_parser')
        self.category_name = get_category_name(target_url)
        self.logger.info(f"Категория: {self.category_name}")

    def init_driver(self):
        """Инициализация драйвера через DriverManager"""
        try:
            self.driver = self.driver_manager.create_driver()
            
            # Дополнительные настройки для сбора ссылок
            self.driver.maximize_window()
            self.logger.info("Браузер инициализирован через DriverManager")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка инициализации браузера: {str(e)}")
            return False

    def load_page(self):
        """Загрузка целевой страницы"""
        try:
            self.logger.info(f"Загрузка страницы: {self.target_url}")
            self.driver.get(self.target_url)
            
            # Ожидаем появления хотя бы одного товара
            WebDriverWait(self.driver, LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".tile-root"))
            )
            self.logger.info("Страница успешно загружена")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка загрузки страницы: {str(e)}")
            return False

    def scroll_page(self):
        """Выполняет плавный скролл до конца страницы"""
        try:
            # Получаем текущую высоту страницы
            current_scroll_position = self.driver.execute_script("return window.pageYOffset")
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Плавный скролл порциями по 300px
            for i in range(current_scroll_position, scroll_height, 300):
                self.driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.05)
            
            # Дополнительная задержка для загрузки контента
            time.sleep(SCROLL_DELAY)
            
        except Exception as e:
            self.logger.warning(f"Ошибка при скролле: {str(e)}")

    def extract_links(self):
        """Извлечение ссылок на товары со страницы"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".tile-root a.tile-clickable-element")
            links = set()
            
            for element in elements:
                href = element.get_attribute("href")
                if href and href.startswith("https://www.ozon.ru/product/"):
                    links.add(href)
            
            return links
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения ссылок: {str(e)}")
            return set()

    def collect_links(self):
        """Сбор новых ссылок и добавление их к общему списку"""
        current_links = self.extract_links()
        new_links = current_links - self.unique_links
        
        if new_links:
            self.logger.info(f"Найдено новых ссылок: {len(new_links)}")
            for link in new_links:
                self.unique_links.add(link)
                self.ordered_links.append(link)
            
            # Сбрасываем счетчик скроллов без изменений
            self.idle_scrolls = 0
            return True
        else:
            self.idle_scrolls += 1
            return False

    def is_page_end_reached(self):
        """Проверка, достигнут ли конец страницы"""
        try:
            # Получаем общую высоту документа
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            # Получаем текущую позицию скролла + высоту окна
            current_position = self.driver.execute_script("return window.pageYOffset + window.innerHeight")
            
            # Считаем, что конец достигнут, если разница меньше 100px
            return (total_height - current_position) < 100
        except Exception as e:
            self.logger.warning(f"Ошибка проверки конца страницы: {str(e)}")
            return False

    def save_links(self):
        """Сохранение собранных ссылок в файл"""
        try:
            links_to_save = self.ordered_links[:TOTAL_LINKS]
            with open(LINKS_OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(links_to_save))
            
            self.logger.info(f"Сохранено {len(links_to_save)} ссылок в файл: {os.path.abspath(LINKS_OUTPUT_FILE)}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка сохранения ссылок: {str(e)}")
            return False

    def run(self):
        """Основной метод запуска парсера ссылок"""
        try:
            # Инициализация драйвера
            if not self.init_driver():
                return False, []
            
            # Загрузка страницы
            if not self.load_page():
                return False, []
                
            # Первоначальный сбор ссылок
            if self.collect_links():
                self.logger.info(f"Начальное количество ссылок: {len(self.ordered_links)}/{TOTAL_LINKS}")
            
            # Основной цикл сбора
            while len(self.ordered_links) < TOTAL_LINKS and self.idle_scrolls < MAX_IDLE_SCROLLS:
                self.scroll_page()
                
                if self.collect_links():
                    current_count = len(self.ordered_links)
                    self.logger.info(f"Всего ссылок: {min(current_count, TOTAL_LINKS)}/{TOTAL_LINKS}")
                
                # Проверяем, не достигли ли мы конца страницы
                if self.is_page_end_reached():
                    self.logger.info("Достигнут конец страницы")
                    break
                
                # Небольшая пауза между итерациями
                time.sleep(0.5)
            
            # Финализация и сохранение результатов
            final_count = min(len(self.ordered_links), TOTAL_LINKS)
            
            if self.save_links():
                if final_count < TOTAL_LINKS:
                    reason = 'конец страницы' if self.idle_scrolls < MAX_IDLE_SCROLLS else 'нет новых ссылок'
                    self.logger.warning(f"Собрано только {final_count} из {TOTAL_LINKS} ссылок (причина: {reason})")
                else:
                    self.logger.info(f"Успешно собрано {final_count} ссылок")
                
                return True, self.ordered_links[:TOTAL_LINKS]
            else:
                self.logger.error("Ошибка сохранения ссылок")
                return False, []
                
        except KeyboardInterrupt:
            self.logger.warning("Прерывание пользователем")
            return False, self.ordered_links[:TOTAL_LINKS] if self.ordered_links else []
        except Exception as e:
            self.logger.critical(f"Критическая ошибка: {str(e)}")
            return False, []
        finally:
            self.cleanup()

    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver_manager.remove_driver(self.driver)
                self.logger.info("Браузер закрыт")
            
            # Закрываем все драйверы в manager'е
            self.driver_manager.close_all_drivers()
        except Exception as e:
            self.logger.warning(f"Ошибка при очистке ресурсов: {str(e)}")

    def get_statistics(self):
        """Получение статистики сбора ссылок"""
        return {
            'total_collected': len(self.ordered_links),
            'unique_links': len(self.unique_links),
            'target_count': TOTAL_LINKS,
            'idle_scrolls': self.idle_scrolls,
            'category': self.category_name
        }