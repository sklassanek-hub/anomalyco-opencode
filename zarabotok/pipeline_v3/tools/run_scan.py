import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from modules import ranker, scanners, store

jobs, errors = scanners.scan_all(include_tg=True, habr_ids=store.load("habr_ids", {}).get("ids", []))
print("total:", len(jobs), "| errors:", errors)
by_p = {}
for j in jobs:
    by_p[j["platform"]] = by_p.get(j["platform"], 0) + 1
print("по площадкам:", by_p)
new = ranker.rank_and_store(jobs, min_score=1)
print("новых по скиллам:", len(new))
for j in new[:12]:
    print(f"  [{j.get('platform')}] {j['title'][:70]} | {j.get('budget')} | author={j.get('author')} | score={j['score']} | {j.get('description', '')[:60]}")