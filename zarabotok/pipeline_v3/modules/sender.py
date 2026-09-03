"""Отправка: Telegram (Telethon, сессии под прокси) и почта (SMTP). Отправка ТОЛЬКО одобренных (approved=True)."""
import imaplib
import json
import os
import random
import re
import smtplib
import time
from email.header import decode_header
from email.utils import parseaddr
from email.mime.text import MIMEText

from modules import chat, fl_bidder, http_client, store, tg_common

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def _sender_cfg() -> dict:
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f).get("sender", {})
    except Exception:
        return {}


def _email_accounts() -> list[dict]:
    """Список email-ящиков: config.json email_accounts; фолбэк на старые settings['email'].""" 
    try:
        with open(CONFIG, encoding="utf-8") as f:
            accs = json.load(f).get("email_accounts", [])
        if isinstance(accs, list):
            accs = [a for a in accs if isinstance(a, dict)
                    and a.get("imap_user") and a.get("imap_pass")]
        else:
            accs = []
        if accs:
            return accs
    except Exception:
        pass
    s = store.load("settings", {}).get("email", {})
    if s.get("imap_user") and s.get("imap_pass"):
        return [{
            "id": "legacy",
            "imap_host": s.get("imap_host", "imap.gmail.com"),
            "imap_port": s.get("imap_port", 993),
            "imap_user": s["imap_user"],
            "imap_pass": s["imap_pass"],
            "smtp_host": s.get("smtp_host", "smtp.gmail.com"),
            "smtp_port": s.get("smtp_port", 465),
            "smtp_user": s.get("smtp_user", ""),
            "smtp_pass": s.get("smtp_pass", ""),
        }]
    return []


def require_approved(box):
    approved = [i for i in box if i.get("approved") and not i.get("sent")]
    return approved


def auto_approve(items):
    """Автоодобрение черновиков: 
    - с прямым контактом (tg/email) или fl.ru
    - ИЛИ высокий score (>= auto_min_score) для любых платформ
    - без стоп-слов.
    Возвращает (count, approved_items) для сохранения."""
    cfg = _sender_cfg()
    n = 0
    limit = int(cfg.get("auto_limit", 10))
    min_score = int(cfg.get("auto_min_score", 3))
    min_score_no_contact = int(cfg.get("auto_min_score_no_contact", 5))
    stop = [w.lower() for w in cfg.get("stopwords", [])]

    def _norm(s: str) -> str:
        repl = {"0": "о", "3": "з", "4": "а", "6": "б", "1": "л",
                "e": "е", "o": "о", "a": "а", "c": "с", "h": "н", "p": "р",
                "k": "к", "m": "м", "t": "т", "x": "х", "y": "у", "b": "в"}
        return "".join(repl.get(ch, ch) for ch in s.lower())

    approved_items = []
    for i in items:
        if n >= limit:
            break
        if i.get("approved") or i.get("sent"):
            continue
        has_contact = (i.get("contact") or i.get("to"))
        is_fl = fl_bidder.is_fl_url(i.get("url", ""))
        score = int(i.get("score", 0) or 0)
        
        if has_contact or is_fl:
            required_score = min_score
        else:
            required_score = min_score_no_contact
        
        if score < required_score:
            continue
        
        title = _norm(((i.get("title") or "") + " " + (i.get("text") or "")))
        if any(w in title for w in stop):
            if not i.get("auto_skip"):
                i["auto_skip"] = True
                store.append("activity", {"ts": store.now(), "text": f"АВТО-пропуск (стоп-слово): {i.get('title','')[:50]}"}, key="activity")
            continue
        i["approved"] = True
        n += 1
        store.append("activity", {"ts": store.now(), "text": f"АВТО-одобрен {i.get('channel')}: {i.get('title','')[:50]}"}, key="activity")
        approved_items.append(i)
    return n, approved_items


