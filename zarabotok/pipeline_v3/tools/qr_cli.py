"""CLI-генератор QR для авторизации Telegram. Запускается фоном; результат:
state/qr.png (картинка) + state/qr_status.txt (статус). Использование: python tools/qr_cli.py <session>"""
import asyncio
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from modules import tg_auth  # noqa: E402

STATE = os.path.join(BASE, "state")


def _dbg(msg: str) -> None:
    try:
        with open(os.path.join(STATE, "qr_dbg.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _on_qr(png: bytes) -> None:
    with open(os.path.join(STATE, "qr.png"), "wb") as f:
        f.write(png)
    with open(os.path.join(STATE, "qr_status.txt"), "w", encoding="utf-8") as f:
        f.write("Жду сканирования (QR живёт ~2 минуты)")
    _dbg("png записан")


def main() -> int:
    session = sys.argv[1] if len(sys.argv) > 1 else "telegram_session_sender"
    _dbg(f"start session={session}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status, png = loop.run_until_complete(tg_auth.qr_login(session, timeout=150, on_qr=_on_qr))
    loop.close()
    _dbg(f"done status={status[:100]}")
    if not os.path.exists(os.path.join(STATE, "qr.png")) and png:
        with open(os.path.join(STATE, "qr.png"), "wb") as f:
            f.write(png)
    with open(os.path.join(STATE, "qr_status.txt"), "w", encoding="utf-8") as f:
        f.write(status)
    print(status[:200], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())