"""Zarabotok v4 — дашборд SPA. JSON API + управление всем циклом, старые роуты v3 сохранены."""
import asyncio
import ctypes
import datetime
import html
import json
import os
import smtplib
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

from modules import billing, chat, crm, executor, proposals, ranker, reports, scanners, store, tg_auth  # noqa: E402

MIN_SCORE = 1
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state")
QR_PNG = os.path.join(STATE, "qr.png")
QR_STATUS = os.path.join(STATE, "qr_status.txt")

WORKERS = ("watchdog", "scanner", "orchestrator", "sender", "listener", "exec_worker", "dashboard")

PLATFORM_COLOR = {
    "FL": "sky", "freelance.ru": "green", "TG": "violet", "Habr": "amber",
    "WeWorkRemotely": "rose",
}


def esc(x, n=1000):
    return html.escape(str(x))[:n]


def proc_alive(pid) -> bool:
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    except Exception:
        return True


def worker_status() -> list:
    rows = []
    for w in WORKERS:
        path = os.path.join(STATE, "watchdog.pid" if w == "watchdog" else f"{w}.py.pid")
        alive = False
        try:
            alive = proc_alive(open(path).read().strip())
        except OSError:
            alive = False
        rows.append((w, alive))
    return rows


# ---------- health / funnel / отчёты ----------

