"""Двусторонняя переписка по заказам: messages.json, привязка по контакту/url, автоответы."""
import re

from modules import store

DIR_RE = re.compile(r"@([a-zA-Z0-9_]{4,32})")

META_FIELDS = ("ts", "direction", "channel", "sender", "text", "order", "kind", "sent", "read")


def normalize_peer(peer: str) -> str:
    """Приводит адрес к каноническому виду: @user | email | url-заказа."""
    peer = (peer or "").strip()
    if peer.startswith("tg:") or peer.startswith("@"):
        m = DIR_RE.search(peer)
        return ("@" + m.group(1).lower()) if m else peer
    if "@" in peer and "." in peer:
        return peer.lower()
    return peer


def find_order_for_peer(peer: str) -> str | None:
    """Находит url заказа по контакту/адресу клиента (по outbox + jobs)."""
    peer = normalize_peer(peer)
    box = store.load("outbox", {"items": []}).get("items", [])
    for i in box:
        cand = normalize_peer(i.get("contact") or "") or normalize_peer(i.get("to") or "")
        if not cand:
            continue
        if cand.startswith("tg:") or cand.startswith("@"):
            cand = normalize_peer(cand)
        if cand and (cand == peer or cand.lstrip("@") == peer.lstrip("@")):
            return i.get("url")
    return None


def add(order_url: str | None, direction: str, channel: str, sender: str,
        text: str, kind: str = "msg", sent: bool = True) -> dict:
    """Добавляет сообщение в цепочку заказа. direction: in|out."""
    def _fn(d):
        d.setdefault("items", [])
        items = d["items"]
        start = len(items) - 50 if len(items) > 50 else 0
        for m in reversed(items[start:]):
            if (m.get("direction") == direction and m.get("channel") == channel
                    and normalize_peer(m.get("sender", "")) == normalize_peer(sender)
                    and m.get("text") == text and (m.get("ts") or "")[:10] == store.now()[:10]):
                return m
        m = {
            "ts": store.now(),
            "direction": direction,
            "channel": channel,
            "sender": normalize_peer(sender),
            "text": text[:4000],
            "order": order_url,
            "kind": kind,
            "sent": sent,
            "read": False,
        }
        items.append(m)
        return m
    return store.mutate("messages", _fn, {"items": []})


def thread(order_url: str, limit: int = 100) -> list[dict]:
    items = store.load("messages", {"items": []}).get("items", [])
    return [m for m in items if m.get("order") == order_url][-limit:]


def unread_counts() -> dict:
    """{order_url: число непрочитанных входящих}"""
    res: dict[str, int] = {}
    for m in store.load("messages", {"items": []}).get("items", []):
        if m.get("direction") == "in" and not m.get("read"):
            res[m.get("order", "")] = res.get(m.get("order", ""), 0) + 1
    return res


def mark_read(order_url: str):
    def _fn(d):
        for m in d.get("items", []):
            if m.get("order") == order_url and m.get("direction") == "in":
                m["read"] = True
        return None
    store.mutate("messages", _fn, {"items": []})


def auto_reply_policy(text: str) -> str | None:
    """Возвращает текст автоответа на типовые вопросы клиента, иначе None."""
    t = (text or "").lower()
    if any(w in t for w in ("цену", "ценa", "сколько стоит", "стоимость", "прайс", "бюджет", "в какую сумму")):
        return ("Бюджет обсуждаем — назовите объём и сроки, подготовлю план и конкретную оценку "
                "в течение часа.")
    if any(w in t for w in ("срок", "когда будет", "как долго", "за какой срок", "сколько по времени")):
        return "Срок зависит от объёма: скиньте ТЗ или ссылку, за 1-2 часа прикину точный тайминг."
    if any(w in t for w in ("портфолио", "примеры", "пример работ", "скиньте примеры")):
        return "Примеры работ отправлю по вашему ТЗ — посмотрю задачу и подберу релевантные кейсы."
    return None