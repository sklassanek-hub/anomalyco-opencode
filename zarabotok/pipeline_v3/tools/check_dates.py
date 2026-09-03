import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
from collections import Counter
box = store.load('outbox', {'items':[]})
items = box.get('items',[])
dates = [ (i.get('created_at') or '')[:10] for i in items if i.get('created_at')]
print(Counter(dates).most_common(10))
# покажем самые свежие по created_at
sorted_items = sorted(items, key=lambda x: x.get('created_at') or '', reverse=True)
print("\nсамые свежие 15:")
for i in sorted_items[:15]:
    print(i.get('created_at'), f"score={i.get('score')} ch={i.get('channel')} approved={i.get('approved')} sent={i.get('sent')} skip={i.get('skip_reason')} | {i.get('title','')[:60]} | {i.get('url')[:50]}")
# проверим есть ли items с created_at 24.08
print("\nitems 24.08:", len([i for i in items if '2026-08-24' in str(i.get('created_at'))]))
print("items 23.08:", len([i for i in items if '2026-08-23' in str(i.get('created_at'))]))
print("items 22.08:", len([i for i in items if '2026-08-22' in str(i.get('created_at'))]))
# проверим state файлы
import os
for f in os.listdir('state'):
    if f.startswith('outbox') or f.startswith('orders'):
        print(f)
