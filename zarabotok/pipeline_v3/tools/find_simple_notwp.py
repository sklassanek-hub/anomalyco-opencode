import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from datetime import datetime
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
exclude = ['тильд','tilda','вордпрес','wordpress','wp','wordpress']
include = ['сайт','лендинг','одностранич','визитка','верстк','сделать сайт','создать сайт','разработать сайт','натяжк','html']
def is_site(i):
    t = ((i.get('title') or '') + ' ' + (i.get('description') or '')).lower()
    if any(e in t for e in exclude):
        return False
    return any(k in t for k in include)

cands = [i for i in items if is_site(i) and (i.get('score') or 0)>=2 and not i.get('sent') and i.get('skip_reason') not in ('paid','dead','spam','scam-stop')]
cands = sorted(cands, key=lambda x: (x.get('created_at') or '', x.get('score',0)), reverse=True)
print(f"простых сайтов без тильды/WP: {len(cands)} (одобрено {len([i for i in cands if i.get('approved')])})")
for i in cands[:20]:
    d = (i.get('created_at') or '')[:10]
    appr = '✓' if i.get('approved') else '·'
    print(f"{d} score={i.get('score')} {appr} | {i.get('title','')[:70]} | {i.get('url')[:55]}")
# также покажем что отфильтровали
all_sites = [i for i in items if any(k in ((i.get('title') or '') + ' ' + (i.get('description') or '')).lower() for k in include)]
excluded = [i for i in all_sites if any(e in ((i.get('title') or '') + ' ' + (i.get('description') or '')).lower() for e in exclude)]
print(f"\nисключено тильда/WP: {len(excluded)}")
