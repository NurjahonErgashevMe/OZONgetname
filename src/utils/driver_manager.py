from selenium import webdriver
from selenium_stealth import stealth
import logging

class DriverManager:
    def __init__(self):
        self.drivers = []
        self.logger = logging.getLogger('driver_manager')
        
    def create_driver(self,headless=True):
        """Создание нового экземпляра браузера с selenium-stealth"""
        options = webdriver.ChromeOptions()
                
        # Основные опции для производительности и обхода детектирования
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--blink-settings=imagesEnabled=false')
        
        if headless:
            options.add_argument('--headless')
        
        # Отключение изображений и настройка JavaScript
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # Отключить изображения
                'javascript': 1  # Включить JavaScript
            }
        }
        options.add_experimental_option('prefs', prefs)
        
        # Создание драйвера с системным chromedriver
        driver = webdriver.Chrome(options=options)
        
        # Применение stealth настроек
        stealth(
            driver,
            languages=["ru-RU", "ru", "en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            webdriver=False
        )
        
        self.drivers.append(driver)
        self.logger.info(f"Создан новый браузер с selenium-stealth. Всего активных: {len(self.drivers)}")
        return driver

    def close_all_drivers(self):
        """Закрытие всех браузеров"""
        for driver in self.drivers:
            try:
                driver.quit()
            except Exception as e:
                self.logger.warning(f"Ошибка при закрытии драйвера: {str(e)}")
        self.drivers.clear()
        self.logger.info("Все браузеры закрыты")

    def remove_driver(self, driver):
        """Удаление драйвера из списка"""
        if driver in self.drivers:
            self.drivers.remove(driver)
            self.logger.debug(f"Драйвер удален из списка. Осталось активных: {len(self.drivers)}")

    def cleanup(self):
        """Очистка ресурсов"""
        self.close_all_drivers()
        self.logger.info("Очистка DriverManager завершена")