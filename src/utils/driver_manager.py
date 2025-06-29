import undetected_chromedriver as uc
import logging
from src.config import CHROMEDRIVER_PATH

class DriverManager:
    def __init__(self):
        self.drivers = []
        self.logger = logging.getLogger('driver_manager')

    def create_driver(self):
        """Создание нового экземпляра браузера"""
        options = uc.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--blink-settings=imagesEnabled=false')
        
        prefs = {'profile.default_content_setting_values': {'images': 2, 'javascript': 1}}
        options.add_experimental_option('prefs', prefs)
        
        driver = uc.Chrome(
            options=options,
            driver_executable_path=CHROMEDRIVER_PATH,
            headless=False,
            use_subprocess=True
        )
        
        self.drivers.append(driver)
        self.logger.info(f"Создан новый браузер. Всего активных: {len(self.drivers)}")
        return driver

    def close_all_drivers(self):
        """Закрытие всех браузеров"""
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass
        self.drivers.clear()
        self.logger.info("Все браузеры закрыты")

    def remove_driver(self, driver):
        """Удаление драйвера из списка"""
        if driver in self.drivers:
            self.drivers.remove(driver)