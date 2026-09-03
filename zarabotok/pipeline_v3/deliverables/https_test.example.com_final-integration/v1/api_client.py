import asyncio
from typing import Any, Dict, List, Optional, Union
import aiohttp
import json
import logging
import sys
from datetime import datetime

# === КОНФИГУРАЦИЯ ===
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
BASE_URL = "https://api.example.com"

# Логирование
logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Базовое исключение для ошибок API"""
    pass


class ConnectionError(APIClientError):
    """Ошибка соединения с сервером"""
    pass


class HTTPError(APIClientError):
    """HTTP-ошибка (не 2xx)"""
    
    def __init__(self, status: int, message: str = "", response_data: Any = None):
        self.status = status
        self.message = message or f"HTTP {status}"
        self.response_data = response_data
    
    def __str__(self) -> str:
        return f"{self.message} (Status: {self.status})"


class APIClient:
    """Базовый клиент для взаимодействия с внешними API"""
    
    def __init__(
        self, 
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[aiohttp.ClientSession] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = headers or {}
        self.session = session
        
    async def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки запроса"""
        result = dict(self.headers)
        result["Accept"] = "application/json"
        return result
    
    async def _request(
        self, 
        method: str, 
        url: str, 
        data: Any = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Выполнить HTTP-запрос с повторными попытками"""
        headers = await self._get_headers()
        
        for attempt in range(MAX_RETRIES):
            try:
                connector = aiohttp.TCPConnector(
                    timeout=self.timeout,
                    ttl_dns_cache=300
                )
                
                async with aiohttp.ClientSession(connector=connector) as session:
                    kwargs = {
                        "method": method.upper(),
                        "url": url,
                        "headers": headers,
                        "json": data if isinstance(data, dict) else None,
                        "params": params or {}
                    }
                    
                    async with session.request(**kwargs) as response:
                        await self._handle_response(response)
                        
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": await response.json() if response.content else b""
                }
                
            except aiohttp.ClientError as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise ConnectionError(str(e))
                await asyncio.sleep(2 ** attempt)
        
        return {}
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> None:
        """Обработать ответ от сервера"""
        if response.status >= 400:
            try:
                error_data = await response.json()
            except:
                error_data = {"message": "Unknown error"}
            
            raise HTTPError(response.status, str(error_data), error_data)


# === ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ УДОБСТВА ===

def create_client(
    base_url: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None
) -> APIClient:
    """Фабричный метод для создания клиента"""
    return APIClient(base_url=base_url or BASE_URL, timeout=timeout, headers=headers)


async def get(
    client: APIClient, 
    url: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Удобный метод GET-запроса"""
    return await client._request("GET", url, params=params)


async def post(
    client: APIClient, 
    url: str, 
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Удобный метод POST-запроса"""
    return await client._request("POST", url, data=data, params=params)


async def put(
    client: APIClient, 
    url: str, 
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Удобный метод PUT-запроса"""
    return await client._request("PUT", url, data=data, params=params)


async def delete(
    client: APIClient, 
    url: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Удобный метод DELETE-запроса"""
    return await client._request("DELETE", url, params=params)


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===

async def main():
    # Создание клиента
    client = create_client(
        base_url="https://api.example.com/v1",
        headers={"Authorization": "Bearer token123"}
    )
    
    try:
        # Пример GET-запроса
        result = await get(client, "/users/1")
        print(f"Status: {result['status_code']}")
        print(f"Body: {json.dumps(result['body'], indent=2)}")
        
        # Пример POST-запроса
        new_user = {"name": "John", "email": "john@example.com"}
        result = await post(client, "/users", data=new_user)
        print(f"Created user: {result['status_code']}")
        
    except HTTPError as e:
        logger.error(f"API Error: {e}")
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
