import logging
import os
from pathlib import Path
from typing import Optional, TextIO, Callable
from datetime import datetime
from enum import IntEnum


class Severity(IntEnum):
    """Уровни логирования с числовыми значениями для сравнения."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    @classmethod
    def from_string(cls, name: str) -> 'Severity':
        """Получить уровень по имени строкой."""
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"Неизвестный уровень severity: {name}")


class LogRotator:
    """Управление ротацией лог-файлов.

    Атрибуты:
        path (Path): Путь к директории логов
        max_size_mb (float): Максимальный размер файла в МБ перед ротацией
        backup_count (int): Количество резервных копий для хранения
    """
    
    def __init__(self, 
                 path: Path = None, 
                 max_size_mb: float = 10.0, 
                 backup_count: int = 5):
        self.path = path or Path(__file__).parent.parent / 'logs'
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.backup_count = backup_count
        
        # Создаём директорию, если не существует
        self.path.mkdir(parents=True, exist_ok=True)
    
    def _get_current_file(self) -> Path:
        """Получить путь к текущему активному файлу."""
        return self.path / 'app.log'
    
    def _rotate_if_needed(self) -> bool:
        """Проверить и выполнить ротацию, если файл слишком большой.

        Возвращает True, если ротация была выполнена.
        """
        current = self._get_current_file()
        
        if not current.exists():
            return False
        
        size_bytes = current.stat().st_size
        
        if size_bytes >= self.max_size_bytes:
            # Переименовываем текущий файл в резервный
            backup_name = f'app.{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            
            # Если уже есть такой бэкап, удаляем старый
            old_backup = self.path / backup_name
            if old_backup.exists():
                old_backup.unlink()
            
            current.rename(self.path / backup_name)
            return True
        
        return False
    
    def _cleanup_old_backups(self):
        """Удалить резервные копии, превышающие лимит."""
        pattern = f'app.*.log'
        
        # Сортируем по имени (время создания), старейшие первыми
        backups = sorted(
            self.path.glob(pattern), 
            key=lambda p: p.name
        )[:self.backup_count]
        
        for backup in backups[self.backup_count - 1 + 1:]:
            try:
                backup.unlink()
            except OSError:
                pass
    
    def _rotate(self):
        """Выполнить ротацию файла."""
        self._rotate_if_needed()
        self._cleanup_old_backups()


class LoggerAdapter(logging.LoggerAdapter):
    """Адаптер логгера для добавления контекста запроса/сессии."""
    
    def __init__(self, logger: logging.Logger, extra: dict = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Добавить контекст в сообщение."""
        if self.extra.get('request_id'):
            request_info = f"[{self.extra['request_id']}]"
            msg = f"{request_info} {msg}"
        
        return msg, kwargs


class ConsoleFormatter(logging.Formatter):
    """Форматтер для вывода в консоль с цветным кодированием."""
    
    COLORS = {
        Severity.DEBUG: '\033[94m',      # синий
        Severity.INFO: '\033[97m',       # белый
        Severity.WARNING: '\033[93m',     # жёлтый
        Severity.ERROR: '\033[91m',      # красный
        Severity.CRITICAL: '\033[95m',   # маджента
    }
    
    RESET = '\033[0m'
    
    def __init__(self, 
                 format_str: str = None,
                 level: Severity = Severity.INFO):
        super().__init__()
        
        if not format_str:
            default_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            self._format_str = datetime.now().strftime(default_format)
        else:
            self._format_str = format_str
        
        self.level = level
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматировать запись с цветным уровнем."""
        color = self.COLORS.get(record.levelno, '')
        
        # Создаём копию записи для форматирования
        formatted = super().format(record)
        
        # Добавляем цветной префикс уровня
        level_name = record.levelname[:4].upper()
        prefix = f"{color}[{level_name}]{self.RESET}"
        
        return f"{prefix} {formatted}"


class FileFormatter(ConsoleFormatter):
    """Форматтер для записи в файл (без цветов)."""
    
    def __init__(self, 
                 format_str: str = None,
                 level: Severity = Severity.DEBUG):
        super().__init__(format_str or "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s", level)


class Logger:
    """Централизованный логгер приложения."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(*args, **kwargs)
        
        return cls._instance
    
    def _init(self, 
              name: str = 'app',
              level: Severity = Severity.INFO,
              console_output: bool = True,
              file_output: bool = False,
              log_dir: Path = None):
        """Инициализировать логгер."""
        
        self.name = name
        self.level = level
        
        # Создаём базовый логгер
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level.value)
        
        # Добавляем обработчик для консоли
        if console_output:
            handler = logging.StreamHandler()
            formatter = ConsoleFormatter(format_str=None, level=level)
            handler.setFormatter(formatter)
            
            # Устанавливаем фильтр по уровню
            handler.addFilter(lambda record: record.levelno >= level.value)
            
            self._logger.addHandler(handler)
        
        # Добавляем обработчик для файла (если включено)
        if file_output and log_dir:
            rotator = LogRotator(path=log_dir, max_size_mb=10.0, backup_count=5)
            
            handler = logging.FileHandler(
                str(log_dir / 'app.log'), 
                encoding='utf-8'
            )
            formatter = FileFormatter(format_str=None, level=level)
            handler.setFormatter(formatter)
            
            # Устанавливаем фильтр по уровню
            handler.addFilter(lambda record: record.levelno >= level.value)
            
            self._logger.addHandler(handler)
        
        return self
    
    def info(self, msg: str, *args, **kwargs):
        """Логирование уровня INFO."""
        self._logger.info(msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        """Логирование уровня DEBUG."""
        self._logger.debug(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Логирование уровня WARNING."""
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Логирование уровня ERROR."""
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Логирование уровня CRITICAL."""
        self._logger.critical(msg, *args, **kwargs)
    
    def log(self, level: Severity, msg: str, *args, **kwargs):
        """Универсальный метод логирования с любым уровнем."""
        method_name = f"{level.name.lower()}"
        
        if hasattr(self._logger, method_name):
            getattr(self._logger, method_name)(msg, *args, **kwargs)


# Глобальная инициализация при импорте модуля
def setup_logger(
    name: str = 'app',
    level: Severity = Severity.INFO,
    console_output: bool = True,
    file_output: bool = False,
    log_dir: Path = None
) -> Logger:
    """Установить и вернуть глобальный логгер."""
    
    logger = Logger(
        name=name,
        level=level,
        console_output=console_output,
        file_output=file_output,
        log_dir=log_dir
    )
    
    return logger


# Экспорт публичного API
__all__ = [
    'Severity', 
    'LogRotator', 
    'ConsoleFormatter', 
    'FileFormatter', 
    'LoggerAdapter',
    'Logger',
    'setup_logger'
]
