import sys
sys.path.insert(0, '.')

from modules import store, scanners as sc

orders = [j for j in store.load('jobs', {'items': []}).get('items', [])
          if j.get('scanned_at', '').startswith(__import__('time').strftime('%Y-%m-%d'))
          and sc.kind_of(j) == 'order']

print('Today orders:', len(orders))

orders.sort(key=lambda x: x.get('score', 0), reverse=True)
fresh = orders[:10]

print('Top 10 fresh:')
from modules import proposals as p
for f in fresh:
    c = p.extract_contacts(f)
    print('Score:', f.get('score'), '| Contact:', c.get('channel'), '|', f.get('title')[:50])

drafts = __import__('modules.proposals', fromlist=['build_outbox']).build_outbox(fresh, max_revise=0, llm_top_n=0)
print('Drafts created:', drafts)

box = __import__('modules.store', fromlist=['load']).load('outbox', {'items': []}).get('items', [])
print('Outbox total:', len(box))
for o in box[-5:]:
    print('  Platform:', o.get('platform', 'NONE'), '| Title:', o.get('title', '')[:50])