"""Автоответ на входящие от заказчиков: LLM-генерация, безопасная отправка.

Правила (после инцидента с плохими автоответами):
1. Один диалог = один ответ за раз: несколько входящих подряд склеиваются,
   отвечаем только на последнее.
2. Cooldown: не чаще раза в DIALOG_COOLDOWN_MIN минут на диалог
   (согласие клиента обрабатывается всегда, вне очереди).
3. Болтовня (<2 значимых слов, без вопроса) — не отвечает вовсе.
4. Ответ проходит контроль качества: длина, запрет фраз, наличие сути;
   при провале — короткий шаблон или молчание.
"""
import json
import re
import time
import urllib.request

from modules import billing, chat, crm, executor, llm, sender, store

SCAM_MARKERS = ("казино", "крипто", "обменник", "анydesk", "anydesk", "rustdesk", "дроп",
                "вложени", "оформить карту", "обнали", "лотере", "бонус", "выигрыш",
                "raбота в день", "набираем людей", "заработок в день", "пассивный доход")

LLM_URL = "http://127.0.0.1:1234/v1/chat/completions"
DIALOG_COOLDOWN_MIN = 5  # default 5; override via store.load('settings',{}).get('dialog_cooldown_min') / config/settings.json          # минимум между нашими ответами одному клиенту
REPLY_MIN_LEN, REPLY_MAX_LEN = 12, 320

_BAD_REPLY_PATTERNS = ("извин", "как ии", "нейросет", "языковая модель",
                       "рад помочь", "с удовольствием помогу")


def _dialog_model() -> str:
    """Модель для переписки: models.writer (живее в разговоре), фолбэк coder."""
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "config.json"), encoding="utf-8") as f:
            return ((json.load(f).get("models") or {}).get("writer")
                    or llm.model_cfg()["model"])
    except Exception:
        try:
            return llm.model_cfg()["model"]
        except Exception:
            return ""


import os  # noqa: E402  (для _dialog_model)


def _llm_reply(order: str, thread: list[dict]) -> str | None:
    """Короткий деловой ответ строго по последнему сообщению клиента."""
    last_client = ""
    for m in reversed(thread):
        if m.get("direction") == "in":
            last_client = m.get("text", "")
            break
    if not last_client:
        return None
    msgs = [f"клиент: {last_client[:500]}"]
    model = _dialog_model()
    if not model:
        return None
    cfg = llm.model_cfg()
    try:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "Ты — фрилансер-разработчик. Клиент написал: одно сообщение. "
                    "Ответь ОДНИМ предложением строго по нему. Правила: "
                    "не выдумывай факты о себе и свой опыт; если данных мало — "
                    "задай один конкретный вопрос; цену и сроки не называй "
                    "(скажи, что оценишь после уточнений); без приветствий, "
                    "благодарностей, извинений, эмодзи и упоминаний ИИ.")},
                *[{"role": "user", "content": s} for s in msgs],
            ],
            "temperature": 0.4,
            "max_tokens": 120,
        }
        req = urllib.request.Request(cfg["url"], data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=min(int(cfg["timeout"]), 90)) as r:
            data = json.loads(r.read())
        text = (data["choices"][0]["message"].get("content") or "").strip()
        return _answer_ok(text) and text or None
    except Exception:
        return None


def _answer_ok(text: str | None) -> bool:
    """Контроль качества ответа: длина, запрет фраз, отсутствие воды."""
    if not text:
        return False
    t = text.strip()
    if not (REPLY_MIN_LEN <= len(t) <= REPLY_MAX_LEN):
        return False
    low = t.lower()
    if any(p in low for p in _BAD_REPLY_PATTERNS):
        return False
    # должен быть либо вопрос, либо конкретика (цифра/файл/шаг), иначе это вода
    if ("?" not in t) and (not re.search(r"\d|файл|скрипт|бот|парсер|сайт|api|правк", low)):
        return False
    return True


def _template_reply(text: str) -> str | None:
    t = (text or "").lower()
    if any(w in t for w in ("цен", "стоимост", "бюджет", "прайс", "сколько стоит")):
        return ("Бюджет обсуждаем — пришлите описание объёма и сроки, подготовлю план "
                "и предварительную оценку.")
    if any(w in t for w in ("срок", "когда", "как долго", "за сколько времени")):
        return "Срок зависит от объёма: дайте ТЗ или ссылку — за 1-2 часа прикину тайминг."
    if any(w in t for w in ("портфолио", "примеры", "кейсы", "работы покаж")):
        return "Примеры работ отправлю под вашу задачу — отпишите, что именно нужно, подберу кейсы."
    return None


