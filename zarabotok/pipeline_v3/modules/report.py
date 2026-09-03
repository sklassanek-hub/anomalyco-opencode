"""Ежедневная сводка оператору: воронка, отправки, ответы, деньги. Чистая сборка текста."""
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name: str, default):
    try:
        with open(os.path.join(BASE, "state", name + ".json"), encoding="utf-8") as f:
            return json.load(f) or default
    except Exception:
        return default


def gather_stats() -> dict:
    today = time.strftime("%Y-%m-%d")
    jobs = _load("jobs", {"items": []}).get("items", [])
    outbox = _load("outbox", {"items": []}).get("items", [])
    sent_log = _load("sent_log", {"items": []}).get("items", [])
    msgs = _load("messages", {"items": []}).get("items", [])
    acts = _load("activity", {})
    acts = acts.get("activity") if isinstance(acts.get("activity"), list) else acts.get("items") or []
    invoices = _load("invoices", {"items": []}).get("items", [])

    def today_count(seq, key=None, contains=""):
        n = 0
        for x in seq:
            ts = str(x.get("ts", ""))
            if not ts.startswith(today):
                continue
            if key and not x.get(key):
                continue
            if contains and contains not in str(x.get("text", "")):
                continue
            n += 1
        return n

    return {
        "date": today,
        "jobs_today": sum(1 for j in jobs if str(j.get("scanned_at", "")).startswith(today)),
        "contact_today": sum(1 for j in jobs
                             if str(j.get("scanned_at", "")).startswith(today) and j.get("contact")),
        "outbox_total": len(outbox),
        "pending": sum(1 for i in outbox if i.get("approved") and not i.get("sent")),
        "sent_today": sum(1 for s in sent_log if s.get("ts", "").startswith(today)),
        "replies_today": sum(1 for m in msgs if m.get("direction") == "in"
                             and m.get("order") and str(m.get("ts", "")).startswith(today)),
        "auto_replies_today": today_count(acts, contains="автоответ отправлен"),
        "invoices_sent": sum(1 for i in invoices if i.get("status") == "sent"),
        "paid_total": sum(1 for i in invoices if i.get("status") == "paid"),
    }


def build_daily_digest(s: dict) -> str:
    lines = [
        f"📊 Сводка за {s.get('date', '')}",
        f"• Найдено заказов сегодня: {s.get('jobs_today', 0)} (с контактом: {s.get('contact_today', 0)})",
        f"• Отправлено откликов: {s.get('sent_today', 0)}",
        f"• Ответов клиентов: {s.get('replies_today', 0)}",
        f"• Автоответов системы: {s.get('auto_replies_today', 0)}",
        f"• В очереди на отправку: {s.get('pending', 0)} из {s.get('outbox_total', 0)}",
        f"• Счета: выставлено-отправлено {s.get('invoices_sent', 0)}, оплачено всего {s.get('paid_total', 0)}",
    ]
    if not s.get("sent_today"):
        lines.append("⚠️ Отправок нет — проверь источники/контакты или QA-гейты в activity.")
    return "\n".join(lines)