def send_telegram(item: dict, err_sink: list | None = None) -> bool:
    import asyncio

    session = store.load("settings", {}).get("tg_session", "telegram_session_sender")
    session_path = tg_common.session_path(session)
    dest = item.get("contact") or item.get("url")
    if isinstance(dest, str) and dest.startswith("tg:"):
        dest = dest[3:]
    if isinstance(dest, str) and "t.me/" in dest:
        m = re.search(r"t\.me/([A-Za-z0-9_]{3,})", dest)
        if m:
            dest = "@" + m.group(1)

    async def _send() -> tuple[bool, str]:
        client = tg_common.tg_client(session_path, proxy=http_client.socks_args())
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return False, "noauth"
            await client.send_message(dest, item["text"])
            return True, ""
        except Exception as e:
            return False, str(e)[:120]
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    try:
        with tg_common.tg_lock():
            ok, err = asyncio.run(asyncio.wait_for(_send(), timeout=90))
    except Exception as e:
        ok, err = False, str(e)[:120]
    bad = any(m in err.lower() for m in ("can't write", "cannot write", "no user has", "username", "user not found", "flood"))
    if ok:
        store.append("activity", {"ts": store.now(), "text": f"TG: отправлено {dest[:60]}"}, key="activity")
    elif err == "noauth":
        store.append("activity", {"ts": store.now(), "text": f"TG: сессия {session} не авторизована"}, key="activity")
    elif bad:
        store.append("activity", {"ts": store.now(), "text": f"TG: контакт недоступен {dest[:60]}"}, key="activity")
    else:
        store.append("activity", {"ts": store.now(), "text": f"TG: ошибка отправки {dest[:60]}: {err}"}, key="activity")
    if not ok and err_sink is not None:
        err_sink.append(err or "telegram: send failed")
    return "bad" if bad else ok


def send_email(item: dict, account_id: str | None = None, err_sink: list | None = None) -> bool:
    accs = _email_accounts()
    acc = None
    if account_id:
        acc = next((a for a in accs if a.get("id") == account_id), None)
    if acc is None and accs:
        acc = accs[0]
    if acc is None or not acc.get("smtp_user") or not acc.get("smtp_pass"):
        store.append("activity", {"ts": store.now(), "text": "EMAIL: нет настроек smtp"}, key="activity")
        if err_sink is not None:
            err_sink.append("нет настроек smtp")
        return False
    msg = MIMEText(item["text"], "plain", "utf-8")
    msg["Subject"] = f"Отклик: {item['title'][:80]}"
    msg["From"] = acc["smtp_user"]
    msg["To"] = item["to"]
    try:
        with smtplib.SMTP_SSL(acc.get("smtp_host", "smtp.gmail.com"), acc.get("smtp_port", 465), timeout=30) as smtp:
            smtp.login(acc["smtp_user"], acc["smtp_pass"])
            smtp.sendmail(acc["smtp_user"], [item["to"]], msg.as_string())
        store.append("activity", {"ts": store.now(), "text": f"EMAIL: отправлено на {item['to']}"}, key="activity")
        return True
    except Exception as e:
        store.append("activity", {"ts": store.now(), "text": f"EMAIL: ошибка: {e}"}, key="activity")
        if err_sink is not None:
            err_sink.append(str(e)[:200])
        return False


def _retry_cfg(cfg: dict) -> tuple:
    """sender.retry из config.json: (max_attempts, base_delay_sec, max_delay_sec)."""
    r = cfg.get("retry", {}) or {}
    return (int(r.get("max_attempts", 4) or 4),
            float(r.get("base_delay_sec", 30) or 30),
            float(r.get("max_delay_sec", 3600) or 3600))


def _next_attempt_ts(attempts: int, base_delay: float, max_delay: float, now: float | None = None) -> float:
    """Экспоненциальная задержка ретрая: base_delay * 2**(attempts-1), кап max_delay."""
    delay = base_delay * (2 ** max(attempts - 1, 0))
    if max_delay > 0:
        delay = min(delay, max_delay)
    return (time.time() if now is None else now) + delay


