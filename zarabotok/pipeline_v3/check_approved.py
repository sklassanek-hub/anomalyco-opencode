import sys
sys.path.insert(0, '.')
from modules import store, sender as snd

box = snd.store.load('outbox', {'items': []}).get('items', [])
tg_items = [o for o in box if o.get('approved') and o.get('channel') == 'tg' and not o.get('sent')]
print('TG approved unsent:', len(tg_items))

approved = [o for o in box if o.get('approved') and not o.get('sent')]
print('Total approved unsent:', len(approved))
for item in approved:
    print('  Score:', item.get('score'), 'Judge:', item.get('judge'), 'Channel:', item.get('channel'), 'Contact:', item.get('contact'))