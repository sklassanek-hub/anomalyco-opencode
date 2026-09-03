import os
import socket

import requests
import socks as sockslib

PROXY = {"http": "socks5h://127.0.0.1:4067", "https": "socks5h://127.0.0.1:4067"}

DIRECT_DOMAINS = ("fl.ru", "freelance.ru", "kwork.ru", "weblancer.net", "habr.com",
                  "vk.com", "userapi.com", "ok.ru")


def enabled() -> bool:
    return os.environ.get("NO_PROXY_APP", "") != "1"


def _proxy_alive(host: str = "127.0.0.1", port: int = 4067, timeout: float = 0.4) -> bool:
    """Быстрая проверка: слушает ли локальный SOCKS-прокси. Если нет — работаем напрямую."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
    except Exception:
        return False


def client(domain: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    })
    direct = any(domain.endswith(d) for d in DIRECT_DOMAINS)
    if not direct and enabled() and _proxy_alive():
        s.proxies.update(PROXY)
    return s


def socks_args():
    """Формат Telethon: dict с ключами addr/port (proxy_type — PySocks-константа).
    Если прокси недоступен — None (Telethon пойдёт напрямую)."""
    if not enabled() or not _proxy_alive():
        return None
    return {"proxy_type": sockslib.SOCKS5, "addr": "127.0.0.1", "port": 4067}