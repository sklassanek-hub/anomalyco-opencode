import sys
sys.path.insert(0, '.')

from modules import store, sender as snd

# Find TG items
box = snd.store.load('outbox', {'items': []}).get('items', [])
tg_items = [o for o in box if o.get('approved') and o.get('channel') == 'tg' and not o.get('sent')]
print(f'TG approved items: {len(tg_items)}')

if tg_items:
    item = tg_items[0]
    print('Item:', item.get('title')[:50])
    print('Contact:', item.get('contact'))
    
    # Try sending
    result = snd.send_telegram(item)
    print('TG send result:', result)