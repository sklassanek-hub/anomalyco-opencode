import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import scanners
from datetime import datetime
print("сканирую FL/FR/WL/WWR + TG...")
jobs, errors = scanners.scan_all(include_tg=True, habr_ids=[])
print(f"найдено всего: {len(jobs)}, ошибок: {len(errors)}")
if errors:
    for e in errors[:10]:
        print("err:", e[:120])
# фильтр простые сайты без тильды/WP
import re
exclude = ['тильд','tilda','вордпрес','wordpress']
include = ['сайт','лендинг','одностранич','визитка','верстк','сделать сайт','создать сайт']
def is_simple(j):
    t = (j.get('title','') + ' ' + j.get('description','')).lower()
    if any(e in t for e in exclude):
        return False
    return any(k in t for k in include)
simple = [j for j in jobs if is_simple(j)]
print(f"простых сайтов без тильды/WP свежих: {len(simple)}")
for j in simple[:15]:
    print(f"[{j['platform']}] {j['title'][:70]} | {j['url']} | {j.get('budget','')}")
# также покажем все TG свежие 24.08
tg = [j for j in jobs if j['platform'].startswith('TG')]
print(f"\nTG всего свежих: {len(tg)}")
for j in tg[:10]:
    print(f"[{j['platform']}] {j['title'][:60]} | contact={j.get('contact')}")
# FL свежие
fl = [j for j in jobs if j['platform']=='FL']
print(f"\nFL свежих: {len(fl)}")
for j in fl[:10]:
    print(f"{j['title'][:70]} | {j['url']}")
