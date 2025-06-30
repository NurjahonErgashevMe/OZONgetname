#!/usr/bin/env python3
"""
Главный файл для запуска Telegram бота
"""
import asyncio
from src.bot.bot_main import main

if __name__ == "__main__":
    asyncio.run(main())