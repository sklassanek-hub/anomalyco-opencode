import sys
sys.path.insert(0, '.')
from modules import proposals as p, store, scanners, ranker

jobs, _ = scanners.scan_all(include_tg=False)

# Check Weblancer jobs
weblancer = [j for j in jobs if j.get('platform') == 'Weblancer']
print('Weblancer jobs:', len(weblancer))
for j in weblancer[:3]:
    print('  Title:', j.get('title')[:60])
    print('  URL:', j.get('url'))
    print('  Score:', j.get('score'))
    print('  Kind:', j.get('kind'))
    print('  Desc len:', len(j.get('description') or ''))
    c = p.extract_contacts(j)
    print('  Contact:', c)
    print()

# Check WWR
wwr = [j for j in jobs if j.get('platform') == 'WeWorkRemotely']
print('WWR jobs:', len(wwr))
for j in wwr[:3]:
    print('  Title:', j.get('title')[:60])
    print('  URL:', j.get('url'))
    print('  Score:', j.get('score'))
    c = p.extract_contacts(j)
    print('  Contact:', c)
    print()