import sys
sys.path.insert(0, '.')

from modules import proposals as p, store, scanners, ranker

store.save('outbox', {'items': []})
jobs, _ = scanners.scan_all(include_tg=False)
drafts = p.build_outbox(jobs, max_revise=0, llm_top_n=0)
print('Drafts created:', drafts)

box = store.load('outbox', {'items': []}).get('items', [])
print('Outbox total:', len(box))

from collections import Counter
cnt = Counter(o.get('platform', 'NONE') for o in box)
print('Platforms:', dict(cnt))

# Check budgets
for o in box[:20]:
    b = o.get('budget', '')
    print('  Budget:', b, '|', o.get('title')[:60])