import sys
sys.path.insert(0, '.')
from modules import store

box = store.load('outbox', {'items': []}).get('items', [])
tg_items = [o for o in box if o.get('approved') and o.get('channel') == 'tg' and not o.get('sent')]
print('TG approved unsent:', len(tg_items))
for item in tg_items[:2]:
    print('  Score:', item.get('score'), 'Judge:', item.get('judge'), 'Contact:', item.get('contact'))