import sys
sys.path.insert(0, '.')
from modules import sender as snd

box = snd.store.load('outbox', {'items': []}).get('items', [])
for i in box:
    ch = (i.get('channel') or '').lower()
    url = (i.get('url') or '').lower()
    contact = i.get('contact') or i.get('to')
    print('URL:', i.get('url', '')[:50])
    print('  ch={} contact={}'.format(ch, contact))
    
    # Check _dispatch logic
    if 'fl.ru' in url:
        print('  dispatch=skip (fl.ru)')
    elif any(s in url for s in ('freelance.ru', 'weblancer', 'kwork', 'habr', 'weworkremotely')):
        print('  dispatch=pending (platform requires manual)')
    elif ch == 'email' and i.get('to'):
        print('  dispatch=auto (email)')
    elif ch == 'tg' or 't.me' in url:
        if contact:
            print('  dispatch=auto (tg with contact)')
        else:
            print('  dispatch=pending (tg no contact)')
    else:
        print('  dispatch=skip')
    print()