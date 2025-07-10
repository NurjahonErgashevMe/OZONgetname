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
        """Парсинг страницы товара с повторными попытками"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            self.logger.info(f"Попытка парсинга {attempt + 1} из {max_attempts}")
            
            result = self._parse_page_attempt(driver, url, attempt)
            
            # Проверяем, нужно ли повторить попытку
            if self._should_retry_parsing(result):
                self.logger.warning(f"Попытка {attempt + 1} неуспешна. Данные не найдены: "
                                  f"товар='{result['product_name']}', компания='{result['company_name']}'")
                
                if attempt < max_attempts - 1:  # Не перезагружаем на последней попытке
                    self.logger.info("Перезагружаем страницу для повторной попытки...")
                    self._reload_page(driver, url)
                    time.sleep(3)  # Даем время на загрузку
                    continue
            else:
                self.logger.info("Парсинг успешно завершен")
                return result
        
        # Если все попытки неуспешны, возвращаем последний результат
        self.logger.error(f"Не удалось получить все данные после {max_attempts} попыток")
        return result

    def _parse_page_attempt(self, driver, url, attempt_num):
        """Одна попытка парсинга страницы"""
        result = {
            'product_name': 'Не найдено',
            'company_name': 'Не найдено',
            'image_url': 'Не найдено',
            'status': 'success'
        }
        
        try:
            self.logger.info(f"Начинаем парсинг страницы: {url}")
            
            # Переходим на страницу только в первой попытке
            if attempt_num == 0:
                driver.get(url)
            
            # Ждем начальной загрузки страницы
            time.sleep(2)
            
            # Проверка на ограничение доступа
            if self._check_access_denied(driver):
                result['status'] = 'access_denied'
                result['product_name'] = 'Доступ ограничен'
                result['company_name'] = 'Доступ ограничен'
                result['image_url'] = 'Доступ ограничен'
                return result
            
            # Проверка наличия товара
            if self._check_out_of_stock(driver):
                result['status'] = 'out_of_stock'
                result['product_name'] = self._get_out_of_stock_product_name(driver)
                result['company_name'] = self._get_out_of_stock_company_name(driver)
                result['image_url'] = self._get_product_image_url(driver)
                return result
            
            # Парсинг названия товара
            product_name = self._get_product_name(driver)
            result['product_name'] = product_name
            self.logger.info(f"Получено название товара: {product_name}")
            
            # Получение информации о компании
            company_info = self.seller_info_parser.get_company_name(driver)
            result['company_name'] = company_info
            self.logger.info(f"Получена информация о компании: {company_info}")
            
            # Получение URL изображения товара
            image_url = self._get_product_image_url(driver)
            result['image_url'] = image_url
            self.logger.info(f"Получен URL изображения: {image_url}")
            
        except Exception as e:
            result['status'] = 'error'
            result['product_name'] = f"Ошибка: {str(e)}"
            result['company_name'] = "Не найдено"
            self.logger.error(f"Ошибка при парсинге {url}: {str(e)}")
            
        return result

    def _should_retry_parsing(self, result):
        """Проверяет, нужно ли повторить парсинг"""

        # Всегда пробуем повторно, если доступ ограничен или произошла ошибка
        if result['status'] in ['access_denied', 'error']:
            return True

        # Проверяем, найдены ли необходимые данные
        product_not_found = (
            result['product_name'] == 'Не найдено' or 
            result['product_name'] == 'Название не найдено' or
            result['product_name'].startswith('Ошибка:')
        )
        
        company_not_found = (
            result['company_name'] == 'Не найдено' or
            result['company_name'] == 'Компания не найдена'
        )
        
        return product_not_found or company_not_found


    def _reload_page(self, driver, url):
        """Перезагрузка страницы с улучшенной логикой"""
        try:
            self.logger.info("Перезагружаем страницу...")
            driver.refresh()
            time.sleep(2)
            
            # Проверяем, что страница загрузилась корректно
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Дополнительная проверка загрузки основного контента
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webProductHeading"], div[data-widget="webOutOfStock"]'))
                )
            except TimeoutException:
                self.logger.warning("Основной контент не загрузился после перезагрузки")
            
        except Exception as e:
            self.logger.error(f"Ошибка при перезагрузке страницы: {str(e)}")
            # Если перезагрузка не удалась, пробуем загрузить URL заново
            try:
                driver.get(url)
                time.sleep(3)
            except Exception as e2:
                self.logger.error(f"Ошибка при загрузке URL: {str(e2)}")

    def _check_access_denied(self, driver):
        """Проверка на ограничение доступа"""
        try:
            # Проверяем заголовок страницы
            page_title = driver.title.lower()
            if "доступ ограничен" in page_title or "access denied" in page_title:
                return True
            
            # Проверяем URL на редирект
            current_url = driver.current_url.lower()
            if "blocked" in current_url or "denied" in current_url:
                return True
            
            # Проверяем наличие элементов с сообщением об ограничении доступа
            access_denied_selectors = [
                '//div[contains(text(), "Доступ ограничен")]',
                '//div[contains(text(), "Access denied")]',
                '//h1[contains(text(), "Доступ ограничен")]',
                '//div[contains(@class, "error") and contains(text(), "403")]'
            ]
            
            for selector in access_denied_selectors:
                try:
                    element = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element and element.is_displayed():
                        return True
                except TimeoutException:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Ошибка при проверке доступа: {str(e)}")
            return False

    def _check_out_of_stock(self, driver):
        """Проверка наличия товара"""
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, '//div[@data-widget="webOutOfStock"]'))
            )
            self.logger.info("Товар отсутствует в продаже")
            return True
        except TimeoutException:
            return False

    def _get_out_of_stock_product_name(self, driver):
        """Получение названия отсутствующего товара"""
        selectors = [
            '//div[@data-widget="webOutOfStock"]//p[contains(@class, "yl6_27")]',
            '//div[@data-widget="webOutOfStock"]//p',
            '//div[@data-widget="webOutOfStock"]//h1'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                text = element.text.strip()
                if text and len(text) > 3:
                    return text
            except:
                continue
        
        return "Название не найдено"

    def _get_out_of_stock_company_name(self, driver):
        """Получение названия компании для отсутствующего товара"""
        try:
            # Для товаров отсутствующих в продаже тоже пробуем получить информацию о компании
            return self.seller_info_parser.get_company_name(driver)
        except:
            return "Компания не найдена"

    def _get_product_name(self, driver):
        """Получение названия товара с улучшенной логикой"""
        try:
            # Сначала ждем загрузки основного контента
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webProductHeading"]'))
            )
            
            # Основные селекторы для названия товара
            selectors = [
                '//div[@data-widget="webProductHeading"]//h1',
                '//div[@data-widget="webProductHeading"]//*[contains(@class, "m9p_27")]',
                '//h1[@data-widget="webProductHeading"]'
            ]
            
            for selector in selectors:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.XPATH, selector))
                    )
                    text = element.text.strip()
                    if text and len(text) > 3:
                        return text
                except TimeoutException:
                    continue
            
            # Альтернативные способы получения названия
            alternative_selectors = [
                'h1[data-widget="webProductHeading"]',
                'div[data-widget="webProductHeading"] h1',
                '.m9p_27',
                '.tsHeadline'
            ]
            
            for selector in alternative_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text and len(text) > 3:
                        return text
                except:
                    continue
            
            # JavaScript способ как последний resort
            try:
                product_js = driver.execute_script("""
                    const widget = document.querySelector('div[data-widget="webProductHeading"]');
                    if (widget) {
                        const h1 = widget.querySelector('h1');
                        if (h1) return h1.innerText.trim();
                        
                        const spans = widget.querySelectorAll('span');
                        for (let span of spans) {
                            if (span.innerText.trim().length > 10) {
                                return span.innerText.trim();
                            }
                        }
                        return widget.innerText.trim();
                    }
                    
                    const classElement = document.querySelector('.m9p_27, .tsHeadline');
                    if (classElement) return classElement.innerText.trim();
                    
                    const title = document.title.split('|')[0].trim();
                    return title.length > 3 ? title : null;
                """)
                
                if product_js and len(product_js) > 3:
                    return product_js
            except Exception as e:
                self.logger.debug(f"Ошибка при получении названия через JavaScript: {str(e)}")
            
            return "Название не найдено"
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении названия товара: {str(e)}")
            return "Название не найдено"
            
    def _get_product_image_url(self, driver):
        """Получение URL изображения товара"""
        try:
            # Ждем загрузки основного контента
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webGallery"]'))
            )
            
            # Селекторы для изображения товара
            selectors = [
                '//div[@data-widget="webGallery"]//img',
                '//div[contains(@class, "gallery")]//img',
                '//div[contains(@id, "gallery")]//img',
                '//div[contains(@class, "product-page")]//img[contains(@src, "ozon.ru")]'
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        src = element.get_attribute("src")
                        if src and ("ozon.ru" in src or "ir.ozone.ru" in src):
                            # Получаем изображение максимального качества
                            src = src.replace("wc50/", "wc1000/").replace("wc250/", "wc1000/").replace("wc500/", "wc1000/")
                            return src
                except Exception as e:
                    self.logger.debug(f"Ошибка при поиске изображения по селектору {selector}: {str(e)}")
                    continue
            
            # JavaScript способ как запасной вариант
            try:
                image_js = driver.execute_script("""
                    // Ищем все изображения на странице
                    const images = document.querySelectorAll('img');
                    
                    // Фильтруем изображения, которые могут быть основным изображением товара
                    for (let img of images) {
                        const src = img.getAttribute('src');
                        if (src && (src.includes('ozon.ru') || src.includes('ir.ozone.ru')) &&
                            (src.includes('wc') || src.includes('multimedia'))) {
                            // Получаем изображение максимального качества
                            return src.replace('wc50/', 'wc1000/').replace('wc250/', 'wc1000/').replace('wc500/', 'wc1000/');
                        }
                    }
                    return null;
                """)
                
                if image_js:
                    return image_js
            except Exception as e:
                self.logger.debug(f"Ошибка при получении изображения через JavaScript: {str(e)}")
            
            return "Изображение не найдено"
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении URL изображения товара: {str(e)}")
            return "Изображение не найдено"