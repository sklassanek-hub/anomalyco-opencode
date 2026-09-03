import asyncio
import logging
from typing import Callable, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# ==================== CONFIG.PY ====================
@dataclass
class Config:
    """Конфигурация приложения"""
    api_base_url: str = "https://api.example.com/v1"
    api_key: str = "test-api-key-12345"
    timeout_seconds: int = 30
    retry_attempts: int = 3
    log_level: str = "INFO"

# Инициализация глобальной конфигурации
config = Config()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)


# ==================== API_CLIENT.PY ====================
class APIClient:
    """Клиент для взаимодействия с внешним API"""
    
    def __init__(self, base_url: str, api_key: str, timeout: int):
        self.base_url = base_url.rstrip('/') + '/'
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _create_session(self) -> None:
        """Создание сессии HTTP-клиента"""
        import aiohttp
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
    async def close(self) -> None:
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            
    async def _request(self, method: str, endpoint: str, 
                       data: Any = None, params: dict = None) -> dict:
        """Выполнение HTTP-запроса с автоматической повторной попыткой"""
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        for attempt in range(config.retry_attempts):
            try:
                kwargs = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "timeout": self.timeout,
                    "json": data if data else None,
                    "params": params or {}
                }
                
                async with self.session.request(**kwargs) as response:
                    # Обработка кодов 4xx и 5xx с увеличением счетчика попыток
                    if response.status >= 400 and response.status < 600:
                        error_body = await response.text()
                        logger.warning(f"Ошибка сервера {response.status}: {error_body[:100]}")
                        raise aiohttp.ClientError(response)
                    
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Запрос {method} {endpoint}: попытка {attempt + 1}/{config.retry_attempts}, ошибка: {e}")
                if attempt == config.retry_attempts - 1:
                    raise
                    
    async def get(self, endpoint: str, params: dict = None) -> dict:
        """GET запрос"""
        await self._create_session()
        return await self._request("GET", endpoint, params=params)
        
    async def post(self, endpoint: str, data: Any = None) -> dict:
        """POST запрос"""
        await self._create_session()
        return await self._request("POST", endpoint, data=data)
        
    async def put(self, endpoint: str, data: Any = None) -> dict:
        """PUT запрос"""
        await self._create_session()
        return await self._request("PUT", endpoint, data=data)
        
    async def delete(self, endpoint: str) -> dict:
        """DELETE запрос"""
        await self._create_session()
        return await self._request("DELETE", endpoint)
        
    async def health_check(self) -> bool:
        """Проверка доступности API (GET /health или аналогичный эндпоинт)"""
        try:
            response = await self.get("/health")
            # Ожидается, что ответ будет содержать статус "healthy" или код 200
            return response.get("status") == "healthy" or response.status_code == 200
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья API: {e}")
            return False

    async def __aenter__(self):
        """Контекстный менеджер для открытия сессии"""
        await self._create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер для закрытия сессии"""
        await self.close()

# ==================== MAIN.PY (ENTRY POINT) ====================

async def main():
    """Точка входа в приложение"""
    client = APIClient(
        base_url=config.api_base_url,
        api_key=config.api_key,
        timeout=config.timeout_seconds
    )
    
    try:
        # Проверка доступности API
        if not await client.health_check():
            logger.error("API недоступен или вернул ошибку")
            return

        # Пример выполнения запроса (можно заменить на реальные эндпоинты)
        logger.info(f"Попытка получить данные с {config.api_base_url}")
        
        try:
            response = await client.get("/users/123")
            logger.info(f"Успешный ответ: {response}")
        except Exception as e:
            logger.error(f"Ошибка при получении данных: {e}")

    finally:
        # Гарантированное закрытие сессии
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
