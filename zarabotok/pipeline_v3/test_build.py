import sys
sys.path.insert(0, '.')

from modules import scanners, ranker, proposals, store

jobs, errs = scanners.scan_all(include_tg=False)
print('Total jobs:', len(jobs))
print('Errors:', errs)

from collections import Counter
cnt = Counter(j.get('platform', '?') for j in jobs)
for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
    print('  {}: {}'.format(k, v))

import time
today = time.strftime('%Y-%m-%d')
orders = [j for j in jobs if j.get('scanned_at', '').startswith(today) and scanners.kind_of(j) == 'order']
print('Today orders:', len(orders))
for o in orders[:5]:
    print('  {} | Platform: {}'.format(o.get('title', '')[:60], o.get('platform', 'NONE')))

drafts = proposals.build_outbox(jobs[:20], max_revise=0, llm_top_n=0)
print('Drafts created:', drafts)

box = store.load('outbox', {'items': []}).get('items', [])
print('Outbox total:', len(box))
for o in box[-5:]:
    print('  Platform: {} | Title: {}'.format(o.get('platform', 'NONE'), o.get('title', '')[:50]))