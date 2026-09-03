"""Приём ответов заказчиков: Telegram-диалоги (Telethon) + почта (IMAP шедулится из watchdog)."""
import time

from modules import chat, crm, executor, http_client, store, tg_common, tz_parser


def _handle_order_reply(order: str, peer: str, text: str, channel: str = "tg"):
    """Общее: зафиксировать входящее, распарсить ТЗ, при наличии ТЗ создать задачу исполнения."""
    chat.add(order, "in", channel, peer, text)
    store.append("activity", {"ts": store.now(), "text": f"{channel.upper()}: входящее от {peer} -> заказ {order}"}, key="activity")
    crm.set_status(order, "reply")
    tz = tz_parser.parse_tz(text)
    crm.update(order, tz_received=store.now(), tz_text=tz["tz_text"],
                tz_deadline=tz["deadline"], tz_budget=tz["budget"])
    if tz["has_tz"] and not executor.task_for(order):
        title = ""
        for j in store.load("jobs", {"items": []}).get("items", []):
            if j.get("url") == order:
                title = j.get("title", "")
                break
        executor.create_exec_task(order, tz=tz["tz_text"], title=title, source="listener")
        store.append("activity", {"ts": store.now(), "text": f"TЗ получено -> задача исполнения: {order}"}, key="activity")


def poll_telegram(mark_seen: bool = True, limit: int = 60) -> int:
    session = store.load("settings", {}).get("tg_session_listener", "telegram_session_listener")
    client = tg_common.tg_client(tg_common.session_path(session), proxy=http_client.socks_args())
    got = 0
    try:
        with tg_common.tg_lock():
            client.start()
            for dialog in client.iter_dialogs(limit=limit):
                ts = dialog.date.timestamp()
                seen = store.load("tg_seen", {})
                key = dialog.id
                if seen.get(str(key), 0) >= ts:
                    continue
                msg = getattr(dialog, "message", None)
                if msg is None or getattr(msg, "out", False):
                    seen[str(key)] = ts
                    store.save("tg_seen", seen)
                    continue
                if (time.time() - ts) <= 3600 * 24:
                    text = (msg.text if msg else "")[:1000]
                    uname = getattr(getattr(dialog, "entity", None), "username", None)
                    peer = ("@" + uname.lower()) if uname else f"tg:{dialog.name}"
                    store.append("threads", {
                        "ts": store.now(),
                        "from": peer,
                        "text": f"[диалог {dialog.name}] {text}",
                    }, key="threads")
                    order = chat.find_order_for_peer(peer)
                    if order:
                        _handle_order_reply(order, peer, text, "tg")
                    seen[str(key)] = ts
                    store.save("tg_seen", seen)
                    got += 1
    except Exception as e:
        store.append("activity", {"ts": store.now(), "text": f"TG poll: {e}"}, key="activity")
    finally:
        client.disconnect()
    return got


def poll_email_tz(limit: int = 50) -> int:
    """Дозор входящей почты: привязка к заказу + парсинг ТЗ (вызывается из sender.poll_email-логики
    или watchdog). Возвращает число обработанных писем с ТЗ."""
    from modules import sender as _sender

    accs = _sender._email_accounts()
    if not accs:
        return 0
    got = 0
    for acc in accs:
        try:
            import imaplib
            from email.utils import parseaddr

            with imaplib.IMAP4_SSL(acc.get("imap_host", "imap.gmail.com"), acc.get("imap_port", 993), timeout=30) as imap:
                imap.login(acc["imap_user"], acc["imap_pass"])
                imap.select("INBOX")
                _, data = imap.search(None, "UNSEEN")
                nums = (data[0] or b"").split()[:limit]
                for num in nums:
                    _, payload = imap.fetch(num, "(RFC822)")
                    raw = payload[0][1]
                    from email import message_from_bytes
                    msg = message_from_bytes(raw)
                    address = parseaddr(msg.get("From", ""))[1].lower()
                    text = ""
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            text = (part.get_payload(decode=True) or b"").decode(
                                part.get_content_charset() or "utf-8", "replace")
                            break
                    order = chat.find_order_for_peer(address)
                    if order:
                        _handle_order_reply(order, address, text, "email")
                        got += 1
                    imap.store(num, "+FLAGS", "\\Seen")
        except Exception as e:
            store.append("activity", {"ts": store.now(), "text": f"EMAIL TZ poll: {e}"}, key="activity")
    return got


def sla_push(minutes: int = 30) -> int:
    """ТЗ 19: клиент ждёт ответа >N минут — уведомление оператору в TG (раз)."""
    import time as _t
    now = _t.time()
    msgs = store.load("messages", {"items": []}).get("items", [])
    n = 0
    for m in msgs:
        if m.get("direction") != "in" or not m.get("order"):
            continue
        if m.get("replied") or m.get("sla_notified") or m.get("decline"):
            continue
        try:
            ts = _t.mktime(_t.strptime(m["ts"][:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue
        if now - ts < minutes * 60:
            continue
        try:
            from modules import sender as _s
            ok = _s.send_telegram({"contact": "me", "text":
                f"SLA: клиент ждёт ответа >{minutes} мин\nЗаказ: {m['order'][:70]}\n"
                f"Сообщение: {m.get('text','')[:80]}"})
        except Exception:
            ok = False
        def _mark(d):
            for x in d.get("items", []):
                if (x.get("order") == m.get("order") and x.get("direction") == "in"
                        and x.get("ts") == m.get("ts")):
                    x["sla_notified"] = True
                    return None
            return None
        store.mutate("messages", _mark, {"items": []})
        n += 1
    return n
