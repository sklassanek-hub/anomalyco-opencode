import sys
sys.path.insert(0, '.')
from modules import sender as snd

# Test auto_approve on current outbox
box = snd.store.load('outbox', {'items': []}).get('items', [])
print('Total in outbox:', len(box))

for o in snd.store.load('outbox', {'items': []}).get('items', [])[:5]:
    print('  Score:', o.get('score'), '| Channel:', o.get('channel'), '| Platform:', o.get('platform'), '| Title:', o.get('title')[:50])

# Run auto_approve
approved = snd.auto_approve(box)
print('Auto-approved:', approved)

# Check results
box2 = snd.store.load('outbox', {'items': []}).get('items', [])
approved_count = sum(1 for o in box2 if o.get('approved'))
print('After auto-approve:', approved_count, 'approved')