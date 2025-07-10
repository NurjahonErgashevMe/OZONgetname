import logging
import threading
import queue
import time
from selenium.webdriver.common.by import By
from src.config import WORKER_COUNT, TABS_PER_WORKER, get_timestamp
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
        self.results_lock = threading.Lock()
        self.tabs_per_worker = TABS_PER_WORKER  # Количество вкладок на каждого воркера
        
        # Инициализация компонентов
        self.driver_manager = DriverManager()
        self.page_parser = PageParser()
        self.excel_exporter = ExcelExporter(category_name, self.timestamp)
        
        # Имя файла Excel для логирования
        self.excel_filename = self.excel_exporter.get_filename()
        
        self.logger.info(f"Инициализирован парсер для категории: {category_name}")
        self.logger.info(f"Настройка: {self.worker_count} воркеров")

    def worker(self, urls_for_worker, worker_id):
        """Рабочий поток для обработки URL"""
        try:
            # Создаем один драйвер для воркера
            driver = self.driver_manager.create_driver()
            self.logger.info(f"Воркер {worker_id} запущен")
            
            # Поскольку у нас только одна вкладка, обрабатываем URL напрямую
            for url_index, url in enumerate(urls_for_worker):
                if self.stop_event.is_set():
                    break
                
                try:
                    # Парсим страницу
                    result = self.page_parser.parse_page(driver, url)
                    
                    # Сохраняем результат
                    with self.results_lock:
                        self.results.append({
                            'url': url,
                            'product_name': result.get('product_name', 'Не найдено'),
                            'company_name': result.get('company_name', 'Не найдено'),
                            'image_url': result.get('image_url', 'Не найдено'),
                            'status': result.get('status', 'success')
                        })
                        self.processed_count += 1
                        current_count = self.processed_count
                    
                    # Логируем результат
                    self.logger.info(f"[{current_count}/{self.total_urls}] Воркер {worker_id}: {url}")
                    self.logger.info(f"   Товар: {result.get('product_name', 'Не найдено')}")
                    self.logger.info(f"   Компания: {result.get('company_name', 'Не найдено')}")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка в воркере {worker_id}: {str(e)}")
                    # Сохраняем результат с ошибкой
                    with self.results_lock:
                        self.results.append({
                            'url': url,
                            'product_name': f"Ошибка: {str(e)}",
                            'company_name': 'Не найдено',
                            'image_url': 'Не найдено',
                            'status': 'error'
                        })
                        self.processed_count += 1
                
                # Небольшая пауза между обработкой URL
                time.sleep(0.3)
                
        except Exception as e:
            self.logger.error(f"Ошибка в воркере {worker_id}: {str(e)}")
        finally:
            # Закрываем драйвер воркера
            try:
                driver.quit()
                self.driver_manager.remove_driver(driver)
            except Exception as e:
                self.logger.warning(f"Ошибка при закрытии драйвера в воркере {worker_id}: {str(e)}")
            
            self.logger.info(f"Воркер {worker_id} завершил работу")


    def distribute_urls(self, urls):
        """Распределение URL между воркерами"""
        urls_per_worker = [[] for _ in range(self.worker_count)]
        
        # Распределяем URL между воркерами
        for i, url in enumerate(urls):
            worker_index = i % self.worker_count
            urls_per_worker[worker_index].append(url)
            
        return urls_per_worker

    def run(self, urls):
        """Запуск парсинга"""
        self.total_urls = len(urls)
        if not urls:
            self.logger.error("Нет URL для обработки")
            return False
        
        start_time = time.time()
        self.logger.info(f"Начало обработки {self.total_urls} товаров")
        
        # Распределяем URL между воркерами
        urls_per_worker = self.distribute_urls(urls)
        
        # Запуск воркеров
        workers = []
        for i in range(self.worker_count):
            worker_urls = urls_per_worker[i]
            if worker_urls:
                worker_thread = threading.Thread(
                    target=self.worker,
                    args=(worker_urls, i+1),
                    daemon=True
                )
                worker_thread.start()
                workers.append(worker_thread)
                time.sleep(1)  # Пауза между запуском воркеров
        
        # Ожидание завершения воркеров
        try:
            for worker in workers:
                worker.join()
        except KeyboardInterrupt:
            self.stop_event.set()
            self.logger.warning("Получен сигнал прерывания!")
            
            for worker in workers:
                worker.join(timeout=5)
        
        # Сохранение результатов
        success = self.excel_exporter.save_results(self.results)
        duration = time.time() - start_time
        
        if success:
            self.logger.info(f"Обработка завершена успешно за {duration:.2f} секунд")
            self.logger.info(f"Обработано товаров: {len(self.results)}")
            self.logger.info(f"Файл сохранен: {self.excel_filename}")
        else:
            self.logger.error(f"Ошибка при сохранении результатов")
            
        return success

    def get_results_summary(self):
        """Получение сводки результатов"""
        return {
            'total': len(self.results),
            'processed': self.processed_count,
            'excel_file': self.excel_filename
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