def _sent_match(entries: list, item: dict) -> bool:
    """True, если в sent_log уже есть запись {url, channel, dest} для этого item
    (защита от дубля при падении между отправкой и пометкой sent)."""
    url = item.get("url", "")
    if not url:
        return False
    ch = (item.get("channel") or "").lower()
    dest = (item.get("contact") or item.get("to") or url)[:60]
    for s in entries:
        if s.get("url") != url or (s.get("channel") or "").lower() != ch:
            continue
        s_dest = (s.get("dest") or "").strip()
        if s_dest and dest and s_dest != dest:
            continue
        return True
    return False


def _mark_sent(box, item):
    for it in box.get("items", []):
        if it["url"] == item["url"]:
            it["sent"] = True
            it["sent_at"] = store.now()
            return None
    return None


def _hil() -> dict:
    return _sender_cfg().get("human_in_loop", {}) or {}


def _quality_ok(item: dict, cfg: dict) -> bool:
    """Авто-отправка только если оценка судьи >= quality_threshold (0-1 -> 0-10)."""
    thr = float(cfg.get("quality_threshold", 0.75)) * 10
    judge_score = item.get("judge", item.get("score", 0))
    return float(judge_score or 0) >= thr


def _dispatch(item: dict, cfg: dict) -> str:
    """Возвращает 'auto' | 'pending' | 'skip'.
    auto — отправляем сразу (TG с контактом / email).
    pending — показываем в дашборде для ручного отклика на сайте.
    skip — не отправляем (FL платный / без контакта / низкое качество)."""
    url = (item.get("url") or "").lower()
    ch = (item.get("channel") or "").lower()
    if "fl.ru" in url:
        return "skip"
    if any(s in url for s in ("freelance.ru", "weblancer", "kwork", "habr", "weworkremotely")):
        return "pending"
    contact = item.get("contact") or item.get("to")
    if ch == "email" and item.get("to"):
        return "auto" if _quality_ok(item, cfg) else "skip"
    if ch == "tg" or "t.me" in url:
        if contact:
            return "auto" if _quality_ok(item, cfg) else "skip"
        return "pending"
    return "skip"


def _mark_pending(item: dict):
    if item.get("pending_approve"):
        return

    def _fn(box):
        for it in box.get("items", []):
            if it["url"] == item["url"]:
                it["pending_approve"] = True
                return None
        return None

    store.mutate("outbox", _fn, {"items": []})
    store.append("activity", {"ts": store.now(),
                "text": f"PENDING (ручной отклик): {item.get('title','')[:50]}"}, key="activity")


def approve_and_send(url: str) -> dict:
    """Ручное подтверждение отклика из дашборда: шлём сразу через канал заказа."""
    box = store.load("outbox", {"items": []}).get("items", [])
    item = next((i for i in box if i["url"] == url), None)
    if not item:
        return {"ok": False, "error": "не найдено"}
    ch = (item.get("channel") or "").lower()
    if ch == "email" and item.get("to"):
        ok = send_email(item)
    elif item.get("contact"):
        ok = send_telegram(item)
    else:
        return {"ok": False, "error": "нет контакта для отправки"}
    if ok:
        def _fn(boxd):
            for it in boxd.get("items", []):
                if it["url"] == url:
                    it["sent"] = True
                    it["sent_at"] = store.now()
                    it["pending_approve"] = False
                    return None
            return None

        store.mutate("outbox", _fn, {"items": []})
        chat.add(url, "out", ch, item.get("contact") or item.get("to"), item.get("text", ""))
        store.append("sent_log", {"ts": store.now(), "channel": ch, "url": url,
                    "dest": (item.get("contact") or item.get("to") or "")[:60]}, key="items")
        return {"ok": True}
    return {"ok": False, "error": "send failed"}


def text_similar(a: str, b: str) -> bool:
    """True = тексты почти идентичны (анти-шаблонный контроль перед отправкой)."""
    import difflib
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= 0.8


