import datetime
import os

from modules import crm, store

STATUSES = ("new", "draft", "ready", "sent", "reply", "negotiation", "won", "lost", "paid", "archive")
REPLIED = ("reply", "negotiation", "won", "paid")
SENT = ("sent", "reply", "negotiation", "won", "paid")


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


def _on_date(ts, date):
    p = _parse(ts)
    return p is not None and p.strftime("%Y-%m-%d") == date


def _earliest(events):
    out = {}
    for url, ts in events:
        p = _parse(ts)
        if p is None or not url:
            continue
        if url not in out or p < out[url]:
            out[url] = p
    return out


def _avg_hours(pairs):
    vals = [h for h in ((b - a).total_seconds() / 3600.0 for a, b in pairs) if h >= 0]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def _channel(url, item):
    if item:
        ch = str(item.get("channel") or "").lower()
        if ch in ("tg", "telegram"):
            return "tg"
        if ch in ("email", "mail"):
            return "email"
        if ch == "fl":
            return "fl"
    u = url or ""
    if "t.me" in u:
        return "tg"
    if "fl.ru" in u:
        return "fl"
    return "other"


def _stage_events(agents):
    reply, won, paid = {}, {}, {}
    for a in agents:
        act = a.get("action") or ""
        url, ts = a.get("order"), a.get("ts")
        if not url or not ts:
            continue
        if act == "статус -> reply" or act == "статус -> negotiation":
            reply.setdefault(url, ts)
        elif act == "статус -> won":
            won.setdefault(url, ts)
        elif act == "статус -> paid":
            paid.setdefault(url, ts)
    return reply, won, paid


def _timings(box, msgs, reply_ev, won_ev, paid_ev):
    sent_src = [(i.get("url"), i.get("sent_at")) for i in box if i.get("sent") and i.get("sent_at")]
    sent_src += [(m.get("order"), m.get("ts")) for m in msgs if m.get("direction") == "out" and m.get("order")]
    sent_ts = _earliest(sent_src)
    reply_src = [(u, t) for u, t in reply_ev.items()]
    reply_src += [(m.get("order"), m.get("ts")) for m in msgs if m.get("direction") == "in" and m.get("order")]
    reply_ts = _earliest(reply_src)
    won_ts = _earliest([(u, t) for u, t in won_ev.items()])
    paid_ts = _earliest([(u, t) for u, t in paid_ev.items()])
    return sent_ts, reply_ts, won_ts, paid_ts


def _filters(act, agents, date=None):
    def _pick(items, key, prefix):
        n = 0
        for x in items:
            if (x.get(key) or "").startswith(prefix) and (date is None or _on_date(x.get("ts"), date)):
                n += 1
        return n
    auto_skip = _pick(act, "text", "АВТО-пропуск")
    auto_approved = _pick(act, "text", "АВТО-одобрен")
    scam = sum(1 for a in agents if (a.get("action") or "") == "вердикт=scam"
               and (date is None or _on_date(a.get("ts"), date)))
    real = sum(1 for a in agents if (a.get("action") or "") == "вердикт=real"
               and (date is None or _on_date(a.get("ts"), date)))
    denom = auto_skip + auto_approved
    denom2 = scam + real
    return {
        "auto_skip": auto_skip,
        "auto_approved": auto_approved,
        "skip_share": round(auto_skip * 100.0 / denom, 1) if denom else 0.0,
        "scam_verdicts": scam,
        "real_verdicts": real,
        "scam_share": round(scam * 100.0 / denom2, 1) if denom2 else 0.0,
    }


