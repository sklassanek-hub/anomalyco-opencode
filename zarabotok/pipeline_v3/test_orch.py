import sys
sys.path.insert(0, '.')

from modules import store, scanners, ranker, proposals

# Simulate orchestrator
jobs = store.load('jobs', {'items': []}).get('items', [])
today = __import__('time').strftime('%Y-%m-%d')
orders = [j for j in jobs if j.get('scanned_at', '').startswith(__import__('time').strftime('%Y-%m-%d')) and __import__('modules.scanners').kind_of(j) == 'order']
print('Today orders:', len(orders))

# Light score
cfg = {}
with open('config.json', 'r', encoding='utf-8') as f:
    import json
    cfg = json.load(f)
skills = [s for s in (cfg.get('skills') or []) if isinstance(s, str)]

from modules import proposals
for j in orders:
    if not j.get('score'):
        j['score'] = proposals._light_score(j, skills)

# Check scores
for j in orders[:10]:
    print('  Score:', j.get('score'), '|', j.get('title')[:50])

# Build outbox
drafts = proposals.build_outbox(orders[:10], max_revise=0, llm_top_n=3)
print('Drafts:', drafts)

# Check outbox
box = store.load('outbox', {'items': []}).get('items', [])
for o in box[:5]:
    print('  Score:', o.get('score'), '|', o.get('title')[:50])