def _qa_gate(item: dict) -> str:
    """Возвращает строку-причину блокировки отправки или '' если отклик можно слать.

    1) скам-маркеры (proposals.is_scam) — мгновенно;
    2) уникальность: похожесть на последние 50 отправленных текстов >= 0.8;
    3) LLM-судья (proposals.judge_eval): pass=False -> блок. Любая ошибка судьи — fail-open.
    """
    try:
        from modules import proposals
        job_like = {"title": item.get("title") or "", "budget": item.get("budget") or "",
                    "description": item.get("description") or ""}
        if proposals.is_scam(job_like):
            return "скам-маркеры в заказе"
        text = item.get("text") or ""
        recent = store.load("sent_texts", {"items": []}).get("items", [])[-50:]
        for r in recent:
            if text_similar(text, r.get("text") or ""):
                return f"дубль текста (похож на {r.get('ts','')[:16]})"
        res = proposals.judge_eval(text, job_like)
        if res and not res.get("pass"):
            viol = "; ".join((res.get("violations") or []))[:80]
            return f"judge {float(res.get('score', 0)):.0f}/10: {viol}"
        return ""
    except Exception:
        return ""


def in_quiet_hours(cfg: dict, now_hm: str | None = None) -> bool:
    """Тихие часы (по умолчанию 23:00–08:00). Явно пустой список = выключены."""
    q = cfg.get("quiet_hours", ["23:00", "08:00"])
    if not q or len(q) < 2:
        return False
    a, b = str(q[0]), str(q[1])
    hm = now_hm or time.strftime("%H:%M")
    if a <= b:
        return a <= hm < b
    return hm >= a or hm < b  # интервал через полночь


def _fl_bid_cycle(cfg: dict) -> int:
    """Авто-отклики на fl.ru по сохранённой сессии (fl_bidder).

    Отдельный поток от outbox: берём лучшие FL-заказы из jobs, шаблонный отклик,
    капы per-cycle/per-day, дедуп 48ч, скам-фильтр, платные помечаем и больше
    не трогаем (fl_paid)."""
    if not cfg.get("fl_auto_bid"):
        return 0
    cap = int(cfg.get("fl_max_per_cycle", 3) or 0)
    per_day = int(cfg.get("fl_max_per_day", 6) or 0)
    min_score = int(cfg.get("fl_min_score", 2) or 2)
    if cap <= 0:
        return 0
    # не чаще раза в 10 минут
    last = store.load("fl_last_bid", {}).get("ts", 0)
    if time.time() - float(last or 0) < 600:
        return 0
    store.save("fl_last_bid", {"ts": time.time()})

    from modules import fl_bidder, proposals as _p

    all_sent = store.load("sent_log", {"items": []}).get("items", [])
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 48 * 3600))
    sent_urls = {s.get("url") for s in all_sent if s.get("ts", "") >= cutoff}
    today = time.strftime("%Y-%m-%d")
    fl_today = sum(1 for s in all_sent if s.get("channel") == "fl" and s.get("ts", "").startswith(today))
    paid_urls = set(store.load("fl_paid", {"urls": []}).get("urls", []))

    jobs = [j for j in store.load("jobs", {"items": []}).get("items", [])
            if "fl.ru" in (j.get("url") or "")
            and (j.get("kind") or "order") != "vacancy"
            and int(j.get("score", 0) or 0) >= min_score]
    jobs.sort(key=lambda x: x.get("score", 0), reverse=True)

    n = 0
    for j in jobs[: cap * 5]:
        if n >= cap or (per_day and fl_today + n >= per_day):
            break
        url = j.get("url") or ""
        if url in sent_urls or url in paid_urls:
            continue
        if _p.is_scam(j):
            continue
        text = _p.template_draft(j)
        try:
            res = fl_bidder.bid_fl(url, text)
        except Exception as e:
            store.append("activity", {"ts": store.now(),
                        "text": f"FL: ошибка биддинга {url[:45]}: {str(e)[:70]}"}, key="activity")
            continue
        if res == "paid":
            paid_urls.add(url)
            store.save("fl_paid", {"urls": list(paid_urls)[-500:]})
            store.append("activity", {"ts": store.now(),
                        "text": f"FL: платный отклик (80₽), в стоп-лист: {(j.get('title') or '')[:40]}"}, key="activity")
            continue
        if res:
            rec = {"ts": store.now(), "channel": "fl", "url": url, "dest": url[:60]}
            store.append("sent_log", rec, key="items")
            store.append("sent_texts", {"ts": store.now(), "text": text[:2000]}, key="items")
            store.append("activity", {"ts": store.now(),
                        "text": f"FL: отклик отправлен: {(j.get('title') or '')[:45]}"}, key="activity")
            n += 1
        else:
            store.append("activity", {"ts": store.now(),
                        "text": f"FL: не прошёл отклик: {(j.get('title') or '')[:40]}"}, key="activity")
    return n


