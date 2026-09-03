"""Отклик-генератор с жёстким контролем качества и соблюдения правил.

Поток (dual_draft):
  Writer (model=writer) пишет отклик по чек-листу правил ->
  Judge (model=judge) оценивает по тем же правилам, возвращает структуру
  {score, confidence, pass, violations, fix} ->
  если не pass и остались попытки -> Revise (исправляет по feedback) -> Judge снова.
  Финальный текст проходит QA-гейт; если и после правок не проходит — шаблон (помечен как template).

Движок LLM — OpenAI-совместимый API LM Studio (127.0.0.1:1234). Все вызовы идут через
_chat(), который можно подменить (chat_fn) для детерминированных тестов.
"""
import json as _json
import html
import os
import re
import time
import urllib.request

from modules import llm, quality, store

# троттлинг: минимальный интервал между LLM-вызовами чтобы не перегружать LM Studio/ПК
_LLM_MIN_GAP = 0.8
_LLM_LAST = [0.0]

# ----------------------------- правила -----------------------------
BAD_PHRASES = (
    "я готов", "я готова", "готов(а) приступить", "готова приступить", "готов приступить",
    "спасибо за интерес", "спасибо за", "буду рад помочь", "буду рад", "предоставлю",
    "предоставить", "напишите мне", "свяжитесь со мной", "обращайтесь",
)
# критичные нарушения — при них отклик бракуется вне зависимости от score
CRITICAL = ("не релевант", "не на русском", "от лица заказчика", "нет вопроса", "спам")

RULES_TEXT = (
    "Правила, которым должен следовать отклик фрилансера на заказ:\n"
    "1) Язык — русский, от первого лица («я»/«у меня»); НЕ от лица заказчика.\n"
    "2) Релевантен заказу: упоминает суть задачи (технологии/действие), а не общие слова.\n"
    "3) Нет клише и запрещённых фраз: «я готов», «готов(а) приступить», «могу», "
    "«предоставлю», «спасибо за интерес», «буду рад помочь», «напишите мне».\n"
    "4) Содержит ровно ОДИН конкретный уточняющий вопрос по деталям заказа "
    "(НЕ «нужен ли вам специалист» и не «готовы обсудить»).\n"
    "5) Не завышает обещания и не называет сроки/цену безосновательно.\n"
    "6) Один абзац, 80–600 символов, без нумерованных/маркированных списков и хештегов.\n"
    "7) Нет повторов, мусора и лишних приветствий/прощаний.\n"
)


def _cfg_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def _sender_cfg() -> dict:
    try:
        with open(_cfg_path(), encoding="utf-8") as f:
            return _json.load(f).get("sender", {})
    except Exception:
        return {}


def _models() -> dict:
    try:
        with open(_cfg_path(), encoding="utf-8") as f:
            return _json.load(f).get("models", {})
    except Exception:
        return {}


def _quality_threshold() -> float:
    try:
        with open(_cfg_path(), encoding="utf-8") as f:
            return float(_json.load(f).get("quality_threshold", 0.75))
    except Exception:
        return 0.75


# ----------------------------- контакты -----------------------------
TG_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")
MAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_contacts(job: dict) -> dict:
    """Прямые контакты заказчика в теле заказа: @username / t.me / email.
    Возвращает {'channel': 'tg'|'email'|'manual', 'contact': ..., 'to': ...}"""
    txt = " ".join(x for x in (job.get("title"), job.get("description")) if x)
    m = TG_RE.search(txt)
    if m:
        user = m.group(1).lstrip(".").lstrip(" ")
        if user.lower() not in ("gotoisland", "devkg", "findwork", "llm_jobs", "freelance_orders",
                                "frilans", "vorkzavr", "workayte", "freelancersu", "telegram", "bot"):
            return {"channel": "tg", "contact": f"tg:@{user}", "to": None}
    m = MAIL_RE.search(txt)
    if m:
        return {"channel": "email", "contact": None, "to": m.group(0)}
    return {"channel": "manual", "contact": None, "to": None}


