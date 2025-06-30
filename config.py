import os
import tkinter.messagebox as messagebox
import tkinter as tk
import sys

class ConfigManager:
    def __init__(self):
        self.some_var = tk.StringVar(value="")
    def get_app_dir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    
    def get_config_path(self):
        return os.path.join(self.get_app_dir(), "config.txt")
    
    def load_existing_config(self):
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key == "TELEGRAM_BOT_TOKEN" and value:
                                self.token_entry.delete(0, tk.END)
                                self.token_entry.insert(0, value)
                            elif key == "TELEGRAM_CHAT_ID" and value:
                                self.chat_id_entry.delete(0, tk.END)
                                self.chat_id_entry.insert(0, value)
                self.status_var.set("Конфигурация загружена")
                self.update_config_info()
                self.logger.info("Конфигурация успешно загружена")
            except Exception as e:
                self.status_var.set(f"Ошибка загрузки: {e}")
                self.logger.error(f"Ошибка загрузки конфигурации: {e}")
    
    def save_config(self):
        token = self.token_entry.get().strip()
        chat_id = self.chat_id_entry.get().strip()
        
        if not token or not chat_id:
            messagebox.showerror("Ошибка", "Пожалуйста, заполните оба поля.")
            self.logger.warning("Попытка сохранения пустой конфигурации")
            return
        
        try:
            config_path = self.get_config_path()
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(f"TELEGRAM_BOT_TOKEN={token}\n")
                f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
            
            messagebox.showinfo("Успех", f"Настройки сохранены!")
            self.status_var.set("Конфигурация сохранена")
            self.update_config_info()
            self.logger.info("Конфигурация успешно сохранена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
            self.status_var.set("Ошибка сохранения")
            self.logger.error(f"Ошибка сохранения конфигурации: {e}")