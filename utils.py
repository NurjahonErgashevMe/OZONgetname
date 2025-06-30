import tkinter.messagebox as messagebox
import os
import tkinter as tk
import re

class Utils:
    def __init__(self, log_manager):
        self.logger = log_manager.logger

    def toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")

    def test_config(self):
        token = self.token_entry.get().strip()
        chat_id = self.chat_id_entry.get().strip()

        if not token or not chat_id:
            messagebox.showwarning("Предупреждение", "Заполните оба поля для проверки.")
            return

        issues = []
        if ':' not in token:
            issues.append("Токен должен содержать символ ':'")
        if len(token) < 35:
            issues.append("Токен слишком короткий")
        if not chat_id.lstrip('-').isdigit():
            issues.append("Chat ID должен быть числом (может начинаться с '-')")

        if issues:
            messagebox.showwarning("Проблемы", "\n".join(issues))
            self.logger.warning(f"Проблемы с конфигурацией: {', '.join(issues)}")
        else:
            messagebox.showinfo("Проверка", "Базовая проверка формата пройдена!")
            self.logger.info("Конфигурация прошла проверку")

        self.status_var.set("Проверка завершена")

    def load_config_file(self, config_path: str = None) -> dict:
        """
        Загружает конфигурацию из config.txt в корневой директории.
        Если файла нет, создаёт шаблонный файл и возвращает пустой словарь.
        """
        if config_path is None:
            config_path = self.get_config_path()

        self.logger.info(f"Загрузка конфигурации из {config_path}")

        if not os.path.exists(config_path):
            self.logger.warning(f"Файл конфигурации {config_path} не найден, создаётся шаблон")
            self.create_default_config(config_path)
            return {}

        config = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and line.strip():
                        key, value = line.strip().split("=", 1)
                        config[key] = value
            self.logger.debug(f"Конфигурация загружена: {config}")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке конфигурации: {e}")
            return {}

        return config
    
    def get_config_path(self):
        return os.path.join(os.getcwd(), "config.txt")

    def update_config_info(self):
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    token_set = any(
                        line.startswith("TELEGRAM_BOT_TOKEN=") and len(line.strip()) > len("TELEGRAM_BOT_TOKEN=")
                        for line in lines
                    )
                    chat_id_set = any(
                        line.startswith("TELEGRAM_CHAT_ID=") and len(line.strip()) > len("TELEGRAM_CHAT_ID=")
                        for line in lines
                    )

                    if token_set and chat_id_set:
                        self.config_info_var.set("✅ Конфигурация настроена")
                    else:
                        missing = []
                        if not token_set:
                            missing.append("токен")
                        if not chat_id_set:
                            missing.append("chat_id")
                        self.config_info_var.set(f"⚠️ Отсутствует: {', '.join(missing)}")
            except:
                self.config_info_var.set("❌ Ошибка чтения")
        else:
            self.config_info_var.set("❌ Файл не найден")