def _freelancer_bid_cycle(cfg: dict) -> int:
    """Авто-биддинг на Freelancer.com через Playwright (freelancer_bidder).

    Берёт проекты из jobs с platform=Freelancer.com, капы per-cycle/per-day,
    дедуп 48ч, скам-фильтр."""
    if not cfg.get("freelancer_auto_bid"):
        return 0
    cap = int(cfg.get("freelancer_max_per_cycle", 3) or 0)
    per_day = int(cfg.get("freelancer_max_per_day", 6) or 0)
    min_score = int(cfg.get("freelancer_min_score", 2) or 2)
    if cap <= 0:
        return 0
    # не чаще раза в 10 минут
    last = store.load("freelancer_last_bid", {}).get("ts", 0)
    if time.time() - float(last or 0) < 600:
        return 0
    store.save("freelancer_last_bid", {"ts": time.time()})

    from modules import freelancer_bidder as fb, proposals as _p

    all_sent = store.load("sent_log", {"items": []}).get("items", [])
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 48 * 3600))
    sent_urls = {s.get("url") for s in all_sent if s.get("ts", "") >= cutoff}
    today = time.strftime("%Y-%m-%d")
    fl_today = sum(1 for s in all_sent if s.get("channel") == "freelancer" and s.get("ts", "").startswith(today))
    paid_urls = set(store.load("freelancer_paid", {"urls": []}).get("urls", []))

    jobs = [j for j in store.load("jobs", {"items": []}).get("items", [])
            if j.get("platform") == "Freelancer.com"
            and (j.get("kind") or "order") != "vacancy"
            and int(j.get("score", 0) or 0) >= min_score]
    jobs.sort(key=lambda x: x.get("score", 0), reverse=True)

    n = 0
    for j in jobs[: cap * 5]:
        if n >= cap or (per_day and fl_today + n >= per_day):
            break
        url = j.get("url") or ""
        if url in sent_urls or url in paid_urls:
            continue
        if _p.is_scam(j):
            continue
        text = _p.template_draft(j)
        # Оценка бюджета из проекта
        bid_amount = None
        try:
            meta = j.get("metadata", {})
            if meta:
                currency = meta.get("currency")
                # Можно добавить логику извлечения бюджета
        except Exception:
            pass
        try:
            res = fb.bid_freelancer(url, text, bid_amount=bid_amount, period_days=7)
        except Exception as e:
            store.append("activity", {"ts": store.now(),
                        "text": f"Freelancer.com: ошибка биддинга {url[:45]}: {str(e)[:70]}"}, key="activity")
            continue
        if res == "paid":
            paid_urls.add(url)
            store.save("freelancer_paid", {"urls": list(paid_urls)[-500:]})
            store.append("activity", {"ts": store.now(),
                        "text": f"Freelancer.com: платный бид, в стоп-лист: {(j.get('title') or '')[:40]}"}, key="activity")
            continue
        if res == "already_bid":
            store.append("activity", {"ts": store.now(),
                        "text": f"Freelancer.com: уже бидили: {(j.get('title') or '')[:40]}"}, key="activity")
            continue
        if res:
            rec = {"ts": store.now(), "channel": "freelancer", "url": url, "dest": url[:60]}
            store.append("sent_log", rec, key="items")
            store.append("sent_texts", {"ts": store.now(), "text": text[:2000]}, key="items")
            store.append("activity", {"ts": store.now(),
                        "text": f"Freelancer.com: бид отправлен: {(j.get('title') or '')[:45]}"}, key="activity")
            n += 1
        else:
            store.append("activity", {"ts": store.now(),
                        "text": f"Freelancer.com: не прошёл бид: {(j.get('title') or '')[:40]}"}, key="activity")
    return n


