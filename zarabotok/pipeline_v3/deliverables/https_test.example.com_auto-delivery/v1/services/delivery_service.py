import uuid
import hashlib
import json
import datetime
from typing import Dict, Any, Optional


class DeliveryService:
    """
    Бизнес-логика сборки пакета данных для отправки.
    
    Ответственность:
    1. Генерация уникального ID заказа.
    2. Сборка payload (данных) для передачи в API.
    3. Подпись payload (опционально, если требуется шифрование).
    """

    # Конфигурация подписи (в реальном проекте берется из env-переменных)
    SECRET_KEY = "super_secret_key_for_delivery_service_v1"

    def __init__(self):
        self.order_counter: int = 0
        self.last_order_id: str = ""

    def generate_order_id(self, prefix: str = "ORD") -> str:
        """
        Генерирует уникальный ID заказа.
        
        Возвращает: Строку вида 'ORD-1234567890abcdef'.
        """
        # Используем UUID для высокой энтропии и уникальности
        unique_part = uuid.uuid4().hex[:8]
        return f"{prefix}-{unique_part}"

    def build_payload(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Собирает payload из сырых данных заказа.
        
        Аргументы:
            order_data (dict): Словарь с данными заказа (например, items, address).
            
        Возвращает: Готовый словарь для JSON-сериализации.
        """
        # Базовая структура ответа API
        payload = {
            "version": 1,
            "source": "auto-delivery",
            "data": order_data.copy()
        }

        # Добавляем метаданные о времени создания (в формате ISO-8601)
        payload["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        return payload

    def sign_payload(self, payload: Dict[str, Any]) -> str:
        """
        Подписывает payload для проверки целостности данных.
        
        Аргументы:
            payload (dict): Данные, которые нужно подписать.
            
        Возвращает: Баз64-кодированную строку подписи.
        """
        # Превращаем словарь в JSON-строку для хеширования
        json_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Вычисляем HMAC-SHA256
        signature = hashlib.sha256(
            (json_str + self.SECRET_KEY).encode('utf-8')
        ).hexdigest()

        return signature

    def prepare_delivery_package(self, order_data: Dict[str, Any], encrypt: bool = False) -> Dict[str, Any]:
        """
        Основной метод подготовки пакета для отправки.
        
        Аргументы:
            order_data (dict): Исходные данные заказа.
            encrypt (bool): Флаг необходимости подписи данных.
            
        Возвращает: Словарь с готовым пакетом и метаданными.
        """
        # 1. Генерируем ID
        order_id = self.generate_order_id()

        # 2. Строим payload
        raw_payload = self.build_payload(order_data)

        # 3. Добавляем подписи, если требуется
        signed_payload: Dict[str, Any] = {}
        
        if encrypt:
            signature = self.sign_payload(raw_payload)
            signed_payload["signature"] = signature
            
            # В реальном проекте здесь может быть поле "encrypted_data" с зашифрованным телом
            signed_payload["data"] = raw_payload
        else:
            signed_payload["data"] = raw_payload

        return {
            "order_id": order_id,
            "payload": signed_payload,
            "metadata": {
                "service_version": "1.0.0",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
