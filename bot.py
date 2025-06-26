import os
import asyncio
import logging
import re
import queue
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
import time
from config import (
    CHROMEDRIVER_PATH, 
    LOG_FILE, 
    WORKER_COUNT, 
    LINKS_OUTPUT_FILE, 
    TOTAL_LINKS,
    RESULTS_DIR,
    get_timestamp,
    get_category_name,
    TELEGRAM_CHAT_ID  # Добавлено в config.py
)
from link_parser import OzonLinkParser
from product_parser import OzonProductParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_bot')

# Конфигурация бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не указан TELEGRAM_BOT_TOKEN в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния FSM
class ParserState(StatesGroup):
    waiting_url = State()

# Очередь для передачи логов между потоками
log_queue = queue.Queue()

# Кастомный обработчик логов для записи в очередь
class QueueLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_queue.put(log_entry)

# Настройка кастомного обработчика
handler = QueueLogHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)

# Фильтр для значимых логов
def is_significant_log(log_entry):
    keywords = [
        'Найдено новых ссылок:',
        'Начальное количество ссылок:',
        'Всего ссылок:',
        '=== ЭТАП',
        'Количество товаров:',
        'Количество воркеров:',
        'Файл результатов:',
        'Начало обработки',
        'Воркер',
        'завершил работу',
        'Обработка завершена',
        'Средняя скорость:',
        'Все браузеры закрыты',
        'УСПЕШНО:',
        'ЗАКОНЧИЛСЯ',
        'ОШИБКА'
    ]
    return any(keyword in log_entry for keyword in keywords)

# Отправщик логов в Telegram с обновлением одного сообщения
async def log_updater(chat_id: int):
    message = None
    log_buffer = []
    last_update = 0
    
    while True:
        try:
            # Собираем новые логи
            new_logs = []
            while not log_queue.empty():
                log_entry = log_queue.get_nowait()
                if is_significant_log(log_entry):
                    new_logs.append(log_entry)
                log_queue.task_done()
            
            # Добавляем новые логи в буфер
            if new_logs:
                log_buffer.extend(new_logs)
                
                # Ограничиваем буфер последними 15 записями
                if len(log_buffer) > 15:
                    log_buffer = log_buffer[-15:]
                
                # Формируем текст сообщения
                log_text = "\n".join(log_buffer)
                message_text = f"```\n{log_text}\n```"
                
                # Обновляем или создаем сообщение
                current_time = time.time()
                if message and current_time - last_update > 2:
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message.message_id,
                            text=message_text,
                            parse_mode="Markdown"
                        )
                        last_update = current_time
                    except Exception:
                        # Если не удалось обновить, создаем новое сообщение
                        message = None
                
                if not message:
                    message = await bot.send_message(
                        chat_id, 
                        message_text, 
                        parse_mode="Markdown"
                    )
                    last_update = current_time
            
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка обновления логов: {e}")
            await asyncio.sleep(5)

# Проверка доступа
def check_access(user_id: int):
    return user_id == int(TELEGRAM_CHAT_ID)

# Функция для запуска парсера (синхронная)
def run_parser(url: str, user_id: int):
    try:
        # Этап 1: Парсинг ссылок
        logger.info(f"Начало парсинга ссылок для {url}")
        link_parser = OzonLinkParser(url)
        success, product_urls = link_parser.run()
        
        if not success or not product_urls:
            logger.error("Не удалось собрать ссылки")
            return None
        
        # Этап 2: Парсинг товаров
        category_name = get_category_name(url)
        logger.info(f"Начало парсинга {len(product_urls)} товаров")
        
        # Создаем уникальное имя файла с ID пользователя
        timestamp = datetime.now().strftime("%d.%m.%Y-%H_%M_%S")
        filename = f"{category_name}_{user_id}_{timestamp}.xlsx"
        excel_path = os.path.join(RESULTS_DIR, filename)
        
        # Модифицируем парсер для использования нового пути
        product_parser = OzonProductParser(category_name)
        product_parser.excel_filename = excel_path
        
        if product_parser.run(product_urls):
            logger.info(f"Файл результатов создан: {excel_path}")
            return excel_path
        return None
    except Exception as e:
        logger.exception(f"Критическая ошибка парсера: {e}")
        return None

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("⛔ Вам доступ к боту ограничен")
        return
        
    welcome_text = (
        "👋 Добро пожаловать в Ozon Parser Bot!\n\n"
        "Я могу собрать для вас данные о товарах с Ozon. "
        "Для начала работы отправьте команду /parse или нажмите кнопку ниже."
    )
    kb = [[types.KeyboardButton(text="🔄 Парсить")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(welcome_text, reply_markup=keyboard)

# Команда /parse
@dp.message(Command("parse"))
@dp.message(F.text.lower() == "🔄 парсить")
async def cmd_parse(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        await message.answer("⛔ Вам доступ к боту ограничен")
        return
        
    await state.set_state(ParserState.waiting_url)
    await message.answer(
        "Введите ссылку на категорию Ozon:\n\n"
        "Примеры:\n"
        "- https://www.ozon.ru/category/sistemnye-bloki-15704/\n"
        "- https://uz.ozon.com/category/kompyuternye-i-ofisnye-kresla-38450/",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработчик ссылок
@dp.message(ParserState.waiting_url)
async def process_url(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        await message.answer("⛔ Вам доступ к боту ограничен")
        return
        
    url = message.text.strip()
    
    # Валидация URL
    if not re.search(r'([a-z]+\.)?ozon\.(ru|kz|com|by|uz)', url, re.IGNORECASE):
        await message.answer("❌ Некорректный URL! Используйте ссылку на категорию Ozon.")
        return
    
    if "/category/" not in url:
        await message.answer("❌ Ссылка должна вести на категорию товаров Ozon.")
        return
    
    await state.clear()
    msg = await message.answer("⏳ Начинаю парсинг... Это может занять несколько минут")
    
    # Запускаем обновление логов
    log_task = asyncio.create_task(log_updater(message.chat.id))
    
    try:
        # Запускаем парсер в отдельном потоке
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(
            None, 
            run_parser, 
            url, 
            message.from_user.id
        )
        
        if not file_path:
            await message.answer("❌ Произошла ошибка при парсинге. Подробности в логах.")
            return
        
        # Отправляем файл
        await message.answer("✅ Парсинг успешно завершен! Отправляю файл...")
        await message.answer_document(FSInputFile(file_path))
        
        # Удаляем файл через 10 секунд
        await asyncio.sleep(10)
        try:
            os.remove(file_path)
            logger.info(f"Файл удален: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")
            
    finally:
        log_task.cancel()
        try:
            await log_task
        except asyncio.CancelledError:
            pass

# Фильтр для проверки доступа
@dp.message(F.chat.id != TELEGRAM_CHAT_ID)
async def handle_unauthorized(message: types.Message):
    await message.answer("⛔ Извините, вам недоступен этот бот")

# Запуск бота
async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())