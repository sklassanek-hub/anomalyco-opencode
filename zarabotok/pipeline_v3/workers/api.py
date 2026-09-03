"""Zarabotok — REST API панели управления (этап G, полное ТЗ).

Сервер: ThreadingHTTPServer, порт из config.json ui.panel_port = 8766.
Отдаёт JSON + статику ui/dist (React-сборка) либо ui/index.html (ванила).

Чтение — через modules.store (PG/JSON с фолбэком).
Запись — через существующие модули (crm, billing, executor) + store.append/mutate.
Реальная отправка писем/сообщений/счетов происходит ТОЛЬКО из эндпоинтов,
которые явно вызывают send_* — панель это делает по действию пользователя.

Запуск:  python workers/api.py
Останавливается вместе с config.ui.enabled=false или Ctrl+C.
"""
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from modules import store  # noqa: E402

# Порядок колонок канбана / воронки (по ТЗ)
FUNNEL_ORDER = ["new", "draft", "sent", "reply", "negotiation", "won", "invoice", "paid", "closed"]
# crm-статус -> стадия ТЗ (для orders/funnel)
STATUS_MAP = {
    "new": "new", "draft": "draft", "ready": "draft",
    "sent": "sent", "reply": "reply", "negotiation": "negotiation",
    "won": "won", "invoice": "invoice", "paid": "paid",
    "lost": "closed", "archive": "closed", "closed": "closed",
}
# стадия канбана ТЗ -> raw crm-статус (для PATCH-перемещений)
STAGE_RAW = {
    "New": "new", "Replied": "reply", "Conversation": "negotiation",
    "Won": "won", "Invoice": "invoice", "Paid": "paid", "Closed": "closed",
}
RU_STATUS = {
    "new": "Новые", "draft": "Черновики", "sent": "Отправлено",
    "reply": "Ответили", "negotiation": "Переговоры", "won": "Выиграно",
    "invoice": "Счёт", "paid": "Оплачено", "closed": "Закрыто",
}
# канбан-колонки ТЗ
STAGES = ["New", "Replied", "Conversation", "Won", "Invoice", "Paid", "Closed"]
SENSITIVE = ("pass", "token", "wallet", "number", "holder", "phone", "hash", "secret", "address")

KILL_FILE = os.path.join(BASE, "state", "KILL_SWITCH")
KILL_STATE_FILE = os.path.join(BASE, "state", "kill_switch_active.json")


def kill_switch_active() -> bool:
    if os.path.exists(KILL_FILE):
        return True
    try:
        with open(KILL_STATE_FILE, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("kill_switch_active", False)
    except Exception:
        return False


def set_kill_switch(active: bool, confirm: str = ""):
    cfg_path = os.path.join(BASE, "config.json")
    if not confirm or confirm != "operator":
        raise ValueError("operator confirmation required (confirm=operator)")
    # Сохраняем состояние очередей
    for fname in ("outbox.json", "exec_tasks.json"):
        src = os.path.join(BASE, "state", fname)
        if os.path.exists(src):
            pass  # данные не удаляем
    # Пишем флаг
    if active:
        open(KILL_FILE, "w").close()
        with open(KILL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"kill_switch_active": True}, f)
    else:
        if os.path.exists(KILL_FILE):
            os.remove(KILL_FILE)
        with open(KILL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"kill_switch_active": False}, f)
    # Обновляем config.json
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
        cfg["kill_switch_active"] = active
        tmp = cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, cfg_path)
    except Exception:
        pass

_URL_RE = re.compile(r"https?://[^\s)\]}<>\"']+", re.IGNORECASE)
_ERROR_HINTS = ("ошибк", "error", "failed", "exception", "traceback", "timeout", "отказ", "не удалось")