def _build(date=None):
    box = store.load("outbox", {"items": []}).get("items", [])
    meta_d = store.load("orders_meta", {"items": {}}).get("items", {})
    msgs = store.load("messages", {"items": []}).get("items", [])
    invs = store.load("invoices", {"items": []}).get("items", [])
    act = store.load("activity", {"activity": []}).get("activity", [])
    agents = store.load("agents_activity", {"items": []}).get("items", [])
    reply_ev, won_ev, paid_ev = _stage_events(agents)
    sent_ts, reply_ts, won_ts, paid_ts = _timings(box, msgs, reply_ev, won_ev, paid_ev)

    new_set = {url for url, m in meta_d.items() if _on_date(m.get("created_at"), date)} if date else set()
    sent_set = {u for u, p in sent_ts.items() if date is None or p.strftime("%Y-%m-%d") == date}
    replied_set = {u for u, p in reply_ts.items() if date is None or p.strftime("%Y-%m-%d") == date}
    won_set = {u for u, p in won_ts.items() if date is None or p.strftime("%Y-%m-%d") == date}
    paid_set = {u for u, p in paid_ts.items() if date is None or p.strftime("%Y-%m-%d") == date}
    for url, m in meta_d.items():
        pay = m.get("payment", {})
        if pay.get("status") == "paid" and (date is None or _on_date(pay.get("paid_at"), date)):
            paid_set.add(url)
    for i in invs:
        if i.get("status") == "paid" and (date is None or _on_date(i.get("paid_at"), date)):
            paid_set.add(i.get("url"))

    if date is None:
        f = dict(crm.funnel())
    else:
        f = {st: 0 for st in STATUSES}
        for url in new_set | sent_set | replied_set | won_set | paid_set:
            st = meta_d.get(url, {}).get("status", "")
            if st in STATUSES and st not in ("new", "sent", "draft", "ready"):
                f[st] += 1
            elif url in sent_set:
                f["sent"] += 1
            elif url in new_set:
                f["new"] += 1
    sent_total = f["sent"] + f["reply"] + f["negotiation"] + f["won"] + f["paid"]
    replied_n = f["reply"] + f["negotiation"] + f["won"] + f["paid"]
    winned = f["won"] + f["paid"]

    reply_pairs = [(sent_ts[u], p) for u, p in reply_ts.items()
                   if u in sent_ts and (date is None or p.strftime("%Y-%m-%d") == date)]
    won_pairs = [(sent_ts[u], p) for u, p in won_ts.items()
                 if u in sent_ts and (date is None or p.strftime("%Y-%m-%d") == date)]

    invoiced = sum(crm._to_float(i.get("amount")) for i in invs
                   if i.get("status") == "sent" and (date is None or _on_date(i.get("created_at"), date)))
    pay_meta = crm.payments() if date is None else None
    if date is None:
        income = {
            "invoiced": round(invoiced, 2),
            "paid": round(sum(crm._to_float(i.get("amount")) for i in invs if i.get("status") == "paid")
                          + pay_meta["paid"], 2),
            "paid_meta": pay_meta["paid"],
            "won": pay_meta["won"],
            "expected": pay_meta["expected"],
        }
    else:
        paid_sum = 0.0
        for url in paid_set:
            amt = crm._to_float(meta_d.get(url, {}).get("payment", {}).get("amount"))
            if not amt:
                amt = crm._to_float(next((i.get("amount") for i in invs if i.get("url") == url), 0))
            paid_sum += amt
        won_sum = 0.0
        for url in won_set:
            amt = crm._to_float(meta_d.get(url, {}).get("payment", {}).get("amount"))
            if not amt:
                amt = crm._to_float(next((i.get("amount") for i in invs if i.get("url") == url), 0))
            won_sum += amt
        paid_meta_day = sum(crm._to_float(m.get("payment", {}).get("amount")) for url, m in meta_d.items()
                            if m.get("payment", {}).get("status") == "paid"
                            and _on_date(m.get("payment", {}).get("paid_at"), date))
        income = {
            "invoiced": round(invoiced, 2),
            "paid": round(paid_sum, 2),
            "paid_meta": round(paid_meta_day, 2),
            "won": round(won_sum, 2),
        }

    box_by_url = {i.get("url"): i for i in box}
    channels = {}
    active = new_set | sent_set | replied_set | won_set | paid_set if date else None
    for url in meta_d:
        if date is not None and url not in active:
            continue
        st = meta_d[url].get("status", "new")
        ch = _channel(url, box_by_url.get(url))
        c = channels.setdefault(ch, {"sent": 0, "replied": 0})
        if st in SENT:
            c["sent"] += 1
        if st in REPLIED:
            c["replied"] += 1

    res = {
        "funnel": f,
        "total": sum(f.values()),
        "conversions": {
            "sent_to_reply": round(replied_n * 100.0 / sent_total, 1) if sent_total else 0.0,
            "reply_to_won": round(winned * 100.0 / replied_n, 1) if replied_n else 0.0,
            "won_to_paid": round(f["paid"] * 100.0 / winned, 1) if winned else 0.0,
        },
        "avg_hours": {
            "sent_to_first_reply": _avg_hours(reply_pairs),
            "sent_to_won": _avg_hours(won_pairs),
        },
        "income": income,
        "channels": channels,
        "filters": _filters(act, agents, date),
        "ts": store.now(),
    }
    if date is not None:
        rows = []
        for url in sorted(won_set | paid_set):
            m = meta_d.get(url, {})
            st = "paid" if url in paid_set else "won"
            amt = crm._to_float(m.get("payment", {}).get("amount"))
            if not amt:
                amt = crm._to_float(next((i.get("amount") for i in invs if i.get("url") == url), 0))
            ts = won_ts.get(url) or paid_ts.get(url)
            rows.append({
                "url": url,
                "title": crm._title_for(url),
                "status": st,
                "amount": round(amt, 2),
                "ts": ts.strftime("%Y-%m-%dT%H:%M:%S%z") if ts
                       else (m.get("payment", {}).get("paid_at") or m.get("updated_at") or ""),
            })
        res["won_paid_orders"] = rows
        res["date"] = date
    return res


def funnel():
    return _build(None)


def daily_summary(date):
    return _build(date)


def save_daily(date, data):
    os.makedirs(os.path.join(store.STATE, "reports"), exist_ok=True)
    store.save("reports/daily_" + date, data)