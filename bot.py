import asyncio
import threading
import tkinter.messagebox as messagebox
import os
import tkinter as tk
from aiogram import Bot, Dispatcher
from src.bot.register_handlers import register_handlers

class BotManager:
    def __init__(self, root, log_manager, utils):
        self.root = root
        self.log_manager = log_manager
        self.utils = utils
        self.is_bot_running = False
        self.bot_status_var = tk.StringVar(value="🔴 Остановлен")
        self.status_var = tk.StringVar(value="")
        self.start_btn = None
        self.stop_btn = None
        self.restart_btn = None
        self.bot = None
        self.dp = None
        self.bot_loop = None
    
    async def run_bot_async(self):
        try:
            config = self.utils.load_config_file(self.utils.get_config_path())
            token = config["TELEGRAM_BOT_TOKEN"]
            
            self.bot = Bot(token=token)
            self.dp = Dispatcher()
            register_handlers(self.dp, self.bot)
            
            self.log_manager.logger.info("Telegram бот инициализирован")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.log_manager.logger.error(f"Ошибка при запуске бота: {e}")
            self.root.after(0, self._bot_error_callback, str(e))
    
    def _bot_error_callback(self, error_msg):
        self.is_bot_running = False
        self.bot_status_var.set("❌ Ошибка")
        if self.start_btn:
            self.start_btn.config(state=tk.NORMAL)
        if self.stop_btn:
            self.stop_btn.config(state=tk.DISABLED)
        if self.restart_btn:
            self.restart_btn.config(state=tk.DISABLED)
        self.status_var.set(f"Ошибка бота: {error_msg}")

    def start_bot_thread(self):
        def run_bot():
            self.bot_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.bot_loop)
            try:
                self.bot_loop.run_until_complete(self.run_bot_async())
            except Exception as e:
                self.log_manager.logger.error(f"Ошибка в потоке бота: {e}")
            finally:
                self.bot_loop.close()
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
    
    def start_bot(self):
        self.log_manager.logger.info("Попытка запуска бота...")
        config_path = self.utils.get_config_path()
        if not os.path.exists(config_path):
            messagebox.showerror("Ошибка", "Сначала настройте конфигурацию!")
            return
        
        try:
            config = self.utils.load_config_file(config_path)
            if not config.get("TELEGRAM_BOT_TOKEN") or not config.get("TELEGRAM_CHAT_ID"):
                messagebox.showerror("Ошибка", "Некорректная конфигурация!")
                return
            
            self.is_bot_running = True
            self.bot_status_var.set("🟡 Запускается...")
            if self.start_btn:
                self.start_btn.config(state=tk.DISABLED)
            self.status_var.set("Запуск бота...")
            
            self.start_bot_thread()
            self.root.after(2000, self._update_bot_started_status)
        except Exception as e:
            self.log_manager.logger.error(f"Ошибка при запуске бота: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить бота: {e}")
            self.is_bot_running = False
            self.bot_status_var.set("🔴 Остановлен")
            if self.start_btn:
                self.start_btn.config(state=tk.NORMAL)
    
    def _update_bot_started_status(self):
        if self.is_bot_running:
            self.bot_status_var.set("🟢 Запущен")
            if self.stop_btn:
                self.stop_btn.config(state=tk.NORMAL)
            if self.restart_btn:
                self.restart_btn.config(state=tk.NORMAL)
            self.status_var.set("Бот запущен и готов к работе")
            self.log_manager.logger.info("Бот успешно запущен и готов к работе")

    def stop_bot(self):
        self.log_manager.logger.info("Остановка бота...")
        try:
            self.is_bot_running = False
            
            if self.bot_loop and not self.bot_loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._stop_bot_async(), self.bot_loop)
                self.root.after(1000, self._update_bot_stopped_status)
            else:
                self._update_bot_stopped_status()
        except Exception as e:
            self.log_manager.logger.error(f"Ошибка при остановке бота: {e}")
            self._update_bot_stopped_status()

    async def _stop_bot_async(self):
        try:
            if self.bot:
                await self.bot.session.close()
                self.log_manager.logger.info("Сессия бота закрыта")
        except Exception as e:
            self.log_manager.logger.error(f"Ошибка при закрытии сессии бота: {e}")

    def _update_bot_stopped_status(self):
        self.bot_status_var.set("🔴 Остановлен")
        if self.start_btn:
            self.start_btn.config(state=tk.NORMAL)
        if self.stop_btn:
            self.stop_btn.config(state=tk.DISABLED)
        if self.restart_btn:
            self.restart_btn.config(state=tk.DISABLED)
        self.status_var.set("Бот остановлен")
        self.log_manager.logger.info("Бот остановлен")
    
    def restart_bot(self):
        self.log_manager.logger.info("Перезапуск бота...")
        self.stop_bot()
        self.root.after(2000, self.start_bot)
