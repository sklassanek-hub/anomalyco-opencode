import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = "http://127.0.0.1:8765"

q = urllib.request.urlopen(base + "/tg_qr", timeout=8).read().decode("utf-8", errors="replace")
if "Сгенерировать QR" in q:
    print("start: кнопка есть, из idle")
else:
    print("start: уже в процессе:", "Жду сканирования" in q)

urllib.request.urlopen(urllib.request.Request(base + "/tg_qr", data=b"x=1", method="POST"), timeout=8).read()
print("POST /tg_qr отправлен")

import time
time.sleep(8)
q = urllib.request.urlopen(base + "/tg_qr", timeout=8).read().decode("utf-8", errors="replace")
has_img = 'src="/tg_qr.png"' in q
print("сканирование:", q.find("Жду сканировани") >= 0, "| QR-картинка:", has_img)
png = urllib.request.urlopen(base + "/tg_qr.png", timeout=8).read()
print("png размер:", len(png))