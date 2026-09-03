"""Watchdog v3: держит живыми scanner/orchestrator/sender/listener, авторестарт при падении."""
import datetime
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state")
PID_FILE = os.path.join(STATE, "watchdog.pid")
DETACHED = 0x00000008 | 0x08000000

WORKERS = ("scanner.py", "orchestrator.py", "sender.py", "listener.py", "exec_worker.py", "dashboard.py", "api.py")

sys.path.insert(0, BASE)
from modules import store  # noqa: E402
from modules.report import build_daily_digest, gather_stats  # noqa: E402
try:
    from modules import voice  # noqa: E402
    _VOICE_OK = True
except Exception:
    _VOICE_OK = False


def _voice_bg(event_type: str, message: str, details: str = ""):
    """Неблокирующий вызов голосового уведомления (thread)."""
    if not _VOICE_OK:
        return
    try:
        import threading
        def _run():
            try:
                voice.announce_event({
                    "type": event_type,
                    "message": message,
                    "details": details,
                })
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
    except Exception:
        pass


def log(msg):
    line = f"{datetime.datetime.now().isoformat()} watchdog: {msg}"
    print(line, flush=True)
    with open(os.path.join(STATE, "watchdog.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def alive(pid_path: str) -> bool:
    try:
        with open(pid_path, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError, FileNotFoundError):
        return False
    return pid_alive(pid)


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_worker(name: str):
    out = open(os.path.join(STATE, name + ".out.log"), "a", encoding="utf-8", errors="ignore")
    err = open(os.path.join(STATE, name + ".err.log"), "a", encoding="utf-8", errors="ignore")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE, "workers", name)],
        cwd=BASE,
        stdout=out,
        stderr=err,
        creationflags=DETACHED,
        close_fds=True,
    )
    out.close()
    err.close()
    with open(os.path.join(STATE, name + ".pid"), "w", encoding="utf-8") as f:
        f.write(str(proc.pid))
    log(f"стартовал {name} (pid {proc.pid})")


def _maybe_send_daily_digest():
    """F2: доставка сводки в TG-туннель (09:00 MSK) — один раз в сутки."""
    try:
        import datetime as _dt
        now = _dt.datetime.now()
        if now.hour != 9 or now.minute > 15:
            return
        last = store.load("report_last", {}).get("date", "")
        today = now.strftime("%Y-%m-%d")
        if last == today:
            return
        digest = build_daily_digest(gather_stats())
        # пробуем отправить в TG (saved messages)
        try:
            from modules import sender
            if sender.send_telegram({"contact": "me", "text": digest}):
                log("ежедневная сводка отправлена в TG")
            else:
                log("ежедневная сводка: не удалось отправить в TG")
        except Exception as e:
            log(f"ежедневная сводка ошибка: {e}")
        store.save("report_last", {"date": today})
    except Exception as e:
        log(f"daily digest error: {e}")


def _check_tunnel():
    """H2: диагностика TG-туннеля / socks — пишет events при проблемах."""
    try:
        import socket
        socks_open = False
        try:
            with socket.create_connection(("127.0.0.1", 4067), timeout=2):
                socks_open = True
        except OSError:
            socks_open = False
        if not socks_open:
            store.append("events", {
                "severity": "warning",
                "source": "watchdog/tunnel",
                "text": "SOCKS 127.0.0.1:4067 закрыт — TG через прокси недоступен, fallback на прямой IP",
            }, key="items")
        # проверка LM Studio
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=3) as r:
                _json.load(r)
        except Exception:
            store.append("events", {
                "severity": "warning",
                "source": "watchdog/lmstudio",
                "text": "LM Studio 127.0.0.1:1234 не отвечает — LLM-генерация остановлена",
            }, key="items")
    except Exception:
        pass


def main() -> int:
    os.makedirs(STATE, exist_ok=True)
    # Защита от дублирования: если watchdog уже запущен — выходим
    if os.path.exists(PID_FILE):
        try:
            existing_pid = int(open(PID_FILE, encoding="utf-8").read().strip())
            if pid_alive(existing_pid) and existing_pid != os.getpid():
                log(f"watchdog уже запущен (pid {existing_pid}), дублирование предотвращено — выход")
                return 1
        except (ValueError, OSError):
            pass
    # Пишем свой pid-файл (без .py в имени)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    log("watchdog v3 запущен (F2 daily digest + H2 tunnel diagnostics активны)")
    _tick = 0
    while True:
        down = []
        alive_n = 0
        for name in WORKERS:
            pid_path = os.path.join(STATE, name + ".pid")
            if not alive(pid_path):
                # Не запускаем новых воркеров при активном kill switch
                kill_path = os.path.join(STATE, "KILL_SWITCH")
                kill_state_path = os.path.join(STATE, "kill_switch_active.json")
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
                    log(f"kill switch active — пропуск запуска {name}")
                    _voice_bg("kill_switch", f"Kill Switch активен — пропуск запуска воркера {name}", "Ой-вей, это серьёзно!")
                    continue
                down.append(name)
                start_worker(name)
            else:
                alive_n += 1
        storage = store.storage_info()
        store.append("metrics", {
            "ts": store.now(),
            "workers_alive": alive_n,
            "workers_total": len(WORKERS),
            "storage": storage,
        }, key="items")
        if down:
            store.append("events", {
                "severity": "warning",
                "source": "watchdog",
                "text": "воркеры неактивны, перезапущены: " + ", ".join(down),
            }, key="items")
            _voice_bg("pipeline_error", f"Воркеры неактивны, перезапущены: {', '.join(down)}", "Ой-вей, это серьёзно!")
        if not storage.get("ok"):
            storage_text = f"хранилище недоступно: {storage.get('mode')} {storage.get('error') or ''}".strip()
            store.append("events", {
                "severity": "warning",
                "source": "watchdog",
                "text": storage_text,
            }, key="items")
            _voice_bg("pipeline_error", storage_text, "Ой-вей, это серьёзно!")
        _tick += 1
        if _tick % 3 == 0:
            _check_tunnel()
        _maybe_send_daily_digest()
        # Голосовое уведомление о сводке (фоново)
        try:
            if _VOICE_OK:
                import threading
                def _digest_voice():
                    try:
                        # Краткий текст для голоса
                        voice.announce_event({
                            "type": "daily_digest",
                            "message": "Ежедневная сводка готова! Проверь состояние конвейера.",
                            "details": "Storytime: сегодня всё работает как нужно.",
                        })
                    except Exception:
                        pass
                threading.Thread(target=_digest_voice, daemon=True).start()
        except Exception:
            pass
        # E2: авто-проверка оплат (ЮMoney по label, USDT по сумме)
        try:
            from modules import billing as _billing
            if _billing.check_yoomoney_payments():
                log("ЮMoney: платёж подтверждён по label")
                _voice_bg("payment", "ЮMoney: платёж подтверждён! Ура, деньги на месте!", "Storytime: оплата прошла успешно.")
            if _billing.check_usdt_payments():
                log("USDT: платёж подтверждён")
                _voice_bg("payment", "USDT: платёж подтверждён! Ура, деньги на месте!", "Storytime: крипто-оплата прошла успешно.")
        except Exception as e:
            log(f"payment watcher error: {e}")
            _voice_bg("pipeline_error", f"Ошибка проверки оплат: {e}", "Ой-вей, это серьёзно!")
        time.sleep(20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())