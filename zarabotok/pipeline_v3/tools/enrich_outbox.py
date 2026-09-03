"""Разовый прогон: проставить черновикам контакты (tg/email) и score из заказов по url."""
import sys

sys.path.insert(0, ".")

from modules import proposals, store  # noqa: E402

jobs = store.load("jobs", {"items": []}).get("items", [])
by_url = {j.get("url"): j for j in jobs}
box = store.load("outbox", {"items": []})
items = box.get("items", [])
upd = 0
for i in items:
    j = by_url.get(i.get("url"))
    if not j:
        continue
    c = proposals.extract_contacts(j)
    ch_old = i.get("channel")
    i["channel"] = c["channel"]
    i["contact"] = c["contact"]
    i["to"] = c["to"]
    i["score"] = j.get("score", i.get("score", 0))
    if c["channel"] != ch_old:
        upd += 1
store.save("outbox", {"items": items})
print(f"обновлено контактов: {upd} из {len(items)}")
from collections import Counter
print(Counter(i.get("channel") for i in items))
