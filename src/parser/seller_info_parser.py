import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

class SellerInfoParser:
    def __init__(self):
        self.logger = logging.getLogger('seller_info_parser')

    def get_company_name(self, driver):
        """Получение названия компании с улучшенной логикой загрузки"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            self.logger.info(f"Попытка {attempt + 1} из {max_attempts} получить название компании")
            
            try:
                # Шаг 1: Дождаться загрузки основного контента страницы
                if not self._wait_for_page_content(driver):
                    self.logger.warning("Не удалось дождаться загрузки основного контента")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                
                # Шаг 2: Скролл к элементу paginator для загрузки секции продавца
                self._scroll_to_paginator(driver)
                
                # Шаг 3: Дождаться загрузки секции продавца
                seller_section = self._wait_for_seller_section(driver)
                if not seller_section:
                    self.logger.warning("Секция продавца не найдена")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                
                # Шаг 4: Найти кнопку тултипа
                tooltip_button = self._find_tooltip_button(seller_section)
                if not tooltip_button:
                    self.logger.warning("Кнопка тултипа не найдена")
                    # Пробуем получить имя продавца как запасной вариант
                    seller_name = self._get_seller_name_fallback(seller_section)
                    if seller_name:
                        return seller_name
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                
                # Шаг 5: Получить данные из тултипа
                company_name = self._get_company_from_tooltip(driver, tooltip_button)
                if company_name and company_name != "Не найдено":
                    self.logger.info(f"✓ Успешно получено название компании: {company_name}")
                    return company_name
                
                # Если получили "Не найдено", продолжаем попытки
                if attempt < max_attempts - 1:
                    self.logger.warning("Название компании не найдено, повторяем попытку...")
                    time.sleep(2)
                    continue
                
                return "Не найдено"                
            except Exception as e:
                self.logger.error(f"Ошибка в попытке {attempt + 1}: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(2)  # Пауза между попытками
                
        self.logger.error("Не удалось получить информацию о компании")
        return "Не найдено"

    def _wait_for_page_content(self, driver):
        """Ожидание загрузки основного контента страницы"""
        try:
            # Ждем загрузки главного контейнера товара
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webPdpGrid"]'))
            )
            self.logger.info("Основной контент страницы загружен")
            return True
        except TimeoutException:
            self.logger.error("Таймаут при ожидании загрузки основного контента")
            return False

    def _scroll_to_paginator(self, driver):
        """Скролл к элементу paginator для загрузки секции продавца"""
        try:
            # Ищем элемент paginator
            paginator_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="paginator"]'))
            )
            
            # Скроллим к элементу paginator, оставляя 20% сверху
            driver.execute_script("""
                const paginator = arguments[0];
                const rect = paginator.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
                const scrollTop = window.pageYOffset + rect.top - (viewportHeight * 0.2);
                
                window.scrollTo({
                    top: Math.max(0, scrollTop),
                    behavior: 'smooth'
                });
            """, paginator_element)
            
            time.sleep(2)  # Даем время на загрузку контента
            self.logger.info("Выполнен скролл к элементу paginator")
            
        except TimeoutException:
            self.logger.warning("Элемент paginator не найден, пробуем альтернативный скролл")
            # Альтернативный скролл вниз страницы
            driver.execute_script("""
                window.scrollTo({
                    top: document.body.scrollHeight * 0.7,
                    behavior: 'smooth'
                });
            """)
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"Ошибка при скролле к paginator: {str(e)}")

    def _wait_for_seller_section(self, driver):
        """Ожидание загрузки секции продавца"""
        try:
            # Ждем появления секции продавца
            seller_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webCurrentSeller"]'))
            )
            
            # Дополнительно ждем, пока секция станет видимой
            WebDriverWait(driver, 5).until(
                EC.visibility_of(seller_section)
            )
            
            self.logger.info("Секция продавца загружена")
            return seller_section
            
        except TimeoutException:
            self.logger.error("Таймаут при ожидании загрузки секции продавца")
            return None

    def _find_tooltip_button(self, seller_section):
        """Улучшенный поиск кнопки тултипа"""
        try:
            # Ищем кнопку рядом с ссылкой на продавца
            # Сначала находим ссылку на продавца
            seller_link = seller_section.find_element(By.CSS_SELECTOR, 'a[title][href*="/seller/"]')
            
            # Ищем кнопку с SVG рядом с ссылкой
            parent_container = seller_link.find_element(By.XPATH, './parent::*/parent::*')
            
            # Различные селекторы для кнопки тултипа
            tooltip_selectors = [
                'button[aria-label=""] svg',
                'button svg',
                'button[class*="ga5_3_1-a"]',
                'button[aria-label=""]'
            ]
            
            for selector in tooltip_selectors:
                try:
                    buttons = parent_container.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        # Если это SVG, получаем родительскую кнопку
                        if button.tag_name == 'svg':
                            button = button.find_element(By.XPATH, './parent::button')
                        
                        if button and button.is_displayed() and button.is_enabled():
                            # Проверяем, что кнопка небольшого размера (характерно для кнопок тултипа)
                            size = button.size
                            if size['width'] <= 50 and size['height'] <= 50:
                                self.logger.info("Найдена кнопка тултипа")
                                return button
                except:
                    continue
            
            self.logger.warning("Кнопка тултипа не найдена")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске кнопки тултипа: {str(e)}")
            return None

    def _get_company_from_tooltip(self, driver, tooltip_button):
        """Получение названия компании из тултипа с дополнительными попытками"""
        max_tooltip_attempts = 3
        
        for attempt in range(max_tooltip_attempts):
            try:
                self.logger.info(f"Попытка {attempt + 1} получить данные из тултипа")
                
                # Скроллим к кнопке
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tooltip_button)
                time.sleep(1)
                
                # Кликаем на кнопку
                ActionChains(driver).move_to_element(tooltip_button).click().perform()
                time.sleep(1.5)
                
                # Ждем появления тултипа
                tooltip = self._wait_for_tooltip(driver)
                
                if tooltip:
                    company_name = self._parse_tooltip_content(tooltip.text)
                    if company_name:
                        # Закрываем тултип (кликаем в другое место)
                        driver.execute_script("document.body.click();")
                        return company_name
                
                # Если не получилось, пробуем еще раз другим способом
                driver.execute_script("arguments[0].click();", tooltip_button)
                time.sleep(1.5)
                
                tooltip = self._wait_for_tooltip(driver)
                if tooltip:
                    company_name = self._parse_tooltip_content(tooltip.text)
                    if company_name:
                        driver.execute_script("document.body.click();")
                        return company_name
                
                # Закрываем тултип перед следующей попыткой
                driver.execute_script("document.body.click();")
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Ошибка в попытке {attempt + 1} получения данных из тултипа: {str(e)}")
                if attempt < max_tooltip_attempts - 1:
                    time.sleep(1)
        
        return None

    def _wait_for_tooltip(self, driver):
        """Ожидание появления тултипа"""
        try:
            # Ждем появления тултипа в элементе vue-portal-target
            for _ in range(15):  # Ждем до 4.5 секунд
                portals = driver.find_elements(By.CSS_SELECTOR, '.vue-portal-target')
                for portal in portals:
                    if portal.is_displayed() and portal.text.strip():
                        # Проверяем, что содержимое похоже на информацию о компании
                        if self._is_company_tooltip(portal.text):
                            self.logger.info("Найден тултип с информацией о компании")
                            return portal
                time.sleep(0.3)
            
            self.logger.warning("Тултип не найден")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при ожидании тултипа: {str(e)}")
            return None

    def _is_company_tooltip(self, text):
        """Проверка, содержит ли тултип информацию о компании"""
        if not text or len(text.strip()) < 5:
            return False
        
        # Ключевые слова для компаний
        company_keywords = ['ООО', 'ИП', 'АО', 'ЗАО', 'ПАО', 'ОАО', 'Ltd', 'LLC', 'Inc']
        
        # Проверяем наличие ключевых слов
        has_keywords = any(keyword in text.upper() for keyword in company_keywords)
        
        # Проверяем наличие длинных чисел (ИНН/ОГРН)
        numbers = ''.join(filter(str.isdigit, text))
        has_long_number = len(numbers) >= 10
        
        # Проверяем наличие фразы "Режим работы"
        has_work_schedule = 'режим работы' in text.lower()
        
        return has_keywords or has_long_number or has_work_schedule

    def _parse_tooltip_content(self, text):
        """Парсинг содержимого тултипа для извлечения названия компании"""
        if not text:
            return None
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Ищем строку с названием компании
        for line in lines:
            # Проверяем, содержит ли строка организационно-правовую форму
            if self._is_company_name_line(line):
                # Очищаем от лишних символов
                cleaned_name = line.strip(' "')
                self.logger.info(f"Найдено название компании: {cleaned_name}")
                return cleaned_name
        
        # Если не найдено явного названия, возвращаем первую строку (часто это название)
        if lines:
            first_line = lines[0].strip(' "')
            if len(first_line) > 3 and not first_line.isdigit():
                return first_line
        
        return None

    def _is_company_name_line(self, line):
        """Проверка, является ли строка названием компании"""
        company_indicators = ['ООО', 'ИП', 'АО', 'ЗАО', 'ПАО', 'ОАО', 'Ltd', 'LLC', 'Inc']
        line_upper = line.upper()
        
        # Проверяем наличие организационно-правовой формы
        for indicator in company_indicators:
            if indicator in line_upper:
                return True
        
        # Дополнительная проверка: строка не должна быть числом и должна быть достаточно длинной
        return len(line) > 5 and not line.isdigit() and not line.replace(' ', '').isdigit()

    def _get_seller_name_fallback(self, seller_section):
        """Получение имени продавца как запасной вариант"""
        try:
            # Ищем ссылку на продавца
            seller_link = seller_section.find_element(By.CSS_SELECTOR, 'a[title][href*="/seller/"]')
            seller_name = seller_link.text.strip()
            
            if seller_name and len(seller_name) > 2:
                self.logger.info(f"Получено имя продавца: {seller_name}")
                return seller_name
            
        except Exception as e:
            self.logger.debug(f"Ошибка при получении имени продавца: {str(e)}")
        
        return None