def read_pid(name: str):
    path = os.path.join(STATE, "watchdog.pid" if name == "watchdog" else f"{name}.py.pid")
    try:
        with open(path, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def check_lmstudio(timeout: float = 3.0) -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        models = [m.get("id") for m in data.get("data", [])] or []
        return {"ok": True, "models": models[:5], "count": len(models)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def check_socks(port: int = 4067, timeout: float = 2.0) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def email_status() -> dict:
    settings = store.load("settings", {})
    email = settings.get("email", {}) or {}
    cfg = load_cfg()
    cemail = cfg.get("email", {}) or {}
    accounts = cfg.get("email_accounts", []) or []
    acc = accounts[0] if accounts else {}
    smtp = email.get("smtp_user") or cemail.get("smtp_user") or acc.get("smtp_user") or ""
    imap = email.get("imap_user") or cemail.get("imap_user") or acc.get("imap_user") or ""
    return {"smtp_user": smtp or "", "imap_user": imap or ""}


def api_health() -> dict:
    workers = [{"name": w, "alive": a, "pid": read_pid(w)} for w, a in worker_status()]
    storage = store.storage_info()
    lm = check_lmstudio()
    mail = email_status()
    socks = check_socks()
    ok = all(w["alive"] for w in workers) and bool(storage.get("ok")) and bool(lm.get("ok")) and socks
    return {
        "ts": store.now(),
        "status": "ok" if ok else "degraded",
        "workers": workers,
        "workers_alive": sum(1 for w in workers if w["alive"]),
        "workers_total": len(workers),
        "storage": storage,
        "lmstudio": lm,
        "email": mail,
        "socks": {"port": 4067, "open": socks},
    }


def _parse_ts(ts):
    if not ts:
        return None
    try:
        p = datetime.datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    if p.tzinfo is None:
        p = p.replace(tzinfo=datetime.timezone.utc)
    return p.astimezone(datetime.timezone.utc)


def _avg_hours(pairs):
    vals = []
    for a, b in pairs:
        pa, pb = _parse_ts(a), _parse_ts(b)
        if pa and pb and pb >= pa:
            vals.append((pb - pa).total_seconds() / 3600.0)
    return round(sum(vals) / len(vals), 1) if vals else None


def funnel_stats() -> dict:
    """Расширенная воронка: статусы CRM, конверсии, средние времена, сегодня/всё время."""
    today = store.now()[:10]
    box = store.load("outbox", {"items": []}).get("items", [])
    jobs = store.load("jobs", {"items": []}).get("items", [])
    meta_d = store.load("orders_meta", {"items": {}}).get("items", {})
    msgs = store.load("messages", {"items": []}).get("items", [])
    invs = store.load("invoices", {"items": []}).get("items", [])
    agents = store.load("agents_activity", {"items": []}).get("items", [])

    counts = {s: 0 for s in crm.STATUSES}
    for m in meta_d.values():
        counts[m.get("status", "new")] = counts.get(m.get("status", "new"), 0) + 1

    first_sent, first_reply = {}, {}
    for m in msgs:
        url, ts = m.get("order"), m.get("ts")
        if not url or not ts:
            continue
        if m.get("direction") == "out" and url not in first_sent:
            first_sent[url] = ts
        if m.get("direction") == "in" and url not in first_reply:
            first_reply[url] = ts
    for i in box:
        if i.get("sent") and i.get("sent_at") and i.get("url") not in first_sent:
            first_sent[i["url"]] = i["sent_at"]

    scanned = {j.get("url"): j.get("scanned_at") for j in jobs if j.get("scanned_at")}
    sent_total = sum(counts[s] for s in ("sent", "reply", "negotiation", "won", "paid"))
    replied_n = sum(counts[s] for s in ("reply", "negotiation", "won", "paid"))
    winned = counts["won"] + counts["paid"]
    conversions = {
        "sent_to_reply": round(replied_n * 100.0 / sent_total, 1) if sent_total else 0.0,
        "reply_to_won": round(winned * 100.0 / replied_n, 1) if replied_n else 0.0,
        "won_to_paid": round(counts["paid"] * 100.0 / winned, 1) if winned else 0.0,
    }
    avg = {
        "scan_to_first_sent": _avg_hours([(scanned.get(u), t) for u, t in first_sent.items() if u in scanned]),
        "scan_to_first_reply": _avg_hours([(scanned.get(u), t) for u, t in first_reply.items() if u in scanned]),
        "sent_to_first_reply": _avg_hours([(first_sent.get(u), t) for u, t in first_reply.items() if u in first_sent]),
    }

    income_paid = round(sum(crm._to_float(i.get("amount")) for i in invs if i.get("status") == "paid"), 2)
    on = lambda ts: (ts or "").startswith(today)
    income_paid_today = round(sum(crm._to_float(i.get("amount")) for i in invs
                                  if i.get("status") == "paid" and on(i.get("paid_at"))), 2)

    won_today, paid_today = set(), set()
    for a in agents:
        act = a.get("action") or ""
        url, ts = a.get("order"), a.get("ts")
        if not url or not on(ts):
            continue
        if act == "статус -> won":
            won_today.add(url)
        elif act == "статус -> paid":
            paid_today.add(url)
    for i in invs:
        if i.get("status") == "paid" and on(i.get("paid_at")):
            paid_today.add(i.get("url"))

    return {
        "ts": store.now(),
        "today": today,
        "statuses": counts,
        "conversions": conversions,
        "avg_hours": avg,
        "all_time": {
            "sent": sent_total,
            "replied": replied_n,
            "won": winned,
            "paid": counts["paid"],
            "income_paid": income_paid,
        },
        "today_counts": {
            "orders_found": sum(1 for j in jobs if on(j.get("scanned_at"))),
            "sent": len(set(u for u, t in first_sent.items() if on(t))),
            "replied": len(set(u for u, t in first_reply.items() if on(t))),
            "won": len(won_today),
            "paid": len(paid_today),
            "income_paid": income_paid_today,
        },
    }


def api_funnel() -> dict:
    return funnel_stats()


def reports_daily() -> str:
    today = store.now()[:10]
    fs = funnel_stats()
    events = store.load("events", {"items": []}).get("items", [])[-5:][::-1]
    if not events:
        events = store.load("activity", {"activity": []}).get("activity", [])[-5:][::-1]
    t = fs["today_counts"]
    lines = [
        f"Дневная сводка за {today}",
        f"Заказы найдено: {t['orders_found']}",
        f"Одобрено (в очереди): {sum(1 for i in store.load('outbox', {'items': []}).get('items', []) if i.get('approved') and not i.get('sent'))}",
        f"Отправлено: {t['sent']}",
        f"Ответы: {t['replied']}",
        f"Победы: {t['won']}",
        f"Оплаты: {t['paid']}",
        f"Доход (paid-инвойсы): {t['income_paid']} ₽",
        "",
        "Последние события:",
    ]
    for e in events:
        lines.append(f"  [{e.get('ts', '')}] [{e.get('severity') or ''} {e.get('source') or ''}] {e.get('text') or ''}")
    return "\n".join(lines)


def health_page() -> str:
    h = api_health()
    rows = "".join(
        f"<tr><td>{esc(w['name'])}</td><td class='{'ok' if w['alive'] else 'bad'}'>"
        f"{'жив' if w['alive'] else 'упал'}</td><td class='mono'>{w['pid'] or '—'}</td></tr>"
        for w in h["workers"]
    )
    lm = h["lmstudio"]
    lm_html = (f"ok · {lm.get('count', 0)} моделей: {esc(', '.join(lm.get('models') or []))}"
               if lm.get("ok") else f"нет связи ({esc(lm.get('error', ''), 80)})")
    st = h["storage"]
    st_html = (f"ok ({st.get('mode')})" if st.get("ok") else f"FAIL ({st.get('mode')}): {esc(st.get('error') or '', 80)}")
    mail = h["email"]
    mail_html = esc(mail.get("smtp_user") or "не настроена") + (f" · imap: {esc(mail.get('imap_user'))}" if mail.get("imap_user") else "")
    socks = h["socks"]
    cls = "ok" if h["status"] == "ok" else "bad"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Health — Zarabotok</title>
<style>body{{font-family:system-ui;background:#0a0e14;color:#e4ecf5;padding:30px;max-width:760px;margin:0 auto}}
h1{{font-size:20px}}h2{{font-size:14px;color:#8b98ad;text-transform:uppercase;letter-spacing:.4px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:8px 10px;border-bottom:1px solid #1e2836;text-align:left}}
.mono{{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#8b98ad}}
.ok{{color:#34d399}}.bad{{color:#fb7185}}
.card{{background:#111720;border:1px solid #1e2836;border-radius:12px;padding:16px;margin-bottom:16px}}
.status{{font-size:16px;font-weight:700}}a{{color:#38bdf8}}</style></head><body>
<div class="card"><h1>Health check</h1><div class="status {cls}">{'OK' if h['status'] == 'ok' else 'DEGRADED'}</div>
<div class="mono">{esc(h['ts'])}</div></div>
<div class="card"><h2>Воркеры ({h['workers_alive']}/{h['workers_total']})</h2>
<table><tr><th>воркер</th><th>состояние</th><th>pid</th></tr>{rows}</table></div>
<div class="card"><h2>Хранилище</h2><div>{st_html}</div></div>
<div class="card"><h2>LM Studio (127.0.0.1:1234)</h2><div>{lm_html}</div></div>
<div class="card"><h2>Почта</h2><div>{mail_html}</div></div>
<div class="card"><h2>Прокси SOCKS :{socks['port']}</h2><div class="{'ok' if socks['open'] else 'bad'}">{'открыт' if socks['open'] else 'закрыт'}</div></div>
<p><a href="/">← на дашборд</a> · <a href="/funnel">funnel JSON</a> · <a href="/reports/daily">дневной отчёт</a></p>
</body></html>"""


# ---------- данные ----------

def load_cfg():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg):
    with open(os.path.join(BASE, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def act(text):
    store.append("activity", {"ts": store.now(), "text": text}, key="activity")


def run_scan():
    jobs, errors = scanners.scan_all(include_tg=True)
    new = ranker.rank_and_store(jobs, min_score=MIN_SCORE)
    act(f"Ручной скан: всего {len(jobs)}, новых {len(new)}, ошибок {len(errors)}")


def edit_item(url, **kw):
    def _fn(box):
        for i in box.get("items", []):
            if i["url"] == url:
                i.update(kw)
                return True
        return False
    return store.mutate("outbox", _fn, {"items": []})


def find_job(url):
    for j in store.load("jobs", {"items": []}).get("items", []):
        if j["url"] == url:
            return j
    return None


def regen_item(url):
    job = find_job(url)
    if not job:
        return "заказ не найден"
    text = proposals.llm_draft(job, []) if proposals.llm_available() else proposals.template_draft(job)
    text = text or proposals.template_draft(job)
    reason = proposals.qa(text, job)
    edit_item(url, text=text, qa=reason or None)
    return f"перегенерировано{' (QA: ' + reason + ')' if reason else ''}"


def dismiss_item(url):
    jobs = store.load("jobs", {"items": []})
    for j in jobs["items"]:
        if j["url"] == url:
            j["ignored"] = True
    store.save("jobs", jobs)
    ignored = store.load("ignored", {"urls": []})
    if url not in ignored["urls"]:
        ignored["urls"].append(url)
    store.save("ignored", ignored)
    return True


def save_email(address, passwd, provider):
    cfg = dict(PROVIDERS[provider])
    cfg.update({"smtp_user": address, "smtp_pass": passwd, "imap_user": address, "imap_pass": passwd})
    with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15) as smtp:
        smtp.login(address, passwd)
    settings = store.load("settings", {})
    settings["email"] = cfg
    store.save("settings", settings)


# ---------- UI-хелперы ----------

def pl(s):
    s = str(s or "")
    key = s if s in PLATFORM_COLOR else (s.split(":")[0] if ":" in s else "FL")
    clo = PLATFORM_COLOR.get(key, "slate")
    return f"<span class='badge b-{clo}'>{esc(s, 18)}</span>"


def score_badge(v):
    v = int(v or 0)
    cls = "s-good" if v >= 6 else ("s-mid" if v >= 3 else "s-low")
    return f"<span class='score {cls}'>{v}</span>"


def status_pill(j, item):
    if not item:
        return "<span class='pill p-new'>новый</span>"
    if item.get("sent"):
        return "<span class='pill p-sent'>отправлен</span>"
    if item.get("approved"):
        return "<span class='pill p-ok'>одобрен</span>"
    return "<span class='pill p-draft'>черновик</span>"


def ch_pill(item):
    ch = (item.get("channel") or "manual").lower()
    if ch == "tg":
        return "<span class='pill p-tg'>TG</span>"
    if ch == "email":
        return "<span class='pill p-mail'>email</span>"
    return "<span class='pill p-manual'>нет контакта</span>"


def qr_file_ts():
    try:
        return os.path.getmtime(QR_PNG)
    except OSError:
        return 0.0


def qr_start():
    if qr_file_ts() > os.path.getmtime(__file__):
        return
    if os.path.exists(QR_STATUS):
        os.remove(QR_STATUS)
    script = os.path.join(BASE, "tools", "qr_cli.py")
    subprocess.Popen(
        [sys.executable, script, "telegram_session_sender"],
        cwd=BASE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def qr_status():
    try:
        return open(QR_STATUS, encoding="utf-8").read().strip()
    except OSError:
        return ""


def collect():
    settings = store.load("settings", {})
    show_vac = bool(settings.get("show_vacancies"))
    cfg = load_cfg()
    email = settings.get("email", {}) or {}
    box = store.load("outbox", {"items": []})
    items = box.get("items", [])
    jobs = store.load("jobs", {"items": []}).get("items", [])
    orders = [j for j in jobs if j.get("score", 0) >= MIN_SCORE and not j.get("ignored") and scanners.kind_of(j) == "order"]
    vacancies = [j for j in jobs if j.get("score", 0) >= MIN_SCORE and not j.get("ignored") and scanners.kind_of(j) == "vacancy"]
    view = (orders + vacancies) if show_vac else orders
    view.sort(key=lambda j: (j.get("score", 0) or 0, j.get("budget") or ""), reverse=True)
    today = store.now()[:10]
    st = {
        "jobs": len(jobs),
        "fresh": sum(1 for j in jobs if j.get("scanned_at", "").startswith(today)),
        "orders": len(orders),
        "drafts": len(items),
        "approved": sum(1 for i in items if i.get("approved") and not i.get("sent")),
        "sent": sum(1 for i in items if i.get("sent")),
        "contacts": sum(1 for i in items if (i.get("contact") or i.get("to"))),
    }
    return {
        "settings": settings, "cfg": cfg, "email": email, "items": items, "jobs": jobs,
        "orders": orders, "vacancies": vacancies, "view": view, "show_vac": show_vac,
        "st": st, "auto_send": bool(cfg.get("sender", {}).get("auto_send", False)),
        "by_url": {i["url"]: i for i in items},
    }


# ---------- отрисовка ----------

CSS = """
:root{--bg:#0a0e14;--panel:#111720;--panel2:#0d1219;--br:#1e2836;--txt:#e4ecf5;--mut:#8b98ad;
--sky:#38bdf8;--green:#34d399;--amber:#fbbf24;--rose:#fb7185;--violet:#c084fc;--slate:#94a3b8}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--sky);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:0;z-index:10;background:rgba(10,14,20,.92);backdrop-filter:blur(8px);
border-bottom:1px solid var(--br);padding:10px 22px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font-size:17px;font-weight:700;letter-spacing:.2px}.brand span{color:var(--sky)}
.brand small{color:var(--mut);font-weight:400;font-size:12px;margin-left:6px}
.top .sp{flex:1}
.wrap{max-width:1200px;margin:0 auto;padding:18px 22px 60px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.stat{background:var(--panel);border:1px solid var(--br);border-radius:12px;padding:14px 16px}
.stat b{font-size:26px;font-weight:700;display:block}
.stat small{color:var(--mut)}.stat i{font-style:normal;font-size:17px;margin-right:6px}
.s-num{color:var(--sky)}.s-fresh{color:var(--green)}.s-draft{color:var(--amber)}
.s-appr{color:var(--green)}.s-sent{color:var(--violet)}.s-cont{color:var(--rose)}
nav{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 20px}
nav a{color:var(--mut);padding:6px 12px;border-radius:8px;border:1px solid transparent;font-size:13px}
nav a:hover{color:var(--txt);text-decoration:none;background:var(--panel2)}
nav a.on{color:var(--sky);border-color:var(--br);background:var(--panel)}
.card{background:var(--panel);border:1px solid var(--br);border-radius:12px;padding:16px 18px;margin-bottom:18px}
.h{font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.h .n{color:var(--mut);font-weight:400;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--mut);text-align:left;font-weight:600;padding:8px 10px;border-bottom:1px solid var(--br);font-size:12px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid #16202e;vertical-align:top}
tr:hover td{background:var(--panel2)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}
.b-sky{background:#0c3b52;color:#7dd3fc}.b-green{background:#0b3b2e;color:#6ee7b7}
.b-violet{background:#331b52;color:#d8b4fe}.b-amber{background:#3d2e0b;color:#fcd34d}
.b-rose{background:#46182a;color:#fda4af}.b-slate{background:#1e2735;color:#cbd5e1}
.score{display:inline-block;min-width:26px;text-align:center;font-weight:700;padding:2px 6px;border-radius:6px;font-size:12px}
.s-good{background:#0b3b2e;color:#6ee7b7}.s-mid{background:#3d2e0b;color:#fcd34d}.s-low{background:#1e2735;color:#94a3b8}
.pill{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;white-space:nowrap}
.p-new{background:#173042;color:#7dd3fc}.p-draft{background:#3d2e0b;color:#fcd34d}
.p-ok{background:#0b3b2e;color:#6ee7b7}.p-sent{background:#331b52;color:#d8b4fe}
.p-tg{background:#0b3b2e;color:#6ee7b7}.p-mail{background:#173042;color:#7dd3fc}.p-manual{background:#1e2735;color:#94a3b8}
.desc{color:var(--mut);font-size:12px;margin-top:3px;max-width:520px}
textarea,input,select{background:var(--panel2);color:var(--txt);border:1px solid var(--br);border-radius:8px;padding:8px 10px;font:inherit;outline:none}
textarea:focus,input:focus,select:focus{border-color:var(--sky)}
textarea{width:100%;resize:vertical;min-height:64px}
button{background:#1a2434;color:var(--txt);border:1px solid var(--br);border-radius:8px;padding:7px 14px;cursor:pointer;font:inherit;font-size:13px;transition:.15s}
button:hover{background:#243348;border-color:#2f4157}
button.act{background:#0c3b52;border-color:#0f4a66;color:#7dd3fc}
button.danger{background:#46182a;border-color:#5c2038;color:#fda4af}
button:disabled{opacity:.35;cursor:not-allowed}
.btnrow{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.setrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px}
.setcard{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.thread{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #16202e}
.thread .av{width:34px;height:34px;border-radius:50%;background:#1a2434;color:var(--sky);display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
.thread .tx b{font-size:13px}.thread .tx small{color:var(--mut);font-size:11px;display:block;margin-bottom:2px}
.thread .tx p{color:#cdd9e8;font-size:13px;margin-top:2px}
.activity{list-style:none;max-height:340px;overflow:auto}
.activity li{display:flex;gap:10px;padding:5px 0;font-size:13px;border-bottom:1px dotted #131c29}
.activity time{color:var(--mut);font-size:11px;white-space:nowrap;padding-top:2px}
.wk{display:inline-flex;align-items:center;gap:6px;background:var(--panel2);border:1px solid var(--br);border-radius:999px;padding:3px 10px;font-size:12px;margin:0 4px 6px 0}
.dot{width:8px;height:8px;border-radius:50%;background:#f87171}
.dot.up{background:#34d399}
.foot{color:var(--mut);font-size:12px;text-align:center;margin-top:30px}
.ok{color:var(--green)}.warn{color:var(--amber)}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--mut)}
"""


def render() -> str:
    d = collect()
    st, cfg = d["st"], d["cfg"]
    auto_send = d["auto_send"]
    email = d["email"]
    show_vac = d["show_vac"]
    settings = d["settings"]
    wks = "".join(
        f"<span class='wk'><span class='dot {'up' if a else ''}'></span>{esc(w)}</span>" for w, a in worker_status()
    )

    rows = "".join(
        f"<tr><td>{pl(j.get('source') or j.get('platform'))}</td>"
        f"<td><a href='{esc(j.get('url'), 220)}'>{esc(j.get('title'), 120)}</a>"
        f"{'<div class=desc>' + esc(j.get('description'), 260) + '</div>' if j.get('description') else ''}"
        f"{'<div class=desc>🗕 ' + esc(j.get('budget')) + (' · заказчик: ' + esc(j.get('author'), 40) if j.get('author') else '') + '</div>' if j.get('budget') or j.get('author') else ''}</td>"
        f"<td nowrap>{esc(j.get('budget')) or '—'}</td>"
        f"<td>{esc(j.get('author')) or '—'}</td>"
        f"<td>{score_badge(j.get('score'))}</td>"
        f"<td>{status_pill(j, d['by_url'].get(j['url']))}</td></tr>"
        for j in d["view"]
    )

    drafts = []
    for i in d["items"]:
        drafts.append(f"""<div class="card" style="margin-bottom:12px">
<div class="h"><a href="{esc(i.get('url'), 220)}">{esc(i.get('title'), 100)}</a>
<span class="n">{esc(i.get('budget')) or ''}</span>{ch_pill(i)}{status_pill({'url': i.get('url')}, i)}
<span class="sp" style="flex:1"></span><span class="mono">{esc(i.get('created_at'), 19)}</span></div>
<form method="post" action="/edit">
<input type="hidden" name="url" value="{esc(i['url'], 220)}">
<textarea name="text" rows="3">{esc(i.get('text'), 3000)}</textarea>
<div class="btnrow">
<button>💾 Сохранить</button>
<button type="button" onclick="navigator.clipboard.writeText(this.dataset.t)" data-t="{esc(i.get('text'), 3000)}">📋 Копировать</button>
</div></form>
<div class="btnrow">
<form method="post" action="/approve"><input type="hidden" name="url" value="{esc(i['url'], 220)}">
<button class="act" {'disabled' if i.get('approved') or i.get('sent') else ''}>{'✅' if i.get('approved') else ''} Одобрить → отправить</button></form>
<form method="post" action="/regen"><input type="hidden" name="url" value="{esc(i['url'], 220)}"><button>🔄 Перегенерировать</button></form>
<form method="post" action="/dismiss"><input type="hidden" name="url" value="{esc(i['url'], 220)}"><button class="danger">✕ Скрыть</button></form>
</div>
<div class="mono" style="margin-top:6px">QA: <span class="{'ok' if not i.get('qa') else 'warn'}">{esc(i.get('qa') or 'ок')}</span>
 · канал: {esc(i.get('channel'))} · контакт: {esc(i.get('contact') or i.get('to') or '—')} · score: {esc(i.get('score'))}</div>
</div>""")

    contracts = store.load("contracts", {"contracts": []}).get("contracts", [])
    c_rows = "".join(
        f"<tr><td class='mono'><a href='{esc(c.get('job_id'))}'>{esc(c.get('job_id'), 60)}</a></td>"
        f"<td>{esc(c.get('agent'))}</td><td>{esc(c.get('status'))}</td>"
        f"<td>{esc(c.get('usage', {}).get('turns'))}</td></tr>"
        for c in contracts[-20:]
    )

    archive = store.load("archive_jobs", {"items": []}).get("items", [])[-60:]
    ar_rows = "".join(
        f"<tr><td>{pl(a2.get('platform'))}</td><td><a href='{esc(a2.get('url'), 220)}'>{esc(a2.get('title'), 110)}</a></td></tr>"
        for a2 in archive
    )

    threads_all = store.load("threads", {"threads": []}).get("threads", [])[-40:][::-1]
    th = "".join(
        f"""<div class="thread"><div class="av">{esc((t.get('from') or '?')[0].upper(), 1)}</div>
<div class="tx"><small>{esc(t.get('ts'))}</small><b>{esc(t.get('from'), 40)}</b>
{('<span class=mono> [' + esc(str(t.get('kind') or t.get('actor')), 24) + ']</span>') if t.get('kind') or t.get('actor') else ''}
<p>{esc(t.get('text'), 700)}</p></div></div>"""
        for t in threads_all
    )

    activity = store.load("activity", {"activity": []}).get("activity", [])[-40:][::-1]
    act_li = "".join(
        f"<li><time>{esc(a.get('ts'), 19)}</time><span>{esc(a.get('text'), 250)}</span></li>" for a in activity
    )

    tg_state = settings.get("tg_poll")
    email_on = bool(email.get("smtp_user"))

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zarabotok v3 — конвейер заказов</title><style>{CSS}</style></head><body>
<div class="top">
<span class="brand">⚡ Zarabotok <span>v3</span><small>фриланс-конвейер</small></span>
<span class="sp"></span>
<button onclick="location.reload()">↻ Обновить</button>
<form method="post" action="/scan" style="margin:0"><button class="act">⟳ Сканировать</button></form>
</div>
<div class="wrap">

<div class="stats">
<div class="stat"><i>🗂</i><b class="s-num">{st['jobs']}</b><small>заказов в базе</small></div>
<div class="stat"><i>✨</i><b class="s-fresh">{st['fresh']}</b><small>новых сегодня</small></div>
<div class="stat"><i>📝</i><b class="s-draft">{st['drafts']}</b><small>черновиков</small></div>
<div class="stat"><i>✅</i><b class="s-appr">{st['approved']}</b><small>ждёт отправки</small></div>
<div class="stat"><i>📨</i><b class="s-sent">{st['sent']}</b><small>отправлено</small></div>
<div class="stat"><i>📇</i><b class="s-cont">{st['contacts']}</b><small>с контактом</small></div>
</div>

<div class="card"><div class="h">🖥 Воркеры</div>{wks}</div>

<nav>
<a href="#orders" class="on">Заказы ({len(d['orders'])})</a>
<a href="#drafts">Черновики ({len(d['items'])})</a>
<a href="#contracts">Контракты ({len(contracts)})</a>
<a href="#archive">Архив ({len(archive)})</a>
<a href="#threads">Переписка ({len(threads_all)})</a>
<a href="#activity">Активность</a>
<a href="#settings">Настройки</a>
</nav>

<div class="card" id="orders">
<div class="h">Заказы по нашим скиллам <span class="n">показано: {len(d['view'])} из {st['jobs']}</span>
<span class="sp" style="flex:1"></span>
<form method="post" action="/toggle_kind" style="margin:0"><button>{'Скрыть вакансии' if show_vac else f'Показать вакансии ({len(d["vacancies"])})'}</button></form>
</div>
<table><tr><th>источник</th><th>заказ</th><th>цена</th><th>заказчик</th><th>score</th><th>статус</th></tr>{rows or '<tr><td colspan=6 style="color:var(--mut)">нет заказов — нажми «Сканировать»</td></tr>'}</table>
</div>

<div class="card" id="drafts">
<div class="h">Черновики ответов <span class="n">одобряй — уйдёт заказчику</span></div>
{drafts or '<div style="color:var(--mut)">черновиков пока нет</div>'}
</div>

<div class="grid2">
<div class="card" id="contracts">
<div class="h">Контракты / агенты <span class="n">{len(contracts)}</span></div>
<table><tr><th>заказ</th><th>агент</th><th>статус</th><th>ходов</th></tr>{c_rows or '<tr><td colspan=4 style="color:var(--mut)">пусто</td></tr>'}</table>
</div>
<div class="card" id="archive">
<div class="h">Архив заказов <span class="n">старая база v2</span></div>
<table><tr><th>платформа</th><th>название</th></tr>{ar_rows or '<tr><td colspan=2 style="color:var(--mut)">пусто</td></tr>'}</table>
</div>
</div>

<div class="grid2">
<div class="card" id="threads">
<div class="h">Переписка <span class="n">{len(threads_all)}</span></div>
{th or '<div style="color:var(--mut)">пока пусто — слушатель подхватит входящие</div>'}
</div>
<div class="card" id="activity">
<div class="h">Активность</div>
<ul class="activity">{act_li or '<li style="color:var(--mut)">пока пусто</li>'}</ul>
</div>
</div>

<div class="card" id="settings">
<div class="h">Настройки</div>
<div class="setcard">
<div class="setcard">
<div class="card" style="margin:0">
<b>Telegram</b> <span class="{'ok' if tg_state else 'warn'}">{'авторизован ✓' if tg_state else 'нет авторизации'}</span><br>
<div class="setrow">
<form method="post" action="/tg_phone"><input name="phone" placeholder="+79344444734"><button>Код по SMS</button></form>
<form method="post" action="/tg_code"><input name="code" placeholder="код из SMS"><button>Ввести код</button></form>
<a href="/tg_qr"><button class="act">📱 QR-вход</button></a>
</div></div>
<div class="card" style="margin:0">
<b>Почта</b> <span class="{'ok' if email_on else 'warn'}">{esc(email.get('smtp_user', ''), 50) or 'не подключена'}</span><br>
<form method="post" action="/save_email">
<div class="setrow"><input name="address" placeholder="user@gmail.com" value="{esc(email.get('smtp_user', ''), 50)}" style="min-width:210px">
<input name="pass" placeholder="пароль приложения" style="min-width:200px">
<select name="provider"><option value="yandex">Yandex</option><option value="mailru">Mail.ru</option><option value="gmail" {'selected' if (email.get('smtp_host') or '').find('gmail') >= 0 else ''}>Gmail</option></select>
<button>Сохранить и проверить</button></div>
</form></div>
<div class="card" style="margin:0">
<b>Автоотправка</b> <span class="{'ok' if auto_send else 'warn'}">{'ВКЛ — одобренные уходят сами' if auto_send else 'ВЫКЛ'}</span><br>
<div class="setrow">
<form method="post" action="/auto_send"><button>{'⏸ Выключить' if auto_send else '▶ Включить'}</button></form>
<small class="mono" style="margin-left:8px">score ≥ {cfg.get('sender', {}).get('auto_min_score', 3)} · лимит {cfg.get('sender', {}).get('auto_limit', 10)}/цикл · автоодобрение {'ВКЛ' if cfg.get('sender', {}).get('auto_approve') else 'ВЫКЛ'}</small>
</div></div>
</div>
</div>

<div class="foot">Zarabotok v3 · 127.0.0.1:8765 · watchdog держит воркеры живыми</div>
</div></body></html>"""


def qr_page() -> str:
    status = qr_status()
    has_png = qr_file_ts() > 0
    scanning = has_png and (status == "" or status.startswith("Жду"))
    auto = '<meta http-equiv="refresh" content="4">' if scanning else ""
    img = ("<img src='/tg_qr.png?v=%d' style='width:260px;background:#fff;padding:8px;border-radius:12px'>"
           % int(qr_file_ts()) if has_png else "")
    hint = ("<p>1) Открой Телеграм на телефоне → Настройки → Устройства → «Сканировать QR-код»<br>"
            "2) Отсканируй код камерой телефона<br>3) Нажми «Войти» — страница обновится сама</p>" if scanning else "")
    btn = "<form method='post' action='/tg_qr'><button>Сгенерировать QR для входа</button></form>" if not scanning else ""
    color = "#4ade80" if status.startswith("ok") else "#e6e6e6"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">{auto}<title>QR-вход Telegram</title>
<style>body{{font-family:system-ui;background:#0a0e14;color:#e6e6e6;text-align:center;padding:40px}}
h2{{margin-bottom:8px}}p{{color:#8b98ad;font-size:14px;line-height:1.7}}
button{{background:#1a2434;color:#e4ecf5;border:1px solid #2f4157;border-radius:8px;padding:9px 18px;cursor:pointer;font-size:14px}}
a{{color:#38bdf8}}</style></head>
<body><h2>Вход в Telegram по QR</h2>
<div style="color:{color};margin:10px 0">{status or ('Генерирую QR… обновите через пару секунд' if not has_png else 'Жду сканирования')}</div>
{img}<br>{hint}<br>{btn}
<p><a href="/">← назад на дашборд</a></p></body></html>"""


# ---------- API v4 (JSON) ----------

def _j(obj, code=200):
    body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    return code, "application/json; charset=utf-8", body


def api_overview():
    d = collect()
    return {
        "st": d["st"],
        "workers": [{"name": w, "alive": a} for w, a in worker_status()],
        "unread_total": _with_timeout(lambda: sum(chat.unread_counts().values()), 0, 6),
        "funnel": _with_timeout(crm.funnel, {"new": 0}, 6),
        "today": store.now()[:10],
    }


def api_orders():
    d = collect()
    unread = _with_timeout(chat.unread_counts, {}, 6)
    meta_d = store.load("orders_meta", {"items": {}}).get("items", {})
    rows = []
    for j in d["view"]:
        url = j["url"]
        it = d["by_url"].get(url)
        m = meta_d.get(url, {}) or {}
        pay = m.get("payment", {}) or {}
        rows.append({
            "url": url,
            "title": j.get("title"),
            "description": j.get("description"),
            "budget": j.get("budget"),
            "author": j.get("author"),
            "score": j.get("score"),
            "source": j.get("source") or j.get("platform"),
            "platform": j.get("platform"),
            "scanned_at": j.get("scanned_at"),
            "kind": scanners.kind_of(j),
            "draft_status": ("sent" if it and it.get("sent")
                             else "approved" if it and it.get("approved")
                             else "draft" if it else "new"),
            "contact": (it or {}).get("contact") or (it or {}).get("to"),
            "channel": (it or {}).get("channel"),
            "text": (it or {}).get("text"),
            "qa": (it or {}).get("qa"),
            "crm_status": m.get("status", "new"),
            "pay_status": pay.get("status"),
            "amount": pay.get("amount"),
            "unread": unread.get(url, 0),
        })
    return {"rows": rows, "st": d["st"], "unread_total": sum(unread.values())}


def api_order(url):
    job = find_job(url)
    item = next((i for i in store.load("outbox", {"items": []}).get("items", [])
                 if i["url"] == url), None)
    return {
        "job": job,
        "draft": item,
        "crm": crm.meta(url),
        "invoice": billing.invoice_for(url),
        "thread": chat.thread(url),
        "files": crm.list_files(url),
        "agents": crm.agents_for(url),
        "exec": executor.exec_report(url),
    }


def api_chat(url):
    job = find_job(url) or {}
    item = next((i for i in store.load("outbox", {"items": []}).get("items", [])
                 if i["url"] == url), None)
    peer = (item or {}).get("contact") or (item or {}).get("to") or ""
    return {"url": url, "title": job.get("title"), "peer": peer, "thread": chat.thread(url)}


def api_finance():
    return {"payments": crm.payments(), "funnel": crm.funnel()}


def api_invoices():
    import modules.billing as b
    items = b._load()
    return {"items": list(reversed(items))}


def api_agents():
    return {"items": store.load("agents_activity", {"items": []}).get("items", [])[-300:][::-1]}


def api_exec():
    return {"tasks": executor.tasks()}


def api_settings():
    settings = store.load("settings", {})
    cfg = load_cfg()
    email = settings.get("email", {}) or {}
    snd = cfg.get("sender", {}) or {}
    return {
        "tg_poll": bool(settings.get("tg_poll")),
        "show_vacancies": bool(settings.get("show_vacancies")),
        "auto_reply": bool(settings.get("auto_reply")),
        "email": {"smtp_user": email.get("smtp_user", "")},
        "auto_send": bool(snd.get("auto_send")),
        "auto_approve": bool(snd.get("auto_approve")),
        "auto_min_score": snd.get("auto_min_score", 3),
        "auto_limit": snd.get("auto_limit", 10),
        "fl_auto_bid": bool(snd.get("fl_auto_bid", True)),
        "fl_min_score": snd.get("fl_min_score", 2),
        "fl_max_per_cycle": snd.get("fl_max_per_cycle", 3),
        "max_per_hour": snd.get("max_per_hour", 0),
        "send_delay_sec": snd.get("send_delay_sec", 5),
        "workers": [{"name": w, "alive": a} for w, a in worker_status()],
        "exec_queued": sum(1 for t in executor.tasks() if t.get("status") == "queued"),
    }


def api_reply(url, text, channel):
    settings = store.load("settings", {})
    email = settings.get("email", {}) or {}
    sender = {"tg": "@me", "email": email.get("smtp_user", "")}.get(channel, channel or "")
    chat.add(url, "out", channel or "email", sender or "@me", text, sent=False)
    chat.mark_read(url)
    return {"ok": True}


# ---- мгновенный дашборд: фоновый пересчёт снапшотов ----
_SNAP = {}
_SNAP_T = {}
_SNAP_TTL = 5


def _snapshot(path):
    if path == "/api/overview":
        return api_overview()
    if path == "/api/orders":
        return api_orders()
    return None


def _refresh_loop():
    while True:
        for p in ("/api/overview", "/api/orders"):
            try:
                _SNAP[p] = _snapshot(p)
                _SNAP_T[p] = time.time()
            except Exception:
                pass
        time.sleep(_SNAP_TTL)


def _cached(path):
    now = time.time()
    if path in _SNAP and (now - _SNAP_T.get(path, 0)) < (_SNAP_TTL + 3):
        return _SNAP[path]
    r = _snapshot(path)
    if r is not None:
        _SNAP[path] = r
        _SNAP_T[path] = now
    return r


def _with_timeout(fn, default, seconds=8):
    """Выполнить fn в потоке; если висит дольше seconds — вернуть default."""
    box = {}

    def _run():
        try:
            box["r"] = fn()
        except Exception:
            box["r"] = default

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(seconds)
    return box.get("r", default)


def _activity_days(days: int = 30) -> dict:
    """Заказы по дням для графика активности (из jobs.scanned_at)."""
    from collections import Counter
    items = store.load("jobs", {"items": []}).get("items", [])
    c = Counter(str(j.get("scanned_at", ""))[:10] for j in items if j.get("scanned_at"))
    out = []
    now = time.time()
    for i in range(days - 1, -1, -1):
        lt = time.localtime(now - i * 86400)
        d = time.strftime("%Y-%m-%d", lt)
        out.append({"day": d, "label": time.strftime("%d.%m", lt),
                    "found": int(c.get(d, 0))})
    return {"items": out}


def api_get(path):
    if path == "/api/activity_days":
        return _j(_activity_days(30))
    if path == "/api/overview":
        return _j(_cached("/api/overview"))
    if path == "/api/orders":
        return _j(_cached("/api/orders"))
    if path.startswith("/api/order/"):
        return _j(api_order(path[len("/api/order/"):]))
    if path.startswith("/api/chat/"):
        return _j(api_chat(path[len("/api/chat/"):]))
    if path == "/api/finance":
        return _j(api_finance())
    if path == "/api/invoices":
        return _j(api_invoices())
    if path == "/api/agents":
        return _j(api_agents())
    if path == "/api/exec":
        return _j(api_exec())
    if path == "/api/settings":
        return _j(api_settings())
    return _j({"error": "not found"}, 404)


def api_post(path, raw):
    if path == "/api/system/stop":
        open(os.path.join(store.STATE, "KILL_SWITCH"), "w").close()
        store.append("activity", {"ts": store.now(), "text": "KILL SWITCH: оператор остановил все отправки"}, key="activity")
        return _j({"ok": True})
    if path == "/api/system/resume":
        _kp = os.path.join(store.STATE, "KILL_SWITCH")
        if os.path.exists(_kp):
            os.remove(_kp)
            store.append("activity", {"ts": store.now(), "text": "KILL SWITCH снят — работа возобновлена"}, key="activity")
        return _j({"ok": True})
    try:
        params = json.loads(raw) if raw else {}
    except ValueError:
        params = {}
    if not isinstance(params, dict):
        params = {}
    if path == "/api/scan":
        run_scan()
        return _j({"ok": True, "msg": "сканирование запущено"})
    if path.startswith("/api/chat/") and path.endswith("/reply"):
        url = path[len("/api/chat/"):-len("/reply")]
        api_reply(url, params.get("text", ""), params.get("channel", ""))
        return _j({"ok": True, "msg": "ответ добавлен"})
    if path.startswith("/api/chat/") and path.endswith("/read"):
        chat.mark_read(path[len("/api/chat/"):-len("/read")])
        return _j({"ok": True})
    if path.startswith("/api/order/") and path.endswith("/status"):
        url = path[len("/api/order/"):-len("/status")]
        m = crm.set_status(url, params.get("status", "new"))
        if m.get("status") == "won":
            if not executor.task_for(url):
                job = find_job(url) or {}
                tz = params.get("tz") or (job.get("description") or job.get("title") or "")
                executor.create_exec_task(url, tz=tz, title=job.get("title", ""), source="auto:status=won")
            if not billing.invoice_for(url):
                billing.make_invoice(url, amount=params.get("amount"))
        return _j({"ok": True, "meta": m})
    if path.startswith("/api/order/") and path.endswith("/execute"):
        url = path[len("/api/order/"):-len("/execute")]
        job = find_job(url) or {}
        tz = params.get("tz") or (job.get("description") or job.get("title") or "")
        t = executor.create_exec_task(url, tz=tz, title=job.get("title", ""),
                                      source=params.get("source") or "manual")
        return _j({"ok": True, "task": t, "msg": "передано агентам: " + ", ".join(a["file"] for a in t.get("agents", []))})
    if path.startswith("/api/order/") and path.endswith("/deliver"):
        url = path[len("/api/order/"):-len("/deliver")]
        ok = executor.deliver_result(url)
        return _j({"ok": ok, "msg": "результат отправлен клиенту" if ok else "не отправлен: задача не в статусе review или нет канала"})
    if path.startswith("/api/order/") and path.endswith("/meta"):
        url = path[len("/api/order/"):-len("/meta")]
        kw = {}
        if params.get("notes") is not None:
            kw["notes"] = params["notes"]
        if params.get("payment"):
            kw["payment"] = params["payment"]
        m = crm.update(url, **kw) if kw else crm.meta(url)
        return _j({"ok": True, "meta": m})
    if path.startswith("/api/order/") and path.endswith("/invoice"):
        url = path[len("/api/order/"):-len("/invoice")]
        inv = billing.make_invoice(url, amount=params.get("amount"),
                                   method=params.get("method", "yoomoney"))
        if inv.get("error"):
            return _j({"ok": False, "error": inv["error"]}, 400)
        if params.get("send"):
            billing.send_to_client(inv, url)
        return _j({"ok": True, "invoice": inv, "msg": f"счёт {inv.get('no')} создан"})
    if path.startswith("/api/order/") and path.endswith("/invoice/send"):
        url = path[len("/api/order/"):-len("/invoice/send")]
        inv = billing.invoice_for(url) or billing.make_invoice(url)
        ok = billing.send_to_client(inv, url) if not inv.get("error") else False
        return _j({"ok": ok, "msg": "счёт отправлен" if ok else "не отправлен — нет контакта/канала"})
    if path == "/api/invoice/paid":
        no = params.get("no", "")
        inv = billing.mark_paid(no)
        return _j({"ok": not bool(inv.get("error")), "invoice": inv, "msg": inv.get("error") or f"счёт {no} оплачен"})
    if path.startswith("/api/order/") and path.endswith("/approve"):
        url = path[len("/api/order/"):-len("/approve")]
        edit_item(url, approved=True)
        # G3: Approve & send — если есть контакт/канал, сразу пытаемся отправить
        try:
            from modules import sender as _sender2  # noqa: E402
            sent = _sender2.approve_and_send(url)
            if sent:
                return _j({"ok": True, "msg": "одобрено и отправлено клиенту"})
        except Exception:
            pass
        return _j({"ok": True, "msg": "одобрено (отправка — следующий цикл sender или вручную)"})
    if path.startswith("/api/order/") and path.endswith("/regen"):
        return _j({"ok": True, "msg": regen_item(path[len("/api/order/"):-len("/regen")])})
    if path.startswith("/api/order/") and path.endswith("/dismiss"):
        dismiss_item(path[len("/api/order/"):-len("/dismiss")])
        return _j({"ok": True, "msg": "скрыто"})
    if path.startswith("/api/order/") and path.endswith("/edit"):
        edit_item(path[len("/api/order/"):-len("/edit")], text=params.get("text", ""), qa=None)
        return _j({"ok": True, "msg": "сохранено"})
    if path.startswith("/api/order/") and path.endswith("/read"):
        chat.mark_read(path[len("/api/order/"):-len("/read")])
        return _j({"ok": True})
    if path == "/api/settings":
        settings = store.load("settings", {})
        if "show_vacancies" in params:
            settings["show_vacancies"] = bool(params["show_vacancies"])
            store.save("settings", settings)
        if "auto_reply" in params:
            settings["auto_reply"] = bool(params["auto_reply"])
            store.save("settings", settings)
        cfg = load_cfg()
        snd = cfg.setdefault("sender", {})
        for k in ("auto_send", "auto_approve"):
            if k in params:
                snd[k] = bool(params[k])
        for k in ("auto_min_score", "auto_limit"):
            if k in params and str(params[k]).isdigit():
                snd[k] = int(params[k])
        if "fl_auto_bid" in params:
            snd["fl_auto_bid"] = bool(params["fl_auto_bid"])
        for k in ("fl_min_score", "fl_max_per_cycle", "max_per_hour"):
            if k in params and str(params[k]).isdigit():
                snd[k] = int(params[k])
        if "send_delay_sec" in params:
            try:
                snd["send_delay_sec"] = float(params["send_delay_sec"])
            except (TypeError, ValueError):
                pass
        save_cfg(cfg)
        return _j({"ok": True, "msg": "сохранено"})
    return _j({"error": "not found"}, 404)


# ---------- SPA v4 ----------

SPA = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zarabotok — панель управления</title>
<style>
:root{
  --background:#ffffff;--foreground:#09090b;
  --card:#ffffff;--primary:#18181b;--primary-fg:#fafafa;
  --secondary:#f4f4f5;--muted:#f4f4f5;--muted-fg:#71717a;
  --accent:#f4f4f5;--border:#e4e4e7;--input:#e4e4e7;--ring:#a1a1aa;
  --sidebar:#fafafa;--sidebar-border:#e4e4e7;
  --ok:#16a34a;--warn:#d97706;--bad:#dc2626;--blue:#2563eb;
  --violet:#7c3aed;--cyan:#0891b2;--orange:#ea580c;
  --radius:10px;--chart2:#71717a;
}
*{box-sizing:border-box;margin:0;padding:0}
html{color-scheme:light}
body{background:var(--background);color:var(--foreground);font:14px/1.5 Inter,"Segoe UI",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{cursor:pointer;font:inherit;color:inherit;background:none;border:none}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#d4d4d8;border-radius:8px;border:2px solid #fff}
.wrap{display:flex;min-height:100vh}
.sb{width:272px;min-width:272px;background:var(--sidebar);border-right:1px solid var(--sidebar-border);position:sticky;top:0;height:100vh;display:flex;flex-direction:column;padding:8px}
.sb-head{display:flex;align-items:center;gap:10px;padding:10px 10px 12px;font-weight:600;font-size:15px}
.sb-head i{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#2563eb,#7c3aed);display:inline-flex;align-items:center;justify-content:center;font-style:normal;color:#fff;font-size:13px}
.sb-label{height:32px;display:flex;align-items:center;padding:0 10px;font-size:12px;font-weight:500;color:var(--muted-fg)}
.mi{display:flex;align-items:center;gap:10px;width:100%;height:32px;padding:0 8px;border-radius:8px;color:var(--muted-fg);font-size:13.5px;text-align:left;margin-bottom:1px}
.mi:hover{background:hsl(240 4.8% 92%);color:var(--foreground)}
.mi.on{background:hsl(240 4.8% 91%);color:var(--foreground);font-weight:500}
.mi .ic{width:18px;text-align:center}
.sb-foot{margin-top:auto;padding:10px 8px;font-size:11.5px;color:var(--muted-fg)}
.wrow{display:flex;align-items:center;gap:8px;padding:2px 0}
.dot{width:7px;height:7px;border-radius:50%;background:#fca5a5;flex:none}
.dot.on{background:#4ade80}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:40;height:48px;display:flex;align-items:center;gap:10px;padding:0 20px;border-bottom:1px solid var(--border);background:rgb(255 255 255/.6);backdrop-filter:blur(8px)}
.topbar h1{font-size:13.5px;font-weight:550;color:var(--muted-fg);margin-right:auto}
.content{max-width:1400px;width:100%;margin:0 auto;padding:24px 24px 64px;display:flex;flex-direction:column;gap:22px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;height:32px;padding:0 12px;border:1px solid var(--input);border-radius:calc(var(--radius) - 2px);background:var(--background);font-weight:500;font-size:13px}
.btn:hover{background:var(--accent)}
.btn.pri{background:var(--primary);color:var(--primary-fg);border-color:var(--primary)}
.btn.pri:hover{opacity:.9;background:var(--primary)}
.btn.sm{height:28px;padding:0 10px;font-size:12.5px;border-radius:8px}
.btn.dng{color:var(--bad);border-color:#fecaca}.btn.dng:hover{background:#fef2f2}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.card{background:var(--card);border-radius:var(--radius);box-shadow:0 0 0 1px rgb(9 9 11/.05),0 1px 2px rgb(0 0 0/.04)}
.card-h{padding:16px 16px 0;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap}
.card-t{font-weight:600;font-size:14px;line-height:1.3}
.card-d{font-size:12.5px;color:var(--muted-fg);margin-top:3px}
.card-a{margin-left:auto;display:flex;gap:8px;align-items:center}
.card-c{padding:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
.mc{display:flex;flex-direction:column;gap:10px;background:linear-gradient(to top,rgba(24,24,27,.03),var(--card));box-shadow:0 0 0 1px rgb(9 9 11/.05),0 1px 2px rgb(0 0 0/.04);border-radius:12px;padding:16px}
.mc .ih{width:28px;height:28px;border-radius:8px;border:1px solid var(--border);background:var(--muted);color:var(--muted-fg);display:inline-flex;align-items:center;justify-content:center;font-style:normal;font-size:13px}
.mc small{font-size:13px;color:var(--muted-fg)}
.mc .vrow{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.mc .val{font-weight:550;font-size:29px;line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums;color:var(--foreground)}
.mc .sub{font-size:13px;color:var(--muted-fg)}
.badge{display:inline-flex;align-items:center;gap:4px;height:20px;padding:0 8px;border-radius:99px;border:1px solid transparent;background:var(--primary);color:var(--primary-fg);font-size:11.5px;font-weight:500;white-space:nowrap}
.badge.up::before{content:"▲";font-size:9px}.badge.down::before{content:"▼";font-size:9px}
.badge.up{background:hsl(142 71% 45%)}.badge.down{background:var(--bad)}
.obdg{display:inline-flex;align-items:center;gap:4px;height:20px;padding:0 8px;border-radius:99px;border:1px solid var(--border);font-size:11.5px;color:var(--muted-fg);white-space:nowrap}
.b-new{color:#71717a}.b-draft{color:#2563eb;border-color:#bfdbfe;background:#eff6ff}.b-ready,.b-review{color:#b45309;border-color:#fde68a;background:#fffbeb}
.b-sent{color:var(--violet);border-color:#ddd6fe;background:#f5f3ff}.b-reply{color:#0e7490;border-color:#a5f3fc;background:#ecfeff}
.b-negotiation{color:#c2410c;border-color:#fed7aa;background:#fff7ed}.b-won{color:#15803d;border-color:#bbf7d0;background:#f0fdf4}
.b-paid{color:#15803d;border-color:#bbf7d0;background:#f0fdf4}.b-lost{color:#a1a1aa}
.b-running{color:#2563eb}.b-done{color:#15803d}.b-failed{color:var(--bad)}.b-queued{color:#71717a}
.b-issued{color:#b45309}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead tr{border-bottom:1px solid var(--border);background:rgb(24 24 27/.02)}
th{text-align:left;padding:11px 12px;font-weight:550;white-space:nowrap}
td{padding:12px;border-bottom:1px solid var(--border);vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .1s}tbody tr:hover{background:var(--muted)}
.cell-obj{display:flex;align-items:center;gap:10px;min-width:0}
.av{width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:var(--muted);display:flex;align-items:center;justify-content:center;flex:none;font-size:13px}
.nm{font-weight:500;font-size:13px;line-height:1.25;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:360px}
.idl{font-size:11px;color:var(--muted-fg);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:360px;margin-top:2px}
.mono{font-variant-numeric:tabular-nums}
input[type=text],select,textarea{background:var(--background);border:1px solid var(--input);border-radius:calc(var(--radius) - 2px);padding:7px 11px;font:inherit;font-size:13px;width:100%;outline:none;color:var(--foreground)}
input:focus,select:focus,textarea:focus{border-color:var(--ring);box-shadow:0 0 0 3px rgb(24 24 27/.07)}
textarea{resize:vertical;min-height:70px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding-bottom:14px}
.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(255px,1fr);gap:14px;overflow-x:auto;padding-bottom:8px}
.kcol{background:var(--secondary);border:1px solid var(--border);border-radius:12px;padding:10px}
.kcol h3{font-size:12.5px;font-weight:550;padding:2px 4px 10px;display:flex;justify-content:space-between;align-items:center}
.kcol h3 span{background:#e4e4e7;color:var(--foreground);border-radius:99px;min-width:20px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:11px;padding:0 6px}
.tcard{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;transition:border-color .12s}
.tcard:hover{border-color:var(--ring)}
.tcard .tt{font-weight:500;font-size:13px;line-height:1.35;margin-bottom:7px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
#modal{position:fixed;inset:0;background:rgb(24 24 27/.45);display:none;z-index:50;padding:24px;overflow:auto}
#modal.open{display:block}
.mbox{max-width:920px;margin:0 auto;background:var(--background);border:1px solid var(--border);border-radius:14px;box-shadow:0 20px 60px rgb(0 0 0/.16)}
.mhd{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--border)}
.mhd b{font-size:14px;margin-right:auto}
.mbd{padding:18px;display:grid;grid-template-columns:1fr 1fr;gap:18px}
.mbd .full{grid-column:1/-1}
.sec{font-size:11.5px;font-weight:600;color:var(--muted-fg);margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em}
.msg{border:1px solid var(--border);border-radius:10px;padding:8px 11px;margin-bottom:8px;background:var(--muted)}
.msg.out{background:#eff6ff;border-color:#bfdbfe}
.msg small{color:var(--muted-fg);display:block;margin-bottom:3px;font-size:11px}
#toasts{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:80}
.toast{background:var(--background);border:1px solid var(--border);border-left:3px solid #2563eb;border-radius:10px;padding:10px 14px;min-width:250px;box-shadow:0 10px 30px rgb(0 0 0/.12);font-size:13px}
.toast.err{border-left-color:var(--bad)}
.empty{color:var(--muted-fg);text-align:center;padding:48px 0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}
.mono{font-variant-numeric:tabular-nums}
.chartwrap{position:relative}
.tip{position:absolute;pointer-events:none;background:var(--primary);color:var(--primary-fg);font-size:11.5px;padding:4px 8px;border-radius:8px;transform:translate(-50%,-130%);white-space:nowrap;display:none}
@media(max-width:900px){.sb{position:fixed;left:-284px;z-index:60;transition:left .15s}.sb.open{left:0}.mburger{display:inline-flex!important}}
</style></head>
<body>
<div class="wrap">
<aside class="sb" id="sb">
  <div class="sb-head"><i>⚡</i> Zarabotok</div>
  <div class="sb-label">Обзор</div>
  <nav id="nav"></nav>
  <div class="sb-foot"><div class="sec" style="margin-bottom:6px">Воркеры</div><div id="workers"></div></div>
</aside>
<main class="main">
  <header class="topbar">
    <button id="mburger" class="btn sm mburger" style="display:none">☰ Меню</button>
    <h1 id="ttl">Дашборд</h1>
    <button class="btn sm" onclick="doScan()">⟳ Сканировать</button>
    <button class="btn sm pri" onclick="render()">Обновить</button>
    <button class="btn sm dng" onclick="killAll()">⛔ СТОП ВСЁ</button>
    <span style="width:30px;height:30px;border-radius:8px;background:var(--muted);display:inline-flex;align-items:center;justify-content:center;font-size:11.5px;color:var(--muted-fg)">АК</span>
  </header>
  <div class="content"><section id="view"><div class="empty">загрузка…</div></section></div>
</main>
</div>
<div id="modal" onclick="if(event.target===this)this.classList.remove('open')"><div class="mbox" id="mbox"></div></div>
<div id="toasts"></div>
<script>
const RU={new:'новый',draft:'черновик',ready:'готов',sent:'отправлен',reply:'ответ',negotiation:'переговоры',won:'выигран',lost:'проигран',paid:'оплачен',archive:'архив',queued:'в очереди',running:'работает',review:'на проверке',done:'готово',failed:'ошибка',issued:'выставлен'};
const VIEWS=[['funnel','Дашборд','▦'],['kanban','Канбан','▥'],['orders','Заказы','☰'],['dialogs','Диалоги','💬'],['exec','Исполнение','⚙'],['finance','Финансы','₽'],['settings','Настройки','⚒']];
let CUR='funnel',CURORD=null,ROWS=[],POLL=null,RANGE=14;
function $(s){return document.querySelector(s)}
function esc(s,n){s=(s==null?'':String(s));if(n)s=s.slice(0,n);const r={'&':'&amp;','<':'&lt;','>':'&#62;','"':'&quot;'};return String(s).replace(/[&<>"]/g,c=>r[c])}
function money(v){const n=Number(String(v==null?'':v).replace(/[^0-9.,-]/g,'').replace(',','.'));return isNaN(n)||!n?(esc(v||'—')):(n.toLocaleString('ru-RU')+' ₽')}
function obadge(st){return '<span class="obdg b-'+esc(st)+'">'+esc(RU[st]||st||'—')+'</span>'}
window.onerror=function(m){toast('JS: '+m,true)};
function toast(t,err){const d=document.createElement('div');d.className='toast'+(err?' err':'');d.textContent=t;document.getElementById('toasts').appendChild(d);setTimeout(()=>d.remove(),4200)}
async function api(p,o){const r=await fetch(p,o);const j=await r.json().catch(()=>({}));if(!r.ok){toast('Ошибка '+(j.error||r.status),true);throw new Error(j.error||r.status)}return j}
async function post(p,body){return api(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})})}

function drawNav(){
  document.getElementById('nav').innerHTML='<div class="sb-label">Разделы</div>'+VIEWS.map(v=>'<button class="mi'+(CUR===v[0]?' on':'')+'" data-v="'+v[0]+'"><span class="ic">'+v[2]+'</span>'+v[1]+'</button>').join('');
  document.querySelectorAll('#nav .mi').forEach(b=>b.onclick=()=>{CUR=b.dataset.v;document.getElementById('sb').classList.remove('open');drawNav();render()});
}
function drawWorkers(w){
  document.getElementById('workers').innerHTML=Object.entries(w||{}).map(([k,v])=>'<div class="wrow"><span class="dot '+(v&&v.running?'on':'')+'"></span>'+esc(String(k).replace('.py',''))+'</div>').join('');
}
async function render(){
  document.querySelectorAll('#nav .mi').forEach(b=>b.classList.toggle('on',b.dataset.v===CUR));
  document.getElementById('ttl').textContent=(VIEWS.find(v=>v[0]===CUR)||['',''])[1];
  try{
    if(CUR==='funnel') await vFunnel();
    else if(CUR==='kanban') await vKanban();
    else if(CUR==='orders') await vOrders();
    else if(CUR==='dialogs') await vDialogs();
    else if(CUR==='exec') await vExec();
    else if(CUR==='finance') await vFinance();
    else if(CUR==='settings') await vSettings();
  }catch(e){document.getElementById('view').innerHTML='<div class="empty">Ошибка: '+esc(e.message,140)+'</div>'}
  clearTimeout(POLL);POLL=setTimeout(render,20000);
}

function metric(icon,label,val,badgeHtml,sub){
  return '<div class="mc"><span class="ih">'+icon+'</span><small>'+label+'</small>'+
   '<div class="vrow"><span class="val">'+val+'</span>'+(badgeHtml||'')+'</div>'+
   '<span class="sub">'+(sub||'&nbsp;')+'</span></div>';
}

async function vFunnel(){
  const o=await api('/api/overview'), ad=await api('/api/activity_days');
  drawWorkers(o.workers);
  const st=o.st||{};
  const items=ad.items||[];
  const last=(items[items.length-1]||{found:0}), prev=(items[items.length-2]||{found:0});
  const delta=last.found-prev.found;
  const trend=delta>=0?('<span class="badge up">'+delta+' за сутки</span>'):('<span class="badge down">'+delta+'</span>');
  const freshBadge=(st.fresh||0)>0?('<span class="badge">+'+st.fresh+' новых</span>'):'';
  document.getElementById('view').innerHTML=
   '<div class="kpis">'+
    metric('📦','Найдено заказов',(st.jobs||0)-(st.fresh||0),trend,'всего в базе за всё время')+
    metric('📝','Черновики откликов',st.drafts||0,freshBadge,'готовы к отправке после одобрения')+
    metric('➤','Отправлено',st.sent||0,'','откликов ушло заказчикам')+
    metric('💬','Ответы клиентов',(o.unread_total||0),'','непрочитанных в диалогах')+
   '</div>'+
   '<div class="card"><div class="card-h"><div><div class="card-t">Активность по дням</div><div class="card-d">Найдено заказов за период — данные реальных сканов</div></div>'+
   '<div class="card-a"><select id="rng" style="max-width:130px;width:auto"><option value="14"'+(RANGE===14?' selected':'')+'>14 дней</option><option value="30"'+(RANGE===30?' selected':'')+'>30 дней</option></select></div></div>'+
   '<div class="card-c chartwrap" id="chart"></div></div>'+
   '<div class="card"><div class="card-h"><div><div class="card-t">Последние заказы</div><div class="card-d">свежие лиды из всех источников</div></div>'+
   '<div class="card-a"><button class="btn sm" id="goord">Все заказы →</button></div></div>'+
   '<div class="card-c" id="recent"></div></div>';
  document.getElementById('rng').onchange=e=>{RANGE=+e.target.value;vFunnel()};
  drawChart(items.slice(-RANGE));
  const od=await api('/api/orders');ROWS=od.rows||[];
  document.getElementById('recent').innerHTML=
   '<table><thead><tr><th>Заказ</th><th>Статус</th><th>Бюджет</th></tr></thead><tbody>'+
   ROWS.slice(0,6).map(r=>'<tr data-u="'+esc(r.url)+'" style="cursor:pointer">'+
    '<td><div class="cell-obj"><span class="av">📋</span><div><span class="nm">'+esc(r.title,84)+'</span><span class="idl">'+esc((r.source||'')+' · '+(r.contact||'без контакта'))+'</span></div></div></td>'+
    '<td>'+obadge(r.status)+(r.sent?' <span class="obdg b-sent">➤</span>':'')+'</td>'+
    '<td class="mono">'+money(r.budget)+'</td></tr>').join('')+
   '</tbody></table>';
  document.querySelectorAll('#recent tr[data-u]').forEach(tr=>tr.onclick=()=>openOrder(tr.dataset.u));
  document.getElementById('goord').onclick=()=>{CUR='orders';drawNav();render()};
}

function drawChart(items){
  const W=920,H=240,P={t:14,r:14,b:26,l:36};
  const iw=W-P.l-P.r, ih=H-P.t-P.b;
  const max=Math.max(10,...items.map(d=>d.found));
  const step=iw/Math.max(items.length-1,1);
  function x(i){return P.l+i*step}
  function y(v){return P.t+ih-(v/max)*ih}
  let line='',area='M '+x(0).toFixed(1)+' '+y(items[0].found).toFixed(1);
  items.forEach((d,i)=>{line+=(i?' L ':'M ')+x(i).toFixed(1)+' '+y(d.found).toFixed(1)});
  area=line+' L '+(P.l+iw).toFixed(1)+' '+(P.t+ih).toFixed(1)+' L '+P.l.toFixed(1)+' '+(P.t+ih).toFixed(1)+' Z';
  let grid='';
  for(let g=0;g<=3;g++){const gy=(P.t+ih*g/3).toFixed(1);grid+='<line x1="'+P.l+'" y1="'+gy+'" x2="'+(P.l+iw)+'" y2="'+gy+'" stroke="#e4e4e7"/>';}
  const every=Math.ceil(items.length/7);
  const labels=items.map((d,i)=>((i%every===0)||(i===items.length-1)?'<text x="'+x(i).toFixed(1)+'" y="'+(H-6)+'" text-anchor="middle" font-size="10.5" fill="#71717a">'+esc(d.label)+'</text>':'')).join('');
  const pts=items.map((d,i)=>'<circle cx="'+x(i).toFixed(1)+'" cy="'+y(d.found).toFixed(1)+'" r="2.5" fill="#18181b" opacity="0" data-i="'+i+'"/>').join('');
  document.getElementById('chart').innerHTML=
   '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:auto;display:block">'+
   '<defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">'+
   '<stop offset="0%" stop-color="#71717a" stop-opacity=".22"/><stop offset="100%" stop-color="#71717a" stop-opacity=".02"/></linearGradient></defs>'+
   grid+'<path d="'+area+'" fill="url(#ga)"/><path d="'+line+'" fill="none" stroke="#71717a" stroke-width="2" stroke-linejoin="round"/>'+
   pts+labels+
   '<line id="cross" x1="0" y1="'+P.t+'" x2="0" y2="'+(P.t+ih)+'" stroke="#a1a1aa" stroke-dasharray="3 3" style="display:none"/></svg><div class="tip" id="ctip"></div>';
  const svg=document.querySelector('#chart svg'), tip=document.getElementById('ctip'), cross=document.getElementById('cross');
  svg.addEventListener('mousemove',ev=>{
    const r=svg.getBoundingClientRect();
    const mx=(ev.clientX-r.left)*(W/r.width);
    let idx=Math.round((mx-P.l)/step);idx=Math.max(0,Math.min(items.length-1,idx));
    const d=items[idx], cx=x(idx), cy=y(d.found);
    cross.setAttribute('x1',cx);cross.setAttribute('x2',cx);cross.style.display='';
    tip.style.display='block';tip.style.left=(cx/W*100)+'%';tip.style.top=((cy/H*100))+'%';
    tip.textContent=d.label+': '+d.found+' заказов';
  });
  svg.addEventListener('mouseleave',()=>{tip.style.display='none';cross.style.display='none'});
}

async function vKanban(){
  const od=await api('/api/orders');ROWS=od.rows||[];
  const cols=['new','draft','ready','sent','reply','negotiation','won','paid'];
  const by={};cols.forEach(c=>by[c]=[]);
  ROWS.forEach(r=>{(by[r.crm_status||'new']||by['new']).push(r)});
  document.getElementById('view').innerHTML='<div class="board">'+cols.map(c=>{
    const list=by[c].slice(0,15).map(cardHtml).join('');
    return '<div class="kcol"><h3>'+esc(RU[c])+'<span>'+by[c].length+'</span></h3>'+(list||'<div style="color:var(--muted-fg);font-size:12px;padding:4px">—</div>')+'</div>';
  }).join('')+'</div>';
  bindCards();
}
function cardHtml(r){
  const ds=(r.draft_status||'new'), sent=(ds==='sent'), approved=(ds==='approved');
  const flags=(r.contact?'📇':'')+(approved&&!sent?' ✓':'')+(sent?' ➤':'');
  return '<div class="tcard" data-u="'+esc(r.url)+'"><div class="tt">'+esc(r.title,90)+'</div>'+
   '<div class="row"><span class="obdg">'+esc(r.source||'')+'</span>'+
   (r.budget?'<span class="mono" style="font-size:12px">'+money(r.budget)+'</span>':'')+
   (r.score?'<span class="obdg" style="margin-left:auto">★ '+esc(r.score)+'</span>':'')+(flags?'<span style="font-size:11px">'+flags+'</span>':'')+'</div></div>';
}
function bindCards(){document.querySelectorAll('.tcard[data-u]').forEach(el=>el.onclick=()=>openOrder(el.dataset.u))}

async function vOrders(){
  const od=await api('/api/orders');ROWS=od.rows||[];
  // collect unique platforms
  const PLATFORMS=[...new Set(ROWS.map(r=>r.platform||'—'))].sort();
  const platOpts=PLATFORMS.map(p=>'<option value="'+esc(p)+'">'+esc(p)+'</option>').join('');
  document.getElementById('view').innerHTML=
   '<div class="card"><div class="card-h"><div><div class="card-t">'+ROWS.length+' заказов</div><div class="card-d">все источники: Telegram-каналы, биржи, сообщества</div></div>'+
    '<div class="card-a"><button class="btn sm" onclick="doScan()">⟳ Сканировать</button></div></div>'+
    '<div class="card-c"><div class="toolbar">'+
    '<input type="text" id="q" style="max-width:320px" placeholder="Поиск по названию, контакту, каналу…">'+
    '<select id="fst" style="max-width:180px;width:auto"><option value="">все статусы</option>'+['new','draft','ready','sent','reply','negotiation','won','paid'].map(k=>'<option value="'+k+'">'+RU[k]+'</option>').join('')+'</select>'+
    '<select id="fpl" style="max-width:180px;width:auto"><option value="">все платформы</option>'+platOpts+'</select>'+
    '<select id="fsort" style="max-width:160px;width:auto"><option value="date">по дате</option><option value="score">по скору ★</option><option value="budget">по бюджету</option></select></div>'+
    '<table><thead><tr><th>Заказ</th><th>Статус</th><th>Бюджет</th><th>Платформа</th><th>Канал</th><th>★</th></tr></thead><tbody id="tb"></tbody></table></div></div>';
  const paint=()=>{
    const q=(document.getElementById('q').value||'').toLowerCase(), 
          fs=document.getElementById('fst').value,
          fp=document.getElementById('fpl').value,
          fsrt=document.getElementById('fsort').value;
    let rows=ROWS.filter(r=>(
      (!q||(r.title||'').toLowerCase().includes(q)||
       (r.contact||'').toLowerCase().includes(q)||
       (r.channel||'').toLowerCase().includes(q)||
       (r.source||'').toLowerCase().includes(q)||
       (r.platform||'').toLowerCase().includes(q))
      &&(!fs||(r.crm_status||'new')===fs)
      &&(!fp||(r.platform||'—')===fp)
    ));
    // sort
    if(fsrt==='score') rows.sort((a,b)=>(Number(b.score||0)-Number(a.score||0)));
    else if(fsrt==='budget') rows.sort((a,b)=>((Number(money(b.budget))||0)-(Number(money(a.budget))||0)));
    else rows.sort((a,b)=>new Date(b.scanned_at||0)-new Date(a.scanned_at||0));
    document.getElementById('tb').innerHTML=rows.map(r=>'<tr class="rw" data-u="'+esc(r.url)+'" style="cursor:pointer">'+
      '<td><div class="cell-obj"><span class="av">📋</span><div><span class="nm">'+esc(r.title,86)+'</span><span class="idl">'+esc((r.source||'')+' · '+(r.contact||'без контакта'))+'</span></div></div></td>'+
      '<td>'+obadge(r.crm_status||'new')+((r.draft_status==='sent')?' <span class="obdg b-sent">➤ ушёл</span>':'')+((r.draft_status==='approved')?' <span class="obdg b-ready">одобрен</span>':'')+'</td>'+
      '<td class="mono">'+money(r.budget)+'</td><td>'+esc(r.platform||'—')+'</td><td>'+esc(r.channel||'—')+'</td><td class="mono">'+esc(r.score||'—')+'</td></tr>').join('')||
      '<tr><td colspan="6" class="empty">ничего не найдено</td></tr>';
    document.querySelectorAll('#tb tr[data-u]').forEach(tr=>tr.onclick=()=>openOrder(tr.dataset.u));
  };
  document.getElementById('q').oninput=paint;
  document.getElementById('fst').onchange=paint;
  document.getElementById('fpl').onchange=paint;
  document.getElementById('fsort').onchange=paint;
  paint();
}

async function vDialogs(){
  const od=await api('/api/orders');
  const rows=(od.rows||[]).filter(r=>(r.crm_status||'new')==='reply'||r.channel==='tg'||r.channel==='email');
  document.getElementById('view').innerHTML='<div class="grid2">'+rows.slice(0,24).map(r=>
    '<div class="card tcard" data-u="'+esc(r.url)+'" style="padding:14px"><div class="tt">'+esc(r.title,70)+'</div><div class="row">'+obadge(r.status)+'<span class="obdg">'+esc(r.contact||r.to||r.channel||'?')+'</span></div></div>').join('')+
    (rows.length?'':'<div class="empty">диалогов пока нет — появятся после первых отправок</div>')+'</div>';
  bindCards();
}

async function vExec(){
  const d=await api('/api/exec');
  const tasks=d.items||d.tasks||[];
  document.getElementById('view').innerHTML=tasks.length?'<div class="grid2">'+tasks.map(t=>
    '<div class="card" style="padding:16px"><div class="row" style="justify-content:space-between;margin-bottom:8px"><b style="font-size:13.5px">'+esc(t.title||t.url,70)+'</b>'+obadge(t.status)+'</div>'+
    (t.note?'<div style="color:var(--muted-fg);font-size:12.5px;margin-bottom:10px">'+esc(t.note,200)+'</div>':'')+
    '<div class="row"><button class="btn sm" data-x="'+esc(t.url)+'" data-act="run">🚀 Агентам</button>'+
    (t.status==='review'?'<button class="btn sm pri" data-x="'+esc(t.url)+'" data-act="deliver">✅ Доставить клиенту</button>':'')+'</div></div>').join('')+'</div>'
    :'<div class="card empty">нет задач — создаются при статусе «выигран» или из карточки заказа</div>';
  document.querySelectorAll('[data-act]').forEach(b=>b.onclick=async()=>{
    const u=b.dataset.x;
    if(b.dataset.act==='deliver'){await post('/api/order/'+encodeURIComponent(u)+'/deliver');toast('Доставка выполнена')}
    else{await post('/api/order/'+encodeURIComponent(u)+'/execute',{tz:''});toast('Передано агентам')}
    render()});
}

async function vFinance(){
  const inv=await api('/api/invoices');
  const items=inv.items||[];
  const paidSum=items.filter(i=>i.status==='paid').reduce((s,i)=>s+Number(String(i.amount==null?'':i.amount).replace(/[^0-9.,-]/g,'').replace(',','.')||0),0);
  document.getElementById('view').innerHTML='<div class="kpis">'+
   metric('💰','Заработано (оплачено)',money(paidSum),'','поступления на счета')+
   metric('🧾','Счетов всего',items.length,'','')+
   metric('⏳','Ожидают оплаты',items.filter(i=>i.status==='sent'||i.status==='issued').length,'','')+
  '</div><div class="card"><div class="card-h"><div><div class="card-t">Счета</div></div></div><div class="card-c">'+
   '<table><thead><tr><th>№</th><th>Сумма</th><th>Метод</th><th>Статус</th></tr></thead><tbody>'+
   items.map(i=>'<tr class="rw"><td class="mono">'+esc(i.no)+'</td><td class="mono">'+money(i.amount)+'</td><td>'+esc(i.method||'')+'</td><td>'+obadge(i.status)+'</td></tr>').join('')||
   '<tr><td colspan="4" class="empty">счетов нет</td></tr></tbody></table></div></div>';
}

async function vSettings(){
  const s=await api('/api/settings');
  const tg=(k,label)=>'<div class="card row" style="justify-content:space-between;padding:14px 16px"><span style="font-size:13.5px">'+label+'</span><button class="btn sm '+(s[k]?'pri':'')+'" data-k="'+k+'">'+(s[k]?'ВКЛ':'ВЫКЛ')+'</button></div>';
  document.getElementById('view').innerHTML='<div class="grid2">'+tg('auto_send','Автоотправка откликов')+tg('auto_approve','Автоодобрение черновиков')+tg('tg_poll','Слушать Telegram')+tg('show_vacancies','Показывать вакансии')+'</div><div class="card row" style="justify-content:space-between;padding:14px 16px"><span>Аварийный стоп снят?</span><button class="btn sm pri" onclick="resumeAll()">▶ Возобновить работу</button></div>';
  document.querySelectorAll('#view [data-k]').forEach(b=>b.onclick=async()=>{
    const k=b.dataset.k,nv=!(s[k]);
    await post('/api/settings',{[k]:nv});toast(k+' = '+nv);render()});
}

window.killAll=async()=>{if(!confirm('Аварийно остановить ВСЕ отправки и автоответы?'))return;await post('/api/system/stop');toast('⛔ Остановлено. Возобновление — Настройки',true)};
window.resumeAll=async()=>{await post('/api/system/resume');toast('Работа возобновлена')};
window.doScan=async()=>{toast('Сканирование запущено…');await post('/api/scan');setTimeout(render,4000)};

async function openOrder(url){
  CURORD=url;
  let d;try{d=await api('/api/order/'+encodeURIComponent(url))}catch(e){return}
  const j=d.job||{},it=d.draft||{},mt=d.crm||{},inv=d.invoice||{},xj=((d.exec||{}).task),xf=((d.exec||{}).files)||[];
  const th=(d.thread||[]).map(x=>'<div class="msg '+esc(x.direction)+'"><small>'+esc(x.ts,19)+' · '+esc(x.sender||'',20)+' · '+esc(x.channel||'')+'</small>'+esc(x.text,600)+'</div>').join('')||'<div style="color:var(--muted-fg)">сообщений нет</div>';
  const files=(d.files||[]).map(f=>'<div class="row" style="justify-content:space-between;padding:3px 0"><span style="font-size:12.5px">'+esc(f.filename,44)+'</span><span class="obdg mono">'+esc(f.size)+' Б</span></div>').join('')||'<span style="color:var(--muted-fg)">файлов нет</span>';
  const sts=['new','draft','ready','sent','reply','negotiation','won','lost','paid','archive'];
  document.getElementById('mbox').innerHTML=
  '<div class="mhd"><b>'+esc(j.title||it.title||url,110)+'</b><span class="obdg">'+esc(j.source||'')+'</span>'+(j.budget?'<span class="obdg mono">'+money(j.budget)+'</span>':'')+'<button class="btn sm" onclick="closeM()">✕</button></div>'+
  '<div class="mbd">'+
   '<div class="full sec">Управление сделкой</div><div class="full row">'+
    '<select id="mst" style="max-width:190px;width:auto">'+sts.map(s=>'<option value="'+s+'" '+(s===(mt.status||'new')?'selected':'')+'>'+RU[s]+'</option>').join('')+'</select>'+
    '<button class="btn sm" onclick="mSetSt()">Сохранить статус</button>'+
    '<a class="btn sm" href="'+esc(j.url||'#')+'" target="_blank" rel="noopener">↗ Открыть на источнике</a></div>'+
   '<div class="full sec" style="margin-top:14px">Черновик отклика '+obadge(it.sent?'sent':(it.approved?'ready':'draft'))+'</div>'+
   '<div class="full"><textarea id="mtx" rows="5">'+esc(it.text||'',2600)+'</textarea>'+
   '<div class="row" style="margin-top:9px">'+
    '<button class="btn sm" onclick="mSave()">💾 Сохранить</button>'+
    '<button class="btn sm pri" onclick="mApprove()" '+(it.approved||it.sent?'disabled':'')+'>✅ Одобрить и отправить</button>'+
    '<button class="btn sm" onclick="mRegen()">🔄 Заново</button>'+
    '<button class="btn sm dng" onclick="mDismiss()">✕ Скрыть</button></div>'+
   ((it.qa)?'<div style="margin-top:8px;color:#b45309;font-size:12.5px">QA: '+esc(it.qa,120)+'</div>':'')+'</div>'+
   '<div class="full sec" style="margin-top:14px">Переписка</div><div class="full">'+th+'</div>'+
   '<div class="full row" style="margin-top:8px"><select id="mch" style="max-width:110px;width:auto"><option value="tg">telegram</option><option value="email">email</option></select>'+
    '<input type="text" id="mrp" placeholder="ответ клиенту…"><button class="btn sm pri" onclick="mReply()">Отправить</button>'+
    '<button class="btn sm" onclick="mRead()">✓ прочитано</button></div>'+
   '<div><div class="sec">Файлы</div>'+files+'</div>'+
   '<div><div class="sec">Счёт</div>'+(inv.no?
     '<div class="row" style="gap:8px"><span class="obdg mono">'+esc(inv.no)+'</span><b class="mono">'+money(inv.amount)+'</b>'+obadge(inv.status)+'</div><div style="color:var(--muted-fg);font-size:12px;margin-top:5px">'+esc(inv.method||'')+'</div>'
     :'<span style="color:var(--muted-fg)">не выставлен (после «выигран» — автоматически)</span>')+'</div>'+
   '<div class="full"><div class="sec" style="margin-top:14px">Исполнение агентами '+(xj?obadge(xj.status):'')+'</div>'+
    (xj?'<div style="color:var(--muted-fg);font-size:12.5px;margin-bottom:8px">'+esc(xj.note||'',200)+'</div>'+
        (xf.length?'<div class="row" style="margin-bottom:10px">'+xf.map(f=>'<span class="obdg mono">'+esc(f.path,34)+'</span>').join('')+'</div>':'')+
        '<div class="row">'+(xj.status==='review'?'<button class="btn sm pri" onclick="mDeliver()">✅ Доставить клиенту</button>':'')+
        '<button class="btn sm" onclick="mExec()">🚀 Передать агентам</button></div>'
     :'<span style="color:var(--muted-fg)">задача не создана</span>')+'</div>'+
  '</div>';
  document.getElementById('modal').classList.add('open');
}
window.closeM=()=>{document.getElementById('modal').classList.remove('open');render()};
async function mPost(act,extra){try{await post('/api/order/'+encodeURIComponent(CURORD)+'/'+act,extra);toast('ок')}catch(e){} }
window.mSetSt=async()=>{await mPost('status',{status:document.getElementById('mst').value});closeM()};
window.mSave=async()=>{await mPost('edit',{text:document.getElementById('mtx').value});closeM()};
window.mApprove=async()=>{await mPost('approve');closeM()};
window.mRegen=async()=>{await mPost('regen');openOrder(CURORD)};
window.mDismiss=async()=>{await mPost('dismiss');closeM()};
window.mReply=async()=>{await post('/api/chat/'+encodeURIComponent(CURORD)+'/reply',{text:document.getElementById('mrp').value,channel:document.getElementById('mch').value});toast('отправлено');closeM()};
window.mRead=async()=>{await post('/api/chat/'+encodeURIComponent(CURORD)+'/read');closeM()};
window.mExec=async()=>{await mPost('execute',{tz:''});openOrder(CURORD)};
window.mDeliver=async()=>{await mPost('deliver');toast('Результат доставлен');closeM()};

document.addEventListener('click',e=>{if(e.target.id==='mburger')document.getElementById('sb').classList.toggle('open')});
drawNav();render();
</script></body></html>
"""

# ---------- HTTP Handler ----------
class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # Serve rebuilt frontend from dist/ (rebuild after any UI change)
        if path == "/" or path == "/index.html":
            dist_path = os.path.join(BASE, "ui", "dist", "index.html")
            try:
                with open(dist_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(html_content.encode("utf-8"))
            except FileNotFoundError:
                # Fallback to embedded SPA if rebuilt dist missing (should never happen after build)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(SPA.encode("utf-8"))
            return
        
        # Serve rebuilt frontend assets from dist/assets/
        if path.startswith("/assets/"):
            asset_path = path.lstrip("/")
            file_path = os.path.join(BASE, "ui", "dist", asset_path)
            # Security: prevent directory traversal
            file_path = os.path.abspath(file_path)
            dist_dir = os.path.abspath(os.path.join(BASE, "ui", "dist"))
            if not file_path.startswith(dist_dir + os.sep) and file_path != dist_dir:
                self.send_response(403)
                self.end_headers()
                return
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                # Set content-type based on extension
                if file_path.endswith(".js"):
                    content_type = "application/javascript; charset=utf-8"
                elif file_path.endswith(".css"):
                    content_type = "text/css; charset=utf-8"
                elif file_path.endswith(".svg"):
                    content_type = "image/svg+xml"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    content_type = "image/jpeg"
                else:
                    content_type = "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
            return
        
        # API routes
        if path.startswith("/api/"):
            try:
                if path == "/api/overview":
                    resp = api_overview()
                elif path == "/api/orders":
                    resp = api_orders()
                elif path == "/api/order/":
                    # Handle /api/order/<url>
                    url = path[len("/api/order/"):]
                    if url:
                        resp = api_order(urllib.parse.unquote(url))
                    else:
                        resp = {"error": "missing url"}
                elif path == "/api/chat/":
                    url = path[len("/api/chat/"):]
                    if url:
                        resp = api_chat(urllib.parse.unquote(url))
                    else:
                        resp = {"error": "missing url"}
                elif path == "/api/finance":
                    resp = api_finance()
                elif path == "/api/invoices":
                    resp = api_invoices()
                elif path == "/api/agents":
                    resp = api_agents()
                elif path == "/api/exec":
                    resp = api_exec()
                elif path == "/api/settings":
                    resp = api_settings()
                elif path == "/api/activity_days":
                    resp = _activity_days(30)
                elif path == "/api/health":
                    resp = api_health()
                else:
                    resp = {"error": "not found"}
                    code = 404
                code = 200
            except Exception as e:
                resp = {"error": str(e)}
                code = 500
            
            body = json.dumps(resp, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        
        # QR page
        if path == "/qr":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(qr_page().encode("utf-8"))
            return
        
        # Health page
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(health_page().encode("utf-8"))
            return
        
        # 404
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(content_length).decode('utf-8')
        
        try:
            if path.startswith("/api/"):
                resp = api_post(parsed.path, raw)
                body = json.dumps(resp, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        except Exception as e:
            resp = {"error": str(e)}
            body = json.dumps(resp, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        
        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default log
        pass

if __name__ == "__main__":
    import signal
    import sys
    
    PORT = 8765
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"Dashboard starting on http://0.0.0.0:{PORT}")
    
    def shutdown(signum, frame):
        print("Shutting down...")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()