def run_cycle() -> int:
    if os.path.exists(os.path.join(store.STATE, "KILL_SWITCH")):
        return 0  # аварийная остановка оператором

    _dbg = os.environ.get("SENDER_TIMING") == "1"

    def _log(msg):
        if _dbg:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def _approve(box):
        items = box.get("items", [])
        if _sender_cfg().get("auto_approve"):
            auto_approve_count, approved_items = auto_approve(items)
            # Сохраняем одобренные элементы
            if approved_items:
                def _save_appr(b):
                    for item in b.get("items", []):
                        for appr in approved_items:
                            if item.get("url") == appr.get("url"):
                                item["approved"] = True
                                break
                    return b
                store.mutate("outbox", _save_appr, {"items": []})
        skip = ("paid", "bad", "dead", "spam")
        paid_too_old = time.time() - 86400
        out = []
        for it in items:
            if not (it.get("approved") and not it.get("sent")):
                continue
            if it.get("skip_reason") in skip:
                if it.get("skip_reason") == "paid" and float(it.get("paid_at", 0) or 0) < paid_too_old:
                    it.pop("skip_reason", None)
                    it.pop("paid_at", None)
                    out.append(dict(it))
                continue
            out.append(dict(it))
        return out

    def _mark_bad(box, item):
        for it in box.get("items", []):
            if it["url"] == item["url"]:
                it["skip_reason"] = "bad"
                # контакт мёртв — снимаем одобрение, чтобы не висело «готово к отправке»
                it["approved"] = False
                it["note"] = "контакт недоступен"
                return None
        return None

    cfg = _sender_cfg()
    max_attempts, base_delay, max_delay = _retry_cfg(cfg)
    # FL-автобиддинг — отдельный поток от outbox (куки, свои капы), не мешает outbox
    try:
        _fl_bid_cycle(cfg)
    except Exception as e:
        store.append("activity", {"ts": store.now(),
                    "text": f"FL-cycle error: {type(e).__name__}: {str(e)[:80]}"}, key="activity")
    # Freelancer.com автобиддинг — отдельный поток (Playwright)
    try:
        _freelancer_bid_cycle(cfg)
    except Exception as e:
        store.append("activity", {"ts": store.now(),
                    "text": f"Freelancer.com-cycle error: {type(e).__name__}: {str(e)[:80]}"}, key="activity")
    now_h = time.strftime("%Y-%m-%dT%H")
    now_d = time.strftime("%Y-%m-%d")
    all_sent = store.load("sent_log", {"items": []}).get("items", [])
    sent_this_hour = [s for s in all_sent if s.get("ts", "").startswith(now_h)]
    sent_today = [s for s in all_sent if s.get("ts", "").startswith(now_d)]
    seen_sent = list(sent_this_hour)
    hour_budget = int(cfg.get("max_per_hour", 0) or 0)
    day_budget = int(cfg.get("max_per_day", 0) or 0)
    d_min = float(cfg.get("send_delay_min_sec", 45) or 45)
    d_max = float(cfg.get("send_delay_max_sec", 180) or 180)

    pending = store.mutate("outbox", _approve, {"items": []})
    if in_quiet_hours(cfg):
        _log("тихие часы — отправки отложены")
        return 0
    pending.sort(key=lambda x: (float(x.get("judge", x.get("score", 0)) or 0),
                                1 if str(x.get("channel")).lower() == "tg" else 0), reverse=True)
    _log(f"pending={len(pending)} (sorted by judge desc)")
    sent = 0
    judged_this_cycle = 0
    for i in pending:
        ch = (i.get("channel") or "").lower()
        url = (i.get("url") or "")[:50]
        if hour_budget and len(sent_this_hour) >= hour_budget:
            _log(f"лимит max_per_hour={hour_budget} исчерпан, стоп цикла")
            break
        if day_budget and len(sent_today) >= day_budget:
            _log(f"лимит max_per_day={day_budget} исчерпан, стоп цикла")
            break
        _log(f"-> {url} ch={ch} score={i.get('score')}")
        t0 = time.monotonic()
        if i.get("skip_reason") in ("paid", "bad"):
            continue
        nxt_ts = float(i.get("next_attempt_ts") or 0)
        if nxt_ts and time.time() < nxt_ts:
            _log(f"ретрай-окно: пропуск {url} до {time.strftime('%H:%M:%S', time.localtime(nxt_ts))}")
            continue
        decision = _dispatch(i, cfg)
        if decision == "skip":
            _log(f"   dispatch=skip {url}")
            continue
        if decision == "pending":
            _mark_pending(i)
            continue
        # ---- QA-гейт перед отправкой (ТЗ#4): скам-маркеры + уникальность + LLM-судья.
        # Только для авто-каналов; при сбое судьи — fail-open (не блокировать отправки).
        if cfg.get("pre_send_judge", True) and judged_this_cycle < 5:
            verdict = _qa_gate(i)
            judged_this_cycle += 1
            if verdict:

                def _mark_qa(box):
                    for it in box.get("items", []):
                        if it["url"] == i["url"]:
                            it["skip_reason"] = "qa"
                            it["note"] = str(verdict)[:140]
                            return None
                    return None

                store.mutate("outbox", _mark_qa, {"items": []})
                store.append("activity", {"ts": store.now(),
                            "text": f"QA-гейт: пропуск {url}: {str(verdict)[:80]}"}, key="activity")
                _log(f"   qa-gate: {verdict}")
                continue
        last_err = ""
        if ch == "email" and (i.get("to")):
            if _sent_match(seen_sent, i):
                _log("уже в sent_log (час) — пропуск повтора")
                store.mutate("outbox", lambda box: _mark_sent(box, i), {"items": []})
                store.append("activity", {"ts": store.now(), "text": f"EMAIL: дубль-защита, уже отправлен: {i.get('to','')}"}, key="activity")
                sent += 1
                continue
            errs = []
            ok = send_email(i, err_sink=errs)
            if errs:
                last_err = errs[0]
        else:
            if _sent_match(seen_sent, i):
                _log("уже в sent_log (час) — пропуск повтора")
                store.mutate("outbox", lambda box: _mark_sent(box, i), {"items": []})
                store.append("activity", {"ts": store.now(), "text": f"TG: дубль-защита, уже отправлен: {i.get('url','')[:45]}"}, key="activity")
                sent += 1
                continue
            errs = []
            ok = send_telegram(i, err_sink=errs)
            if errs:
                last_err = errs[0]
        if ok == "bad":
            i["skip_reason"] = "bad"
            store.mutate("outbox", lambda box: _mark_bad(box, i), {"items": []})
            continue
        if ok:
            _log(f"   ok, {round(time.monotonic()-t0,1)}s")

            def _mark(box):
                for it in box.get("items", []):
                    if it["url"] == i["url"]:
                        it["sent"] = True
                        it["sent_at"] = store.now()
                        return None
                return None

            store.mutate("outbox", _mark, {"items": []})
            dest = i.get("contact") or i.get("to") or i.get("url", "")
            chat.add(i.get("url"), "out", ch, dest, i.get("text", ""))
            rec = {"ts": store.now(), "channel": ch, "url": i.get("url", ""), "dest": dest[:60]}
            store.append("sent_log", rec, key="items")
            store.append("sent_texts", {"ts": store.now(), "text": (i.get("text") or "")[:2000]}, key="items")
            all_sent.append(rec)
            seen_sent.append(rec)
            sent += 1
        else:
            err = (last_err or f"{ch}: отправка не удалась")[:200]
            attempts = int(i.get("attempts", 0) or 0) + 1
            if attempts >= max_attempts:
                note = f"dead after {attempts} attempts: {err}"

                def _dead(box):
                    for it in box.get("items", []):
                        if it["url"] == i["url"]:
                            it["skip_reason"] = "dead"
                            it["attempts"] = attempts
                            it["last_error"] = err
                            it["note"] = note
                            it["dead_at"] = store.now()
                            return None
                    return None

                store.mutate("outbox", _dead, {"items": []})
                dead_item = dict(i)
                dead_item.update({"attempts": attempts, "last_error": err,
                                  "skip_reason": "dead", "note": note, "dead_at": store.now()})
                store.append("outbox_dead", dead_item, key="items")
                store.append("activity", {"ts": store.now(), "text": f"DEAD (DLQ): {url}: {err[:100]}"}, key="activity")
                _log(f"DEAD: {url}")
            else:
                nxt_ts = _next_attempt_ts(attempts, base_delay, max_delay)

                def _retry(box):
                    for it in box.get("items", []):
                        if it["url"] == i["url"]:
                            it["attempts"] = attempts
                            it["last_error"] = err
                            it["next_attempt_ts"] = nxt_ts
                            return None
                    return None

                store.mutate("outbox", _retry, {"items": []})
                _log(f"ретрай #{attempts} для {url}: пауза {round(nxt_ts - time.time(), 1)}s")
        time.sleep(random.uniform(d_min, d_max))
    return sent


