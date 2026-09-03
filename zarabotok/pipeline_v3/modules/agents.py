"""Внутренние агенты pipeline: конвейер обработки заказов через локальный LLM (LM Studio).

Каждый агент — функция run(ctx) -> dict с вердиктом/данными. Оркестратор гоняет конвейер
по каждому свежему заказу; каждое действие фиксируется в state/agents_activity.json.
LLM-слой — OpenAI-совместимый (127.0.0.1:1234/v1), при недоступности — эвристический фолбэк,
поэтому конвейер работает и без локальной модели.
"""
import json
import re
import time
import urllib.request

from modules import proposals, store

LLM_URL = "http://127.0.0.1:1234/v1/chat/completions"
TIME_OUT = 60
AGENTS = ("extraction", "consolidation", "reality_checker", "proposal",
          "model_qa", "outreach", "analyzer")


# ---------- LLM-обёртка ----------

def llm(prompt: str, system: str = "Ты — часть фриланс-аналитической системы.", max_tokens: int = 300) -> str | None:
    try:
        body = {
            "model": "local",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3 if "верни JSON" not in prompt else 0.1,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            LLM_URL,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=TIME_OUT) as r:
            data = json.loads(r.read())
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return None


def log(order_url: str, agent: str, action: str, result: str = "", ok: bool = True):
    def _fn(d):
        d.setdefault("items", []).append({
            "ts": store.now(), "order": order_url, "agent": agent,
            "action": action, "result": result[:300], "ok": bool(ok),
        })
        if len(d["items"]) > 5000:
            d["items"] = d["items"][-3000:]
        return None
    store.mutate("agents_activity", _fn, {"items": []})


# ---------- Агент 1: extraction (нормализация полей) ----------

_BUDGET_RE = re.compile(r"(\d[\d\s\u00a0]*)(\s?₽|\s?руб|рублей|рубля|usd|\$|€|euro|евро|\bлсд\b|\bcny\b)", re.I)
_NUM_RE = re.compile(r"(\d[\d\s\u00a0]*)")


def _parse_budget(text: str) -> str:
    m = _BUDGET_RE.search(text or "")
    if m:
        cur = {"₽": "руб", "руб": "руб", "рублей": "руб", "рубля": "руб",
               "usd": "USD", "$": "USD", "€": "EUR", "евро": "EUR", "euro": "EUR",
               "лсд": "LSD", "cny": "CNY", "\u00a0": "руб"}.get(m.group(2).lower().strip(), m.group(2))
        return (m.group(1).replace(" ", "").replace("\u00a0", "") + " " + cur).strip()
    m = _NUM_RE.search(text or "")
    return (m.group(1).replace(" ", "").replace("\u00a0", "") + " ?") if m else ""


def run_extraction(job: dict) -> dict:
    text = " ".join(str(x) for x in (job.get("title"), job.get("description")) if x)
    budget = job.get("budget") or _parse_budget(text)
    deadline = ""
    m = re.search(r"(срок|deadline|крайний срок|до конца|в течение)\s*[:\-]?\s*([^.]+)", text, re.I)
    if m:
        deadline = m.group(2).strip()[:60]
    c = proposals.extract_contacts(job)
    log(job.get("url", ""), "extraction", "поля нормализованы",
        f"budget={budget!r} deadline={deadline!r} contact={c['channel']}")
    return {"budget": budget, "deadline": deadline, "channel": c["channel"],
            "contact": c["contact"], "to": c["to"]}


# ---------- Агент 2: consolidation (дедупликация) ----------

