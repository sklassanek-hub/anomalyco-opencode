import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from modules import http_client as hc

w = hc.client("weworkremotely.com").get("https://weworkremotely.com/remote-jobs/search?term=python", timeout=25).text
for m in list(re.finditer(r'<li class="[^"]*new-listing[^"]*"', w))[:3]:
    seg = w[m.start() : m.start() + 1800]
    links = re.findall(r'href="([^"]+)"', seg)
    print("LINKS:", links[:8])
    i = seg.find("aria-label")
    print("ARIA:", re.sub(r"\s+", " ", seg[i - 120 : i + 260]) if i >= 0 else "none")
    print("---")