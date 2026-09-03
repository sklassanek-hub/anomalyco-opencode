import sys
sys.path.insert(0, '.')

from modules import store, sender as snd

box = snd.store.load('outbox', {'items': []}).get('items', [])
print('Total in outbox:', len(box))

for o in box[:10]:
    score = o.get('score', 0)
    channel = o.get('channel')
    platform = o.get('platform')
    print('  Score:', score, '| Channel:', channel, '| Platform:', platform, '|', o.get('title')[:50])

approved_count, approved_items = snd.auto_approve(box)
print('Auto-approved:', approved_count)