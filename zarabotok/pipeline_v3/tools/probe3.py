import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modules import http_client as hc

s = hc.client("habr.com")
r = s.get('https://career.habr.com/vacancies?q=%22telegram%22&type=all', timeout=25)
txt = r.text
print("habr vacancies/ count:", txt.count("vacancies/"))
for m in re.finditer(r'vacancies/(\d+)', txt):
    start = m.start()
    seg = txt[start - 200 : start + 300]
    clean = re.sub(r"\s+", " ", seg)
    print("---", clean[:420])
    if m.start() > 100000:
        break

f = hc.client("fl.ru")
rf = f.get("https://www.fl.ru/projects/", timeout=25).text
print("\nfl users/ count:", rf.count('"/users/'))
for m in re.finditer(r'href="/users/([^"]+)"', rf):
    print("user:", m.group(1)[:60])
    if m.start() > 200000:
        break