import sys
sys.path.insert(0, '.')

from modules import proposals, store, scanners, ranker

store.save('outbox', {'items': []})
jobs, _ = scanners.scan_all(include_tg=False)
new = ranker.rank_and_store(jobs, min_score=0, contact_only=False)
drafts = proposals.build_outbox(jobs, max_revise=0, llm_top_n=0)
print('Drafts created:', drafts)

box = store.load('outbox', {'items': []}).get('items', [])
print('Outbox total:', len(box))

from collections import Counter
cnt = Counter(o.get('platform', 'NONE') for o in box)
print('Platforms:', dict(cnt))