def _is_scam(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in SCAM_MARKERS)


AGREE_MARKERS = ("ок", "окей", "хорошо", "давай", "давайте", "соглас", "договорились",
                 "приступай", "приступайте", "начинайте", "можно начинать", "делаем",
                 "го", "вперед", "вперёд", "подходит", "отлично", "супер", "ждём", "жду результат",
                 "утверждаю", "одобрено", "запускайте")


def _has_agree(text: str) -> bool:
    """Маркер согласия. Короткие («ок»/«го») — только как целое слово
    (иначе «отклик»/«него» дают ложное согласие)."""
    low = (text or "").lower()
    for m in AGREE_MARKERS:
        if m in ("ок", "го"):
            if re.search(rf"\b{re.escape(m)}\b", low):
                return True
        elif m in low:
            return True
    return False


BUDGET_RE = re.compile(r"\d[\d\s]{1,9}\s?(?:₽|руб|тыс|k)", re.IGNORECASE)
DEADLINE_RE = re.compile(r"(?:за|через|в течение|до)\s*(\d+)\s?(?:дн|день|дня|нед|час)", re.IGNORECASE)
CONTACT_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
DECLINE_MARKERS = ("не надо", "передумал", "отмени", "отказаться", "уже нашли", "другого")
QUESTION_MARKERS = ("сколько", "когда", "какие сроки", "бюджет", "объем", "объём", "требования", "подробнее")


def classify_message(text: str) -> dict:
    """Классификация входящего: agree/decline/question/unclear + сущности."""
    low = (text or "").lower()
    entities = {"budget": None, "deadline": None, "contact": None}
    m = BUDGET_RE.search(low)
    if m:
        entities["budget"] = m.group(0).strip()
    m = DEADLINE_RE.search(low)
    if m:
        entities["deadline"] = m.group(0).strip()
    m = CONTACT_RE.search(low)
    if m:
        entities["contact"] = m.group(0)
    if any(mark in low for mark in DECLINE_MARKERS):
        return {"type": "decline", "entities": entities}
    if _has_agree(text):
        return {"type": "agree", "entities": entities}
    if any(mark in low for mark in QUESTION_MARKERS):
        return {"type": "question", "entities": entities}
    return {"type": "unclear", "entities": entities}


def check_agreement(url: str, text: str) -> bool:
    """Клиент подтвердил старт работы -> статус won, задача агентам, автосчёт."""
    if not _has_agree(text):
        return False
    meta = crm.meta(url)
    if meta.get("status") not in ("reply", "negotiation", "ready", "sent"):
        return False
    crm.set_status(url, "won")
    job = next((j for j in store.load("jobs", {"items": []}).get("items", [])
                if j.get("url") == url), None) or {}
    tz = (job.get("description") or job.get("title") or "")
    if not executor.task_for(url):
        executor.create_exec_task(url, tz=tz, title=job.get("title", ""), source="auto:agreement")
    inv = billing.auto_invoice(url)
    if inv and not inv.get("error"):
        billing.send_to_client(inv, url)
    store.append("activity", {"ts": store.now(), "text": f"СОГЛАСИЕ: заказ {url[:60]} -> won, задача агентам, счёт"}, key="activity")
    return True


def _find_order_for_text(text: str) -> str | None:
    """Пытается найти заказ в jobs по ключевым словам из входящего сообщения."""
    low = (text or "").lower()
    jobs = store.load("jobs", {"items": []}).get("items", [])
    # Ищем заказ, чей title/description пересекается с входящим
    for j in jobs:
        jtext = ((j.get("title") or "") + " " + (j.get("description") or "")).lower()
        # Простое пересечение слов
        words = set(re.findall(r"[а-яёa-z0-9]{4,}", low))
        jwords = set(re.findall(r"[а-яёa-z0-9]{4,}", jtext))
        if len(words & jwords) >= 2:
            return j.get("url")
    return None


