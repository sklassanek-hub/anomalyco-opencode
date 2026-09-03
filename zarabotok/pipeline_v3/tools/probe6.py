import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from modules import http_client as hc

fr = hc.client("freelance.ru").get("https://freelance.ru/project/search/", timeout=25).text
print("fr /task/view/:", fr.count("/task/view/"))
i = fr.find("/task/view/")
print("fr ctx:", fr[max(0, i - 300) : i + 200] if i >= 0 else "none")

w = hc.client("weworkremotely.com").get("https://weworkremotely.com/remote-jobs/search?term=python", timeout=25).text
print("\nwr remote-jobs/:", w.count('href="/remote-jobs/'))
for m in list(re.finditer(r'href="(/remote-jobs/[^"]+)"', w))[:3]:
    seg = w[max(0, m.start() - 250) : m.end()]
    print("  ctx:", re.sub(r"\s+", " ", seg)[-260:])

try:
    h = hc.client("habr.com").get("https://career.habr.com/api/vacancies?q=telegram", timeout=25)
    print("\nhabr api:", h.status_code, h.text[:200])
except Exception as e:
    print("\nhabr api ERR:", e)