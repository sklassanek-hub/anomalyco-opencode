import sys
sys.path.insert(0, '.')

from modules import store, sender as snd

box = snd.store.load('outbox', {'items': []}).get('items', [])
print(f'Outbox: {len(box)} items')

scores = [o.get('score', 0) for o in box]
print(f'Scores: min={min(scores)}, max={max(scores)}')

# Test auto_approve
approved_count, approved_items = snd.auto_approve(box)
print(f'Auto-approved: {approved_count}')

# Save approved
box = snd.store.load('outbox', {'items': []}).get('items', [])
for item in box:
    for appr in snd.auto_approve(box)[1]:
        if item.get('url') == appr.get('url'):
            item['approved'] = True
            break
store.save('outbox', {'items': box})
print('Saved approved items')

# Verify
box2 = store.load('outbox', {'items': []}).get('items', [])
approved_count = sum(1 for o in box2 if o.get('approved'))
print(f'After save: {approved_count} approved')