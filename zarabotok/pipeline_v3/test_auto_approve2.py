import sys
sys.path.insert(0, '.')
from modules import sender as snd

box = snd.store.load('outbox', {'items': []}).get('items', [])
print('Total in outbox:', len(box))

for o in box[:5]:
    print('  Score:', o.get('score'), '| Channel:', o.get('channel'), '| Platform:', o.get('platform'), '| Title:', o.get('title')[:50])

approved_count, approved_items = snd.auto_approve(box)
print('Auto-approved count:', approved_count)

if approved_count > 0:
    # Save approved items
    def _save_appr(box):
        for item in box.get('items', []):
            for appr in approved_items:
                if item.get('url') == appr.get('url'):
                    item['approved'] = True
                    break
        return box
    
    snd.store.mutate('outbox', lambda b: b, {'items': []})
    
    # Actually save by updating items
    box = snd.store.load('outbox', {'items': []}).get('items', [])
    for item in box:
        for appr in approved_items:
            if item.get('url') == appr.get('url'):
                item['approved'] = True
                break
    snd.store.save('outbox', {'items': box})
    print('Saved to store')

# Verify
box2 = snd.store.load('outbox', {'items': []}).get('items', [])
approved_count = sum(1 for o in box2 if o.get('approved'))
print('After save:', approved_count, 'approved')