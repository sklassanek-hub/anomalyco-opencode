import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store, proposals
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
# простые сайты без тильды/WP, с freelance.ru/weblancer
simple = [i for i in items if 'сайт' in (i.get('title','')+i.get('description','')).lower() and 'тильд' not in (i.get('title','')+i.get('description','')).lower() and 'wordpress' not in (i.get('title','').lower()) and i.get('channel')!='manual']
print('не manual простые:', len([i for i in items if 'сайт' in (i.get('title','').lower())]))
# проверим все простые с freelance.ru/weblancer
for i in items:
    if 'freelance.ru' in i.get('url','') or 'weblancer' in i.get('url',''):
        if 'сайт' in (i.get('title','') or '').lower() and (i.get('score') or 0)>=2:
            print(f"{i.get('url')[:50]} score={i.get('score')} ch={i.get('channel')} contact={i.get('contact')} to={i.get('to')} approved={i.get('approved')} sent={i.get('sent')}")
            print(' ', i.get('title')[:60])
# проверим наличие fl_cookies
import os, json
print('\nfl_cookies exists:', os.path.exists('fl_cookies.json'))
if os.path.exists('fl_cookies.json'):
    try:
        print(json.load(open('fl_cookies.json',encoding='utf-8'))[:1])
    except Exception as e:
        print('err',e)
else:
    print('нет файла fl_cookies.json - FL автобид не работает')
