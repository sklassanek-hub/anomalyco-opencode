import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from datetime import datetime, timedelta
import json
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
# посмотрим ключи первого элемента
if items:
    print('keys sample:', list(items[0].keys())[:30])
    for i in items[:3]:
        print('---', i.get('url')[:50])
        for k in ('ts','created_at','published','date','first_seen','updated_at','score','channel','approved','sent','skip_reason'):
            if k in i:
                print(k, ':', i.get(k))
# найдем свежие: по ts или published
now = datetime.now()
def parse_ts(s):
    if not s: return None
    try:
        # формат 2026-08-24T...
        return datetime.fromisoformat(s.replace('Z','+00:00').split('+')[0])
    except: return None

fresh = []
for i in items:
    ts = i.get('ts') or i.get('created_at') or i.get('published') or i.get('date')
    dt = parse_ts(str(ts)) if ts else None
    if dt and (now - dt).days <= 2:
        fresh.append((dt,i))

print(f"\nсвежих (2 дня) всего: {len(fresh)}")
# фильтр нормальных свежих
cands = [ (dt,i) for dt,i in fresh if i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=3 and i.get('skip_reason') not in ('paid','dead','spam','scam-stop','bad')]
print(f"свежих нормальных score>=3 без скипа: {len(cands)}")
for dt,i in sorted(cands, key=lambda x: x[0], reverse=True)[:15]:
    print(dt.strftime('%m-%d %H:%M'), f"score={i.get('score')} ch={i.get('channel')} | {i.get('title','')[:60]} | {i.get('url')[:50]}")
# также покажем все свежие одобренные без фильтра скипа
all_fresh_approved = [ (dt,i) for dt,i in fresh if i.get('approved') and not i.get('sent')]
print(f"\nвсе свежие approved&not sent: {len(all_fresh_approved)}")
for dt,i in sorted(all_fresh_approved, key=lambda x: x[0], reverse=True)[:15]:
    print(dt.strftime('%m-%d %H:%M'), f"score={i.get('score')} skip={i.get('skip_reason')} | {i.get('title','')[:50]} | {i.get('url')[:45]}")
