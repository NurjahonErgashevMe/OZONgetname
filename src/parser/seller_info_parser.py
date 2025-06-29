import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class SellerInfoParser:
    def __init__(self):
        self.logger = logging.getLogger('seller_info_parser')
        self.max_attempts = 3
        self.visited_products = set()

    def get_seller_details(self, driver, seller_url=None):
        """Получение детальной информации о продавце"""
        seller_details = {'company_name': 'Не найдено', 'inn': 'Не найдено'}
        
        for attempt in range(self.max_attempts):
            try:
                self.logger.info(f"Попытка {attempt + 1} получить данные продавца")
                
                # Активируем контент скроллом
                driver.execute_script("window.scrollTo(0, 600);")
                time.sleep(0.5)
                
                # Ищем секцию с продавцом
                seller_section = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webCurrentSeller"]'))
                )
                
                # Дополнительный скролл к секции
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seller_section)
                time.sleep(1)
                
                # Ищем кнопку с информацией
                info_button = self._find_info_button(seller_section)
                if info_button:
                    tooltip_data = self._get_tooltip_data(driver, info_button)
                    if tooltip_data:
                        seller_details.update(tooltip_data)
                        break
                
                # Если не получилось, пробуем следующую попытку
                if attempt < self.max_attempts - 1:
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Ошибка в попытке {attempt + 1}: {str(e)}")
                
        return seller_details

    def _find_info_button(self, seller_section):
        """Поиск кнопки с информацией о продавце"""
        button_selectors = [
            'div.ea20-a.k9j_27.n7j_27 button.ga20-a',
            'button.ga20-a[aria-label=""]',
            'div[data-widget="webCurrentSeller"] button[aria-label=""]',
            'button.ga20-a',
            'button[class*="ga20"]',
            'button[aria-label=""]',
            'button svg'
        ]
        
        for selector in button_selectors:
            try:
                buttons = seller_section.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button and button.is_displayed() and button.is_enabled():
                        if self._is_info_button(button):
                            return button
            except:
                continue
        return None

    def _is_info_button(self, button):
        """Проверка, является ли кнопка кнопкой информации"""
        try:
            # Проверяем наличие SVG иконки
            try:
                icon = button.find_element(By.TAG_NAME, 'svg')
                if icon:
                    return True
            except:
                pass
            
            # Проверяем размер кнопки (кнопки информации обычно маленькие)
            size = button.size
            if size['width'] <= 40 and size['height'] <= 40:
                return True
                
            return False
        except:
            return False

    def _get_tooltip_data(self, driver, info_button):
        """Получение данных из тултипа"""
        try:
            # Скроллим к кнопке
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", info_button)
            time.sleep(0.5)
            
            # Запоминаем количество порталов до клика
            portals_before = len(driver.find_elements(By.CSS_SELECTOR, 'body .vue-portal-target'))
            
            # Наводим курсор и кликаем
            actions = ActionChains(driver)
            actions.move_to_element(info_button).click().perform()
            time.sleep(1)
            
            # Ждем появления тултипа
            tooltip = self._wait_for_tooltip(driver, portals_before)
            if tooltip:
                return self._parse_tooltip_content(tooltip)
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении тултипа: {str(e)}")
            
        return None

    def _wait_for_tooltip(self, driver, initial_count):
        """Ожидание появления тултипа"""
        max_wait = 3
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                current_portals = driver.find_elements(By.CSS_SELECTOR, 'body .vue-portal-target')
                
                if len(current_portals) > initial_count:
                    for portal in current_portals:
                        if portal.is_displayed():
                            text = portal.text.strip()
                            if self._looks_like_seller_info(text):
                                return portal
                
                time.sleep(0.2)
                elapsed += 0.2
                
            except:
                time.sleep(0.2)
                elapsed += 0.2
                
        return None

    def _parse_tooltip_content(self, tooltip):
        """Парсинг содержимого тултипа"""
        seller_details = {}
        
        try:
            text_content = tooltip.text.strip()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            for line in lines:
                if self._is_company_name(line):
                    seller_details['company_name'] = line
                elif self._is_inn(line):
                    seller_details['inn'] = line
                    
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге тултипа: {str(e)}")
            
        return seller_details

    def _looks_like_seller_info(self, text):
        """Проверка, похож ли текст на информацию о продавце"""
        seller_keywords = [
            'ИП', 'ООО', 'АО', 'ЗАО', 'ПАО', 'Ltd', 'LLC', 'Inc'
        ]
        
        # Проверяем наличие длинных чисел (ИНН/ОГРН)
        has_long_number = any(len(''.join(filter(str.isdigit, word))) >= 10 for word in text.split())
        
        # Проверяем ключевые слова
        has_keywords = any(keyword.lower() in text.lower() for keyword in seller_keywords)
        
        return has_long_number or has_keywords

    def _is_company_name(self, text):
        """Проверка, является ли текст названием компании"""
        company_indicators = ['ИП', 'ООО', 'АО', 'ЗАО', 'ПАО', 'Ltd', 'LLC', 'Inc', 'ОАО']
        return any(indicator in text for indicator in company_indicators)

    def _is_inn(self, text):
        """Проверка, является ли текст ИНН или ОГРН"""
        digits_only = ''.join(filter(str.isdigit, text))
        valid_lengths = [10, 12, 13, 15]
        
        if len(digits_only) in valid_lengths and len(digits_only) / len(text) > 0.8:
            return True
        
        return False

    def reset_for_new_seller(self):
        """Сброс состояния для нового продавца"""
        self.visited_products.clear()