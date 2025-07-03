import logging
import time
import os
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
        self.idle_scrolls = 0
        self.logger = logging.getLogger('link_parser')
        self.category_name = get_category_name(target_url)
        self.logger.info(f"Категория: {self.category_name}")

    def init_driver(self):
        try:
            self.driver = self.driver_manager.create_driver()
            self.driver.maximize_window()
            self.logger.info("Драйвер успешно инициализирован")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации драйвера: {str(e)}")
            return False

    def load_page(self):
        try:
            self.logger.info(f"Открытие страницы: {self.target_url}")
            self.driver.get(self.target_url)
            WebDriverWait(self.driver, LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "contentScrollPaginator"))
            )
            self.logger.info("Страница загружена успешно")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке страницы: {str(e)}")
            return False

    def scroll_page(self):
        try:
            last_seen_index = -1

            while True:
                container = self.driver.find_element(By.ID, "contentScrollPaginator")
                items = container.find_elements(By.CSS_SELECTOR, "div[data-index]")
                if not items:
                    self.logger.warning("Нет товаров в контейнере")
                    break

                current_last_index = int(items[-1].get_attribute("data-index"))

                if current_last_index == last_seen_index:
                    self.logger.debug("Новые товары не загружаются — выходим из скролла")
                    break

                last_seen_index = current_last_index

                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});", items[-1])
                time.sleep(SCROLL_DELAY)

        except Exception as e:
            self.logger.warning(f"Ошибка при скролле: {str(e)}")

    def extract_links(self):
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".tile-root a.tile-clickable-element")
            links = set()

            for element in elements:
                href = element.get_attribute("href")
                if href and href.startswith("https://www.ozon.ru/product/"):
                    links.add(href)

            return links
        except Exception as e:
            self.logger.warning(f"Ошибка при извлечении ссылок: {str(e)}")
            return set()

    def collect_links(self):
        current_links = self.extract_links()
        new_links = current_links - self.unique_links

        if new_links:
            self.logger.info(f"Найдено новых ссылок: {len(new_links)}")
            for link in new_links:
                self.unique_links.add(link)
                self.ordered_links.append(link)
            self.idle_scrolls = 0
            return True
        else:
            self.idle_scrolls += 1
            return False

    def save_links(self):
        try:
            links_to_save = self.ordered_links[:TOTAL_LINKS]
            with open(LINKS_OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(links_to_save))

            self.logger.info(f"Сохранено {len(links_to_save)} ссылок в файл: {os.path.abspath(LINKS_OUTPUT_FILE)}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении ссылок: {str(e)}")
            return False

    def run(self):
        try:
            if not self.init_driver():
                return False, []

            if not self.load_page():
                return False, []

            self.collect_links()

            while len(self.ordered_links) < TOTAL_LINKS and self.idle_scrolls < MAX_IDLE_SCROLLS:
                self.scroll_page()
                if self.collect_links():
                    self.logger.info(f"Собрано: {len(self.ordered_links)}/{TOTAL_LINKS}")
                time.sleep(0.5)

            if self.save_links():
                self.logger.info(f"Собрано финально: {len(self.ordered_links)} ссылок")
                return True, self.ordered_links[:TOTAL_LINKS]
            else:
                return False, []
        except KeyboardInterrupt:
            self.logger.warning("Остановка по Ctrl+C")
            return False, self.ordered_links[:TOTAL_LINKS]
        except Exception as e:
            self.logger.critical(f"Критическая ошибка: {str(e)}")
            return False, []
        finally:
            self.cleanup()

    def cleanup(self):
        try:
            if self.driver:
                self.driver.quit()
                self.driver_manager.remove_driver(self.driver)
            self.driver_manager.close_all_drivers()
            self.logger.info("Ресурсы очищены")
        except Exception as e:
            self.logger.warning(f"Ошибка очистки: {str(e)}")

    def get_statistics(self):
        return {
            'total_collected': len(self.ordered_links),
            'unique_links': len(self.unique_links),
            'target_count': TOTAL_LINKS,
            'idle_scrolls': self.idle_scrolls,
            'category': self.category_name
        }
