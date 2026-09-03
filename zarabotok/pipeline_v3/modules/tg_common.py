"""Общие настройки Telegram: api_id/api_hash из config.json + кросс-процессный
лок на сессию (один процесс за раз — иначе Telethon инвалидирует авторизацию)."""
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tg_creds() -> tuple[int, str]:
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    tg = cfg.get("tg", {})
    return int(tg.get("api_id", 0)), tg.get("api_hash", "")


def session_path(session_name: str) -> str:
    """Полный путь к файлу сессии Telethon (приоритет .json.session — рабочая)."""
    state = os.path.join(BASE, "state")
    name = (session_name or "telegram_session_sender").strip()
    pref = os.path.join(state, name + ".json.session")
    if os.path.isfile(pref):
        return pref
    return os.path.join(state, name + ".session")


class tg_lock:
    """Эксклюзивный доступ к TG-сессии между процессами (sender/listener/scanner).

    Windows-only (msvcrt). При таймауте ожидания работает без лока (деградация),
    чтобы система не вставала навсегда из-за зависшего держателя."""

    def __init__(self, timeout_s: float = 120.0):
        import msvcrt
        self._msvcrt = msvcrt
        self.timeout_s = timeout_s
        self.path = os.path.join(BASE, "state", "tg_session.lock")
        self._fh = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._fh = open(self.path, "a+")
        deadline = time.time() + self.timeout_s
        while True:
            try:
                self._fh.seek(0)
                self._msvcrt.locking(self._fh.fileno(), self._msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                if time.time() >= deadline:
                    return self
                time.sleep(0.5)

    def __exit__(self, *exc):
        try:
            self._fh.seek(0)
            self._msvcrt.locking(self._fh.fileno(), self._msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        finally:
            try:
                self._fh.close()
            except Exception:
                pass


def tg_client(session_path_arg=None, proxy=None, session_name: str = "telegram_session_sender"):
    """Клиент под кросс-процессным локом: используй `with tg_lock(): ...` вокруг работы."""
    api_id, api_hash = tg_creds()
    from telethon import TelegramClient

    path = str(session_path_arg or session_path(session_name))
    return TelegramClient(path, api_id, api_hash, proxy=proxy, sequential_updates=True)
