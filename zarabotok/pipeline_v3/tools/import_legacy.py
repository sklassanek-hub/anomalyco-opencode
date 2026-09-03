"""Одноразовый импорт старой базы v2 в state v3: переписка (threads), заказы-архив (scanner_seen),
контракты, очередь откликов. Запуск: python tools/import_legacy.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from modules import store  # noqa: E402

LEGACY = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\state"

threads = store.load("threads", {"threads": []})
existing = {t.get("key") for t in threads["threads"]}
n_threads = 0
with open(os.path.join(LEGACY, "threads.json"), encoding="utf-8") as f:
    old = json.load(f)
for job_id, rec in old.items():
    for ev in rec.get("events", []):
        key = f"{job_id}|{ev.get('ts')}|{ev.get('kind')}"
        if key in existing:
            continue
        threads["threads"].append({
            "key": key,
            "from": job_id,
            "actor": ev.get("actor", ""),
            "kind": ev.get("kind", ""),
            "ts": ev.get("ts", ""),
            "text": ev.get("text", "")[:2000],
        })
        n_threads += 1
store.save("threads", threads)
print(f"threads: +{n_threads} (всего {len(threads['threads'])})")

habr_ids = []
with open(os.path.join(LEGACY, "scanner_seen.json"), encoding="utf-8") as f:
    seen = json.load(f).get("ids", [])
for s in seen:
    if s.startswith("habr_career:"):
        habr_ids.append(s.split(":", 1)[1])
print(f"habr ids из архива: {len(habr_ids)}")

archive = store.load("archive_jobs", {"items": []})
by_url = {j["job_id"] for j in archive["items"]}
n_arc = 0
for s in seen:
    if s in by_url or ":" not in s:
        continue
    plat, jid = s.split(":", 1)
    url = {"habr_career": f"https://career.habr.com/vacancies/{jid}"}.get(plat) or f"https://t.me/s/{jid}"
    archive["items"].append({"job_id": s, "platform": plat, "url": url, "title": jid[:90], "archive": True})
    n_arc += 1
store.save("archive_jobs", archive)
print(f"архив заказов: +{n_arc} (всего {len(archive['items'])})")

contracts = store.load("contracts", {"contracts": []})
existing_c = {c.get("job_id") for c in contracts["contracts"]}
n_c = 0
with open(os.path.join(LEGACY, "contracts.json"), encoding="utf-8") as f:
    old_c = json.load(f).get("contracts", [])
for c in old_c:
    if c.get("job_id") in existing_c:
        continue
    contracts["contracts"].append(c)
    n_c += 1
store.save("contracts", contracts)
print(f"контракты: +{n_c} (всего {len(contracts['contracts'])})")

with open(os.path.join(LEGACY, "proposals_to_send.json"), encoding="utf-8") as f:
    old_p = json.load(f).get("items", [])
box = store.load("outbox", {"items": []})
have = {i["url"] for i in box["items"]}
n_p = 0
for p in old_p:
    url = p.get("job_url", "")
    if not url or url in have:
        continue
    box["items"].append({
        "url": url,
        "title": p.get("title", "")[:100],
        "text": f"Черновик из старой базы: {p.get('title', '')[:300]}",
        "channel": "manual",
        "approved": False,
        "sent": False,
        "created_at": p.get("created_at", ""),
        "legacy": True,
    })
    n_p += 1
store.save("outbox", box)
print(f"старые отклики: +{n_p}")

store.save("habr_ids", {"ids": habr_ids})
print("готово; habr_ids сохранён в state/habr_ids.json")