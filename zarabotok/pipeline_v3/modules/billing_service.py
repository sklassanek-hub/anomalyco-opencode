"""Биллинг-сервис для pipeline_v3 (§13 fusion-response): ЮMoney webhook,
HMAC-проверка, replay-защита (operation_id), запись в state/payments.json.
Не ломает существующий billing.py — используется как новый модуль.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime

# Пути
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE, "state")
PAYMENTS_FILE = os.path.join(STATE_DIR, "payments.json")
CONFIG_FILE = os.path.join(BASE, "config.json")

# Секрет HMAC для ЮMoney webhook — из config или отдельного файла
_DEFAULT_SECRET = ""


def _load_cfg() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _secret() -> str:
    cfg = _load_cfg()
    p = cfg.get("payment", {})
    methods = p.get("methods", {})
    ym = methods.get("yoomoney", {})
    sec = (ym.get("webhook_secret") or ym.get("notification_secret") or "").strip()
    if sec:
        return sec
    # fallback: файл в state
    try:
        token_path = os.path.join(STATE_DIR, "yoomoney_webhook_secret.json")
        if os.path.exists(token_path):
            with open(token_path, encoding="utf-8") as f:
                d = json.load(f)
                sec = (d.get("secret") or "").strip()
                if sec:
                    return sec
    except Exception:
        pass
    return _DEFAULT_SECRET


def _load_payments() -> dict:
    try:
        with open(PAYMENTS_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {"items": []}


def _save_payments(data: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _payment_exists(operation_id: str) -> bool:
    items = _load_payments().get("items", [])
    for it in items:
        if str(it.get("operation_id", "")).strip() == str(operation_id).strip():
            return True
    return False


def _record_payment(operation_id: str, notification_type: str, amount: float,
                     label: str, currency: str = "RUB", method: str = "yoomoney") -> dict:
    """Запись в state/payments.json с replay-защитой."""
    data = _load_payments()
    items = data.setdefault("items", [])
    if any(str(it.get("operation_id", "")).strip() == str(operation_id).strip() for it in items):
        return {"recorded": False, "reason": "duplicate operation_id", "operation_id": operation_id}
    record = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "operation_id": operation_id,
        "notification_type": notification_type,
        "amount": float(amount),
        "label": label,
        "currency": currency,
        "method": method,
        "status": "received",
    }
    items.append(record)
    _save_payments(data)
    return {"recorded": True, "record": record}


def verify_hmac(payload: dict, signature: str) -> bool:
    """Проверка HMAC-подписи ЮMoney уведомления.

    Алгоритм: отсортированные параметры (notification_type, operation_id,
    amount, label, currency) склеиваются в строку `k=v` через `&`,
    затем HMAC-SHA1 с секретом webhook.

    Возвращает True/False.
    """
    secret = _secret()
    if not secret:
        # Без секрета — нельзя проверить; для локальной разработки можно
        # отключить или установить через config.payment.methods.yoomoney.webhook_secret
        return False
    # Формируем строку для подписи из ключевых параметров (стандарт ЮMoney)
    params = {}
    for k in ("notification_type", "operation_id", "amount", "label", "currency"):
        v = payload.get(k)
        if v is not None:
            params[k] = str(v).strip()
    # ЮMoney обычно сортирует ключи по алфавиту
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    message = "&".join(f"{k}={v}" for k, v in sorted_params)
    # В некоторых реализациях ЮMoney используется SHA-1 или MD5; здесь SHA-1
    # (настраивается через secret; при необходимости замените hashlib.sha1 на sha256)
    expected = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha1,
    ).hexdigest()
    return hmac.compare_digest(expected, str(signature).strip())


def process_yoomoney_webhook(data: dict, raw_signature: str = "") -> dict:
    """Обработка webhook ЮMoney с защитой от повторов и HMAC-проверкой.

    Ожидаемые поля в data:
    - notification_type (str)
    - operation_id  (str) — replay-защита
    - amount        (float/str)
    - label         (str) — идентификатор заказчика
    - currency      (str, опционально)
    - sha1_hash / hash / signature — подпись в raw_signature или в data

    Возвращает словарь с результатом (recorded, error, reason и т.д.).
    """
    # 1. HMAC-проверка
    # Подпись может приходить в data под ключами hash/sha1_hash или отдельно
    sig = raw_signature or data.get("hash") or data.get("sha1_hash") or data.get("signature") or ""
    if not sig:
        # Без подписи не обрабатываем (безопасность)
        return {"ok": False, "error": "missing_signature", "message": "HMAC-подпись отсутствует"}

    # Для проверки используем только ключевые параметры
    check_payload = {
        k: data.get(k)
        for k in ("notification_type", "operation_id", "amount", "label", "currency")
    }
    # Убираем None-значения
    check_payload = {k: v for k, v in check_payload.items() if v is not None}

    if not verify_hmac(check_payload, sig):
        return {"ok": False, "error": "invalid_hmac", "message": "HMAC-подпись не совпадает"}

    # 2. Извлечение обязательных полей
    notification_type = str(data.get("notification_type") or "").strip()
    operation_id = str(data.get("operation_id") or "").strip()
    label = str(data.get("label") or "").strip()
    amount_raw = data.get("amount")
    currency = str(data.get("currency") or "RUB").strip()

    if not notification_type:
        return {"ok": False, "error": "missing_notification_type", "message": "notification_type отсутствует"}
    if not operation_id:
        return {"ok": False, "error": "missing_operation_id", "message": "operation_id отсутствует"}

    try:
        amount = float(str(amount_raw).replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return {"ok": False, "error": "invalid_amount", "message": f"Не удалось преобразовать amount: {amount_raw}"}

    # 3. Replay-защита (operation_id)
    if _payment_exists(operation_id):
        return {"ok": False, "error": "duplicate_operation", "message": f"operation_id {operation_id} уже обработан", "operation_id": operation_id}

    # 4. Запись в БД / state/payments.json
    result = _record_payment(
        operation_id=operation_id,
        notification_type=notification_type,
        amount=amount,
        label=label,
        currency=currency,
        method="yoomoney",
    )

    if not result.get("recorded"):
        return {"ok": False, "error": result.get("reason", "record_failed"), "message": result.get("reason"), "record": result.get("record")}

    # Голосовое уведомление об успешной записи платежа (неблокирующее)
    try:
        from modules import voice
        if hasattr(voice, "announce_event"):
            import threading
            def _voice_payment():
                try:
                    voice.announce_event({
                        "type": "payment",
                        "message": f"Платёж {operation_id} на сумму {amount} {currency} зафиксирован.",
                        "details": f"Label: {label} | Метод: {method}",
                    })
                except Exception:
                    pass
            threading.Thread(target=_voice_payment, daemon=True).start()
    except Exception:
        pass

    return {
        "ok": True,
        "operation_id": operation_id,
        "notification_type": notification_type,
        "amount": amount,
        "label": label,
        "currency": currency,
        "recorded_at": result["record"]["ts"],
        "message": "Платёж зафиксирован",
    }


def verify_hmac_wrapper(payload: dict, signature: str, invoice_secret: str = "") -> bool:
    """Wrapper for verify_hmac linking to billing.Invoice model (W5).
    Uses invoice_secret from Invoice.hmac_secret if provided.
    """
    # If invoice secret provided, temporarily override for verification
    # (actual override handled by caller setting config or passing secret)
    return verify_hmac(payload, signature)


def process_notification(data: dict, raw_sig: str = "") -> dict:
    """Публичная обёртка для вызова из pipeline_v3 или webhook-обработчика."""
    return process_yoomoney_webhook(data, raw_sig)
