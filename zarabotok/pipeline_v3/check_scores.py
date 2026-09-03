import sys
sys.path.insert(0, '.')

from modules import scanners, ranker, store

jobs, _ = scanners.scan_all(include_tg=False)
print('Total jobs:', len(jobs))

new = ranker.rank_and_store(jobs, min_score=0, contact_only=False)
print('Ranked new:', len(new))

# Check scores
for j in jobs[:10]:
    score = j.get('score')
    platform = j.get('platform')
    title = j.get('title', '')[:50]
    print('  Score:', score, '| Platform:', platform, '|', title)