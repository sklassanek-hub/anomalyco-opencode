import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
box = store.load('outbox', {'items':[]})
cands = []
for i in box['items']:
    if i.get('sent') or i.get('skip_reason') in ('paid','dead','spam','scam-stop','bad'):
        continue
    if (i.get('score') or 0) <2:
        continue
    if not (i.get('contact') or i.get('to')):
        continue
    t = (i.get('title','') + ' ' + i.get('description','')).lower()
    if any(x in t for x in ['тильд','tilda','вордпрес','wordpress']):
        continue
    # любой заказ с контактом, но приоритет сайт
    is_site = any(k in t for k in ['сайт','лендинг','одностранич','визитка','верстк'])
    cands.append((is_site, i))

# сортировка: сначала сайты, потом score
cands_sorted = sorted(cands, key=lambda x: (x[0], x[1].get('score',0)), reverse=True)
print(f"с контактами простых и не только: {len(cands_sorted)}")
for is_site, i in cands_sorted[:15]:
    print(f"{'SITE' if is_site else '    '} score={i.get('score')} ch={i.get('channel')} contact={i.get('contact') or i.get('to')} | {i.get('title','')[:60]} | {i.get('url')[:50]} | {i.get('created_at','')[:10]}")
