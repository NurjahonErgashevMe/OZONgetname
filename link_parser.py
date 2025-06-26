import logging
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from config import *

class OzonLinkParser:
    def __init__(self, target_url):
        self.target_url = target_url
        self.driver = None
        self.unique_links = set()
        self.ordered_links = []
        self.scroll_attempts = 0
        self.logger = logging.getLogger('link_parser')
        
        # Извлекаем имя категории
        self.category_name = get_category_name(target_url)
        self.logger.info(f"Категория: {self.category_name}")

    def init_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        
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
            
            WebDriverWait(self.driver, LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".tile-root"))
            )
            self.logger.info("Страница успешно загружена")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка загрузки страницы: {str(e)}")
            return False

    def scroll_page(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
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
            for link in new_links:
                self.unique_links.add(link)
                self.ordered_links.append(link)
            
            new_count = len(self.ordered_links)
            self.logger.info(f"Найдено новых ссылок: {len(new_links)} | Всего: {new_count}/{TOTAL_LINKS}")
            self.scroll_attempts = 0
            return True
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
            while len(self.ordered_links) < TOTAL_LINKS and self.scroll_attempts < MAX_SCROLL_ATTEMPTS:
                self.scroll_page()
                self.scroll_attempts += 1
                
                if not self.collect_links():
                    self.logger.info(f"Новых ссылок не обнаружено. Попытка: {self.scroll_attempts}/{MAX_SCROLL_ATTEMPTS}")
            
            # Финализация
            self.save_links()
            final_count = len(self.ordered_links)
            
            if final_count < TOTAL_LINKS:
                self.logger.warning(f"Собрано только {final_count} из {TOTAL_LINKS} ссылок")
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