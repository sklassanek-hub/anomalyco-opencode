import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from datetime import datetime
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
# простые сайт-заказы: ключевые слова
import re
keywords = ['сайт','лендинг','одностраничник','визитка','тильда','tilda','wordpress','вордпресс','верстк','landing']
def is_simple_site(i):
    t = (i.get('title') or '') + ' ' + (i.get('description') or '')
    tl = t.lower()
    return any(k in tl for k in keywords)
# фильтр: простые сайты, score>=2, не paid/dead/spam, не отправлено, свежие 18-21.08
cands = [i for i in items if is_simple_site(i) and (i.get('score') or 0)>=2 and not i.get('sent') and i.get('skip_reason') not in ('paid','dead','spam','scam-stop')]
# отсортировать по свежести + score
def dt(i):
    try: return datetime.fromisoformat(i.get('created_at','').split('+')[0])
    except: return datetime.min
cands = sorted(cands, key=lambda x: (dt(x), x.get('score',0)), reverse=True)
print(f"простых сайтов всего: {len(cands)} (среди них одобрено {len([i for i in cands if i.get('approved')])})")
for i in cands[:20]:
    d = i.get('created_at','')[:10]
    appr = '✓' if i.get('approved') else '·'
    print(f"{d} score={i.get('score')} approved={appr} | {i.get('title','')[:65]} | {i.get('url')[:55]} | {str(i.get('budget') or '')[:15]}")
# также покажем не одобренные но score>=3
draft_sites = [i for i in cands if not i.get('approved') and (i.get('score') or 0)>=3]
print(f"\nчерновиков-простых сайтов score>=3: {len(draft_sites)}")
for i in draft_sites[:10]:
    print(f"score={i.get('score')} | {i.get('title','')[:65]} | {i.get('url')[:55]}")
