import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from datetime import datetime
box = store.load('outbox', {'items':[]})
sent = [i for i in box['items'] if i.get('sent')]
print(f"отправлено всего: {len(sent)}")
# сортировка по дате отправки (если есть sent_at) иначе created_at
def get_sent_time(i):
    return i.get('sent_at') or i.get('created_at') or ''
sent_sorted = sorted(sent, key=lambda x: get_sent_time(x), reverse=True)
for i in sent_sorted[:20]:
    t = get_sent_time(i)[:16]
    print(f"{t} | {i.get('channel')} | score={i.get('score')} | {i.get('title','')[:60]} | {i.get('url')[:50]}")
# ждем ответа = sent но не в won/paid
print(f"\nждем ответа (sent & not won/paid): {len([i for i in sent if not i.get('skip_reason') in ('paid',)])}")
# покажем CRM sent
import modules.crm as crm
f=crm.funnel()
print(f"\nCRM funnel: {f}")
p=crm.payments()
print(f"payments rows: {len(p.get('rows',[]))}")
for r in p.get('rows',[])[:5]:
    print(r.get('url')[:50], r.get('status'), r.get('payment'))
