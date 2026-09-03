import sys
sys.path.insert(0, '.')

from modules import scanners, ranker, store, proposals as p

# 1. Сканируем и ранжируем БЕЗ фильтра contact_only
jobs, _ = scanners.scan_all(include_tg=False)
new = ranker.rank_and_store(jobs, min_score=1, contact_only=False)
print('Ranked:', len(new), 'new')

# 2. Платформы в скане
platforms = set(j.get('platform') for j in jobs)
print('Platforms in scan:', platforms)

# 3. Задачи с контактами
with_contact = 0
for j in jobs[:50]:
    c = p.extract_contacts(j)
    if c.get('channel') != 'manual':
        with_contact += 1
        print('  Contact:', c, '|', j.get('platform'), '|', j.get('title')[:50])
print('With contact:', with_contact, '/50')