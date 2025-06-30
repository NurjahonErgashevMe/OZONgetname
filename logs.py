import logging
import tkinter as tk
import queue

class QueueHandler(logging.Handler):
    """Custom logging handler that puts log records into a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        self.log_queue.put(self.format(record))

class LogManager:
    def __init__(self, root, log_queue, log_text):
        self.root = root
        self.log_queue = log_queue
        self.log_text = log_text
        self.logger = None

    def setup_logging(self):
        """Инициализация системы логирования."""
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики (если есть)
        self.logger.handlers.clear()
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Обработчик для GUI (через очередь)
        gui_handler = QueueHandler(self.log_queue)
        gui_handler.setFormatter(formatter)
        self.logger.addHandler(gui_handler)

        # Обработчик для файла
        try:
            file_handler = logging.FileHandler("application.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Не удалось создать файл логов: {e}")

        # Предотвращаем дублирование логов
        self.logger.propagate = False
        
        self.logger.info("Система логирования инициализирована")

    def update_logs(self):
        """Обновление логов в интерфейсе."""
        if self.log_text is None:
            self.root.after(100, self.update_logs)
            return
            
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, log_entry + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.update_logs)
    
    def clear_logs(self):
        """Очистка логов в интерфейсе."""
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
        if self.logger:
            self.logger.info("Логи очищены")
    
    def is_ready(self):
        """Проверяет, готов ли логгер к использованию."""
        return self.logger is not None
    
    def safe_log(self, level, message):
        """Безопасное логирование с проверкой готовности логгера."""
        if self.logger:
            getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")  # Fallback на print