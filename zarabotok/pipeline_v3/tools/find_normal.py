import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from collections import Counter
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
cands = [i for i in items if i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=3 and i.get('skip_reason') not in ('paid','dead','spam','scam-stop','bad')]
print(f'кандидатов score>=3 без скипа: {len(cands)}')
print('по каналам:', dict(Counter(str(i.get('channel')) for i in cands)))
print('по score:', dict(Counter(str(i.get('score')) for i in cands)))
tops = sorted(cands, key=lambda x: x.get('score',0), reverse=True)[:15]
for i in tops:
    title = (i.get('title') or '')[:70].replace('\n',' ')
    url = (i.get('url') or '')[:60]
    contact = str(i.get('contact') or i.get('to') or '-')[:30]
    print(f"score={i.get('score')} ch={i.get('channel')} | {title} | {url} | contact={contact}")

# также черновики с высоким скором не одобренные
drafts = [i for i in items if not i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=4]
print(f"\nчерновиков score>=4 не одобрено: {len(drafts)}")
for i in sorted(drafts, key=lambda x: x.get('score',0), reverse=True)[:10]:
    title = (i.get('title') or '')[:70].replace('\n',' ')
    url = (i.get('url') or '')[:60]
    print(f"score={i.get('score')} ch={i.get('channel')} | {title} | {url}")
