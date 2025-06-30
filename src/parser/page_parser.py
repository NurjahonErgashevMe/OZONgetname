import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .seller_info_parser import SellerInfoParser

class PageParser:
    def __init__(self):
        self.logger = logging.getLogger('page_parser')
        self.seller_info_parser = SellerInfoParser()

    def parse_page(self, driver, url):
        """Парсинг страницы товара"""
        result = {
            'product': 'Not Found',
            'seller': 'Not Found',
            'company_name': 'Не найдено',
            'inn': 'Не найдено',
            'status': 'success'
        }
        
        try:
            driver.get(url)
            time.sleep(1)  # Даем время на загрузку
            
            # Проверка на ограничение доступа
            if self._check_access_denied(driver, result):
                return result
            
            # Проверка наличия товара
            if self._check_out_of_stock(driver, result):
                return result
            
            # Парсинг названия товара
            result['product'] = self._get_product_name(driver)
            
            # Скролл для активации контента
            driver.execute_script("window.scrollTo(0, 600);")
            time.sleep(0.5)
            
            # Парсинг продавца
            result['seller'] = self._get_seller_name(driver)
            
            # Получение детальной информации о продавце
            seller_details = self.seller_info_parser.get_seller_details(driver)
            result.update(seller_details)
            
        except Exception as e:
            result['status'] = "error"
            result['seller'] = f"Ошибка: {str(e)}"
            self.logger.error(f"Ошибка при парсинге {url}: {str(e)}")
            
        return result

    def _check_access_denied(self, driver, result):
        """Проверка на ограничение доступа"""
        try:
            # Проверяем заголовок страницы
            page_title = driver.title.lower()
            if "доступ ограничен" in page_title or "access denied" in page_title:
                result['status'] = "access_denied"
                result['product'] = "Доступ ограничен"
                result['seller'] = "Доступ ограничен"
                return True
            
            # Проверяем наличие элементов с сообщением об ограничении доступа
            access_denied_selectors = [
                '//div[contains(text(), "Доступ ограничен")]',
                '//div[contains(text(), "Access denied")]',
                '//div[contains(text(), "доступ запрещен")]',
                '//h1[contains(text(), "Доступ ограничен")]',
                '//span[contains(text(), "Доступ ограничен")]',
                '//*[contains(@class, "error") and contains(text(), "доступ")]',
                '//*[contains(@class, "blocked")]',
                '//div[contains(@class, "access-denied")]'
            ]
            
            for selector in access_denied_selectors:
                try:
                    element = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element and element.is_displayed():
                        result['status'] = "access_denied"
                        result['product'] = "Доступ ограничен"
                        result['seller'] = "Доступ ограничен"
                        return True
                except TimeoutException:
                    continue
            
            # Проверяем через JavaScript
            access_denied_js = driver.execute_script("""
                const bodyText = document.body.innerText.toLowerCase();
                const accessDeniedKeywords = [
                    'доступ ограничен',
                    'access denied',
                    'доступ запрещен',
                    'страница недоступна',
                    'access blocked'
                ];
                
                for (let keyword of accessDeniedKeywords) {
                    if (bodyText.includes(keyword)) {
                        return true;
                    }
                }
                return false;
            """)
            
            if access_denied_js:
                result['status'] = "access_denied"
                result['product'] = "Доступ ограничен"
                result['seller'] = "Доступ ограничен"
                return True
            
            # Проверяем на наличие капчи или блокировки
            captcha_selectors = [
                '//div[contains(@class, "captcha")]',
                '//form[contains(@class, "captcha")]',
                '//*[contains(text(), "Captcha")]',
                '//*[contains(text(), "Подтвердите")]'
            ]
            
            for selector in captcha_selectors:
                try:
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element and element.is_displayed():
                        result['status'] = "access_denied"
                        result['product'] = "Требуется подтверждение"
                        result['seller'] = "Капча/Подтверждение"
                        return True
                except TimeoutException:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Ошибка при проверке доступа: {str(e)}")
        
        return False

    def _check_out_of_stock(self, driver, result):
        """Проверка наличия товара"""
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, '//div[@data-widget="webOutOfStock"]'))
            )
            result['status'] = "out_of_stock"
            
            # Парсинг для отсутствующего товара
            result['product'] = self._get_out_of_stock_product_name(driver)
            result['seller'] = self._get_out_of_stock_seller_name(driver)
            
            return True
            
        except TimeoutException:
            return False

    def _get_out_of_stock_product_name(self, driver):
        """Получение названия отсутствующего товара"""
        selectors = [
            '//div[@data-widget="webOutOfStock"]//p[contains(@class, "yl6_27")]',
            '//div[@data-widget="webOutOfStock"]//p[contains(text(), "Intel") or contains(text(), "Системный")]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                return element.text.strip()
            except:
                continue
        
        return "Название не найдено"

    def _get_out_of_stock_seller_name(self, driver):
        """Получение названия продавца для отсутствующего товара"""
        try:
            element = driver.find_element(
                By.XPATH, 
                '//div[@data-widget="webOutOfStock"]//a[contains(@href, "/seller/")]'
            )
            return element.text.strip()
        except:
            return "Продавец не найден"

    def _get_product_name(self, driver):
        """Получение названия товара"""
        # Основные селекторы для названия товара
        selectors = [
            '//div[@data-widget="webProductHeading"]//h1',
            '//div[@data-widget="webProductHeading"]//*[contains(@class, "m9p_27")]',
            '//h1[@data-widget="webProductHeading"]'
        ]
        
        for selector in selectors:
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, selector))
                )
                return element.text.strip()
            except TimeoutException:
                continue
        
        # Альтернативные способы получения названия
        try:
            container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "p9m_27")]'))
            )
            element = container.find_element(By.TAG_NAME, 'h1')
            return element.text.strip()
        except:
            pass
        
        # JavaScript способ
        try:
            product_js = driver.execute_script("""
                const widget = document.querySelector('div[data-widget="webProductHeading"]');
                if (widget) {
                    const h1 = widget.querySelector('h1');
                    if (h1) return h1.innerText.trim();
                    return widget.innerText.trim();
                }
                
                const classElement = document.querySelector('.m9p_27, .tsHeadline');
                if (classElement) return classElement.innerText.trim();
                
                return document.title.split('|')[0].trim();
            """)
            
            if product_js:
                return product_js
        except:
            pass
        
        return "Название не найдено"

    def _get_seller_name(self, driver):
        """Получение названия продавца"""
        # Основной селектор
        try:
            element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((
                    By.XPATH, 
                    '//div[@data-widget="webCurrentSeller"]//a[contains(@class, "s1k_27") and @title] | '
                    '//a[contains(@href, "/seller/") and @title]'
                ))
            )
            return element.text.strip()
        except TimeoutException:
            pass
        
        # Альтернативные селекторы
        seller_locators = [
            (By.XPATH, '//div[@data-widget="webCurrentSeller"]//a[@title]'),
            (By.CSS_SELECTOR, 'div[data-widget="webCurrentSeller"] a.s1k_27'),
            (By.XPATH, '//a[contains(@class, "s1k_27") and @title]'),
            (By.XPATH, '//a[contains(@href, "/seller/")]')
        ]
        
        for locator in seller_locators:
            try:
                element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located(locator)
                )
                return element.text.strip()
            except TimeoutException:
                continue
        
        # JavaScript способ
        try:
            seller_js = driver.execute_script("""
                const sellerElement = 
                    document.querySelector('div[data-widget="webCurrentSeller"] a.s1k_27[title]') ||
                    document.querySelector('div[data-widget="webCurrentSeller"] a[title]') ||
                    document.querySelector('a.s1k_27[title]') ||
                    document.querySelector('a[href*="/seller/"][title]');
                return sellerElement ? sellerElement.textContent.trim() : '';
            """)
            
            if seller_js:
                return seller_js
        except:
            pass
        
        return "Продавец не найден"