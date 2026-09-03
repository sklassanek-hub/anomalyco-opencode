import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from modules import tg_auth

status, png = asyncio.run(tg_auth.qr_login("telegram_session_sender", timeout=10))
print("status:", status[:200])
print("png bytes:", len(png))