def poll_email(limit: int = 50) -> int:
    accounts = _email_accounts()
    if not accounts:
        return 0
    from modules import autoreply
    got = 0
    for acc in accounts:
        try:
            with imaplib.IMAP4_SSL(acc.get("imap_host", "imap.gmail.com"), acc.get("imap_port", 993), timeout=30) as imap:
                imap.login(acc["imap_user"], acc["imap_pass"])
                imap.select("INBOX")
                _, data = imap.search(None, "UNSEEN")
                nums = (data[0] or b"").split()[:limit]
                if not nums:
                    continue
                for num in nums:
                    _, msg = imap.fetch(num, "(RFC822)")
                    payload = msg[0][1]
                    try:
                        text = _decode_body(payload)
                    except Exception:
                        text = ""
                    raw = payload.decode("utf-8", "replace")
                    from_line = next((l for l in raw.splitlines() if l.lower().startswith("from:")), "")
                    address = parseaddr(from_line)[1].lower()
                    if text and address:
                        store.append("threads", {
                            "ts": store.now(),
                            "from": address,
                            "text": text[:1000],
                            "account": acc.get("id", ""),
                        }, key="threads")
                        order = chat.find_order_for_peer(address)
                        chat.add(order, "in", "email", address, text)
                        cls = autoreply.classify_message(text)
                        store.append("chat_classify", {
                            "ts": store.now(),
                            "order": order,
                            "type": cls["type"],
                            "entities": cls["entities"],
                        }, key="items")
                        if order:
                            store.append("activity", {"ts": store.now(), "text": f"EMAIL: входящее от {address} -> заказ {order}"}, key="activity")
                        got += 1
                imap.store(b",".join(nums), "+FLAGS", "\\Seen")
        except Exception as e:
            store.append("activity", {"ts": store.now(), "text": f"EMAIL poll ({acc.get('id', '?')}): {e}"}, key="activity")
    return got


def _decode_body(payload: bytes) -> str:
    import email as em
    msg = em.message_from_bytes(payload)
    parts = []
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            raw = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            parts.append(raw.decode(charset, errors="replace"))
    return "\n".join(parts)