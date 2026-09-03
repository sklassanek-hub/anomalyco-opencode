import logging
from typing import Any, Callable, Dict, Optional, Union

# Настройка логирования по умолчанию для модуля
logger = logging.getLogger(__name__)

# Типы данных для сообщений и ответов
MessageType = Union[str, bytes]
ResponseData = Dict[str, Any]

def create_response(text: str, data: Optional[Dict[str, Any]] = None) -> ResponseData:
    """Фабрика для создания стандартного JSON-ответа."""
    result: ResponseData = {"text": text}
    if data:
        result["data"] = data
    return result

def dispatch(message_type: str, payload: MessageType, context: Optional[Dict[str, Any]] = None) -> ResponseData:
    """
    Центральный роутинг входящих сообщений.
    
    Аргументы:
        message_type: Тип сообщения (например, 'command', 'text', 'media').
        payload: Содержимое сообщения.
        context: Дополнительный контекст (session_id, user_data).
        
    Возвращает:
        ResponseData: Готовый ответ для отправки пользователю.
    """
    try:
        # Определение обработчика на основе типа сообщения
        handler_map = {
            'command': handle_command,
            'text': handle_text_message,
            'media': handle_media_message,
            'error': handle_error_message,
        }

        if message_type in handler_map:
            return handler_map[message_type](payload, context)
        else:
            logger.warning(f"Unknown message type received: {message_type}")
            return create_response("System detected an unknown message format.", {"type": "system_warning"})

    except Exception as e:
        # Глобальная обработка ошибок внутри роутера
        error_msg = f"Routing error for type '{message_type}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_response("An internal system error occurred.", {"error": str(e)})

def handle_command(payload: MessageType, context: Optional[Dict[str, Any]] = None) -> ResponseData:
    """Обработчик команд (например, /start, /help)."""
    if not payload:
        return create_response("Command format is empty.")

    # Парсинг команды (пример для простого текстового парсинга)
    command_parts = payload.strip().split()
    cmd_name = command_parts[0].lower()

    if cmd_name == 'start':
        if not context:
            return create_response("Welcome! Please provide a session ID in the metadata.")
        # Логика инициализации сессии
        logger.info(f"Session started for {context.get('session_id')}")
        return create_response("Hello, user!", {"status": "active"})

    elif cmd_name == 'help':
        return create_response("Available commands: /start, /help", {"commands": ["start", "help"]})

    else:
        return create_response(f"Unknown command: {cmd_name}. Type /help for list.", {"unknown_cmd": cmd_name})

def handle_text_message(payload: MessageType, context: Optional[Dict[str, Any]] = None) -> ResponseData:
    """Обработчик обычных текстовых сообщений."""
    if not payload:
        return create_response("Message content is empty.")

    text_content = str(payload).strip()
    
    # Проверка на простые фразы-триггеры
    triggers = {
        "hello": "Hello back!",
        "bye": "See you soon.",
    }

    for trigger, response in triggers.items():
        if trigger in text_content.lower():
            return create_response(response)

    # Дефолтная реакция на текст
    return create_response(f"Received: {text_content[:50]}...", {"length": len(text_content)})

def handle_media_message(payload: MessageType, context: Optional[Dict[str, Any]] = None) -> ResponseData:
    """Обработчик медиа-контента (фото, видео)."""
    if not payload:
        return create_response("No media data attached.")

    # Пример обработки типа файла
    mime_type = getattr(payload, 'mime', 'application/octet-stream')
    
    if 'image' in mime_type.lower():
        return create_response("Image received and processed.", {"type": "image"})
    elif 'video' in mime_type.lower():
        return create_response("Video file detected.", {"type": "video"})
    else:
        return create_response(f"Media type {mime_type} handled generically.", {"type": "other_media"})

def handle_error_message(payload: MessageType, context: Optional[Dict[str, Any]] = None) -> ResponseData:
    """Обработчик ошибок API или сети."""
    if not payload:
        return create_response("Error payload missing.")

    error_code = getattr(payload, 'code', 0)
    description = str(payload).strip()

    logger.error(f"API Error: {description}")

    # Стратегия обработки в зависимости от кода ошибки
    if error_code == 429:
        return create_response("Rate limit exceeded. Try again later.", {"retry_after": 60})
    elif error_code in (400, 500):
        return create_response(f"Server responded with code {error_code}.", {"code": error_code})

    return create_response("General network or API error occurred.", {"details": description})