def load_cfg():
    with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _num(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return v
        s = str(v).replace(" ", "").replace(",", ".").replace("₽", "").replace("руб", "").strip()
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _activity(text):
    store.append("activity", {"ts": _now(), "text": text}, key="activity")


def _event(level, source, text, **fields):
    ev = {"ts": _now(), "severity": level, "source": source, "text": text, **fields}
    store.append("events", ev, key="items")
    return ev


# ---------- агрегаты ----------

def _meta_map():
    return store.load("orders_meta", {"items": {}}).get("items", {})


def _job_map():
    jobs = store.load("jobs", {"items": []}).get("items", [])
    return {j.get("url"): j for j in jobs}


def _outbox_list():
    return store.load("outbox", {"items": []}).get("items", [])


def _outbox_map():
    return {i.get("url"): i for i in _outbox_list()}


def _invoices_list():
    return store.load("invoices", {"items": []}).get("items", [])


def _invoices_map():
    return {i.get("url"): i for i in _invoices_list()}


def _tasks_list():
    return store.load("exec_tasks", {"items": []}).get("items", [])


def _msg_count(url):
    return sum(1 for m in store.load("messages", {"items": []}).get("items", [])
               if m.get("order") == url)


def _messages_for(url):
    return [m for m in store.load("messages", {"items": []}).get("items", [])
            if m.get("order") == url]


def _agents_log_for(url):
    return [a for a in store.load("agents_activity", {"items": []}).get("items", [])
            if a.get("order") == url]


def _invoice_for(url):
    inv = _invoices_map().get(url)
    if not inv:
        return None
    return {"no": inv.get("no"), "amount": _num(inv.get("amount")),
            "status": inv.get("status"), "paid_at": inv.get("paid_at"),
            "method": inv.get("method"), "created_at": inv.get("created_at"),
            "sent_at": inv.get("sent_at")}


def _task_for(url):
    for t in _tasks_list():
        if t.get("url") == url:
            return {"status": t.get("status"), "created_at": t.get("created_at"),
                    "done_at": t.get("done_at"), "note": t.get("note"),
                    "agents": [a.get("file") for a in t.get("agents", [])],
                    "version": t.get("version")}
    return None


def _assigned_agent(url, task):
    m = _meta_map().get(url, {})
    if m.get("assigned_agent"):
        return m["assigned_agent"]
    if task and task.get("agents"):
        return task["agents"][0]
    log = _agents_log_for(url)
    return log[-1].get("agent") if log else None


def _quality_gate(task, url):
    if not task:
        return "none"
    if task.get("status") == "done":
        return "ok"
    if task.get("status") == "failed":
        return "failed"
    return "none"


def _artifacts(url, version=""):
    try:
        from modules import executor
        d = executor.version_dir(url, version or "")
        if not os.path.isdir(d):
            return []
        out = []
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                out.append({"name": name, "size": os.path.getsize(p)})
        return out
    except Exception:
        return []


def _order_row(url, m):
    jobs = _job_map()
    outbox = _outbox_map()
    job = jobs.get(url, {})
    ob = outbox.get(url, {})
    pay = m.get("payment", {}) or {}
    task = _task_for(url)
    return {
        "url": url,
        "status": STATUS_MAP.get(m.get("status", "new"), "new"),
        "raw_status": m.get("status", "new"),
        "title": job.get("title") or m.get("title"),
        "budget": job.get("budget") or pay.get("amount") or ob.get("budget") or "",
        "score": job.get("score") or ob.get("score"),
        "source": job.get("source") or job.get("platform") or m.get("source"),
        "channel": ob.get("channel") or (m.get("channel") or None),
        "contact": ob.get("contact") or ob.get("to") or m.get("contact"),
        "client": ob.get("contact") or ob.get("to") or m.get("contact"),
        "ts": m.get("updated_at") or m.get("created_at") or job.get("scanned_at"),
        "scanned_at": job.get("scanned_at"),
        "notes": m.get("notes"),
        "reason_codes": job.get("reason_codes") or m.get("reason_codes"),
        "filter_action": m.get("filter_action") or job.get("filter_action"),
        "assigned_agent": _assigned_agent(url, task),
        "messages": _msg_count(url),
        "invoice": _invoice_for(url),
        "invoice_status": (_invoice_for(url) or {}).get("status"),
        "exec_task": task,
        "quality_gate": _quality_gate(task, url),
        "payment": {"status": pay.get("status"), "amount": _num(pay.get("amount")),
                    "paid_at": pay.get("paid_at"), "method": pay.get("method")},
    }


def api_orders():
    meta_d = _meta_map()
    rows = [_order_row(url, m) for url, m in meta_d.items()]
    rows.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return {"rows": rows, "count": len(rows), "columns": FUNNEL_ORDER}


def api_order_detail(url):
    meta_d = _meta_map()
    m = meta_d.get(url)
    if not m:
        return None
    row = _order_row(url, m)
    job = _job_map().get(url, {})
    task = _task_for(url)
    exec_report = None
    if task:
        try:
            from modules import executor
            exec_report = executor.exec_report(url)
        except Exception:
            exec_report = None
    row["raw_job"] = job
    row["raw_meta"] = m
    row["messages"] = _messages_for(url)
    row["agents_activity"] = _agents_log_for(url)
    row["exec_report"] = exec_report
    row["artifacts"] = _artifacts(url, (task or {}).get("version", "")) if task else []
    return row


def api_deals():
    meta_d = _meta_map()
    rows = []
    for url, m in meta_d.items():
        row = _order_row(url, m)
        raw = m.get("status", "new")
        msgs = _messages_for(url)
        has_inbound = any(x.get("direction") == "in" for x in msgs)
        if raw in ("reply",):
            stage = "Replied"
        elif raw == "negotiation":
            stage = "Conversation"
        elif raw == "won":
            stage = "Won"
        elif raw == "invoice":
            stage = "Invoice"
        elif raw == "paid":
            stage = "Paid"
        elif raw in ("lost", "archive", "closed"):
            stage = "Closed"
        elif raw == "sent" and has_inbound:
            stage = "Replied"
        else:
            stage = "New"
        row["stage"] = stage
        rows.append(row)
    rows.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return {"rows": rows, "count": len(rows), "columns": STAGES}


def api_deal_detail(url):
    meta_d = _meta_map()
    m = meta_d.get(url)
    if not m:
        return None
    return api_order_detail(url)


def _reply_status(ob, max_attempts=4):
    if ob.get("sent"):
        return "sent"
    if ob.get("skip_reason") or (ob.get("attempts") or 0) >= max_attempts:
        return "failed"
    if ob.get("text"):
        return "generated"
    return "draft"


def api_replies():
    items = _outbox_list()
    max_attempts = (load_cfg().get("sender", {}).get("retry", {}) or {}).get("max_attempts", 4)
    rows = []
    for idx, ob in enumerate(items):
        st = _reply_status(ob, max_attempts)
        rows.append({
            "id": ob.get("url") + "#" + str(idx),
            "order": ob.get("url"),
            "model": ob.get("model") or "template",
            "variant": ob.get("variant") or "none",
            "status": st,
            "channel": ob.get("channel") or "manual",
            "contact": ob.get("contact") or ob.get("to"),
            "created_at": ob.get("created_at") or ob.get("ts"),
            "score": ob.get("score"),
            "attempts": ob.get("attempts", 0),
            "last_error": ob.get("last_error"),
            "sent": bool(ob.get("sent")),
        })
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    generated = sum(1 for r in rows if r["status"] == "generated")
    sent = sum(1 for r in rows if r["status"] == "sent")
    failed = sum(1 for r in rows if r["status"] == "failed")
    variants = {}
    for r in rows:
        v = r["variant"]
        vd = variants.setdefault(v, {"generated": 0, "sent": 0, "failed": 0})
        vd[r["status"]] += 1
    return {
        "items": rows, "count": len(rows),
        "metrics": {
            "total": len(rows), "generated": generated, "sent": sent, "failed": failed,
            "response_rate": round(sent * 100.0 / generated, 1) if generated else 0.0,
            "avg_gen_time_ms": None, "tokens_total": None,
            "variants": [{"variant": v, **d} for v, d in variants.items()],
        },
    }


def api_reply_detail(rid):
    items = _outbox_list()
    if "#" in rid:
        url, _, idx = rid.rpartition("#")
        try:
            ob = items[int(idx)]
        except (ValueError, IndexError):
            return None
        if ob.get("url") != url:
            return None
    else:
        for ob in items:
            if ob.get("url") == rid:
                ob = ob
                break
        else:
            return None
    job = _job_map().get(ob.get("url"), {})
    out = dict(ob)
    out["order_title"] = job.get("title")
    out["order_budget"] = job.get("budget")
    return out


def api_filter_pending():
    meta_d = _meta_map()
    jobs = _job_map()
    rows = []
    for url, m in meta_d.items():
        job = jobs.get(url, {})
        score = job.get("score") or m.get("score")
        action = m.get("filter_action") or job.get("filter_action")
        pending = m.get("status") == "manual" or action == "manual" or (score is not None and 0.4 <= score <= 0.7)
        if not pending:
            continue
        suggested = action or ("accept" if (score or 0) >= 0.7 else "reject")
        rows.append({
            "url": url, "title": job.get("title") or m.get("title"),
            "budget": job.get("budget") or "",
            "score": score, "reason_codes": job.get("reason_codes") or m.get("reason_codes"),
            "suggested_action": suggested, "source": job.get("source") or job.get("platform"),
            "scanned_at": job.get("scanned_at") or m.get("updated_at"),
            "description": (job.get("description") or "")[:500],
        })
    rows.sort(key=lambda r: r.get("scanned_at") or "", reverse=True)
    return {"items": rows, "count": len(rows)}


def _agent_stats(agent_file):
    tasks = _tasks_list()
    act = store.load("agents_activity", {"items": []}).get("items", [])
    mine = [t for t in tasks if any(a.get("file") == agent_file for a in t.get("agents", []))]
    active = [t for t in mine if t.get("status") in ("queued", "running")]
    done = [t for t in mine if t.get("status") == "done"]
    durations = []
    for t in done:
        try:
            c = datetime.fromisoformat(str(t.get("created_at") or ""))
            d = datetime.fromisoformat(str(t.get("done_at") or ""))
            durations.append((d - c).total_seconds())
        except (ValueError, TypeError):
            pass
    recent = [a for a in act if a.get("agent") in (agent_file,) and
              str(a.get("ts", "")).startswith((datetime.now().strftime("%Y-%m-%d"),
                                               datetime.now().strftime("%Y-%m-%dT")))]
    avg_dur = round(sum(durations) / len(durations)) if durations else None
    return {
        "active": len(active), "total": len(mine),
        "done": len(done), "success_rate": round(len(done) * 100.0 / len(mine), 1) if mine else None,
        "avg_duration_s": avg_dur, "online": bool(active or recent),
    }


def api_agents():
    try:
        from modules import executor
        agents = executor.all_agents()
    except Exception:
        agents = []
    cat_map = {}
    try:
        from modules import executor
        for cat, lst in executor.agent_index().items():
            if isinstance(lst, list):
                for a in lst:
                    if isinstance(a, dict):
                        cat_map[a.get("file")] = cat
    except Exception:
        pass
    rows = []
    for a in agents:
        f = a.get("file", "")
        st = _agent_stats(f)
        rows.append({
            "name": a.get("name") or f, "file": f, "type": cat_map.get(f, "Общее/Прочее"),
            "desc": (a.get("desc") or "")[:160], **st,
        })
    rows.sort(key=lambda r: r["name"].lower())
    return {"items": rows, "count": len(rows)}


def api_tasks():
    tasks = _tasks_list()
    jobs = _job_map()
    rows = []
    for t in reversed(tasks):
        url = t.get("url")
        ags = [a.get("file") for a in t.get("agents", [])]
        rows.append({
            "id": url, "deal": (jobs.get(url, {}) or {}).get("title") or t.get("title") or url,
            "url": url, "type": ", ".join(a.get("name") or a.get("file") for a in t.get("agents", []))[:120],
            "agents": ags, "assigned_agent": (ags[0] if ags else None),
            "status": t.get("status"), "created_at": t.get("created_at"), "done_at": t.get("done_at"),
            "deadline": None, "note": t.get("note"),
            "quality_gate": _quality_gate(t, url),
            "artifacts": _artifacts(url, t.get("version", "")),
            "version": t.get("version"),
        })
    return {"items": rows, "count": len(rows)}


def api_task_detail(url):
    tasks = _tasks_list()
    task = next((t for t in tasks if t.get("url") == url), None)
    if not task:
        return None
    job = _job_map().get(url, {})
    artifacts = _artifacts(url, task.get("version", ""))
    checks = []
    if not artifacts:
        checks = [{"name": "spec-compliance", "status": "n/a", "note": "артефакты отсутствуют"}]
    for a in artifacts:
        size_ok = a["size"] > 0
        checks.append({"name": f"spec-compliance ({a['name']})", "status": "ok" if size_ok else "failed",
                       "note": f"{a['size']} байт"})
    checks += [
        {"name": "lint", "status": "n/a", "note": "нет интеграции линтера"},
        {"name": "tests", "status": "n/a", "note": "нет интеграции тестов"},
        {"name": "antiplagiarism", "status": "n/a", "note": "нет интеграции"},
    ]
    return {
        "url": url, "deal": job.get("title") or task.get("title") or url,
        "task": task, "artifacts": artifacts, "checks": checks,
        "agents_activity": _agents_log_for(url),
        "report": _task_for(url),
    }


def _parse_ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _naive(dt):
    if dt and dt.tzinfo:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def api_metrics():
    funnel = api_funnel()
    since = _naive(datetime.now()) - timedelta(hours=24)
    jobs = _job_map()
    outbox = _outbox_list()
    invoices = _invoices_list()
    tasks = _tasks_list()

    def count_since(items, key):
        n = 0
        for it in items:
            t = _naive(_parse_ts(it.get(key) or it.get("ts") or it.get("created_at")))
            if t and t >= since:
                n += 1
        return n

    throughput = {
        "orders": round(count_since(jobs.values(), "scanned_at") / 24.0, 1),
        "filter": round(count_since(outbox, "created_at") / 24.0, 1),
        "llm": round(count_since([o for o in outbox if o.get("text")], "created_at") / 24.0, 1),
        "agents": round(count_since(tasks, "created_at") / 24.0, 1),
        "billing": round(count_since(invoices, "created_at") / 24.0, 1),
    }
    lat = []
    for ob in outbox:
        if not ob.get("sent"):
            continue
        j = jobs.get(ob.get("url"))
        t0 = _naive(_parse_ts((j or {}).get("scanned_at")))
        t1 = _naive(_parse_ts(ob.get("created_at") or ob.get("ts")))
        if t0 and t1:
            lat.append((t1 - t0).total_seconds())
    lat.sort()
    def pct(p):
        if not lat:
            return None
        i = min(len(lat) - 1, int(p * len(lat)))
        return round(lat[i], 1)
    paid_inv = [i for i in invoices if i.get("status") == "paid"]
    pay_times = []
    for i in paid_inv:
        c = _parse_ts(i.get("created_at"))
        p = _parse_ts(i.get("paid_at"))
        if c and p:
            pay_times.append((p - c).total_seconds() / 3600.0)
    metrics_items = store.load("metrics", {"items": []}).get("items", [])
    workers = metrics_items[-1] if metrics_items else None
    return {
        "funnel": funnel,
        "throughput_per_stage": throughput,
        "latency_scan_to_sent": {"p50_s": pct(0.50), "p95_s": pct(0.95), "n": len(lat)},
        "kpi": {
            "reply_rate": funnel["conversions"][3]["percent"] if len(funnel["conversions"]) > 3 else 0.0,
            "won_to_paid": funnel.get("won_to_paid", {}).get("percent", 0.0),
            "time_to_payment_h": round(sum(pay_times) / len(pay_times), 1) if pay_times else None,
            "paid_sum": sum(_num(i.get("amount")) or 0 for i in paid_inv),
        },
        "workers": workers,
        "storage": store.storage_info(),
        "ts": _now(),
    }


def _level_of(src, sev, text):
    if sev in ("error", "warning", "info"):
        return sev
    low = (text or "").lower()
    if sev == "critical" or "traceback" in low:
        return "error"
    if any(h in low for h in _ERROR_HINTS):
        return "error" if sev in ("error",) else "warning"
    if "вним" in low or "warning" in low:
        return "warning"
    return "info"


def _order_links(text, known=None):
    if not text:
        return []
    urls = set(_URL_RE.findall(text))
    if known is None:
        known = set(_meta_map().keys()) | set(_job_map().keys())
    return [u for u in urls if u in known]


def _tail_lines(path, n=200, chunk=65536):
    """Хвост файла без чтения целиком (для больших логов)."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    if size <= 0:
        return []
    lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        pos = size
        buf = ""
        while pos > 0 and len(lines) < n:
            pos = max(0, pos - chunk)
            f.seek(pos)
            buf = f.read(min(chunk, size - pos)) + buf
            lines = buf.splitlines()
        return lines[-n:]


def api_logs(service=None, level=None, limit=200, since=None):
    since_dt = _parse_ts(since) if since else None
    known_urls = set(_meta_map().keys()) | set(_job_map().keys())
    entries = []

    def add(ts, svc, sev, text, **extra):
        if service and svc != service:
            return
        lvl = _level_of(svc, sev, text)
        if level and lvl != level:
            return
        t = _parse_ts(ts)
        if since_dt and t and t < since_dt:
            return
        links = _order_links(text, known_urls)
        entries.append({
            "ts": ts, "service": svc, "level": lvl, "text": str(text)[:2000],
            "trace_id": None, "links": [{"order": u} for u in links], **extra,
        })

    for e in store.load("events", {"items": []}).get("items", []):
        add(e.get("ts"), e.get("source") or "events", e.get("severity"), e.get("text") or e.get("msg"),
            **{k: v for k, v in e.items() if k in ("worker", "url", "no")})
    for a in store.load("activity", {"activity": []}).get("activity", []):
        add(a.get("ts"), "activity", "info", a.get("text"))
    for m in store.load("metrics", {"items": []}).get("items", []):
        add(m.get("ts"), "watchdog", "info", "metrics: workers {}/{} storage {}".format(
            m.get("workers_alive"), m.get("workers_total"), m.get("storage", {}).get("mode")))

    logdir = os.path.join(BASE, "logs")
    if os.path.isdir(logdir):
        for fp in sorted(os.listdir(logdir)):
            if not fp.endswith(".jsonl"):
                continue
            try:
                for line in _tail_lines(os.path.join(logdir, fp), 200):
                    try:
                        o = json.loads(line)
                        add(o.get("ts"), o.get("worker") or "logger", o.get("level"), o.get("msg"),
                            **{k: v for k, v in o.items() if k in ("fields",)})
                    except (ValueError, TypeError):
                        continue
            except OSError:
                pass

    for name in ("scanner", "orchestrator", "sender", "listener", "exec_worker", "dashboard", "api", "watchdog"):
        p = os.path.join(BASE, "state", name + (".out.log" if name != "watchdog" else ".log"))
        try:
            for line in _tail_lines(p, 200):
                line = line.strip()
                if line:
                    ts = line[:25] if line[:10].replace("-", "").isdigit() else _now()
                    add(ts, name, "info", line)
        except OSError:
            pass
    entries.sort(key=lambda e: str(e.get("ts") or ""), reverse=True)
    return {"items": entries[:limit], "count": len(entries), "limit": limit,
            "filters": {"service": service, "level": level, "since": since}}


# ---------- существующие эндпоинты ----------

def api_funnel():
    meta_d = _meta_map()
    outbox = _outbox_list()
    counts = {s: 0 for s in FUNNEL_ORDER}
    for m in meta_d.values():
        key = STATUS_MAP.get(m.get("status", "new"), "closed")
        counts[key] += 1
    for i in outbox:
        if i.get("sent"):
            counts["sent"] += 1
        elif i.get("approved"):
            counts["draft"] += 1
        elif i.get("text"):
            counts["draft"] += 1
    total = sum(counts.values()) or 1
    conversions = []
    for a, b in zip(FUNNEL_ORDER, FUNNEL_ORDER[1:]):
        percent = round(counts[b] * 100.0 / counts[a], 1) if counts[a] else 0.0
        conversions.append({"from": a, "to": b, "count_from": counts[a],
                            "count_to": counts[b], "percent": percent})
    won_to_paid = {"from": "won", "to": "paid",
                   "percent": round(counts["paid"] * 100.0 / counts["won"], 1) if counts["won"] else 0.0,
                   "count_from": counts["won"], "count_to": counts["paid"]}
    return {"counts": counts, "total": sum(counts.values()), "order": FUNNEL_ORDER,
            "conversions": conversions, "won_to_paid": won_to_paid, "ru": RU_STATUS}


def api_events(limit=50):
    items = []
    for a in store.load("activity", {"activity": []}).get("activity", []):
        items.append({"ts": a.get("ts"), "source": "activity", "text": a.get("text"), "level": "info"})
    for e in store.load("events", {"items": []}).get("items", []):
        items.append({"ts": e.get("ts"), "source": "events", "text": e.get("text") or e.get("msg"),
                      "level": e.get("severity") or e.get("level")})
    items.sort(key=lambda e: e.get("ts") or "", reverse=True)
    return {"events": items[:limit], "total": len(items), "limit": limit}


def api_invoices():
    items = _invoices_list()
    rows = [{"no": i.get("no"), "url": i.get("url"), "title": i.get("title"),
             "amount": _num(i.get("amount")), "method": i.get("method"),
             "status": i.get("status"), "paid_at": i.get("paid_at"),
             "created_at": i.get("created_at"), "sent_at": i.get("sent_at"),
             "retries": i.get("retries", 0)}
            for i in reversed(items)]
    return {"items": rows, "count": len(rows)}


def api_invoice_detail(no):
    for i in _invoices_list():
        if i.get("no") == no:
            out = dict(i)
            out["amount"] = _num(i.get("amount"))
            out["text"] = None
            try:
                from modules import billing
                out["text"] = billing.render(i)
            except Exception:
                pass
            return out
    return None


def api_payments():
    raw = store.load("payments", {"items": []})
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    if not items:
        meta_d = _meta_map()
        for url, m in meta_d.items():
            pay = m.get("payment", {}) or {}
            if pay.get("status") and pay.get("status") != "none":
                items.append({"url": url, "status": m.get("status"),
                              "pay_status": pay.get("status"), "amount": _num(pay.get("amount")),
                              "method": pay.get("method"), "paid_at": pay.get("paid_at"),
                              "ts": m.get("updated_at")})
    return {"items": items, "count": len(items), "derived": not bool(raw.get("items"))}


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: ("***" if any(s in k.lower() for s in SENSITIVE) else _sanitize(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    return obj


def api_settings():
    cfg = load_cfg()
    return {"config": _sanitize(cfg), "storage": store.storage_info(),
            "panel_port": cfg.get("ui", {}).get("panel_port", 8766),
            "health": api_health_summary()}


def api_health_summary():
    metrics_items = store.load("metrics", {"items": []}).get("items", [])
    last = metrics_items[-1] if metrics_items else {}
    workers_alive = (last or {}).get("workers_alive")
    workers_total = (last or {}).get("workers_total")
    storage = store.storage_info()
    status = "healthy"
    problems = []
    if storage and not storage.get("ok"):
        status = "error"
        problems.append("Хранилище недоступно")
    if workers_total and workers_alive is not None and workers_alive < workers_total:
        status = "degraded"
        problems.append(f"Воркеры {workers_alive}/{workers_total}")
    return {"status": status, "problems": problems, "workers": last, "storage": storage}


def api_orchestrator_status():
    state_dir = os.path.join(BASE, "state")
    workers_alive = {}
    workers_total = 0
    for name in ("watchdog", "scanner", "orchestrator", "sender", "listener", "exec_worker", "dashboard", "api"):
        workers_total += 1
        pid_path = os.path.join(state_dir, "watchdog.pid" if name == "watchdog" else f"{name}.py.pid")
        alive = False
        try:
            pid = int(open(pid_path, encoding="utf-8").read().strip())
            # Check if process exists
            if os.name == "nt":
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                alive = bool(h)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
            else:
                os.kill(pid, 0)
                alive = True
        except Exception:
            alive = False
        workers_alive[name] = alive
    # Read last orchestrator log lines
    log_lines = []
    log_path = os.path.join(state_dir, "orchestrator.out.log")
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
            log_lines = [l for l in lines[-20:] if l.strip()]
    except Exception:
        pass
    return {
        "workers_alive": workers_alive,
        "watchdog_active": workers_alive.get("watchdog", False),
        "orchestrator_active": workers_alive.get("orchestrator", False),
        "log_lines": log_lines,
        "ts": _now(),
    }


def api_orchestrator_queue():
    outbox = store.load("outbox", {"items": []}).get("items", [])
    pending = [item for item in outbox if not item.get("approved")]
    return {
        "queue_length": len(pending),
        "pending_items": pending[:20],
        "total_outbox": len(outbox),
        "ts": _now(),
    }


def api_orchestrator_command(body: dict):
    cmd = (body or {}).get("command", "")
    if not cmd:
        return {"ok": False, "error": "command required"}, 400
    allowed = {"status", "refresh", "restart", "queue", "pause", "resume"}
    if cmd not in allowed:
        return {"ok": False, "error": f"command '{cmd}' not allowed. Use: {allowed}"}, 400
    # Execute basic actions
    if cmd == "status":
        return {"ok": True, "status": api_orchestrator_status()}
    if cmd == "queue":
        return {"ok": True, "queue": api_orchestrator_queue()}
    # For restart/refresh, touch a state file or return message
    if cmd == "restart":
        # Write a restart trigger file for watchdog to pick up
        try:
            state_dir = os.path.join(BASE, "state")
            with open(os.path.join(state_dir, "ORCHESTRATOR_RESTART"), "w", encoding="utf-8") as f:
                f.write(_now())
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500
        return {"ok": True, "message": "restart signal written"}
    if cmd == "refresh":
        return {"ok": True, "message": "refresh acknowledged", "status": api_orchestrator_status()}
    if cmd == "pause":
        # Write kill switch temporarily? Not safe. Just return message.
        return {"ok": True, "message": "pause acknowledged (manual action required)"}
    if cmd == "resume":
        return {"ok": True, "message": "resume acknowledged"}
    return {"ok": True, "command": cmd}


def api_index():
    return {"name": "zarabotok api", "version": "1.0",
            "endpoints": [
                {"method": "GET", "path": "/api/orders", "desc": "заказы (таблица) + связанные"},
                {"method": "GET", "path": "/api/orders/:id", "desc": "детали заказа"},
                {"method": "GET", "path": "/api/deals", "desc": "сделки для канбана (стадии ТЗ)"},
                {"method": "GET", "path": "/api/deals/:id", "desc": "детали сделки"},
                {"method": "GET", "path": "/api/replies", "desc": "отклики + метрики вариантов"},
                {"method": "GET", "path": "/api/replies/:id", "desc": "отклик (prompt/response)"},
                {"method": "GET", "path": "/api/filter/pending", "desc": "очередь ручного ревью"},
                {"method": "GET", "path": "/api/agents", "desc": "агенты и их метрики"},
                {"method": "GET", "path": "/api/tasks", "desc": "задачи исполнителей"},
                {"method": "GET", "path": "/api/tasks/:id", "desc": "детали задачи + артефакты + quality gate"},
                {"method": "GET", "path": "/api/invoices", "desc": "счета"},
                {"method": "GET", "path": "/api/invoices/:id", "desc": "детали счёта (рендер)"},
                {"method": "GET", "path": "/api/payments", "desc": "платежи"},
                {"method": "GET", "path": "/api/metrics", "desc": "агрегированные метрики"},
                {"method": "GET", "path": "/api/logs", "desc": "логи (фильтры service/level/since)"},
                {"method": "GET", "path": "/api/funnel", "desc": "воронка + конверсии"},
                {"method": "GET", "path": "/api/events", "desc": "журнал событий"},
                {"method": "GET", "path": "/api/settings", "desc": "config без секретов"},
                {"method": "POST", "path": "/api/filter/decision", "desc": "решение по ручному ревью"},
                {"method": "PATCH", "path": "/api/deals/:id", "desc": "смена статуса/заметка/назначение агента"},
                {"method": "POST", "path": "/api/invoices/:id/resend", "desc": "повторная отправка счёта"},
                {"method": "POST", "path": "/api/invoices/:id/mark-paid", "desc": "отметить оплаченным"},
                {"method": "POST", "path": "/api/tasks/:id/cancel", "desc": "отмена задачи"},
                {"method": "POST", "path": "/api/tasks/:id/reassign", "desc": "переназначение агента"},
            ]}


# ---------- write-хелперы ----------

def _update_meta(url, **fields):
    def _fn(d):
        m = d.setdefault("items", {}).setdefault(url, {})
        m.update(fields)
        return d
    store.mutate("orders_meta", _fn, {"items": {}})


def _write_filter_decision(body):
    url = (body or {}).get("url")
    decision = (body or {}).get("decision")
    note = (body or {}).get("note") or ""
    if not url or decision not in ("accept", "reject", "manual"):
        return {"error": "url и decision (accept|reject|manual) обязательны"}, 400
    from modules import crm
    target = {"accept": "ready", "reject": "archive", "manual": "new"}[decision]
    try:
        crm.set_status(url, target)
    except Exception as e:
        return {"error": str(e)}, 500
    _update_meta(url, filter_action=decision, updated_at=_now())
    _activity(f"Ручное решение [{decision}]: {url}" + (f" — {note}" if note else ""))
    _event("info", "api", f"filter decision {decision}: {url}", url=url)
    return {"ok": True, "status": target, "url": url}, 200


def _write_deal_patch(url, body):
    from modules import crm
    meta_d = _meta_map()
    if url not in meta_d:
        return {"error": "deal not found"}, 404
    status = (body or {}).get("status")
    note = (body or {}).get("note")
    agent = (body or {}).get("agent")
    if status:
        if status not in crm.STATUSES:
            return {"error": f"unknown status {status}"}, 400
        try:
            crm.set_status(url, status)
        except Exception as e:
            return {"error": str(e)}, 500
        if status == "won":
            try:
                from modules import billing
                inv = billing.auto_invoice(url)
                _activity(f"Победа → создан счёт {inv.get('no')}: {url}")
            except Exception as e:
                _event("warning", "api", f"auto_invoice failed: {e}", url=url)
        _activity(f"Статус изменён → {status}: {url}")
    if note:
        old = meta_d.get(url, {}).get("notes") or ""
        new_note = (old + "\n" + note).strip() if old else note
        _update_meta(url, notes=new_note, updated_at=_now())
        _activity(f"Заметка: {note} ({url})")
    if agent:
        _update_meta(url, assigned_agent=agent, updated_at=_now())
        store.mutate("exec_tasks", lambda d: _prepend_agent(d, url, agent) or d, {"items": []})
        _activity(f"Назначен агент {agent}: {url}")
        _event("info", "api", f"agent assigned {agent}: {url}", url=url)
    row = api_order_detail(url)
    return {"ok": True, "deal": row}, 200


def _prepend_agent(d, url, agent):
    for t in d.setdefault("items", []):
        if t.get("url") == url:
            ags = t.setdefault("agents", [])
            ags.insert(0, {"file": agent, "name": agent})
            return True
    return False


def _write_invoice_resend(no):
    inv = next((i for i in _invoices_list() if i.get("no") == no), None)
    if not inv:
        return {"error": "invoice not found"}, 404
    from modules import billing
    text = billing.render(inv)
    _activity(f"Повторная отправка счёта {no} ({inv.get('url')})")
    _event("info", "api", f"invoice resend {no}", no=no, url=inv.get("url"))
    # реальная отправка выполняется здесь в проде; тесты не вызывают эндпоинт
    try:
        ok = billing.send_to_client(inv, inv.get("url"))
        return {"ok": bool(ok), "no": no, "method": inv.get("method"), "url": inv.get("url")}, 200
    except Exception as e:
        return {"ok": False, "no": no, "error": str(e)}, 500


def _write_invoice_mark_paid(no):
    inv = next((i for i in _invoices_list() if i.get("no") == no), None)
    if not inv:
        return {"error": "invoice not found"}, 404
    from modules import billing
    try:
        res = billing.mark_paid(no)
        _activity(f"Счёт оплачен: {no} ({inv.get('url')})")
        return {"ok": True, "invoice": res}, 200
    except Exception as e:
        return {"error": str(e)}, 500


def _write_task_cancel(url):
    from modules import executor
    try:
        ok = executor.cancel_task(url)
        _activity(f"Задача отменена: {url}")
        return {"ok": bool(ok), "url": url}, 200
    except Exception as e:
        return {"error": str(e)}, 500


def _write_task_reassign(url, body):
    agent = (body or {}).get("agent")
    if not agent:
        return {"error": "agent обязателен"}, 400
    tasks = _tasks_list()
    if not any(t.get("url") == url for t in tasks):
        return {"error": "task not found"}, 404
    _update_meta(url, assigned_agent=agent, updated_at=_now())
    store.mutate("exec_tasks", lambda d: _prepend_agent(d, url, agent) or d, {"items": []})
    _activity(f"Задача {url} переназначена агенту {agent}")
    _event("info", "api", f"task reassign {url} -> {agent}", url=url)
    return {"ok": True, "url": url, "agent": agent}, 200


# ---------- HTTP-обработчик ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "ZarabotokAPI/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[api] %s\n" % (fmt % args))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return False
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        return True

    def _static(self, rel):
        rel = rel.lstrip("/")
        if rel in ("", "/"):
            index = os.path.join(BASE, "ui", "dist", "index.html")
            if os.path.isfile(index):
                return self._file(index, "text/html; charset=utf-8")
            return self._file(os.path.join(BASE, "ui", "index.html"), "text/html; charset=utf-8")
        dist = os.path.join(BASE, "ui", "dist", rel)
        if os.path.isfile(dist):
            ctype = ("application/javascript" if rel.endswith(".js") else
                     "text/css" if rel.endswith(".css") else
                     "application/json" if rel.endswith(".json") else
                     "image/svg+xml" if rel.endswith(".svg") else
                     "application/octet-stream")
            return self._file(dist, ctype)
        return False

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _decode_url(self, raw):
        return urllib.parse.unquote(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)
        # корень и любые не-API пути — на единую панель (8765)
        if not path.startswith("/api/"):
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:8765/")
            self.end_headers()
            return
        try:
            if path == "/api/orders":
                return self._json(api_orders())
            if path.startswith("/api/orders/"):
                url = self._decode_url(path[len("/api/orders/"):])
                row = api_order_detail(url)
                if row is None:
                    return self._json({"error": "order not found", "url": url}, 404)
                return self._json(row)
            if path == "/api/deals":
                return self._json(api_deals())
            if path.startswith("/api/deals/"):
                url = self._decode_url(path[len("/api/deals/"):])
                row = api_deal_detail(url)
                if row is None:
                    return self._json({"error": "deal not found", "url": url}, 404)
                return self._json(row)
            if path == "/api/replies":
                return self._json(api_replies())
            if path.startswith("/api/replies/"):
                rid = self._decode_url(path[len("/api/replies/"):])
                row = api_reply_detail(rid)
                if row is None:
                    return self._json({"error": "reply not found", "id": rid}, 404)
                return self._json(row)
            if path == "/api/filter/pending":
                return self._json(api_filter_pending())
            if path == "/api/agents":
                return self._json(api_agents())
            if path == "/api/tasks":
                return self._json(api_tasks())
            if path.startswith("/api/tasks/"):
                url = self._decode_url(path[len("/api/tasks/"):])
                row = api_task_detail(url)
                if row is None:
                    return self._json({"error": "task not found", "url": url}, 404)
                return self._json(row)
            if path == "/api/invoices":
                return self._json(api_invoices())
            if path.startswith("/api/invoices/"):
                no = self._decode_url(path[len("/api/invoices/"):])
                row = api_invoice_detail(no)
                if row is None:
                    return self._json({"error": "invoice not found", "no": no}, 404)
                return self._json(row)
            if path == "/api/payments":
                return self._json(api_payments())
            if path == "/api/metrics":
                return self._json(api_metrics())
            if path == "/api/logs":
                return self._json(api_logs(
                    service=q.get("service", [None])[0],
                    level=q.get("level", [None])[0],
                    limit=max(1, min(int(q.get("limit", ["200"])[0]), 2000)),
                    since=q.get("since", [None])[0]))
            if path == "/api/funnel":
                return self._json(api_funnel())
            if path == "/api/events":
                limit = int(q.get("limit", ["50"])[0])
                return self._json(api_events(max(1, min(limit, 500))))
            if path == "/api/settings":
                return self._json(api_settings())
            if path == "/api/health":
                return self._json(api_health_summary())
            if path == "/api/match":
                url = q.get("url", [""])[0]
                return self._json(api_match(url))
            if path == "/api/orchestrator/status":
                return self._json(api_orchestrator_status())
            if path == "/api/orchestrator/queue":
                return self._json(api_orchestrator_queue())
            if path.startswith("/api/"):
                return self._json({"error": "not found", "path": path}, 404)
            if path == "/" or path.startswith("/assets/") or path.startswith("/favicon"):
                if self._static(path):
                    return
                return self._json(api_index())
            return self._json({"error": "not found", "path": path}, 404)
        except Exception as e:  # noqa: BLE001 — ошибка не должна ронять сервер
            return self._json({"error": str(e), "path": path}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        try:
            if path == "/api/filter/decision":
                res, code = _write_filter_decision(body)
                return self._json(res, code)
            if path.startswith("/api/invoices/") and path.endswith("/resend"):
                no = self._decode_url(path[len("/api/invoices/"):-len("/resend")])
                res, code = _write_invoice_resend(no)
                return self._json(res, code)
            if path.startswith("/api/invoices/") and path.endswith("/mark-paid"):
                no = self._decode_url(path[len("/api/invoices/"):-len("/mark-paid")])
                res, code = _write_invoice_mark_paid(no)
                return self._json(res, code)
            if path.startswith("/api/tasks/") and path.endswith("/cancel"):
                url = self._decode_url(path[len("/api/tasks/"):-len("/cancel")])
                res, code = _write_task_cancel(url)
                return self._json(res, code)
            if path.startswith("/api/tasks/") and path.endswith("/reassign"):
                url = self._decode_url(path[len("/api/tasks/"):-len("/reassign")])
                res, code = _write_task_reassign(url, body)
                return self._json(res, code)
            if path == "/api/system/stop":
                try:
                    set_kill_switch(True, confirm=body.get("confirm", ""))
                    return self._json({"ok": True, "kill_switch_active": True})
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)}, 400)
            if path == "/api/system/resume":
                try:
                    set_kill_switch(False, confirm=body.get("confirm", ""))
                    return self._json({"ok": True, "kill_switch_active": False})
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)}, 400)
            if path == "/api/approve":
                res, code = _write_approve(body)
                return self._json(res, code)
            if path == "/api/orchestrator/command":
                res = api_orchestrator_command(body)
                if isinstance(res, tuple):
                    return self._json(res[0], res[1] if len(res) > 1 else 200)
                return self._json(res, 200)
            if path == "/api/transfer":
                res, code = _write_transfer(body)
                return self._json(res, code)
            if path.startswith("/api/transfer/"):
                url = self._decode_url(path[len("/api/transfer/"):])
                return self._json(api_transfer_status(url))
            return self._json({"error": "not found", "path": path}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e), "path": path}, 500)

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        try:
            if path.startswith("/api/deals/"):
                url = self._decode_url(path[len("/api/deals/"):])
                res, code = _write_deal_patch(url, body)
                return self._json(res, code)
            return self._json({"error": "not found", "path": path}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e), "path": path}, 500)


def api_match(url: str):
    """Матчинг заказа с агентами-исполнителями (modules.matcher)."""
    if not url:
        return {"error": "url required"}
    job = None
    for j in store.load("jobs", {"items": []}).get("items", []):
        if j.get("url") == url:
            job = j
            break
    if job is None:
        for o in store.load("outbox", {"items": []}).get("items", []):
            if o.get("url") == url:
                job = o
                break
    if job is None:
        return {"url": url, "title": "", "matched": []}
    from modules import matcher
    return {"url": url, "title": job.get("title", ""), "matched": matcher.match_order(job)}


def _write_approve(body):
    """Подтверждение отклика из гибридного режима (sender.approve_and_send)."""
    url = (body or {}).get("url")
    if not url:
        return {"error": "url required"}, 400
    from modules import sender
    ok = sender.approve_and_send(url)
    return {"url": url, "approved": ok}, (200 if ok else 500)


def _write_transfer(body):
    """Agent transfer handoff endpoint (POST /api/transfer)."""
    url = (body or {}).get("url")
    target_agent = (body or {}).get("target_agent")
    reason = (body or {}).get("reason", "")
    if not url or not target_agent:
        return {"error": "url and target_agent required"}, 400
    from modules import conversation, kill_switch
    try:
        link_id = conversation.link_message(url, target_agent, reason)
        kill_switch.write_event({
            "event": "transfer_request",
            "url": url,
            "agent": target_agent,
            "reason": reason
        })
        return {"url": url, "target_agent": target_agent, "link_id": link_id, "status": "ok"}, 200
    except Exception as e:
        return {"error": str(e)}, 500


def api_transfer_status(url: str):
    """GET /api/transfer/<url> — list links."""
    from modules import conversation
    return {"url": url, "links": conversation.list_links(url)}


def main():
    cfg = load_cfg()
    ui = cfg.get("ui", {}) or {}
    if not ui.get("enabled"):
        print("api.py: config ui.enabled=false — сервер не запускаю")
        return
    port = int(ui.get("panel_port", 8766))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"api.py v1.0: http://127.0.0.1:{port} (панель + REST)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("api.py: остановлен")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()