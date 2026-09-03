import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get():
    return urllib.request.urlopen("http://127.0.0.1:8765", timeout=8).read().decode("utf-8", errors="replace")


def post(path):
    urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765" + path, data=b"x=1", method="POST"), timeout=8).read()


body = get()
m = re.search(r"Заказы по нашим скиллам \((\d+)\)", body)
print("по умолчанию (только заказы):", m.group(1) if m else "?")

post("/toggle_kind")
body = get()
m = re.search(r"Заказы по нашим скиллам \((\d+)\)", body)
print("после показа вакансий:", m.group(1) if m else "?")

post("/toggle_kind")
body = get()
m = re.search(r"Заказы по нашим скиллам \((\d+)\)", body)
print("обратно (заказы):", m.group(1) if m else "?")