def _norm(s: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", (s or "").lower())


def run_consolidation(job: dict) -> dict:
    jobs = store.load("jobs", {"items": []}).get("items", [])
    title_n = _norm(job.get("title"))
    dup = None
    for j in jobs:
        if j is job or j.get("url") == job.get("url"):
            continue
        if _norm(j.get("title")) == title_n and title_n:
            dup = j.get("url")
            break
    if dup:
        log(job.get("url", ""), "consolidation", "дубликат", f"совпадает с {dup}")
        return {"dup": dup, "verdict": "dup"}
    log(job.get("url", ""), "consolidation", "уникален")
    return {"dup": None, "verdict": "new"}


# ---------- Агент 3: reality_checker (анти-фрод) ----------

_SCAM_HINTS = (
    "вложени", "инвестиц", "крипто", "обменник", "обмен валют", "кази", "депаю",
    "заработ в день", "в день", "за час", "anydesk", "rustdesk", "оборудован",
    "нейросе", "нише", "без опыта", "обучение бесплат", "подписчик", "накрутк",
    "#резюме", "#помогу", "#предлагаю", "заказать рекламу", "рекламу в telegram",
    "пассивн", "ломбард", "кредит", "микрозайм", "деньги под", "ставки", "спорт-ставк",
    "через 5 минут", "прямо сейчас", "срочно 100", "выплат от", "за 1 час",
)
_CUSTOMER_HINTS = ("нужен", "нужна", "нужно", "ищем", "ищу", "требуется", "требуют",
                   "хотим", "хочет", "заказ", "проект", "сделать", "разработать",
                   "написать", "сверстать", "подключить", "собрать", "создать")


def run_reality_checker(job: dict) -> dict:
    text = " ".join(str(x) for x in (job.get("title"), job.get("description")) if x).lower()
    hits = [h for h in _SCAM_HINTS if h in text]
    is_customer = any(h in text for h in _CUSTOMER_HINTS)
    resume = any(h in text for h in ("#резюме", "#помогу", "#предлагаю", "привет! я", "меня зовут"))
    if hits or resume:
        verdict = "scam"
        reason = f"сигналы: {', '.join(hits[:3])}" + ("; резюме исполнителя" if resume else "")
    elif is_customer:
        verdict = "real"
        reason = "похоже на заказ от заказчика"
    else:
        verdict = "unknown"
        reason = "недостаточно маркеров"
    log(job.get("url", ""), "reality_checker", f"вердикт={verdict}", reason)
    return {"verdict": verdict, "reason": reason}


# ---------- Агент 6: proposal (черновик отклика) ----------

_PROPOSAL_SYS = (
    "Ты — фрилансер-программист из России. Напиши отклик на заказ: 1-3 предложения, "
    "без приветствий и клише, конкретно по задаче. Запрещено: 'я готов', 'предоставить', "
    "'спасибо за интерес'. В конце один уточняющий вопрос по ТЗ. Отклик на русском."
)


def run_proposal(job: dict) -> dict:
    draft = proposals.llm_draft(job, [])
    if not draft:
        draft = proposals.template_draft(job)
    log(job.get("url", ""), "proposal", "черновик готов", draft[:150])
    return {"text": draft}


# ---------- Агент 5: model_qa (проверка черновика) ----------

def run_model_qa(job: dict, draft: str) -> dict:
    reason = proposals.qa(draft, job)
    if reason:
        log(job.get("url", ""), "model_qa", "QA reject", reason)
        return {"pass": False, "reason": reason, "text": draft}
    src = "llm" if "<" not in draft else "template"
    log(job.get("url", ""), "model_qa", "QA pass", f"источник={src}")
    return {"pass": True, "reason": None, "text": draft, "source": src}


# ---------- Агент 6: outreach (очередь/канал отправки) ----------

def run_outreach(job: dict, meta: dict) -> dict:
    ch = meta.get("channel", "manual")
    decision = "send" if ch in ("tg", "email") and meta.get("contact") or meta.get("to") else "hold"
    reason = f"канал={ch} контакт={'есть' if (meta.get('contact') or meta.get('to')) else 'нет'}"
    log(job.get("url", ""), "outreach", f"решение={decision}", reason)
    return {"decision": decision, "reason": reason}


# ---------- Агент 7: analyzer (сводка по воронке) ----------

def run_analyzer() -> dict:
    jobs = store.load("jobs", {"items": []}).get("items", [])
    box = store.load("outbox", {"items": []}).get("items", [])
    meta = store.load("orders_meta", {"items": {}}).get("items", {})
    total = len(jobs)
    with_contact = sum(1 for i in box if i.get("contact") or i.get("to"))
    approved = sum(1 for i in box if i.get("approved"))
    sent = sum(1 for i in box if i.get("sent"))
    won = sum(1 for v in meta.values() if v.get("status") == "won")
    paid = sum(1 for v in meta.values() if v.get("payment", {}).get("status") == "paid")
    summary = {
        "total": total, "drafts": len(box), "with_contact": with_contact,
        "approved": approved, "sent": sent, "won": won, "paid": paid,
        "ts": store.now(),
    }
    log(":system:", "analyzer", "сводка", json.dumps(summary, ensure_ascii=False)[:250])
    return summary


# ---------- Агенты-исполнители (exec_worker): локальные функции без LLM ----------

NON_TEXT_EXEC_AGENTS = {"vote-prices"}


def run_orch_fake(tz: str = "") -> dict:
    time.sleep(2)
    text = (
        f"# Результат агента (детерминированный тест)\n\n"
        f"ТЗ: {tz or '(пусто)'}\n\n"
        "Это фиксированный вывод агента-исполнителя для проверки конвейера exec_worker "
        "без обращения к LM Studio. Содержит более двухсот символов, чтобы пройти валидацию "
        "длины текстового вывода: задача, план работ, шаги, ожидаемые артефакты, критерии "
        "приёмки, оценка стоимости и сроков, список рисков, порядок сдачи, контакты и ссылки. "
        "Текст на русском языке занимает достаточно объёма для проверки непустоты и минимальной "
        "длины вывода агента.\n"
    )
    return {"text": text}


def run_vote_prices(tz: str = "") -> dict:
    return {"text": "цена_голоса: 5 руб, репост: 15 руб, подписчик: 25 руб"}


def run_orch_empty(tz: str = "") -> dict:
    return {"text": ""}


EXEC_AGENT_FUNCS = {"orch-fake": run_orch_fake, "vote-prices": run_vote_prices, "orch-empty": run_orch_empty}


def validate_exec_output(agent_file: str, text: str) -> bool:
    text = text or ""
    if agent_file in NON_TEXT_EXEC_AGENTS:
        return bool(text.strip())
    return len(text.strip()) > 200


# ---------- Конвейер ----------

def pipeline_for(job: dict, dry: bool = False) -> dict:
    """Прокачивает заказ через весь конвейер агентов. Возвращает обогащённый job."""
    meta = run_extraction(job)
    job.setdefault("budget", meta["budget"] or job.get("budget", ""))
    job["deadline"] = meta["deadline"]
    if meta["channel"] != "manual":
        job["channel"] = meta["channel"]
        job["contact"] = meta["contact"]
        job["to"] = meta["to"]

    dup = run_consolidation(job)
    if dup["verdict"] == "dup" and not dry:
        return {**job, "agent_verdict": "dup"}

    rc = run_reality_checker(job)
    job["agent_verdict"] = rc["verdict"]
    if rc["verdict"] == "scam" and not dry:
        return {**job, "agent_reason": rc["reason"]}

    pr = run_proposal(job)
    qa = run_model_qa(job, pr["text"])
    job["draft_text"] = qa["text"]
    if not qa["pass"] and not dry:
        return {**job, "agent_reason": qa["reason"]}

    out = run_outreach(job, meta)
    job["outreach"] = out["decision"]
    return job


def run_all(fresh_jobs: list[dict]) -> dict:
    """Запуск по всем свежим заказам (из оркестратора). Возвращает краткую сводку."""
    result = {"processed": 0, "scam": 0, "dup": 0, "drafts": 0, "contact": 0}
    for j in fresh_jobs:
        out = pipeline_for(j)
        result["processed"] += 1
        if out.get("agent_verdict") == "scam":
            result["scam"] += 1
            continue
        if out.get("agent_verdict") == "dup":
            result["dup"] += 1
            continue
        c = out.get("channel") or "manual"
        if out.get("contact") or out.get("to"):
            result["contact"] += 1
        if out.get("draft_text"):
            result["drafts"] += 1
    summary = run_analyzer()
    result["summary"] = summary
    return result