def _ensure_order_for_peer(peer: str, text: str) -> str | None:
    """Находит или создаёт заказ для пира на основе контекста."""
    # Сначала пробуем стандартный поиск по пиру
    order = chat.find_order_for_peer(peer)
    if order:
        return order
    # Потом — поиск по тексту
    order = _find_order_for_text(text)
    if order:
        return order
    return None


def _meaningful(text: str) -> bool:
    """Не болтовня ли: есть вопрос или >=2 значимых слова."""
    t = (text or "").strip()
    if "?" in t:
        return True
    return len(re.findall(r"[а-яёa-z0-9]{3,}", t.lower())) >= 2


def _last_out_ts(thread: list[dict]) -> float:
    """Время нашего последнего исходящего в диалоге (epoch), 0 если не было."""
    ts = 0.0
    for x in thread:
        if x.get("direction") != "out":
            continue
        try:
            ts = max(ts, time.mktime(time.strptime(x["ts"][:19], "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            continue
    return ts


def cycle(limit: int = 5) -> int:
    """Отвечает заказчикам. Один диалог — один ответ за цикл (на ПОСЛЕДНЕЕ входящее),
    кулдаун DIALOG_COOLDOWN_MIN между нашими ответами, болтовня и скам — мимо.
    Также отвечает на входящие без заказа, если есть ключевые слова (бюджет, сроки, ТЗ, кейсы)."""
    kill_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "KILL_SWITCH")
    kill_state_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "kill_switch_active.json")
    kill_active = False
    if os.path.exists(kill_path):
        kill_active = True
    else:
        try:
            import json
            with open(kill_state_path, "r", encoding="utf-8") as f:
                kill_active = (json.load(f) or {}).get("kill_switch_active", False)
        except Exception:
            pass
    if kill_active:
        return 0
    # AUTO-REPLY MUST BE ENABLED VIA SETTINGS:
    #   zarabotok/pipeline_v3/config/settings.json  -> {"auto_reply": true, "dialog_cooldown_min": 5}
    #   zarabotok/pipeline_v3/state/settings.json     -> must have "auto_reply": true
    #   store.load("settings", {}).get("auto_reply")  must be truthy or cycle() exits (line 256).
    if not store.load("settings", {}).get("auto_reply"):
        return 0
    # ---- глобальный дневной лимит автоответов (анти-спам)
    try:
        acts = store.load("activity", {})
        items = acts.get("activity") if isinstance(acts.get("activity"), list) else acts.get("items") or []
        today = time.strftime("%Y-%m-%d")
        sent_today = sum(1 for a in items
                         if str(a.get("ts", "")).startswith(today)
                         and "автоответ отправлен" in str(a.get("text", "")))
        if sent_today >= 25:
            return 0
    except Exception:
        pass
    replied = 0
    msgs = store.load("messages", {"items": []}).get("items", [])
    
    # ---- 1. Сообщения с заказом (старая логика)
    targets_with_order = [m for m in msgs if m.get("direction") == "in" and m.get("order") and not m.get("replied")]
    # батчинг: несколько входящих подряд = отвечаем только на последнее
    latest: dict[str, dict] = {}
    for m in sorted(targets_with_order, key=lambda x: x.get("ts", "")):
        latest[m["order"]] = m
    for m in targets_with_order:
        if latest.get(m.get("order")) is not m:
            _mark_replied(m, m["order"], skip=True)
    targets_with_order = list(latest.values())
    
    # ---- 2. Сообщения БЕЗ заказа, но с триггерами (новая логика)
    TRIGGER_WORDS = ("бюджет", "стоимост", "цен", "прайс", "сколько стоит",
                     "срок", "когда", "как долго", "за сколько", "тайминг",
                     "портфолио", "примеры", "кейсы", "работы покаж",
                     "тз", "техническое задание", "описание задачи", "подробнее",
                     "сколько стоит", "стоимость", "цена")
    
    targets_no_order = [
        m for m in msgs 
        if m.get("direction") == "in" 
        and not m.get("order") 
        and not m.get("replied")
        and any(w in (m.get("text") or "").lower() for w in TRIGGER_WORDS)
        and not _is_scam(m.get("text", ""))
    ]
    # батчинг для без-заказных
    latest_no_order: dict[str, dict] = {}
    for m in sorted(targets_no_order, key=lambda x: x.get("ts", "")):
        key = m.get("sender", "") + "|" + str(m.get("ts", "")[:10])
        latest_no_order[key] = m
    targets_no_order = list(latest_no_order.values())
    
    all_targets = targets_with_order + targets_no_order

    for m in all_targets[:limit]:
        order = m.get("order")
        text_in = m.get("text", "")
        cls = classify_message(text_in)
        
        # Если нет заказа — пытаемся найти/создать
        if not order:
            peer = m.get("sender", "")
            order = _ensure_order_for_peer(peer, text_in)
            if not order:
                # Не нашли заказ — отвечаем шаблоном без привязки к заказу
                text = _template_reply(text_in)
                if not text:
                    _mark_replied(m, "no_order", skip=True)
                    continue
                peer = m.get("sender", "")
                channel = m.get("channel", "tg")
                ok = _send(peer, channel, text)
                if ok:
                    crm.agents_log("no_order", "autoreply", f"автоответ без заказа ({channel}): {text[:90]}...")
                    replied += 1
                _mark_replied(m, "no_order", skip=False)
                continue
            # Нашли заказ — обновляем сообщение
            def _set_order(d):
                for x in d.get("items", []):
                    if x.get("ts") == m.get("ts") and x.get("sender") == m.get("sender"):
                        x["order"] = order
                        return None
                return None
            store.mutate("messages", _set_order, {"items": []})
        
        if cls["type"] == "decline":
            def _decline(d):
                for x in d.get("items", []):
                    if (x.get("order") == order and x.get("direction") == "in"
                            and x.get("ts") == m.get("ts")):
                        x["decline"] = True
                        x["replied"] = True
                        x["replied_skip"] = True
                        return None
                return None
            store.mutate("messages", _decline, {"items": []})
            continue

        # согласие клиента — приоритет, вне кулдауна
        check_agreement(order, text_in)

        thread = chat.thread(order)
        if any(x.get("replied_to", "") == m.get("ts") for x in thread):
            continue

        # ---- кулдаун: наши недавние ответы не спамим повторами
        cooldown = store.load("settings", {}).get("dialog_cooldown_min") or DIALOG_COOLDOWN_MIN
        if time.time() - _last_out_ts(thread) < cooldown * 60:
            continue

        # ---- болтовня/неясное короткое — молча пропускаем
        if cls["type"] == "unclear" and not _meaningful(text_in):
            crm.agents_log(order, "autoreply", f"болтовня/неясное, пропуск: {text_in[:40]}")
            _mark_replied(m, order, skip=True)
            continue

        if _is_scam(text_in):
            crm.agents_log(order, "autoreply", "скам-входящее, автоответ пропущен")
            _mark_replied(m, order, skip=True)
            continue

        text = _llm_reply(order, thread) or _template_reply(text_in)
        if not text:
            # LLM недоступен/ответ забракован QA — НЕ отправляем мусор, попробуем в след. цикле
            crm.agents_log(order, "autoreply", "ответ не прошёл контроль качества, пропуск")
            continue
        peer = m.get("sender", "")
        channel = m.get("channel", "tg")
        ok = _send(peer, channel, text)
        if ok:
            out = chat.add(order, "out", channel, peer, text)
            out["replied_to"] = m.get("ts")
            crm.agents_log(order, "autoreply", f"автоответ отправлен ({channel}): {text[:90]}...")
            replied += 1
        else:
            crm.agents_log(order, "autoreply", f"ошибка отправки автоответа ({channel})")
        _mark_replied(m, order, skip=False)
    return replied


def _send(peer: str, channel: str, text: str) -> bool:
    if channel == "email":
        return sender.send_email({"title": "Ответ по проекту", "to": peer, "text": text})
    if channel == "fl":
        from modules import fl_bidder
        return fl_bidder.send_dialog(peer, text)
    return sender.send_telegram({"contact": peer, "text": text})


def _mark_replied(m: dict, order: str, skip: bool = False):
    def _fn(d):
        for x in d.get("items", []):
            if (x.get("order") == order and x.get("direction") == "in"
                    and x.get("ts") == m.get("ts")):
                x["replied"] = True
                x["replied_skip"] = skip
                return None
        return None
    store.mutate("messages", _fn, {"items": []})