"""
Состояния FSM для Telegram бота
"""
from aiogram.fsm.state import State, StatesGroup


class ParserState(StatesGroup):
    """Состояния парсера"""
    waiting_url = State()
    waiting_product_links = State() 