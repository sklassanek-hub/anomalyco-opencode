import os
from pathlib import Path
from typing import Optional


class Settings:
    """Конфигурация приложения с разделением по окружениям."""
    
    # --- Базовые настройки ---
    APP_NAME = "ExceptionBot"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # --- Пути к файлам и директориям ---
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGS_DIR = BASE_DIR / "logs"
    DATA_DIR = BASE_DIR / "data"
    BACKUPS_DIR = BASE_DIR / "backups"
    
    # --- База данных (SQLite по умолчанию) ---
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")  # sqlite, postgresql, mysql
    
    if DB_TYPE == "sqlite":
        DB_PATH: Path = os.getenv(
            "DB_PATH", 
            BASE_DIR / "data" / "app.db"
        )
        DB_URL: str = f"sqlite:///{DB_PATH}"
    else:
        DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        DB_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))
        DB_NAME: str = os.getenv("POSTGRES_DB", "exception_bot")
        DB_USER: str = os.getenv("POSTGRES_USER", "postgres")
        DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
        
        if DB_TYPE == "postgresql":
            DB_URL: str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        else:  # mysql
            DB_URL: str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # --- Логирование ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    if not DEBUG:
        LOG_LEVEL = "WARNING"
    
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # --- API ключи и внешние сервисы ---
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_ID: Optional[int] = int(os.getenv("BOT_ID", "0")) if os.getenv("BOT_ID") else None
    
    TELEGRAM_API_URL: str = os.getenv(
        "TELEGRAM_API_URL", 
        "https://api.telegram.org/bot" + BOT_TOKEN
    )
    
    # --- Сессии и лимиты ---
    SESSION_TIMEOUT: int = 3600  # 1 час в секундах
    MAX_MESSAGE_LENGTH: int = 4096
    
    # --- Отладка и мониторинг ---
    MONITORING_ENABLED: bool = DEBUG
    METRICS_PORT: int = 8000
    METRICS_PATH: str = "/metrics"
    
    # --- Кэширование ---
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "redis")  # redis, memory
    
    if CACHE_TYPE == "redis":
        REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
        REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
        REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
        
        if REDIS_PASSWORD:
            REDIS_URL: str = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        else:
            REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:  # memory
        REDIS_URL: Optional[str] = None
    
    # --- Флаги функциональности ---
    ENABLE_WEBHOOKS: bool = DEBUG
    ALLOW_PRIVATE_MESSAGES: bool = True
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    
    # --- Валидация обязательных переменных окружения ---
    REQUIRED_ENV_VARS = [
        "BOT_TOKEN"
    ]
    
    for var in REQUIRED_ENV_VARS:
        if not getattr(os, 'environ', {}).get(var):
            raise RuntimeError(
                f"Отсутствует обязательная переменная окружения: {var}"
            )


# --- Инициализация настроек при импорте ---
def load_settings() -> None:
    """Перезагрузка настроек из переменных окружения."""
    global DEBUG, DB_TYPE, LOG_LEVEL, BOT_TOKEN, CACHE_TYPE
    
    # Пересчёт DEBUG (влияет на логирование)
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Пересчёт типа БД и URL
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")
    
    if DB_TYPE == "sqlite":
        DB_PATH: Path = os.getenv(
            "DB_PATH", 
            BASE_DIR / "data" / "app.db"
        )
        DB_URL: str = f"sqlite:///{DB_PATH}"
    else:
        DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        DB_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))
        DB_NAME: str = os.getenv("POSTGRES_DB", "exception_bot")
        DB_USER: str = os.getenv("POSTGRES_USER", "postgres")
        DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
        
        if DB_TYPE == "postgresql":
            DB_URL: str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        else:  # mysql
            DB_URL: str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Пересчёт уровня логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    if not DEBUG:
        LOG_LEVEL = "WARNING"
    
    # Пересчёт API URL бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    TELEGRAM_API_URL: str = os.getenv(
        "TELEGRAM_API_URL", 
        "https://api.telegram.org/bot" + BOT_TOKEN
    )
    
    # Пересчёт типа кэша и URL Redis
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "redis")
    
    if CACHE_TYPE == "redis":
        REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
        REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
        REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
        
        if REDIS_PASSWORD:
            REDIS_URL: str = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        else:
            REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:  # memory
        REDIS_URL: Optional[str] = None
    
    print(f"[Settings] Загружены настройки для окружения: DEBUG={DEBUG}, DB_TYPE={DB_TYPE}")


# --- Утилиты для работы с настройками ---

def get_db_url() -> str:
    """Получить URL подключения к базе данных."""
    return Settings.DB_URL if hasattr(Settings, 'DB_URL') else "sqlite:///app.db"


def get_redis_url() -> Optional[str]:
    """Получить URL подключения к Redis или None для memory-кэша."""
    return Settings.REDIS_URL if hasattr(Settings, 'REDIS_URL') else None


def is_debug_mode() -> bool:
    """Проверить режим отладки."""
    return DEBUG


def get_log_level() -> str:
    """Получить текущий уровень логирования."""
    return LOG_LEVEL


# --- Экспорт ключевых настроек для импорта без инициализации ---
__all__ = [
    'Settings',
    'load_settings',
    'get_db_url',
    'get_redis_url',
    'is_debug_mode',
    'get_log_level'
]
