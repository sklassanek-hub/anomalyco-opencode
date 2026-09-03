"""Парсер ТЗ из входящих сообщений заказчика (TG/email).

Извлекает: дедлайн, бюджет, признак наличия ТЗ, а также сам текст ТЗ для передачи
исполнителям. Не претендует на идеал — даёт исполнителям структурированный контекст.
"""
import re

_DEADLINE_RE = re.compile(
    r"(срок|deadline|крайний срок|сделай до|нужно к|готово к|by|due)\s*[:\-]?\s*([^.\n]{3,60})",
    re.I)
_BUDGET_RE = re.compile(
    r"(\d[\d\s\u00a0]*)(\s?₽|\s?руб|рублей|рубля|usd|\$|€|euro|евро)", re.I)
_TZ_HINTS = ("тз", "техническ", "задани", "нужно сделать", "сделай", "прикреп",
             "во вложени", "файл", "специфик", "требован", "задач")


def parse_tz(text: str) -> dict:
    text = (text or "").strip()
    deadline = ""
    m = _DEADLINE_RE.search(text)
    if m:
        deadline = m.group(2).strip()[:60]
    budget = ""
    m = _BUDGET_RE.search(text)
    if m:
        budget = (m.group(1).replace(" ", "").replace("\u00a0", "") + " " +
                  {"₽": "руб", "руб": "руб", "рублей": "руб", "рубля": "руб",
                   "usd": "USD", "$": "USD", "€": "EUR", "евро": "EUR"}.get(
                      m.group(2).lower().strip(), m.group(2))).strip()
    has_tz = any(h in text.lower() for h in _TZ_HINTS) or len(text) > 120
    return {
        "deadline": deadline,
        "budget": budget,
        "has_tz": bool(has_tz),
        "tz_text": text[:2000],
    }
