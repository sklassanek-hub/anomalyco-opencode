"""CRM-метаданные заказов: статусы, оплаты, материалы (files.json), заметки.
Отдельно от jobs.json, чтобы не трогать данные сканера.
"""
import os
import time

from modules import store

STATUSES = ("new", "draft", "ready", "sent", "reply", "negotiation", "won", "lost", "paid", "archive")
PAY_STATUSES = ("none", "partial", "paid", "refund")
PAY_METHODS = ("card", "yoomoney", "usdt", "crypto", "cash", "other")


def meta(order_url: str) -> dict:
    d = store.load("orders_meta", {"items": {}}).get("items", {})
    m = d.get(order_url)
    if m is None:
        m = {"url": order_url, "status": "new", "notes": "", "payment": {"status": "none",
             "amount": "", "currency": "руб", "method": "", "paid_at": "", "receipt_file": ""},
             "created_at": store.now(), "updated_at": store.now()}
    return dict(m)


def update(order_url: str, **kw) -> dict:
    def _fn(d):
        d.setdefault("items", {})
        m = d["items"].get(order_url)
        if m is None:
            m = {"url": order_url, "status": "new", "notes": "", "payment": {"status": "none",
                 "amount": "", "currency": "руб", "method": "", "paid_at": "", "receipt_file": ""},
                 "created_at": store.now(), "updated_at": store.now()}
            d["items"][order_url] = m
        for k, v in kw.items():
            if k == "payment":
                m.setdefault("payment", {}).update(v)
            else:
                m[k] = v
        m["updated_at"] = store.now()
        return None
    store.mutate("orders_meta", _fn, {"items": {}})
    return meta(order_url)


def set_status(order_url: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    old_meta = meta(order_url)
    old_status = old_meta.get("status")
    m = update(order_url, status=status)
    agents_log(order_url, "crm", f"статус -> {status}")
    # Auto-create executor task when status becomes "won"
    if status == "won" and old_status != "won":
        from modules import executor, store, billing
        if not executor.task_for(order_url):
            job = next((j for j in store.load("jobs", {"items": []}).get("items", [])
                        if j.get("url") == order_url), None) or {}
            tz = (job.get("description") or job.get("title") or "")
            executor.create_exec_task(order_url, tz=tz, title=job.get("title", ""), source="crm:won")
            # Auto-invoice
            inv = billing.auto_invoice(order_url)
            if inv and not inv.get("error"):
                billing.send_to_client(inv, order_url)
            store.append("activity", {"ts": store.now(), "text": f"АВТО: заказ {order_url[:60]} -> won, задача агентам, счёт"}, key="activity")
    return m


# ---------- файлы (материалы) ----------

def files_dir() -> str:
    d = os.path.join(store.STATE, "files")
    os.makedirs(d, exist_ok=True)
    return d


def add_file(order_url: str, filename: str, path: str, source: str = "manual") -> dict:
    """Регистрирует файл в реестре files.json (сам файл кладём в state/files)."""
    def _fn(d):
        d.setdefault("items", [])
        d["items"].append({
            "ts": store.now(), "order": order_url, "filename": filename,
            "path": path, "source": source, "size": os.path.getsize(path) if os.path.exists(path) else 0,
        })
        return None
    store.mutate("files", _fn, {"items": []})
    return store.load("files", {"items": []}).get("items", [])[-1]


def list_files(order_url: str | None = None) -> list[dict]:
    items = store.load("files", {"items": []}).get("items", [])
    if order_url:
        return [f for f in items if f.get("order") == order_url]
    return items


def remove_file(file_id: int) -> bool:
    removed = [False]

    def _fn(d):
        items = d.get("items", [])
        if 0 <= file_id < len(items):
            removed[0] = True
            del items[file_id]
        return None
    store.mutate("files", _fn, {"items": []})
    return removed[0]


# ---------- агент-логи ----------

def agents_log(order_url: str, agent: str, action: str, result: str = ""):
    def _fn(d):
        d.setdefault("items", []).append({
            "ts": store.now(), "order": order_url, "agent": agent,
            "action": action, "result": result[:300], "ok": True,
        })
        if len(d["items"]) > 5000:
            d["items"] = d["items"][-3000:]
        return None
    store.mutate("agents_activity", _fn, {"items": []})


def agents_for(order_url: str, limit: int = 60) -> list[dict]:
    return [a for a in store.load("agents_activity", {"items": []}).get("items", [])
            if a.get("order") == order_url][-limit:]


# ---------- агрегаты ----------

def funnel() -> dict:
    box = store.load("outbox", {"items": []}).get("items", [])
    meta_d = store.load("orders_meta", {"items": {}}).get("items", {})
    f = {"new": 0, "draft": 0, "ready": 0, "sent": 0, "reply": 0, "negotiation": 0,
         "won": 0, "lost": 0, "paid": 0, "archive": 0}
    for m in meta_d.values():
        s = m.get("status", "new")
        f[s] = f.get(s, 0) + 1
    f["draft"] += sum(1 for i in box if not i.get("approved"))
    f["ready"] += sum(1 for i in box if i.get("approved") and not i.get("sent"))
    f["sent"] += sum(1 for i in box if i.get("sent"))
    return f


def payments() -> dict:
    meta_d = store.load("orders_meta", {"items": {}}).get("items", {})
    total_expected = 0.0
    total_paid = 0.0
    total_won = 0.0
    rows = []
    for url, m in meta_d.items():
        pay = m.get("payment", {})
        amt = _to_float(pay.get("amount"))
        if pay.get("status") == "paid":
            total_paid += amt
        if m.get("status") == "won":
            total_won += amt
        if m.get("status") in ("won", "paid", "negotiation"):
            total_expected += amt
        rows.append({"url": url, "title": _title_for(url), "status": m.get("status"),
                     "payment": pay, "amount": amt})
    return {"won": round(total_won, 2), "paid": round(total_paid, 2),
            "expected": round(total_expected, 2), "rows": rows}


def _to_float(v) -> float:
    try:
        return float(str(v).replace(" ", "").replace(",", ".").replace("₽", ""))
    except (TypeError, ValueError):
        return 0.0


def _title_for(url: str) -> str:
    for j in store.load("jobs", {"items": []}).get("items", []):
        if j.get("url") == url:
            return (j.get("title") or "")[:80]
    for i in store.load("outbox", {"items": []}).get("items", []):
        if i.get("url") == url:
            return (i.get("title") or "")[:80]
    return url[:60]