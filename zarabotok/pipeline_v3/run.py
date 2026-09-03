"""Zarabotok CLI — единое управление конвейером:
python run.py {start|stop|restart|status|funnel|box|logs|probe}"""
import datetime
import json
import os
import socket
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state")
SINGBOX = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe"
SINGBOX_CFG = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\config.json"
DETACHED = 0x00000008 | 0x08000000
WORKERS = ("scanner.py", "orchestrator.py", "sender.py", "listener.py", "exec_worker.py", "dashboard.py", "api.py")

HELP = """Использование: python run.py <команда>

  start     запустить прокси + watchdog (поднимет всех воркеров)
  stop      остановить всех воркеров и watchdog
  restart   перезапустить всех воркеров (watchdog сам поднимет)
  status    статус воркеров + прокси + дашборд
  funnel    воронка: заказы → черновики → одобрено → отправлено → выиграно → оплачено
  box       очередь откликов (одобрённые ждут отправки)
  logs      хвосты логов воркеров (5 мин опроса)
  probe     пробный скан всех источников
"""


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def proxy_up() -> bool:
    if port_open(4067):
        return True
    try:
        subprocess.Popen(
            [SINGBOX, "run", "-c", SINGBOX_CFG],
            creationflags=DETACHED,
            close_fds=True,
        )
        return True
    except Exception as e:
        print(f"sing-box: {e}")
        return False


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
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


def _pid_path(name: str) -> str:
    """pid-файлы: воркеры пишут state/<имя>.py.pid, watchdog — state/watchdog.pid."""
    if name == "watchdog":
        return os.path.join(STATE, "watchdog.pid")
    stem = name[:-3] if name.endswith(".py") else name
    return os.path.join(STATE, stem + ".py.pid")


def _kill_pid(name: str):
    path = _pid_path(name)
    try:
        pid = int(open(path).read().strip())
    except Exception:
        return
    if pid_alive(pid):
        try:
            os.kill(pid, 9)
            print(f"{name}: остановлен ({pid})")
        except OSError:
            pass
    try:
        os.remove(path)
    except OSError:
        pass


def start() -> int:
    os.makedirs(STATE, exist_ok=True)
    print("sing-box:", "ok (127.0.0.1:4067)" if proxy_up() else "FAIL")
    pid_path = _pid_path("watchdog")
    if os.path.exists(pid_path):
        try:
            if pid_alive(int(open(pid_path).read().strip())):
                print("watchdog уже запущен")
                return 0
        except Exception:
            pass
    out = open(os.path.join(STATE, "watchdog.out.log"), "a", encoding="utf-8", errors="ignore")
    err = open(os.path.join(STATE, "watchdog.err.log"), "a", encoding="utf-8", errors="ignore")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE, "watchdog.py")],
        cwd=BASE, stdout=out, stderr=err,
        creationflags=DETACHED, close_fds=True,
    )
    out.close()
    err.close()
    with open(pid_path, "w") as f:
        f.write(str(proc.pid))
    print(f"watchdog запущен (pid {proc.pid}); дашборд: http://127.0.0.1:8765")
    return 0


def stop() -> int:
    for name in WORKERS:
        _kill_pid(name)
    _kill_pid("watchdog")
    return 0


def restart() -> int:
    for name in WORKERS:
        _kill_pid(name)
    print("воркеры остановлены — watchdog поднимет их заново в течение 20с")
    return 0


def status() -> int:
    print(datetime.datetime.now().isoformat())
    for name in WORKERS + ("watchdog",):
        try:
            pid = int(open(_pid_path(name)).read().strip())
            state = f"работает (pid {pid})" if pid_alive(pid) else "ОСТАНОВЛЕН"
        except Exception:
            state = "ОСТАНОВЛЕН"
        print(f"{name:16s} {state}")
    print(f"{'socks 4067':16s} {'OK' if port_open(4067) else 'DOWN'}")
    print(f"{'dashboard 8765':16s} {'OK' if port_open(8765) else 'DOWN'}")
    print(f"{'api 8766':16s} {'OK' if port_open(8766) else 'DOWN'}")
    return 0


def funnel() -> int:
    sys.path.insert(0, BASE)
    from modules import crm, store

    box = store.load("outbox", {"items": []}).get("items", [])
    f = crm.funnel()
    items_sent = sum(1 for i in box if i.get("sent"))
    items_appr = sum(1 for i in box if i.get("approved") and not i.get("sent"))
    fl = [i for i in box if "fl.ru" in i.get("url", "")]
    t = datetime.datetime.now().strftime("%H:%M")
    print(f"[{t}] очередь: черновиков {len(box)} · одобрено {items_appr} · отправлено {items_sent} · FL всего {len(fl)}")
    print("воронка CRM:", " → ".join(f"{k}={v}" for k, v in f.items()))
    paid = f.get("paid", 0)
    print(f"оплачено заказов: {paid}")
    return 0


def box() -> int:
    sys.path.insert(0, BASE)
    from modules import store

    outbox = store.load("outbox", {"items": []}).get("items", [])
    jobs = store.load("jobs", {"items": []}).get("items", [])
    pending = [x for x in outbox if x.get("approved") and not x.get("sent")]
    print(f"jobs: {len(jobs)} | outbox: {len(outbox)} | одобрено к отправке: {len(pending)}")
    for i in pending[:15]:
        mark = "APPROVED" if i["approved"] else "draft"
        print(f"  [{mark}] {i['url']} :: {(i.get('text') or '')[:100]}")
    return 0


def logs() -> int:
    import time as _t

    names = WORKERS + ("watchdog",)
    seq = {}
    for _ in range(3):
        for name in names:
            path = os.path.join(STATE, name + ".out.log")
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            new = lines[seq.get(name, len(lines) - 1):]
            seq[name] = len(lines)
            for ln in new[-3:]:
                print(f"[{name:12s}] {ln[:150]}")
        _t.sleep(2)
    return 0


def probe() -> int:
    sys.path.insert(0, BASE)
    from modules import scanners

    jobs, errors = scanners.scan_all(include_tg=True)
    print(f"total={len(jobs)} errors={errors}")
    for j in jobs[:15]:
        print(f"  {j['source']}: {j['title'][:90]} [{j['budget']}]")
    return 0


CMDS = {"start": start, "stop": stop, "restart": restart, "status": status,
        "funnel": funnel, "box": box, "logs": logs, "probe": probe}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd not in CMDS:
        print(HELP)
        raise SystemExit(1)
    raise SystemExit(CMDS[cmd]())