def _our_email() -> str:
    try:
        return (store.load("settings", {}).get("email", {}) or {}).get("smtp_user", "")
    except Exception:
        return ""


def _parse_budget(text: str) -> int:
    """Extract budget in RUB from text. Returns 0 if not found or not in RUB."""
    if not text:
        return 0
    # Handle HTML entities
    text = text.replace("&nbsp;", " ").replace("&nbsp;", " ")
    # Pattern for RUB amounts: "100 000 ₽", "5000 ₽", "1000 руб", "5000 руб.", "100 000 руб."
    m = re.search(r"(\d[\d\s\u00a0.,]{0,11})\s*(?:₽|руб\.?(?:лей)?|rub\b)", text, re.IGNORECASE)
    if m:
        try:
            val = int(re.sub(r"\D", "", m.group(1)))
            return val
        except:
            pass
    # Pattern for "X тыс" or "Xk" meaning thousands
    m = re.search(r"(?:до\s*)?(\d+(?:[.,]\d+)?)\s*тыс", text, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1).replace(",", "."))
            return int(val * 1000)
        except:
            pass
    return 0


def _is_relevant_job(job: dict) -> bool:
    """Filter out non-relevant/non-profitable jobs."""
    # Skip if description too short
    if len((job.get("description") or "").strip()) < 80:
        return False
    
    # Check for scam markers
    if is_scam(job):
        return False
    
    # Check budget - must be at least 5000 RUB or "по договоренности"
    budget_str = (job.get("budget") or "").lower()
    if budget_str and "по договоренности" not in budget_str:
        budget_val = _parse_budget(budget_str)
        if budget_val and budget_val < 5000:
            return False  # Not profitable for agent network
    
    # Skip scam/spam markers
    low_title = (job.get("title") or "").lower()
    SKIP_MARKERS = (
        "без опыта", "опыт не нужен", "обучение бесплат", "под ключ",
        "подписчиков за", "накрутк", "бomж", "бомж", "деньги просто так",
        "быстрый заработ", "лёгкий заработ", "легкий заработ",
        "казино", "дроп", "лотере", "выигрыш", "набираем",
        "в казик", "бонус", "фаст", "stake", "каппер", "ставк",
        "трейдинг", "сигнал", "крипто", "инвестиц", "вложени",
        "обменник", "пассивн", "passive", "заработ в день",
        "заработать в день", "заработок в день", "за 1 час", "за час",
        "anydesk", "rustdesk", "teamviewer", "удаленный доступ", "удалённый доступ",
        "оборудован", "майнинг", "нейросе", "нише", "ниша",
        "подписчиков за", "накрутк", "бomж", "бомж", "деньги просто так",
        "быстрый заработ", "лёгкий заработ", "легкий заработ",
        "оборудован", "майнинг", "нейросе", "нише", "ниша",
        "подписчиков за", "накрутк", "бomж", "бомж", "деньги просто так",
        "быстрый заработ", "лёгкий заработ", "легкий заработ",
        "оборудован", "майнинг", "нейросе", "нише", "ниша",
    )
    title_low = (job.get("title") or "").lower()
    if any(marker in title_low for marker in SKIP_MARKERS):
        return False
    
    return True


def llm_available(url: str = "http://127.0.0.1:1234/v1/models") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


