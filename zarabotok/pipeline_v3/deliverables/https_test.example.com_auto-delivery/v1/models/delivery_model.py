from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DeliveryStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class DeliveryRequest:
    """DTO для входящего запроса на доставку."""

    order_id: str
    status: Optional[DeliveryStatus] = None
    delivery_date: Optional[datetime] = None
    address: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    notes: Optional[str] = field(default="")


@dataclass(frozen=True)
class DeliveryResponse:
    """DTO для ответа серверу на запрос доставки."""

    success: bool
    order_id: str
    status: DeliveryStatus
    message: str = ""
    new_delivery_date: Optional[datetime] = None
    tracking_url: Optional[str] = None
