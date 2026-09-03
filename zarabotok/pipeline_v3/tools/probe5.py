import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from modules import http_client as hc

f = hc.client("fl.ru")
rf = f.get("https://www.fl.ru/projects/", timeout=25).text
for marker in ("b-post__grid position-relative", "b-post__grid", 'class="b-post d-flex'):
    print(f"fl [{marker}]:", rf.count(marker))
m = re.search(r'<section[^>]*class="[^"]*b-post[^"]*"[^>]*>', rf)
print("post section:", rf[m.start() : m.start() + 400] if m else "none")

fr = hc.client("freelance.ru").get("https://freelance.ru/project/search/", timeout=25).text
for marker in ("task-title", "task-list", "task_view", "task-view", "project-item"):
    print(f"fr [{marker}]:", fr.count(marker))
i = fr.find("task")
print("fr task context:", fr[max(0, i - 120) : i + 320] if i >= 0 else "none")

h = hc.client("habr.com").get("https://career.habr.com/vacancies/1000167599", timeout=25).text
for marker in ("<h1", "vacancy-title", "vacancy-header__title"):
    i = h.find(marker)
    print(f"habr [{marker}]:", (re.sub(r"\s+", " ", h[i:i + 260]) if i >= 0 else "none"))

w = hc.client("weworkremotely.com").get("https://weworkremotely.com/remote-jobs/search?term=python", timeout=25).text
i = w.find("new-listing")
print("wr new-listing ctx:", w[i - 80 : i + 400] if i >= 0 else "none")