# ----------------------------- LLM-вызов -----------------------------
def _chat(model_id: str, system: str, user: str, *,
          max_tokens: int = 600, temperature: float = 0.3,
          timeout: int = 180, retries: int = 1) -> str | None:
    # троттлинг: не чаще _LLM_MIN_GAP между вызовами
    _gap = _LLM_MIN_GAP - (time.time() - _LLM_LAST[0])
    if _gap > 0:
        time.sleep(_gap)
    _LLM_LAST[0] = time.time()
    last = None
    for _ in range(max(retries, 1)):
        try:
            body = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "enable_thinking": False,
            }
            req = urllib.request.Request(
                "http://127.0.0.1:1234/v1/chat/completions",
                data=_json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                msg = _json.loads(r.read())["choices"][0]["message"]
                content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            if content:
                return content
            last = "empty"
        except Exception as e:  # noqa: BLE001
            last = str(e)
    return None


# ----------------------------- шаблон (фолбэк) -----------------------------
def template_draft(job: dict) -> str:
    """Надёжный деловой отклик от первого лица по типу задачи (без LLM-галлюцинаций)."""
    title = html.unescape((job.get("title") or ""))
    t = title.lower() + " " + html.unescape(job.get("description") or "").lower()
    b = html.unescape((job.get("budget") or "").strip())
    if any(w in t for w in ("парсер", "парсинг", "скрап", "scrap", "сбор данных", "цена", "walmart", "amazon", "ozon", "wb ", "маркетплейс")):
        body = ("Пишу парсеры на Python 4+ года: сбор с сайтов и маркетплейсов, обход блокировок, "
                "отчёты в JSON/Excel/БД. По задаче сделаю прототип за 1-2 дня. "
                "Какие источники и с какой периодичностью нужно опрашивать?")
    elif any(w in t for w in ("сайт", "лендинг", "tilda", "тильда", "wordpress", "вордпресс", "вёрстк", "верстк", "landing", "lp ")):
        body = ("Делаю сайты/лендинги: от вёрстки до полноценного сайта с админкой и оплатой. "
                "Быстро, аккуратно, с базовым SEO. "
                "Скиньте ТЗ или пример?")
    elif any(w in t for w in ("aiogram", "telebot", "chatbot", "чат-бот", "чатбот", "телеграм-бот", "телеграм бот", "discord-бот", "бот для", "бота на", "написать бота", "разработать бота", "сделать бота")):
        body = ("Разрабатываю Telegram/чат-ботов на Python (aiogram/telebot): приём заявок, "
                "оплата, интеграции, админка. Есть готовые кейсы. "
                "Какой сценарий бота вам нужен?")
    elif any(w in t for w in ("ai", "llm", "нейросет", "gpt", "openai", "ml", "computer vision", "npl", "модел")):
        body = ("Python-разработчик с опытом AI/LLM-интеграций: генерация, CV, обработка данных, "
                "API (OpenAI/локальные модели). Готов разобраться в задаче — "
                "какой объём и ожидаемый результат нужны?")
    elif any(w in t for w in ("api", "интеграц", "webhook", "автоматизац", "скрипт", "backend", "бэкенд", "fastapi", "django")):
        body = ("Бэкенд-разработчик Python (FastAPI/Django): API, интеграции, вебхуки, "
                "автоматизация процессов. Возьму задачу — "
                "что должно быть на входе и выходе?")
    elif any(w in t for w in ("excel", "таблиц", "отчёт", "отчет", "дашборд", "dashboard", "аналитик")):
        body = ("Автоматизирую работу с данными: Excel/Google Sheets, отчёты, дашборды, "
                "сбор из источников. Сделаю систему под ваши процессы. "
                "Какие данные и в каком виде нужны?")
    else:
        body = ("Python-разработчик (FastAPI/Django, парсинг, боты, AI-интеграции, автоматизация). "
                "Разберусь в деталях и сделаю надёжно, с тестами. "
                "Пришите подробности или ссылку на проект?")
    price = f" Бюджет ({b}) обсуждаем." if b else ""
    title = html.unescape((job.get("title") or "")).strip()
    ref = f"По задаче «{title[:90]}» " if title else ""
    out = ref + body + price
    em = _our_email()
    if em:
        out += f"\nОперативно отвечу на почте: {em}"
    return quality.clean_output(out)


# ----------------------------- QA-гейт -----------------------------
def _structural_violations(text: str) -> list[str]:
    """Детерминированные проверки, не зависящие от мягкости LLM-Judge."""
    v = []
    low = text.lower()
    if re.search(r"(?m)^\s*\d+[\.\)]\s+\S", text):
        v.append("нумерованный список")
    if re.search(r"(?m)^\s*[\*\-]\s+\S", text):
        v.append("маркированный список")
    if "**" in text or "__" in text or re.search(r"(?m)^#+\s", text):
        v.append("markdown-разметка")
    if len(re.findall(r"[а-яёa-z0-9]{3,}", low)) < 12:
        v.append("слишком короткий")
    if len(text) > 700:
        v.append("слишком длинный")
    for p in BAD_PHRASES:
        if p in low:
            v.append(f"клише: {p}")
    return v


def qa(text: str, job: dict) -> str | None:
    """Возвращает причину брака или None, если отклик допустим к отправке."""
    if not text:
        return "пустой текст"
    struct = _structural_violations(text)
    if struct:
        return "структура: " + "; ".join(struct)
    low = text.lower()
    tz_words = [w for w in re.findall(r"[а-яё]{5,}", (job.get("title") or "").lower())
                if w not in ("заказ", "нужно", "написание", "сделать")]
    if tz_words and not any(w in low for w in tz_words[:5]):
        return "отклик не связан с заданием"
    if "?" not in text and "？" not in text:
        # вопрос может быть выражен глаголом запроса/уточнения (если LLM не поставил знак)
        if not re.search(r"(уточни|опишите|пришлите|скиньте|расскажите|какие|какой|что|напишите|как\s)", low):
            return "нет уточняющего вопроса"
    if re.search(r"\b(мы предлагаем|наша компания|наш специалист|заказчику нужно)\b", low):
        return "написано от лица заказчика"
    if any(w in low for w in ("качественно", "индивидуальный подход",
                               "любой сложности", "работаю на результат")):
        return "вода/шаблонность"
    return None


# ----------------------------- Writer / Judge / Revise -----------------------------
_WRITER_SYS = quality.inject(
    "Ты — опытный фрилансер-разработчик из России. Пишешь отклик НА ЗАКАЗ от своего имени, "
    "чтобы заказчик захотел взять именно тебя.\n\n"
    + RULES_TEXT +
    "\nПиши ОДНИМ абзацем 2-4 предложения обычным текстом: чем полезен по ЭТОЙ задаче "
    "(конкретный опыт/навык), и в конце — один уточняющий вопрос по деталям. "
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: нумерованные/маркированные списки, markdown-разметка "
    "(звёздочки **, жирный шрифт, # заголовки), перечисления через тире. "
    "Только сплошной живой текст, без приветствий и прощаний."
)


def writer_draft(job: dict, chat_fn=_chat, skills: list | None = None) -> str | None:
    mid = _models().get("writer") or "omnicoder-qwen3.5-9b-claude-4.6-opus-uncensored-v2"
    skills = skills or []
    skill_line = f"\nТвои релевантные навыки (упомяни уместно): {', '.join(skills)}." if skills else ""
    prompt = (
        f"ЗАКАЗ: {job.get('title','')}\n"
        f"БЮДЖЕТ: {job.get('budget','')}\n"
        f"ОПИСАНИЕ: {(job.get('description') or '')[:600]}{skill_line}\n\n"
        "Напиши отклик строго по правилам."
    )
    out = chat_fn(mid, _WRITER_SYS, prompt, max_tokens=400, temperature=0.4, timeout=180, retries=1)
    return quality.clean_output(out) if out else None


_JUDGE_SYS = (
    "Ты — строгий редактор, проверяющий отклик фрилансера на соблюдение правил. "
    "Не смягчай оценку. Верни ТОЛЬКО JSON без пояснений:\n"
    '{"score":0-10,"confidence":0-1,"pass":true/false,"violations":["..."],"fix":"..."}\n'
    "score — общая оценка; pass=true только если соблюдены ВСЕ правила и score>=7; "
    "violations — список нарушенных пунктов (если есть); fix — конкретная инструкция по исправлению."
)


def judge_eval(text: str, job: dict, chat_fn=_chat) -> dict:
    """Структурированная оценка. Никогда не падает — при сбое парсинга возвращает разумные дефолты."""
    mid = _models().get("judge") or "qwen2.5-omni-3b"
    threshold = _quality_threshold() * 10
    prompt = (
        RULES_TEXT +
        f"\nЗАКАЗ: {job.get('title','')} | {job.get('budget','')}\n"
        f"ОТКЛИК:\n{text}\n\nОцени по правилам, верни JSON."
    )
    out = chat_fn(mid, _JUDGE_SYS, prompt, max_tokens=200, temperature=0.1, timeout=90, retries=1)
    try:
        m = re.search(r"\{.*\}", out or "", re.S)
        d = _json.loads(m.group(0))
        score = float(d.get("score", 5))
        conf = float(d.get("confidence", 0.5))
        viol = [str(x) for x in (d.get("violations") or [])]
        fix = str(d.get("fix") or "-")
        has_critical = any(any(c in v.lower() for c in CRITICAL) for v in viol)
        passed = (score >= threshold) and not has_critical
        # детерминированный контроль структуры — перевешивает мягкость LLM-Judge
        struct = _structural_violations(text)
        if struct:
            viol = viol + struct
            passed = False
            if fix in ("-", "", None):
                fix = "убери списки/markdown, пиши сплошным абзацем"
        return {"score": score, "confidence": conf, "pass": passed,
                "violations": viol, "fix": fix}
    except Exception:
        return {"score": 5.0, "confidence": 0.3, "pass": False,
                "violations": ["не удалось разобрать оценку"], "fix": "перепиши четче, без клише"}


_REVISE_SYS = (
    "Ты — редактор. Исправь отклик фрилансера, устранив перечисленные нарушения правил, "
    "сохрани суть и живой стиль первого лица. Верни ТОЛЬКО исправленный отклик, без пояснений."
)


def revise(text: str, job: dict, feedback: str, chat_fn=_chat) -> str | None:
    mid = _models().get("writer") or "omnicoder-qwen3.5-9b-claude-4.6-opus-uncensored-v2"
    prompt = (
        f"НАРУШЕНИЯ ПРАВИЛ:\n{feedback}\n\n"
        f"ИСХОДНЫЙ ОТКЛИК:\n{text}\n\n"
        f"ЗАКАЗ: {job.get('title','')}\n\nИсправленный отклик:"
    )
    out = chat_fn(mid, _REVISE_SYS, prompt, max_tokens=400, temperature=0.4, timeout=180, retries=1)
    return quality.clean_output(out) if out else None


def _heuristic_score(text: str, job: dict) -> tuple[float, float]:
    """Детерминированный скоринг качества (без LLM) для горячего пути.

    Возвращает (score 0-10, confidence). Если не проходит QA — 0.
    """
    if qa(text, job):
        return 0.0, 0.3
    s = 8.0
    low = text.lower()
    t = (job.get("title") or "").lower()
    if any(w in low for w in re.findall(r"[а-яёa-z]{4,}", t)):
        s += 0.5
    if "?" in text:
        s += 0.5
    if 120 <= len(text) <= 520:
        s += 0.5
    return min(10.0, s), 0.7


def dual_draft(job: dict, skills: list | None = None, chat_fn=_chat,
              max_revise: int = 0, threshold: float | None = None,
              use_llm: bool = True, use_judge: bool = False) -> dict:
    """Контролируемая генерация отклика.

    use_llm=False -> только детерминированный шаблон (мгновенно, без нагрузки на LLM).
    use_judge=False -> оценка детерминиров and struct-проверкой (без 2-го LLM-вызова).
    Возвращает dict: {text, score, confidence, fix, source, judge, violations, attempts}.
    """
    threshold = threshold if threshold is not None else _quality_threshold() * 10

    def _eval(cur):
        if use_judge:
            return judge_eval(cur, job, chat_fn=chat_fn)
        sc, conf = _heuristic_score(cur, job)
        struct = _structural_violations(cur)
        passed = (sc >= threshold) and not struct
        return {"score": sc, "confidence": conf, "pass": passed,
                "violations": struct, "fix": "убери списки/markdown" if struct else "-"}

    if not use_llm:
        t = template_draft(job)
        sc, conf = _heuristic_score(t, job)
        return {"text": t, "score": sc, "confidence": conf, "fix": "-", "source": "template",
                "judge": sc, "violations": [], "attempts": [{"step": "template", "score": sc, "pass": sc >= threshold}]}

    text = writer_draft(job, chat_fn=chat_fn, skills=skills)
    if not text:
        t = template_draft(job)
        sc, conf = _heuristic_score(t, job)
        return {"text": t, "score": sc, "confidence": conf, "fix": "-", "source": "template",
                "judge": sc, "violations": [], "attempts": [{"step": "template", "score": sc, "pass": sc >= threshold}]}

    cur = text
    attempts = []
    for attempt in range(max_revise + 1):
        j = _eval(cur)
        attempts.append({"step": "draft" if attempt == 0 else "revise", "score": j["score"],
                         "pass": j["pass"], "violations": j["violations"], "fix": j["fix"]})
        if j["pass"]:
            source = "llm" if attempt == 0 else "llm-revised"
            return _finalize(cur, j, source, attempts)
        if attempt >= max_revise:
            break
        fb = j["fix"] + " | нарушения: " + "; ".join(j["violations"])
        revised = revise(cur, job, fb, chat_fn=chat_fn)
        if not revised:
            break
        cur = revised

    t = template_draft(job)
    sc, conf = _heuristic_score(t, job)
    return {"text": t, "score": sc, "confidence": conf, "fix": "-", "source": "template",
            "judge": sc, "violations": [], "attempts": attempts}


def _finalize(text: str, j: dict, source: str, attempts: list) -> dict:
    text = quality.clean_output(text)
    em = _our_email()
    if em and "почт" not in text.lower():
        text = text.rstrip() + f"\nОперативно отвечу на почте: {em}"
    return {"text": text, "score": j["score"], "confidence": j["confidence"],
            "fix": j["fix"], "source": source, "judge": j["score"],
            "violations": j["violations"], "attempts": attempts}


# ----------------------------- скам-гейт -----------------------------
# Маркеры криминала/схем: такие «заказы» не откликаем никогда (бан аккаунта + риск).
SCAM_MARKERS = (
    "кардинг", "карж", "пробив", "кладмен", "закладк", "обнал", "дропп",
    "воркер", "научу работать", "освоить множество", "ищу людей", "без опыта", "оплатить подписку", "требует оплатить", "работа на ставках", "заработок на ставках", "казино",
    "схема заработка", "лёгкий заработ", "легкий заработ", "быстрый заработ",
    "оплата ежедневно", "доход в день", "зарплата каждый день",
    "набор сотрудников", "требуются люди", "ищем людей", "нужны люди",
    "инвестиц", "материалов не требуется", "обучение бесплат", "без опыта работы",
    "скупаю", "скупка", "сим-карт", "сим карт", "купим вашу", "куплЮ", "залива",
    "казик", "казино", "ставки на", "воркер", "обнал", "дроп", "требуются люди",
)


_HOMO = str.maketrans({"0": "о", "3": "з", "4": "а", "6": "б", "1": "л", "5": "с",
                       "e": "е", "o": "о", "a": "а", "c": "с", "h": "н", "p": "р",
                       "k": "к", "m": "м", "t": "т", "x": "х", "y": "у", "b": "в",
                       "u": "и"})


def is_scam(job_like: dict) -> bool:
    """True = заказ похож на скам. Текст нормализуется против гомоглифов
    («БEЗ 0ПЫТА» латиницей == «без опыта»)."""
    t = ((job_like.get("title") or "") + " " +
         (job_like.get("description") or "")).lower().translate(_HOMO)
    return any(m.translate(_HOMO) in t for m in SCAM_MARKERS)


def _quality_threshold() -> float:
    try:
        with open(_cfg_path(), encoding="utf-8") as _f:
            return float((_json.load(_f) or {}).get("quality_threshold", 0.75))
    except Exception:
        return 0.75


# ----------------------------- сборка outbox -----------------------------
AUTHOR_SPAM = {}


def build_outbox(jobs: list[dict], chat_fn=_chat, max_revise: int = 0, llm_top_n: int = 3) -> int:
    """Обновляет outbox новыми черновиками. LLM-генерация вне файлового лока."""
    box = store.load("outbox", {"items": []}).get("items", [])
    by_url = {i["url"]: i for i in box}
    drafts = 0
    to_add = []
    stop = [w.lower() for w in _sender_cfg().get("stopwords", [])]
    try:
        with open(_cfg_path(), encoding="utf-8") as _f:
            _cfg_full = _json.load(_f)
    except Exception:
        _cfg_full = {}
    fl_only = bool((_cfg_full.get("sources") or {}).get("fl_scan_only"))
    skills = [s for s in (_cfg_full.get("skills") or []) if isinstance(s, str)]
    # персональный LLM-драфт — только топ-N лидов по score (остальные — мгновенный шаблон)
    ordered = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)
    llm_ids = {id(ordered[i]) for i in range(min(llm_top_n, len(ordered)))}
    for j in jobs:
        if (j.get("kind") or "").lower() == "vacancy":
            continue
        if fl_only and ("fl.ru" in (j.get("url") or "") or (j.get("source") or "") == "FL"):
            continue
        title = (j.get("title") or "") + " " + (j.get("description") or "")
        if (j.get('platform') or '') == 'GitHub':
            continue  # нет канала доставки (нужен GH-токен)
        if not _is_relevant_job(j):
            continue
        if is_scam(j):
            continue
        # один ник, публикующий много разных «заказов» за день = спамер
        _ak = (j.get('contact') or '').lower()
        if _ak:
            cnt = AUTHOR_SPAM.setdefault(_ak, 0)
            AUTHOR_SPAM[_ak] = cnt + 1
            if cnt >= 3:
                continue
        if len((j.get('description') or '').strip()) < 80:
            continue  # нет содержательного ТЗ — радар-пинги и болтовня
        # Создаём черновики ДЛЯ ВСЕХ платформ.
        # Если контакт есть (TG/email) — channel=tg/email, автоотправка возможна.
        # Если контакта нет (manual) — создаём черновик для ручной отправки через дашборд.
        # НЕ пропускаем manual — создаём черновик для ручной обработки через дашборд.
        # if c["channel"] == "manual":
        #     continue
        url = j["url"]
        c = extract_contacts(j)
        if url in by_url:
            item = by_url[url]
            dirty = False
            if c["channel"] != "manual" and not (item.get("contact") or item.get("to")):
                item["channel"] = c["channel"]
                item["contact"] = c["contact"]
                item["to"] = c["to"]
                dirty = True
            if j.get("score") and not item.get("score"):
                item["score"] = j["score"]
                dirty = True
            # Always sync platform from job
            if j.get("platform") and item.get("platform") != j.get("platform"):
                item["platform"] = j["platform"]
                dirty = True
            if dirty:
                drafts += 1
            continue
        use_llm = id(j) in llm_ids
        dd = dual_draft(j, skills=skills, chat_fn=chat_fn, max_revise=max_revise,
                        use_llm=use_llm, use_judge=False)
        text = dd["text"]
        if qa(text, j):
            continue
        if use_llm:
            time.sleep(1.5)  # пауза только после LLM-заказа — снижение нагрузки
        to_add.append({
            "url": url,
            "title": j["title"],
            "description": j.get("description", ""),
            "budget": j.get("budget", ""),
            "text": text,
            "channel": c["channel"],
            "contact": c["contact"],
            "to": c["to"],
            "score": j.get("score", 0),
            "judge": dd.get("score", 0),
            "confidence": dd.get("confidence", 0),
            "source": dd.get("source", "template"),
            "violations": dd.get("violations", []),
            "audit": dd.get("attempts", []),
            "approved": False,
            "sent": False,
            "created_at": store.now(),
            "platform": j.get("platform", ""),
        })
        drafts += 1

    def _fn(boxd):
        boxd.setdefault("items", [])
        boxd["items"].extend(to_add)
        return len(to_add)

    if to_add:
        store.mutate("outbox", _fn, {"items": []})
    return drafts


# обратная совместимость со старыми вызовами
llm_draft = writer_draft
