import sys
sys.path.insert(0, '.')
from modules import store, crm

f = crm.funnel()
print('Funnel:', f)

box = store.load('outbox', {'items': []}).get('items', [])
total = len(box)
approved = sum(1 for o in box if o.get('approved'))
sent = sum(1 for o in box if o.get('sent'))
pending = sum(1 for o in box if not o.get('approved') and not o.get('sent'))
print('Total:', len(box), 'Approved:', approved, 'Sent:', sent, 'Pending:', pending)