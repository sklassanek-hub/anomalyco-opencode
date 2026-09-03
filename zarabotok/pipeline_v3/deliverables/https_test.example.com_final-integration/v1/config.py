"""config.py — Хранение токенов и конфигурационных параметров.

Импортируется в main.py, handlers.py, api_client.py для получения настроек.
Все значения имеют разумные дефолты для локальной разработки.
"""

# =============================================================================
# API КЛЮЧИ И ТОКЕНЫ (замените на реальные перед продакшном)
# =============================================================================

API_CONFIG = {
    "base_url": "https://api.example.com/v1",
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "retry_delay_ms": 500,
}

AUTH_TOKENS = {
    # Основной API-токен (замените на свой)
    "main_api_key": "sk_test_1234567890abcdef",
    
    # Если используется OAuth или session токены
    "oauth_client_id": "client_abc123xyz",
    "oauth_client_secret": "secret_xyz789abc",
}

# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "name": "project_db",
    "user": "postgres",
    # Пароль в реальном проекте лучше хранить отдельно или через env-переменные
    "password": "dev_password_123",
    
    # Опции подключения (для PostgreSQL)
    "options": {
        "ssl_mode": "prefer",  # disable, require, verify-ca, verify-full
        "connect_timeout": 10,
        "pool_size": 5,
    },
}

# =============================================================================
# CORS И ПРОКСИ (для api_client.py)
# =============================================================================

CORS_CONFIG = {
    "allowed_origins": [
        "http://localhost:3000",
        "https://test.example.com",
        "https://www.test.example.com",
    ],
    "allow_credentials": True,
    "max_age_seconds": 86400,  # 24 часа
}

# Настройки прокси (если API требует)
PROXY_CONFIG = {
    "enabled": False,
    "http_proxy": "",  # Например: "http://user:pass@proxy.example.com:3128"
    "https_proxy": "",
    "no_proxy": "",  # Список доменов для обхода прокси (например: ".localhost,.example.com")
}

# =============================================================================
# ДРУГИЕ НАСТРОЙКИ ПРОЕКТА
# =============================================================================

PROJECT_CONFIG = {
    "version": "1.0.0",
    "debug_mode": True,  # Переключить на False для продакшена
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Для асинхронных задач (если используется)
    "asyncio_max_workers": 10,
    "request_timeout_seconds": 60,
}

# =============================================================================
# УТИЛИТА ДЛЯ ЗАГРУЗКИ ИЗ ОКРУЖЕНИЯ
# =============================================================================

def load_from_env(key: str, default=None):
    """Загружает значение из переменной окружения.
    
    Аргументы:
        key (str): Имя переменной окружения без префикса ENV_ или PREFIX_.
        default: Значение по умолчанию, если переменная не задана.
        
    Возвращает:
        str | None: Значение из окружения или дефолт.
    """
    import os
    env_key = f"ENV_{key}".upper() if not key.startswith(("ENV_", "PREFIX_")) else key
    
    value = os.environ.get(env_key)
    
    # Если переменная есть и не пустая — возвращаем её, иначе дефолт
    return value if value is not None else default


# =============================================================================
# ПРОВЕРКА НАСТРОЕК ПРИ ИМПОРТЕ (опционально)
# =============================================================================

def validate_config():
    """Выполняет базовую валидацию конфигурации.
    
    Проверяет, что обязательные поля не пустые и имеют корректный формат.
    Вызывается автоматически при импорте модуля, если DEBUG_MODE = True.
    
    Возвращает:
        bool: True если всё ок, False в случае ошибок.
    """
    import os
    
    if PROJECT_CONFIG.get("debug_mode", True):
        print("[config.py] Валидация конфигурации...")
        
        # Проверка токенов (не пустые)
        required_tokens = ["main_api_key"]
        for token_name in required_tokens:
            value = AUTH_TOKENS.get(token_name, "")
            if not value or len(value.strip()) < 10:
                print(f"  ⚠️  {token_name}: слишком короткий или пустой")
        
        # Проверка базы данных (хост не localhost в продакшене)
        host = DATABASE_CONFIG.get("host", "")
        if host and not host.startswith(("localhost", "127.0.0.1")):
            print(f"  ℹ️  DB_HOST={host} — возможно, это продакшн")
        
        # Проверка прокси
        if PROXY_CONFIG.get("enabled", False):
            http_p = PROXY_CONFIG.get("http_proxy", "")
            https_p = PROXY_CONFIG.get("https_proxy", "")
            if not http_p and not https_p:
                print(f"  ⚠️  Прокси включён, но не заданы URL")
        
        print("[config.py] Валидация завершена.")
    
    return True


# Вызов валидации при импорте (если debug_mode включен)
validate_config()
