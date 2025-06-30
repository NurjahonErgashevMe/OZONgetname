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
        self.max_attempts = 5
        self.visited_products = set()

    def get_seller_details(self, driver, seller_url=None):
        """Получение детальной информации о продавце с повторными попытками"""
        seller_details = {'company_name': 'Не найдено', 'inn': 'Не найдено'}
        
        for attempt in range(self.max_attempts):
            self.logger.info(f"=== ПОПЫТКА {attempt + 1} из {self.max_attempts} получить данные продавца ===")
            
            try:
                # Если это не первая попытка - обновляем страницу
                if attempt > 0:
                    self.logger.info("Обновляем страницу перед повторной попыткой...")
                    driver.refresh()
                    time.sleep(3)  # Ждем загрузки страницы
                    self.logger.info("Страница обновлена, ждем загрузки контента...")
                
                # Активируем контент скроллом
                self.logger.info("Прокручиваем страницу для активации контента...")
                driver.execute_script("window.scrollTo(0, 600);")
                time.sleep(1)
                
                # Ищем секцию с продавцом
                self.logger.info("Ищем секцию с информацией о продавце...")
                seller_section = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-widget="webCurrentSeller"]'))
                )
                self.logger.info("✓ Секция продавца найдена!")
                
                # Дополнительный скролл к секции
                self.logger.info("Прокручиваем к секции продавца...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seller_section)
                time.sleep(1.5)
                
                # Ищем кнопку с информацией
                self.logger.info("Ищем кнопку с информацией о продавце...")
                info_button = self._find_info_button(seller_section)
                
                if info_button:
                    self.logger.info("✓ Кнопка информации найдена!")
                    tooltip_data = self._get_tooltip_data(driver, info_button, attempt + 1)
                    
                    if tooltip_data and (tooltip_data.get('company_name') != 'Не найдено' or tooltip_data.get('inn') != 'Не найдено'):
                        self.logger.info(f"✓ Успешно получены данные продавца: {tooltip_data}")
                        seller_details.update(tooltip_data)
                        break
                    else:
                        self.logger.warning("Данные из тултипа не получены или пустые")
                else:
                    self.logger.warning("✗ Кнопка информации не найдена")
                
                # Если не получилось и есть еще попытки
                if attempt < self.max_attempts - 1:
                    self.logger.info(f"Попытка {attempt + 1} неуспешна, готовимся к следующей...")
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"✗ Ошибка в попытке {attempt + 1}: {str(e)}")
                if attempt < self.max_attempts - 1:
                    self.logger.info("Ждем перед следующей попыткой...")
                    time.sleep(3)
        
        if seller_details['company_name'] == 'Не найдено' and seller_details['inn'] == 'Не найдено':
            self.logger.error(f"✗ После {self.max_attempts} попыток данные продавца не найдены")
        else:
            self.logger.info(f"✓ Итоговые данные продавца: {seller_details}")
            
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
            'button svg',
            'button[class*="button"]',
            '*[role="button"]'
        ]
        
        self.logger.info(f"Проверяем {len(button_selectors)} различных селекторов кнопок...")
        
        for i, selector in enumerate(button_selectors, 1):
            try:
                self.logger.debug(f"Селектор {i}: {selector}")
                buttons = seller_section.find_elements(By.CSS_SELECTOR, selector)
                self.logger.debug(f"Найдено {len(buttons)} элементов по селектору {i}")
                
                for j, button in enumerate(buttons):
                    try:
                        if button and button.is_displayed() and button.is_enabled():
                            self.logger.debug(f"Проверяем кнопку {j+1} на соответствие критериям...")
                            if self._is_info_button(button):
                                self.logger.info(f"✓ Найдена подходящая кнопка по селектору {i}, элемент {j+1}")
                                return button
                    except Exception as e:
                        self.logger.debug(f"Ошибка при проверке кнопки {j+1}: {str(e)}")
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Ошибка с селектором {i}: {str(e)}")
                continue
                
        self.logger.warning("Подходящая кнопка не найдена ни по одному селектору")
        return None

    def _is_info_button(self, button):
        """Проверка, является ли кнопка кнопкой информации"""
        try:
            # Проверяем наличие SVG иконки
            try:
                icon = button.find_element(By.TAG_NAME, 'svg')
                if icon:
                    self.logger.debug("Кнопка содержит SVG иконку")
                    return True
            except:
                pass
            
            # Проверяем размер кнопки (кнопки информации обычно маленькие)
            size = button.size
            self.logger.debug(f"Размер кнопки: {size}")
            if size['width'] <= 50 and size['height'] <= 50:
                self.logger.debug("Кнопка подходит по размеру")
                return True
            
            # Проверяем атрибуты
            class_attr = button.get_attribute('class') or ''
            aria_label = button.get_attribute('aria-label') or ''
            
            if 'info' in class_attr.lower() or aria_label == '':
                self.logger.debug("Кнопка подходит по атрибутам")
                return True
                
            return False
        except Exception as e:
            self.logger.debug(f"Ошибка при проверке кнопки: {str(e)}")
            return False

    def _get_tooltip_data(self, driver, info_button, attempt_num):
        """Получение данных из тултипа с детальным логированием"""
        try:
            self.logger.info(f"--- Начинаем получение данных из тултипа (попытка {attempt_num}) ---")
            
            # Скроллим к кнопке
            self.logger.info("Прокручиваем к кнопке информации...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", info_button)
            time.sleep(1)
            
            # Запоминаем количество порталов до клика
            portals_before = len(driver.find_elements(By.CSS_SELECTOR, 'body .vue-portal-target'))
            self.logger.info(f"Количество порталов до клика: {portals_before}")
            
            # Пробуем разные способы взаимодействия с кнопкой
            interaction_methods = [
                self._click_with_actions,
                self._click_with_javascript,
                self._hover_and_click
            ]
            
            for method_num, method in enumerate(interaction_methods, 1):
                try:
                    self.logger.info(f"Пробуем способ взаимодействия {method_num}: {method.__name__}")
                    method(driver, info_button)
                    
                    # Ждем появления тултипа
                    self.logger.info("Ожидаем появление тултипа...")
                    tooltip = self._wait_for_tooltip(driver, portals_before, method_num)
                    
                    if tooltip:
                        self.logger.info("✓ Тултип найден! Парсим содержимое...")
                        parsed_data = self._parse_tooltip_content(tooltip)
                        if parsed_data:
                            self.logger.info(f"✓ Данные успешно извлечены: {parsed_data}")
                            return parsed_data
                        else:
                            self.logger.warning("Парсинг тултипа не дал результатов")
                    else:
                        self.logger.warning(f"Тултип не появился после способа {method_num}")
                        
                    # Небольшая пауза между попытками
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка в способе {method_num}: {str(e)}")
                    continue
                    
            self.logger.error("Все способы взаимодействия с кнопкой исчерпаны")
            return None
                
        except Exception as e:
            self.logger.error(f"Общая ошибка при получении тултипа: {str(e)}")
            return None

    def _click_with_actions(self, driver, button):
        """Клик через ActionChains"""
        self.logger.debug("Выполняем клик через ActionChains...")
        actions = ActionChains(driver)
        actions.move_to_element(button).click().perform()
        time.sleep(1.5)

    def _click_with_javascript(self, driver, button):
        """Клик через JavaScript"""
        self.logger.debug("Выполняем клик через JavaScript...")
        driver.execute_script("arguments[0].click();", button)
        time.sleep(1.5)

    def _hover_and_click(self, driver, button):
        """Наведение курсора и клик"""
        self.logger.debug("Наводим курсор и кликаем...")
        actions = ActionChains(driver)
        actions.move_to_element(button).pause(0.5).click().perform()
        time.sleep(1.5)

    def _wait_for_tooltip(self, driver, initial_count, method_num):
        """Ожидание появления тултипа с улучшенным логированием"""
        max_wait = 5
        elapsed = 0
        check_interval = 0.3
        
        self.logger.info(f"Ждем появления тултипа (макс. {max_wait}с, способ {method_num})...")
        
        while elapsed < max_wait:
            try:
                current_portals = driver.find_elements(By.CSS_SELECTOR, 'body .vue-portal-target')
                new_portals_count = len(current_portals)
                
                if new_portals_count > initial_count:
                    self.logger.info(f"Обнаружены новые порталы: {new_portals_count} (было {initial_count})")
                    
                    for i, portal in enumerate(current_portals):
                        try:
                            if portal.is_displayed():
                                text = portal.text.strip()
                                self.logger.debug(f"Проверяем портал {i+1}, текст: '{text[:100]}...'")
                                
                                if self._looks_like_seller_info(text):
                                    self.logger.info(f"✓ Найден тултип с информацией о продавце в портале {i+1}")
                                    return portal
                        except Exception as e:
                            self.logger.debug(f"Ошибка при проверке портала {i+1}: {str(e)}")
                            continue
                
                time.sleep(check_interval)
                elapsed += check_interval
                
                if elapsed % 1 == 0:  # Логируем каждую секунду
                    self.logger.debug(f"Прошло {elapsed:.1f}с, порталов: {new_portals_count}")
                
            except Exception as e:
                self.logger.debug(f"Ошибка при ожидании тултипа: {str(e)}")
                time.sleep(check_interval)
                elapsed += check_interval
                
        self.logger.warning(f"Тултип не появился за {max_wait}с")
        return None

    def _parse_tooltip_content(self, tooltip):
        """Парсинг содержимого тултипа с детальным логированием"""
        seller_details = {}
        
        try:
            text_content = tooltip.text.strip()
            self.logger.info(f"Содержимое тултипа: '{text_content}'")
            
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            self.logger.info(f"Строки для анализа ({len(lines)}): {lines}")
            
            for i, line in enumerate(lines, 1):
                self.logger.debug(f"Анализируем строку {i}: '{line}'")
                
                if self._is_company_name(line):
                    self.logger.info(f"✓ Найдено название компании: '{line}'")
                    seller_details['company_name'] = line
                elif self._is_inn(line):
                    self.logger.info(f"✓ Найден ИНН/ОГРН: '{line}'")
                    seller_details['inn'] = line
                else:
                    self.logger.debug(f"Строка не распознана как важная информация")
                    
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге тултипа: {str(e)}")
            
        if not seller_details:
            self.logger.warning("Из тултипа не удалось извлечь информацию о продавце")
        else:
            self.logger.info(f"Извлеченная информация: {seller_details}")
            
        return seller_details

    def _looks_like_seller_info(self, text):
        """Проверка, похож ли текст на информацию о продавце"""
        if not text or len(text.strip()) < 5:
            return False
            
        seller_keywords = [
            'ИП', 'ООО', 'АО', 'ЗАО', 'ПАО', 'Ltd', 'LLC', 'Inc', 'ОАО'
        ]
        
        # Проверяем наличие длинных чисел (ИНН/ОГРН)
        has_long_number = any(len(''.join(filter(str.isdigit, word))) >= 10 for word in text.split())
        
        # Проверяем ключевые слова
        has_keywords = any(keyword.lower() in text.lower() for keyword in seller_keywords)
        
        result = has_long_number or has_keywords
        self.logger.debug(f"Текст '{text[:50]}...' {'ПОХОЖ' if result else 'НЕ ПОХОЖ'} на информацию о продавце")
        
        return result

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
        self.logger.info("Состояние парсера сброшено для нового продавца")