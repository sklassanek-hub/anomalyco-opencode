import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modules import http_client as hc

s = hc.client("habr.com")
r = s.get("https://career.habr.com/vacancies/1000168036", timeout=25)
print("habr detail:", r.status_code, len(r.text))
for needle in ("vacancy_title", "salary", "1000168036", "company"):
    i = r.text.find(needle)
    if i >= 0:
        seg = re.sub(r"\s+", " ", r.text[i - 60 : i + 220])
        print(f"  ['{needle}'] {seg[:260]}")
    else:
        print(f"  ['{needle}'] NOT FOUND")

f = hc.client("fl.ru")
rf = f.get("https://www.fl.ru/projects/5518032/?", timeout=25).text
print("\nfl detail:", len(rf))
for needle in ('href="/users/', "b-post__body", "b-post__price"):
    i = rf.find(needle)
    if i >= 0:
        seg = re.sub(r"\s+", " ", rf[i - 40 : i + 160])
        print(f"  ['{needle}'] {seg[:200]}")
    else:
        print(f"  ['{needle}'] NOT FOUND")

w = hc.client("weworkremotely.com")
rw = w.get("https://weworkremotely.com/remote-jobs/search?term=python", timeout=25).text
print("\nweworkremotely len:", len(rw), "| 'new-listing':", rw.count("new-listing"))
for m in list(re.finditer(r'<li class="new-listing[^"]*">\s*<a href="([^"]+)"[^>]*>\s*(?:<h2>([^<]+)</h2>|<span class="title">([^<]+)</span>)', rw))[:2] + list(re.finditer(r'<span class="title">([^<]+)</span>', rw))[:2]:
    print("  match:", m.groups()[:2])