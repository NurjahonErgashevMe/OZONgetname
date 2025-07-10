"""
Обработчики команд Telegram бота
"""
import asyncio
import logging
import os

from aiogram import Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest

from .config import TELEGRAM_CHAT_ID
from .states import ParserState
from .keywords import BOT_MESSAGES, KEYBOARD_BUTTONS
from .utils import (
    check_access, 
    validate_ozon_url, 
    validate_product_links,
    run_parser_sync, 
    run_product_parser_sync,
    cleanup_file
)
from .logging_handler import LogUpdater
from .file_utils import validate_file_for_telegram, compress_file
from src.config import LINKS_OUTPUT_FILE

logger = logging.getLogger(__name__)


class BotHandlers:
    """Класс для обработки команд бота"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    def _get_main_menu_keyboard(self):
        """Возвращает основную клавиатуру меню"""
        kb = [
            [KeyboardButton(text=KEYBOARD_BUTTONS['parse'])],
            [KeyboardButton(text=KEYBOARD_BUTTONS['parse_products'])]
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    def _get_post_parsing_menu_keyboard(self):
        """Возвращает клавиатуру с действиями после парсинга"""
        kb = [
            [KeyboardButton(text="🔄 Новый парсинг"), KeyboardButton(text="📊 Парсить товары")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="🏠 Главное меню")]
        ]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    async def cmd_start(self, message: types.Message):
        """
        Обработчик команды /start
        
        Args:
            message: Сообщение пользователя
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        keyboard = self._get_main_menu_keyboard()
        await message.answer(BOT_MESSAGES['welcome'], reply_markup=keyboard)
    
    async def cmd_parse(self, message: types.Message, state: FSMContext):
        """
        Обработчик команды /parse
        
        Args:
            message: Сообщение пользователя
            state: Состояние FSM
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        await state.set_state(ParserState.waiting_url)
        await message.answer(
            BOT_MESSAGES['parse_request'],
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def cmd_parse_products(self, message: types.Message, state: FSMContext):
        """
        Обработчик команды /parse_products
        
        Args:
            message: Сообщение пользователя
            state: Состояние FSM
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        await state.set_state(ParserState.waiting_product_links)
        await message.answer(
            BOT_MESSAGES['parse_products_request'],
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def handle_menu_actions(self, message: types.Message, state: FSMContext):
        """
        Обработчик действий из меню после парсинга
        
        Args:
            message: Сообщение пользователя
            state: Состояние FSM
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        text = message.text.lower()
        
        if text == "🔄 новый парсинг":
            await self.cmd_parse(message, state)
        elif text == "📊 парсить товары":
            await self.cmd_parse_products(message, state)
        elif text == "ℹ️ помощь":
            help_text = (
                "🤖 <b>Помощь по использованию бота</b>\n\n"
                "📋 <b>Доступные команды:</b>\n"
                "• <b>Парсить категорию</b> - парсинг товаров из категории Ozon\n"
                "• <b>Парсить товары</b> - парсинг конкретных товаров по ссылкам\n\n"
                "🔗 <b>Форматы ссылок:</b>\n"
                "• Для категорий: ссылки на категории Ozon\n"
                "• Для товаров: по одной ссылке на строку\n\n"
                "📊 <b>Результаты:</b>\n"
                "• Excel файл с данными о товарах\n"
                "• Файл со ссылками (при парсинге категорий)\n\n"
                "⚠️ <b>Ограничения:</b>\n"
                "• Максимальный размер файла: 50MB\n"
                "• Большие файлы автоматически сжимаются"
            )
            await message.answer(help_text, parse_mode="HTML")
        elif text == "🏠 главное меню":
            keyboard = self._get_main_menu_keyboard()
            await message.answer("🏠 Главное меню", reply_markup=keyboard)
    
    async def process_url(self, message: types.Message, state: FSMContext):
        """
        Обработчик URL для парсинга категории
        
        Args:
            message: Сообщение с URL
            state: Состояние FSM
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        url = message.text.strip()
        
        # Валидация URL
        is_valid, error_key = validate_ozon_url(url)
        if not is_valid:
            await message.answer(BOT_MESSAGES[error_key])
            return
        
        await state.clear()
        await message.answer(BOT_MESSAGES['parsing_start'])
        
        # Запускаем обновление логов
        log_updater = LogUpdater(self.bot)
        log_task = asyncio.create_task(log_updater.start(message.chat.id))
        
        try:
            # Запускаем парсер категории в отдельном потоке
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(
                None, 
                run_parser_sync, 
                url, 
                message.from_user.id
            )
            
            if not file_path:
                await message.answer(BOT_MESSAGES['parsing_error'])
                return
            
            # Отправляем основной файл
            await self._send_parsing_results(message, file_path)
            
            # Ищем и отправляем links.json
            await self._send_links_file(message, file_path)
            
            # Показываем меню с действиями после парсинга
            await self._show_post_parsing_menu(message)
                
        except Exception as e:
            logger.exception(f"Ошибка при обработке URL: {e}")
            await message.answer(BOT_MESSAGES['parsing_error'])
        finally:
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass
    
    async def process_product_links(self, message: types.Message, state: FSMContext):
        """
        Обработчик ссылок на товары для парсинга
        
        Args:
            message: Сообщение со ссылками
            state: Состояние FSM
        """
        if not check_access(message.from_user.id):
            await message.answer(BOT_MESSAGES['access_denied'])
            return
        
        text = message.text.strip()
        
        # Валидация ссылок
        is_valid, error_key, valid_links = validate_product_links(text)
        if not is_valid:
            await message.answer(BOT_MESSAGES[error_key])
            return
        
        await state.clear()
        await message.answer(
            f"🚀 Парсинг товаров запущен...\n"
            f"📦 Найдено {len(valid_links)} валидных ссылок\n"
            f"📊 Следите за обновлениями в реальном времени"
        )
        
        # Запускаем обновление логов
        log_updater = LogUpdater(self.bot)
        log_task = asyncio.create_task(log_updater.start(message.chat.id))
        
        try:
            # Запускаем парсер товаров в отдельном потоке
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(
                None, 
                run_product_parser_sync, 
                valid_links, 
                message.from_user.id
            )
            
            if not file_path:
                await message.answer(BOT_MESSAGES['parsing_error'])
                return
            
            # Отправляем файл с результатами
            await self._send_parsing_results(message, file_path)
            
            # Показываем меню с действиями после парсинга
            await self._show_post_parsing_menu(message)
                
        except Exception as e:
            logger.exception(f"Ошибка при обработке ссылок на товары: {e}")
            await message.answer(BOT_MESSAGES['parsing_error'])
        finally:
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass
    
    async def _show_post_parsing_menu(self, message: types.Message):
        """
        Показывает меню с действиями после завершения парсинга
        
        Args:
            message: Сообщение для ответа
        """
        keyboard = self._get_post_parsing_menu_keyboard()
        menu_text = (
            "🎉 <b>Парсинг успешно завершен!</b>\n\n"
            "💡 <b>Что хотите сделать дальше?</b>\n"
            "• 🔄 <b>Новый парсинг</b> - парсить другую категорию\n"
            "• 📊 <b>Парсить товары</b> - парсить конкретные товары\n"
            "• ℹ️ <b>Помощь</b> - получить справку\n"
            "• 🏠 <b>Главное меню</b> - вернуться к началу"
        )
        await message.answer(menu_text, reply_markup=keyboard, parse_mode="HTML")
    
    async def _send_parsing_results(self, message: types.Message, file_path: str):
        """
        Отправляет результаты парсинга
        
        Args:
            message: Сообщение для ответа
            file_path: Путь к файлу с результатами
        """
        # Отправляем файл с обработкой ошибок
        filename = os.path.basename(file_path)
        await message.answer(f"✅ Парсинг завершен!\n📄 Файл: {filename}")
        
        # Проверяем возможность отправки файла
        can_send, reason, size_mb = validate_file_for_telegram(file_path)
        
        if not can_send:
            if "слишком большой" in reason:
                # Пытаемся сжать файл
                await message.answer(f"📦 Файл большой ({size_mb:.1f}MB), сжимаю...")
                zip_path = compress_file(file_path)
                
                if zip_path:
                    can_send_zip, reason_zip, size_zip_mb = validate_file_for_telegram(zip_path)
                    if can_send_zip:
                        await message.answer(f"📤 Отправляю сжатый файл ({size_zip_mb:.1f}MB)...")
                        await self._send_document_with_retry(message, zip_path, max_retries=3)
                        asyncio.create_task(cleanup_file(zip_path))
                    else:
                        await message.answer(f"❌ Даже сжатый файл слишком большой ({size_zip_mb:.1f}MB)")
                else:
                    await message.answer("❌ Не удалось сжать файл")
            else:
                await message.answer(f"❌ {reason}")
        else:
            # Файл можно отправить как есть
            await message.answer(f"📤 Отправляю файл ({size_mb:.1f}MB)...")
            await self._send_document_with_retry(message, file_path, max_retries=3)
        
        # Планируем удаление файла
        asyncio.create_task(cleanup_file(file_path))

    async def _send_links_file(self, message: types.Message, main_file_path: str):
        """
        Отправляет файл LINKS_OUTPUT_FILE если он существует в той же директории
        
        Args:
            message: Сообщение для ответа
            main_file_path: Путь к основному файлу Excel
        """
        try:
            # Получаем директорию основного файла
            links_file_path = os.path.join(os.getcwd(), LINKS_OUTPUT_FILE)
            
            # Проверяем существование файла LINKS_OUTPUT_FILE
            if os.path.exists(links_file_path):
                # Проверяем размер файла
                can_send, reason, size_mb = validate_file_for_telegram(links_file_path)
                
                if can_send:
                    await message.answer(f"📤 Отправляю файл со ссылками ({size_mb:.1f}MB)...")
                    await self._send_document_with_retry(message, links_file_path, max_retries=3)
                    # Планируем удаление файла links.json
                    asyncio.create_task(cleanup_file(links_file_path))
                else:
                    await message.answer(f"❌ Файл links.json {reason}")
            else:
                logger.info(f"Файл {LINKS_OUTPUT_FILE} не найден")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке файла links.json: {e}")
            await message.answer("⚠️ Не удалось отправить файл со ссылками")

    async def _send_document_with_retry(self, message: types.Message, file_path: str, max_retries: int = 3):
        """
        Отправляет документ с повторными попытками
        
        Args:
            message: Сообщение для ответа
            file_path: Путь к файлу
            max_retries: Максимальное количество попыток
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Проверяем, что файл существует
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Файл не найден: {file_path}")
                
                # Создаем InputFile каждый раз заново
                input_file = FSInputFile(file_path)
                
                # Определяем тип файла для подписи
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension == '.txt' or file_extension == '.json':
                    caption = f"🔗 Файл со ссылками\n📄 {os.path.basename(file_path)}"
                else:
                    caption = f"📊 Результаты парсинга\n📄 {os.path.basename(file_path)}"
                
                # Отправляем файл
                await message.answer_document(
                    input_file,
                    caption=caption
                )
                
                logger.info(f"Файл успешно отправлен: {file_path}")
                return
                
            except (TelegramNetworkError, TelegramBadRequest) as e:
                last_error = e
                logger.warning(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 10)  # Максимум 10 секунд задержки
                    await message.answer(f"⏳ Ошибка сети, повторяю через {delay}с...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                last_error = e
                logger.error(f"Непредвиденная ошибка при отправке файла (попытка {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    
        # Если все попытки неудачны
        raise last_error or Exception("Не удалось отправить файл после всех попыток")
    
    async def handle_unauthorized(self, message: types.Message):
        """
        Обработчик неавторизованных пользователей
        
        Args:
            message: Сообщение пользователя
        """
        await message.answer(BOT_MESSAGES['unauthorized'])


