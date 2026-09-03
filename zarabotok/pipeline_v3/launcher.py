"""Zarabotok Launcher: один клик = прокси + все процессы + дашборд в браузере.
Закрытие окна НЕ останавливает систему (работает в фоне), управление: python run.py stop"""
import datetime
import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state")
SINGBOX = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe"
SINGBOX_CFG = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\config.json"
DETACHED = 0x00000008 | 0x08000000

os.makedirs(STATE, exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


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


def ensure_proxy():
    if port_open(4067):
        print("  [ok] прокси sing-box уже работает (127.0.0.1:4067)")
        return True
    try:
        subprocess.Popen([SINGBOX, "run", "-c", SINGBOX_CFG], creationflags=DETACHED, close_fds=True)
        for _ in range(10):
            if port_open(4067):
                print("  [ok] прокси sing-box запущен")
                return True
            time.sleep(1)
        print("  [!!] прокси не поднялся — проверь sing-box")
        return False
    except Exception as e:
        print(f"  [!!] прокси: {e}")
        return False


def ensure_watchdog():
    wp = os.path.join(STATE, "watchdog.pid")
    if os.path.exists(wp):
        try:
            if pid_alive(int(open(wp).read())):
                print("  [ok] система уже запущена")
                return
        except Exception:
            pass
    out = open(os.path.join(STATE, "launcher.out.log"), "a", encoding="utf-8", errors="ignore")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE, "watchdog.py")],
        cwd=BASE, stdout=out, stderr=out,
        creationflags=DETACHED, close_fds=True,
    )
    out.close()
    with open(wp, "w") as f:
        f.write(str(proc.pid))
    print(f"  [ok] watchdog запущен (pid {proc.pid})")


def show_logs():
    print("\n=== ЛОГИ (обновляются каждые 10 сек, Ctrl+C — закрыть окно, система продолжит работу) ===")
    try:
        while True:
            print("\n" + datetime.datetime.now().strftime("%H:%M:%S"))
            ok = True
            for name in ("scanner.py", "orchestrator.py", "dashboard.py"):
                pp = os.path.join(STATE, name + ".pid")
                try:
                    pid = int(open(pp).read())
                    state = "OK" if pid_alive(pid) else "СТОП"
                except Exception:
                    state = "нет"
                print(f"  {name:14s} {state}")
            print(f"  {'socks 4067':14s} {'OK' if port_open(4067) else 'DOWN'}")
            print(f"  {'dashboard':14s} {'http://127.0.0.1:8765 (открыта в браузере)' if port_open(8765) else 'DOWN'}")
            time.sleep(10)
            if not ok:
                break
    except KeyboardInterrupt:
        pass


def main() -> int:
    print("== Zarabotok: запуск всего одной кнопкой ==")
    ensure_proxy()
    ensure_watchdog()
    for _ in range(30):
        if port_open(8765):
            break
        time.sleep(1)
    if port_open(8765):
        print("  [ok] дашборд: http://127.0.0.1:8765")
        if os.environ.get("ZARABOTOK_NO_BROWSER") != "1":
            webbrowser.open("http://127.0.0.1:8765")
    show_logs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())