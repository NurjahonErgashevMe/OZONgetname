import tkinter as tk
import queue
from logs import LogManager
from utils import Utils
from bot import BotManager
from tabs import TabManager

class TelegramBotApp:
    def __init__(self):
        self.root = tk.Tk()
        self.log_queue = queue.Queue()
        
        # Инициализация компонентов
        self.log_manager = LogManager(self.root, self.log_queue, None)  # log_text будет установлен позже
        
        # ВАЖНО: Настраиваем логирование СРАЗУ после создания LogManager
        self.log_manager.setup_logging()
        
        self.utils = Utils(self.log_manager)
        
        # Создаем BotManager (теперь logger уже инициализирован)
        self.bot_manager = BotManager(self.root, self.log_manager, self.utils)
        
        # Создаем TabManager, передавая ему BotManager для связи методов
        self.tab_manager = TabManager(self.root, self.utils, self.log_manager, self.bot_manager)
        
        # Устанавливаем log_text из TabManager
        self.log_manager.log_text = self.tab_manager.log_text
        
        # Связываем BotManager с элементами интерфейса TabManager
        self.link_bot_manager_with_tabs()

        # Настройка пользовательского интерфейса
        self.setup_ui()

        # Запускаем обновление логов
        self.log_manager.update_logs()

    def link_bot_manager_with_tabs(self):
        """Связывает BotManager с элементами интерфейса TabManager"""
        # Передаем ссылки на кнопки и переменные статуса
        self.bot_manager.start_btn = self.tab_manager.start_btn
        self.bot_manager.stop_btn = self.tab_manager.stop_bot_btn
        self.bot_manager.restart_btn = self.tab_manager.restart_btn
        self.bot_manager.bot_status_var = self.tab_manager.bot_status_var
        self.bot_manager.status_var = self.tab_manager.status_var

    def setup_ui(self):
        """Настройка основного интерфейса приложения."""
        # TabManager уже настроил весь интерфейс
        pass

    def run(self):
        """Запуск приложения."""
        self.root.title("OZON Parser Manager")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Закрытие приложения."""
        if tk.messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            # Останавливаем бота перед закрытием
            if self.bot_manager.is_bot_running:
                self.bot_manager.stop_bot()
            self.root.destroy()

if __name__ == "__main__":
    app = TelegramBotApp()
    app.run()