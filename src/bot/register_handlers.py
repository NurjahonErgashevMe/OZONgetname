from .handlers import BotHandlers
from aiogram import Bot, types, F
from aiogram.filters import Command

from .keywords import KEYBOARD_BUTTONS
from .states import ParserState
from .config import TELEGRAM_CHAT_ID


def register_handlers(dp, bot: Bot):
    """
    Регистрирует обработчики команд
    
    Args:
        dp: Диспетчер
        bot: Экземпляр бота
    """
    handlers = BotHandlers(bot)
    
    # Команда /start
    dp.message.register(handlers.cmd_start, Command("start"))
    
    # Команда /parse и кнопка "Парсить категорию"
    dp.message.register(handlers.cmd_parse, Command("parse"))
    dp.message.register(
        handlers.cmd_parse, 
        F.text.lower() == KEYBOARD_BUTTONS['parse'].lower()
    )
    
    # Команда /parse_products и кнопка "Парсить товары"
    dp.message.register(handlers.cmd_parse_products, Command("parse_products"))
    dp.message.register(
        handlers.cmd_parse_products, 
        F.text.lower() == KEYBOARD_BUTTONS['parse_products'].lower()
    )
    
    # Обработчик действий из меню после парсинга
    dp.message.register(
        handlers.handle_menu_actions,
        F.text.in_([
            "🔄 Новый парсинг",
            "📊 Парсить товары", 
            "ℹ️ Помощь",
            "🏠 Главное меню"
        ])
    )
    
    # Обработчик URL для категории
    dp.message.register(handlers.process_url, ParserState.waiting_url)
    
    # Обработчик ссылок на товары
    dp.message.register(handlers.process_product_links, ParserState.waiting_product_links)
    
    # Фильтр для неавторизованных пользователей
    dp.message.register(
        handlers.handle_unauthorized, 
        F.chat.id != TELEGRAM_CHAT_ID
    )