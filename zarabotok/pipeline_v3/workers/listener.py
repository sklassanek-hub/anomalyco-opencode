import sys
import time

sys.path.insert(0, ".")

from modules import autoreply, billing, fl_bidder, listener, report, sender, store  # noqa: E402

INTERVAL = 60 * 5
FL_POLL_EVERY = 60 * 30
REPORT_HOUR = 9


def _daily_report_due() -> bool:
    """Один раз в сутки после REPORT_HOUR: сводка оператору в сохранёнки."""
    now = time.localtime()
    if now.tm_hour < REPORT_HOUR:
        return False
    today = time.strftime("%Y-%m-%d")
    last = store.load("report_last", {}).get("date", "")
    return last != today


def _fl_poll_due() -> bool:
    s = store.load("fl_last_poll", {})
    last = s.get("ts", 0)
    return time.time() - last >= FL_POLL_EVERY


def fl_poll_once() -> int:
    """Забирает входящие из FL-чатов в messages (одна страница /messages/)."""
    try:
        dialogs = fl_bidder.poll_messages()
    except Exception as e:
        store.append("activity", {"ts": store.now(), "text": f"FL-чаты: ошибка опроса {type(e).__name__}: {str(e)[:80]}"}, key="activity")
        return 0
    store.save("fl_last_poll", {"ts": time.time()})
    got = 0
    for d in dialogs:
        if d["url"] in store.load("fl_seen_msgs", {"urls": []}).get("urls", []):
            continue
        text = d["text"]
        order = ""
        for j in store.load("jobs", {"items": []}).get("items", []):
            if j.get("url", "").startswith("https://www.fl.ru"):
                order = order or ""
        store.append("threads", {"ts": store.now(), "from": f"FL:{d['peer']}", "text": text[:400]}, key="threads")
        store.append("messages", {
            "ts": store.now(), "direction": "in", "channel": "fl",
            "peer": d["url"], "order": "", "text": text[:400],
        }, key="items")
        seen = store.load("fl_seen_msgs", {"urls": []})
        seen.setdefault("urls", []).append(d["url"])
        store.save("fl_seen_msgs", seen)
        store.append("activity", {"ts": store.now(), "text": f"FL: входящее от {d['peer'][:40]} -> {d['url'][:50]}"}, key="activity")
        got += 1
    return got


def main() -> int:
    print("listener v3 start", flush=True)
    while True:
        try:
            got = 0
            settings = store.load("settings", {})
            # слушаем входящие той же авторизованной сессией, что и отправка,
            # если отдельная listener-сессия не настроена/не авторизована
            if settings.get("tg_poll"):
                if not settings.get("tg_session_listener"):
                    settings["tg_session_listener"] = settings.get("tg_session", "telegram_session_sender")
                try:
                    got += listener.poll_telegram()
                except Exception as e:
                    print(f"tg poll error: {e}", flush=True)
            else:
                print("listener: TG-опрос отключён (tg_poll=false) — жду настройки", flush=True)
            try:
                got += sender.poll_email()
            except Exception as e:
                print(f"email poll error: {e}", flush=True)
            if _fl_poll_due():
                got += fl_poll_once()
            if got:
                print(f"listener: got {got} new messages", flush=True)
            replied = autoreply.cycle()
            if replied:
                print(f"listener: автоответов отправлено {replied}", flush=True)
            try:
                listener.sla_push(30)
            except Exception as e:
                print(f"sla error: {e}", flush=True)
            try:
                paid = billing.check_usdt_payments()
                if paid:
                    print(f"listener: USDT-оплат подтверждено: {paid}", flush=True)
            except Exception as e:
                print(f"usdt watcher error: {e}", flush=True)
            if _daily_report_due():
                try:
                    digest = report.build_daily_digest(report.gather_stats())
                    if sender.send_telegram({"contact": "me", "text": digest}):
                        store.save("report_last", {"date": time.strftime("%Y-%m-%d")})
                        print("listener: дневная сводка отправлена оператору", flush=True)
                except Exception as e:
                    print(f"daily report error: {e}", flush=True)
        except Exception as e:
            print(f"listener error: {e}", flush=True)
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())