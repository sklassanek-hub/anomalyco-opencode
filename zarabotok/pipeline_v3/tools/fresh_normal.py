import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from datetime import datetime
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
# кандидаты нормальные
cands = [i for i in items if i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=3 and i.get('skip_reason') not in ('paid','dead','spam','scam-stop','bad')]
# сортировка по дате свежести (created_at) + score
def dt_key(i):
    try:
        return datetime.fromisoformat(i.get('created_at','').split('+')[0])
    except:
        return datetime.min
cands_sorted = sorted(cands, key=lambda x: (dt_key(x), x.get('score',0)), reverse=True)
print(f"нормальных одобрено: {len(cands)} (из них FL/manual 52)")
for i in cands_sorted[:15]:
    d = i.get('created_at','')[:10]
    print(f"{d} score={i.get('score')} | {i.get('title','')[:65]} | {i.get('url')[:50]}")
# TG свежие среди всех
tg_all = [i for i in items if str(i.get('channel')).lower()=='tg']
tg_fresh = sorted([i for i in tg_all if i.get('created_at','')[:10] >= '2026-08-19'], key=lambda x: x.get('created_at'), reverse=True)
print(f"\nTG свежих с 19.08: {len(tg_fresh)}")
for i in tg_fresh[:10]:
    print(f"{i.get('created_at')[:16]} score={i.get('score')} sent={i.get('sent')} skip={i.get('skip_reason')} | {i.get('title','')[:55]}")
