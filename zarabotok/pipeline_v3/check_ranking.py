import sys
sys.path.insert(0, '.')

from modules import scanners, ranker, store

# Test ranking
jobs, _ = scanners.scan_all(include_tg=False)
print('Before ranker:')
for j in jobs[:5]:
    print('  Score:', j.get('score'), '| Platform:', j.get('platform'), '|', j.get('title')[:50])

# Run ranker
new = ranker.rank_and_store(jobs, min_score=1, contact_only=False)
print('Ranked new:', len(new))

# Check scores after
for j in jobs[:5]:
    print('  Score:', j.get('score'), '| Platform:', j.get('platform'), '|', j.get('title')[:50])

# Check DB
jobs_db = store.load('jobs', {'items': []}).get('items', [])
with_score = [j for j in jobs_db if j.get('score') is not None]
print('DB jobs with score:', len(with_score))