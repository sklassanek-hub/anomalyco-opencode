import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import scanners, proposals
jobs, _ = scanners.scan_all(include_tg=True, habr_ids=[])
# фильтр простые сайты без тильды/WP, не FL (чтобы без платного)
targets = []
for j in jobs:
    t = (j.get('title','')+' '+j.get('description','')).lower()
    if any(x in t for x in ['тильд','tilda','вордпрес','wordpress']):
        continue
    if not any(k in t for k in ['сайт','лендинг','одностранич','визитка','верстк']):
        continue
    if j['platform'] == 'FL':
        continue
    targets.append(j)
print(f"не-FL простых сайтов сегодня: {len(targets)}")
for j in targets[:12]:
    print(f"[{j['platform']}] {j['title'][:70]} | {j['url']} | {j.get('budget','')}")
    txt = proposals.template_draft(j)
    print("  отклик:", txt[:180].replace('\n',' '))
    print()
