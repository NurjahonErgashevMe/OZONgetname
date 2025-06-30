import logging
import threading
import queue
import time
from src.config import WORKER_COUNT, get_timestamp
from src.utils.driver_manager import DriverManager
from .page_parser import PageParser
from src.utils.excel_exporter import ExcelExporter

class OzonProductParser:
    def __init__(self, category_name):
        self.results = []
        self.processed_count = 0
        self.stop_event = threading.Event()
        self.logger = logging.getLogger('product_parser')
        self.category_name = category_name
        self.timestamp = get_timestamp()
        self.worker_count = WORKER_COUNT
        self.total_urls = 0
        self.failed_urls = queue.Queue()  # Очередь для повторной обработки
        
        # Инициализация компонентов
        self.driver_manager = DriverManager()
        self.page_parser = PageParser()
        self.excel_exporter = ExcelExporter(category_name, self.timestamp)
        
        # Имя файла Excel для логирования
        self.excel_filename = self.excel_exporter.get_filename()
        
        self.logger.info(f"Инициализирован парсер для категории: {category_name}")

    def worker(self, url_queue, worker_id):
        """Рабочий поток для обработки URL"""
        driver = self.driver_manager.create_driver()
        self.logger.info(f"Воркер {worker_id} запущен")
        
        while not url_queue.empty() and not self.stop_event.is_set():
            try:
                url = url_queue.get_nowait()
                
                # Парсим страницу с обработкой ошибок доступа
                result = self._parse_with_retry(driver, url, worker_id)
                
                # Если не удалось обработать после всех попыток
                if result is None:
                    # Добавляем URL в очередь для повторной обработки новым воркером
                    self.failed_urls.put(url)
                    self.logger.warning(f"URL {url} добавлен в очередь для повторной обработки")
                    continue
                
                # Сохраняем результат
                with threading.Lock():
                    self.results.append((
                        url,
                        result['product'], 
                        result['seller'], 
                        result['company_name'],
                        result['inn'],
                        result['status']
                    ))
                    self.processed_count += 1
                    current_count = self.processed_count
                
                # Логируем результат
                status_msg = {
                    "out_of_stock": "ЗАКОНЧИЛСЯ",
                    "error": "ОШИБКА",
                    "success": "УСПЕШНО",
                    "access_denied": "ДОСТУП ОГРАНИЧЕН"
                }.get(result['status'], "НЕИЗВЕСТНО")
                
                self.logger.info(f"[{current_count}/{self.total_urls}] {status_msg}: {url}")
                self.logger.info(f"   Товар: {result['product']}")
                self.logger.info(f"   Продавец: {result['seller']}")
                self.logger.info(f"   Компания: {result['company_name']}")
                self.logger.info(f"   ИНН: {result['inn']}")
                
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в воркере {worker_id}: {str(e)}")
            finally:
                try:
                    url_queue.task_done()
                except:
                    pass
                time.sleep(0.3)
                
        # Закрываем драйвер воркера
        try:
            driver.quit()
            self.driver_manager.remove_driver(driver)
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии драйвера в воркере {worker_id}: {str(e)}")
        
        self.logger.info(f"Воркер {worker_id} завершил работу")

    def _parse_with_retry(self, driver, url, worker_id, max_retries=3):
        """Парсинг с повторными попытками при ошибке доступа"""
        for attempt in range(max_retries):
            try:
                result = self.page_parser.parse_page(driver, url)
                
                # Проверяем на ошибку доступа
                if self._is_access_denied(result):
                    self.logger.warning(f"Воркер {worker_id}, попытка {attempt + 1}: Доступ ограничен для {url}")
                    
                    if attempt < max_retries - 1:
                        # Перезагружаем страницу
                        driver.refresh()
                        time.sleep(2)
                        continue
                    else:
                        # Все попытки исчерпаны
                        self.logger.error(f"Воркер {worker_id}: Все попытки исчерпаны для {url}")
                        return None
                
                # Успешный результат
                return result
                
            except Exception as e:
                self.logger.error(f"Воркер {worker_id}, попытка {attempt + 1}: Ошибка при парсинге {url}: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    # Возвращаем результат с ошибкой
                    return {
                        'product': 'Ошибка парсинга',
                        'seller': f'Ошибка: {str(e)}',
                        'company_name': 'Не найдено',
                        'inn': 'Не найдено',
                        'status': 'error'
                    }
        
        return None

    def _is_access_denied(self, result):
        """Проверка на ошибку доступа"""
        # Проверяем различные признаки ограничения доступа
        access_denied_indicators = [
            "доступ ограничен",
            "access denied",
            "доступ запрещен",
            "страница недоступна"
        ]
        
        for field in ['product', 'seller']:
            if result.get(field, '').lower() in [indicator.lower() for indicator in access_denied_indicators]:
                return True
        
        return result.get('status') == 'access_denied'

    def _process_failed_urls(self):
        """Обработка неудачных URL новыми воркерами"""
        if self.failed_urls.empty():
            return
        
        self.logger.info(f"Запуск обработки {self.failed_urls.qsize()} неудачных URL")
        
        # Запускаем новые воркеры для обработки неудачных URL
        workers = []
        for i in range(min(self.worker_count, self.failed_urls.qsize())):
            worker_thread = threading.Thread(
                target=self._retry_worker,
                args=(i + 100),  # Используем другие ID для retry воркеров
                daemon=True
            )
            worker_thread.start()
            workers.append(worker_thread)
            time.sleep(1)
        
        # Ждем завершения retry воркеров
        for worker in workers:
            worker.join()

    def _retry_worker(self, worker_id):
        """Воркер для повторной обработки неудачных URL"""
        driver = self.driver_manager.create_driver()
        self.logger.info(f"Retry воркер {worker_id} запущен")
        
        while not self.failed_urls.empty() and not self.stop_event.is_set():
            try:
                url = self.failed_urls.get_nowait()
                
                # Парсим страницу
                result = self.page_parser.parse_page(driver, url)
                
                # Сохраняем результат
                with threading.Lock():
                    self.results.append((
                        url,
                        result['product'], 
                        result['seller'], 
                        result['company_name'],
                        result['inn'],
                        result['status']
                    ))
                    self.processed_count += 1
                
                self.logger.info(f"Retry воркер {worker_id}: Успешно обработан {url}")
                
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в retry воркере {worker_id}: {str(e)}")
            finally:
                try:
                    self.failed_urls.task_done()
                except:
                    pass
                time.sleep(0.3)
        
        # Закрываем драйвер
        try:
            driver.quit()
            self.driver_manager.remove_driver(driver)
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии драйвера в retry воркере {worker_id}: {str(e)}")
        
        self.logger.info(f"Retry воркер {worker_id} завершил работу")

    def run(self, urls):
        """Запуск парсинга"""
        self.total_urls = len(urls)
        if not urls:
            self.logger.error("Нет URL для обработки")
            return False
        
        start_time = time.time()
        self.logger.info(f"Начало обработки {self.total_urls} товаров")
        
        # Создание очереди задач
        url_queue = queue.Queue()
        for url in urls:
            url_queue.put(url)
        
        # Запуск воркеров
        workers = []
        for i in range(self.worker_count):
            worker_thread = threading.Thread(
                target=self.worker,
                args=(url_queue, i+1),
                daemon=True
            )
            worker_thread.start()
            workers.append(worker_thread)
            time.sleep(1)
        
        # Ожидание завершения основных воркеров
        try:
            for worker in workers:
                worker.join()
        except KeyboardInterrupt:
            self.stop_event.set()
            self.logger.warning("Получен сигнал прерывания!")
            
            for worker in workers:
                worker.join(timeout=5)
        
        # Обрабатываем неудачные URL, если они есть
        if not self.stop_event.is_set():
            self._process_failed_urls()
        
        # Сохранение результатов
        success = self.excel_exporter.save_results(self.results)
        duration = time.time() - start_time
        
        if success:
            self.logger.info(f"Обработка завершена успешно за {duration:.2f} секунд")
            self.logger.info(f"Обработано товаров: {len(self.results)}")
            self.logger.info(f"Успешно: {sum(1 for r in self.results if r[5] == 'success')}")
            self.logger.info(f"Закончились: {sum(1 for r in self.results if r[5] == 'out_of_stock')}")
            self.logger.info(f"Ошибки: {sum(1 for r in self.results if r[5] == 'error')}")
            self.logger.info(f"Доступ ограничен: {sum(1 for r in self.results if r[5] == 'access_denied')}")
        else:
            self.logger.error(f"Ошибка при сохранении результатов")
            
        return success

    def get_results_summary(self):
        """Получение сводки результатов"""
        if not self.results:
            return {
                'total': 0,
                'success': 0,
                'out_of_stock': 0,
                'error': 0,
                'access_denied': 0
            }
        
        return {
            'total': len(self.results),
            'success': sum(1 for r in self.results if r[5] == 'success'),
            'out_of_stock': sum(1 for r in self.results if r[5] == 'out_of_stock'),
            'error': sum(1 for r in self.results if r[5] == 'error'),
            'access_denied': sum(1 for r in self.results if r[5] == 'access_denied')
        }

    def stop_parsing(self):
        """Остановка парсинга"""
        self.stop_event.set()
        self.logger.info("Запрошена остановка парсинга")

    def __del__(self):
        """Деструктор - закрытие всех ресурсов"""
        try:
            if hasattr(self, 'driver_manager'):
                self.driver_manager.cleanup()
        except Exception as e:
            pass