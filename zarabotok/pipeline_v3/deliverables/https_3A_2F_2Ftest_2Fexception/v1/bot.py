import asyncio
from pathlib import Path
from typing import Callable, Any

import telebot
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, ContextTypes,
    filters, Command, ConversationHandler,
)

# Импорт из внутренних модулей проекта
from handlers.exceptions import ExceptionHandler, ErrorHandlerConfig
from config.settings import BotSettings, get_settings
from utils.logger import Logger, LogLevel
from models.error_types import ErrorType, ErrorCode


class BotInitializer:
    """Класс инициализации бота с обработкой команд и настройкой."""

    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.bot = telebot.TeleBot(settings.token)
        self.logger = Logger(
            name="bot", 
            level=settings.log_level,
            file_path=f"{settings.data_dir}/logs/bot_{settings.version}.log"
        )
        self.exception_handler = ExceptionHandler(config=ErrorHandlerConfig())

    def _register_command_handlers(self):
        """Регистрация обработчиков команд."""
        
        # Команды управления ботом
        help_handler = CommandHandler("help", self._handle_help)
        start_handler = CommandHandler("start", self._handle_start)
        about_handler = CommandHandler("about", self._handle_about)
        
        # Команда для обработки URL из <tz>
        tz_handler = CommandHandler("tz", self._handle_tz_command)
        
        # Обработчик исключений
        exception_cmd = CommandHandler("exception", self._handle_exception)
        
        return [help_handler, start_handler, about_handler, tz_handler, exception_cmd]

    def _register_message_handlers(self):
        """Регистрация обработчиков обычных сообщений."""
        
        # Обработчик текстовых сообщений
        text_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_text_message
        )
        
        # Обработчик URL (для анализа из <tz>)
        url_handler = MessageHandler(
            filters.Regex(r"https?://.*"),
            self._handle_url_message
        )
        
        return [text_handler, url_handler]

    def _register_callback_handlers(self):
        """Регистрация обработчиков кнопок."""
        
        # Кнопки для меню помощи
        help_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Помощь", callback_data="help_main")],
            [InlineKeyboardButton("О боте", callback_data="about_main")]
        ])

        def _handle_help_callback(update: Update, query: CallbackQuery):
            """Обработчик кнопки помощи."""
            self.logger.info(f"Callback help pressed by user {query.from_user.id}")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Полная помощь", callback_data="help_full")],
                [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
            ])
            
            query.edit_message_text(
                "Выберите действие:",
                reply_markup=keyboard
            )

        def _handle_about_callback(update: Update, query: CallbackQuery):
            """Обработчик кнопки о боте."""
            self.logger.info(f"Callback about pressed by user {query.from_user.id}")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Техническая информация", callback_data="about_tech")],
                [InlineKeyboardButton("Вернуться назад", callback_data="about_main")]
            ])
            
            query.edit_message_text(
                "Информация о боте:\n\n"
                f"Версия: {self.settings.version}\n"
                f"Токен установлен: Да\n"
                f"Лог-уровень: {self.settings.log_level}",
                reply_markup=keyboard
            )

        def _handle_tz_callback(update: Update, query: CallbackQuery):
            """Обработчик кнопки TZ."""
            self.logger.info(f"Callback tz pressed by user {query.from_user.id}")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Полная информация", callback_data="tz_full")],
                [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
            ])
            
            query.edit_message_text(
                "Информация о команде TZ:\n\n"
                "Обработчик URL для анализа ссылок из тестового окружения.",
                reply_markup=keyboard
            )

        def _handle_exception_callback(update: Update, query: CallbackQuery):
            """Обработчик кнопки exception."""
            self.logger.info(f"Callback exception pressed by user {query.from_user.id}")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Полная информация", callback_data="exception_full")],
                [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
            ])
            
            query.edit_message_text(
                "Информация об обработке исключений:\n\n"
                "Модуль для обработки ошибок в асинхронных задачах бота.",
                reply_markup=keyboard
            )

        return [
            CallbackQueryHandler(_handle_help_callback, pattern="help_"),
            CallbackQueryHandler(_handle_about_callback, pattern="about_"),
            CallbackQueryHandler(_handle_tz_callback, pattern="tz_"),
            CallbackQueryHandler(_handle_exception_callback, pattern="exception_"),
        ]

    def _handle_help(self, update: Update) -> None:
        """Обработчик команды help."""
        self.logger.info(f"Command 'help' executed by user {update.effective_user.id}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Помощь", callback_data="help_main")],
            [InlineKeyboardButton("О боте", callback_data="about_main")],
            [InlineKeyboardButton("TZ Команда", callback_data="tz_full")],
            [InlineKeyboardButton("Exception", callback_data="exception_full")]
        ])
        
        update.effective_message.reply_text(
            "Добро пожаловать! Выберите раздел помощи:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _handle_start(self, update: Update) -> None:
        """Обработчик команды start."""
        self.logger.info(f"Command 'start' executed by user {update.effective_user.id}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать работу", callback_data="help_main")],
            [InlineKeyboardButton("Получить помощь", callback_data="about_tech")]
        ])
        
        update.effective_message.reply_text(
            "Бот инициализирован успешно!\n\n"
            "Нажмите кнопку ниже для начала работы:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _handle_about(self, update: Update) -> None:
        """Обработчик команды about."""
        self.logger.info(f"Command 'about' executed by user {update.effective_user.id}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Техническая информация", callback_data="about_tech")],
            [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
        ])
        
        update.effective_message.reply_text(
            "Информация о боте:\n\n"
            f"Версия: {self.settings.version}\n"
            f"Токен установлен: Да\n"
            f"Лог-уровень: {self.settings.log_level}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _handle_tz_command(self, update: Update) -> None:
        """Обработчик команды tz."""
        self.logger.info(f"Command 'tz' executed by user {update.effective_user.id}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Полная информация", callback_data="tz_full")],
            [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
        ])
        
        update.effective_message.reply_text(
            "Информация о команде TZ:\n\n"
            "Обработчик URL для анализа ссылок из тестового окружения.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _handle_exception(self, update: Update) -> None:
        """Обработчик команды exception."""
        self.logger.info(f"Command 'exception' executed by user {update.effective_user.id}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Полная информация", callback_data="exception_full")],
            [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
        ])
        
        update.effective_message.reply_text(
            "Информация об обработке исключений:\n\n"
            "Модуль для обработки ошибок в асинхронных задачах бота.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _handle_text_message(self, update: Update) -> None:
        """Обработчик текстовых сообщений."""
        self.logger.info(f"Text message received from user {update.effective_user.id}")
        
        text = update.effective_message.text or ""
        
        if len(text.strip()) > 1024:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Показать полностью", callback_data="show_full")]
            ])
            
            update.effective_message.reply_text(
                "Сообщение слишком длинное. Нажмите кнопку для просмотра:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            update.effective_message.reply_text(f"Вы написали:\n\n{text}")

    def _handle_url_message(self, update: Update) -> None:
        """Обработчик URL сообщений."""
        self.logger.info(f"URL message received from user {update.effective_user.id}")
        
        url = update.effective_message.text or ""
        
        # Извлечение домена из URL
        try:
            domain = url.split("//")[-1].split("/")[0] if "//" in url else url
            self.logger.info(f"Parsed domain: {domain}")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Анализировать URL", callback_data="analyze_url")]
            ])
            
            update.effective_message.reply_text(
                f"Обнаружен URL:\n\n{url}\n\nДомен: {domain}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Error parsing URL: {e}")
            update.effective_message.reply_text(
                "Произошла ошибка при анализе URL.",
                parse_mode='Markdown'
            )

    def _handle_callback_query(self, query: CallbackQuery) -> None:
        """Обработчик общих callback-запросов."""
        self.logger.info(f"Callback query from user {query.from_user.id}: {query.data}")
        
        data = query.data or ""
        
        if "show_full" in data:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
            ])
            
            query.edit_message_text(
                f"Полный текст сообщения:\n\n{query.message.text}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    def _handle_callback_query(self, query: CallbackQuery) -> None:
        """Обработчик callback-запросов."""
        self.logger.info(f"Callback query from user {query.from_user.id}: {query.data}")
        
        data = query.data or ""
        
        if "show_full" in data:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Вернуться назад", callback_data="help_main")]
            ])
            
            query.edit_message_text(
                f"Полный текст сообщения:\n\n{query.message.text}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    def run(self) -> None:
        """Запуск бота."""
        self.logger.info("Starting bot initialization...")
        
        # Создание приложения
        app = ApplicationBuilder().token(self.settings.token).build()
        
        # Регистрация обработчиков команд
        command_handlers = self._register_command_handlers()
        
        # Регистрация обработчиков сообщений
        message_handlers = self._register_message_handlers()
        
        # Регистрация callback-обработчиков
        callback_handlers = self._register_callback_handlers()
        
        # Добавление всех обработчиков в приложение
        for handler in command_handlers:
            app.add_handler(handler)
        
        for handler in message_handlers:
            app.add_handler(handler)
        
        for handler in callback_handlers:
            app.add_handler(handler)
        
        # Обработчик для общих callback-запросов
        app.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        self.logger.info("All handlers registered successfully")
        
        # Запуск приложения
        self.logger.info(f"Bot started with token: {self.settings.token[:20]}...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    def stop(self) -> None:
        """Остановка бота."""
        self.logger.info("Stopping bot...")
        
        # Очистка обработчиков
        for handler in command_handlers:
            try:
                app.remove_handler(handler)
            except Exception as e:
                self.logger.error(f"Error removing command handler: {e}")
        
        for handler in message_handlers:
            try:
                app.remove_handler(handler)
            except Exception as e:
                self.logger.error(f"Error removing message handler: {e}")
        
        for handler in callback_handlers:
            try:
                app.remove_handler(handler)
            except Exception as e:
                self.logger.error(f"Error removing callback handler: {e}")
        
        # Остановка приложения
        app.stop_polling()
        self.logger.info("Bot stopped successfully")


# Глобальная переменная для доступа к экземпляру бота
_bot_instance: BotInitializer = None

def get_bot_initializer(settings: BotSettings | None = None) -> BotInitializer:
    """Получение или создание экземпляра инициализатора бота."""
    global _bot_instance
    
    if _bot_instance is not None:
        return _bot_instance
    
    if settings is None:
        settings = get_settings()
    
    _bot_instance = BotInitializer(settings)
    return _bot_instance


def start_bot() -> None:
    """Запуск бота."""
    bot = get_bot_initializer()
    bot.run()


def stop_bot() -> None:
    """Остановка бота."""
    if _bot_instance is not None:
        _bot_instance.stop()


# Точка входа для запуска при импорте файла
if __name__ == "__main__":
    try:
        bot = get_bot_initializer()
        print(f"Bot initialized with version: {bot.settings.version}")
        print("Press Ctrl+C to stop the bot")
        
        # Запуск бота в бесконечном цикле для обработки Ctrl+C
        while True:
            asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()
