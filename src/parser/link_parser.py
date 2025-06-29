import logging
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from src.config import *

class OzonLinkParser:
    def __init__(self, target_url):
        self.target_url = target_url
        self.driver = None
        self.unique_links = set()
        self.ordered_links = []
        self.idle_scrolls = 0  # Счетчик скроллов без новых ссылок
        self.logger = logging.getLogger('link_parser')
        self.category_name = get_category_name(target_url)
        self.logger.info(f"Категория: {self.category_name}")

    def init_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        
        self.driver = uc.Chrome(
            driver_executable_path=CHROMEDRIVER_PATH,
            options=options,
            headless=False,
            use_subprocess=True
        )
        self.logger.info("Браузер инициализирован")

    def load_page(self):
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
        # Плавный скролл вместо резкого прыжка
        scroll_height = self.driver.execute_script("return document.body.scrollHeight")
        for i in range(0, scroll_height, 300):
            self.driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.05)
        time.sleep(SCROLL_DELAY)

    def extract_links(self):
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".tile-root a.tile-clickable-element")
            return {element.get_attribute("href") for element in elements if element.get_attribute("href")}
        except Exception:
            return set()

    def collect_links(self):
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

    def save_links(self):
        try:
            with open(LINKS_OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(self.ordered_links))
            self.logger.info(f"Ссылки сохранены в файл: {os.path.abspath(LINKS_OUTPUT_FILE)}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения ссылок: {str(e)}")

    def run(self):
        try:
            self.init_driver()
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
                    self.logger.info(f"Всего ссылок: {current_count}/{TOTAL_LINKS}")
                
                # Проверяем, не достигли ли мы конца страницы
                new_scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                old_scroll_height = self.driver.execute_script("return window.pageYOffset + window.innerHeight")
                
                if new_scroll_height <= old_scroll_height:
                    self.logger.info("Достигнут конец страницы")
                    break
            
            # Финализация
            final_count = len(self.ordered_links)
            self.save_links()
            
            if final_count < TOTAL_LINKS:
                self.logger.warning(f"Собрано только {final_count} из {TOTAL_LINKS} ссылок (причина: {'конец страницы' if self.idle_scrolls < MAX_IDLE_SCROLLS else 'нет новых ссылок'})")
            else:
                self.logger.info(f"Успешно собрано {final_count} ссылок")
                
            return True, self.ordered_links
                
        except Exception as e:
            self.logger.critical(f"Критическая ошибка: {str(e)}")
            return False, []
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("Браузер закрыт")