import sys
sys.path.insert(0, '.')
from modules import store, proposals, scanners, ranker

print('=== РЕАЛЬНОЕ СОСТОЯНИЕ ===')

# 1. Outbox
box = store.load('outbox', {'items': []}).get('items', [])
print('Outbox:', len(box), 'элементов')
for o in box:
    print('  URL:', o.get('url', '')[:60])
    print('  Approved:', o.get('approved'), 'Sent:', o.get('sent'))
    print('  Platform:', o.get('platform', 'NONE'))
    print('  Channel:', o.get('channel', 'NONE'))
    print('  Text:', (o.get('text') or '')[:80])
    print()

# 2. Sent log
sent = store.load('sent_log', {'items': []}).get('items', [])
print('Sent log:', len(sent), 'записей')
for s in sent[-5:]:
    print('  ', s.get('ts', ''), '|', s.get('channel', ''), '|', s.get('url', '')[:60])

# 3. Генерация черновиков сейчас
from modules import scanners, ranker, proposals
jobs, _ = scanners.scan_all(include_tg=False)
new = ranker.rank_and_store(jobs, min_score=1, contact_only=False)
drafts = proposals.build_outbox(jobs[:20], max_revise=0, llm_top_n=0)
print('Drafts created now:', drafts)

# 4. Автоотправка
import os
os.environ['SENDER_TIMING'] = '1'
from modules import sender as snd
sent = snd.run_cycle()
print('Auto-send sent:', sent)