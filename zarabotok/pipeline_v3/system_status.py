import sys
sys.path.insert(0, '.')

import socket
import urllib.request
import json

from modules import store, scanners, ranker, proposals, sender, crm, executor, fl_bidder

print('=== ЗАБОТОК PIPELINE - СТАТУС СИСТЕМЫ ===')
print()

# 1. Сканер
from modules import store, scanners, ranker, proposals, sender, crm, executor, fl_bidder

jobs, errs = scanners.scan_all(include_tg=False)
print(f'1. Сканер: {len(jobs)} заказов, ошибок: {len(errs)}')
from collections import Counter
cnt = Counter(j.get('platform', '?') for j in jobs)
for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')

# 2. Ранкер
new = ranker.rank_and_store(jobs, min_score=0, contact_only=False)
print(f'Ранкер: {len(new)} новых')

# 3. Outbox
box = store.load('outbox', {'items': []}).get('items', [])
approved = sum(1 for o in box if o.get('approved'))
sent = sum(1 for o in box if o.get('sent'))
pending = len(box) - approved - sum(1 for o in box if o.get('sent'))
print(f'Outbox: {len(box)} всего, одобрено: {approved}, отправлено: {sent}, в ожидании: {pending}')

# 4. Воронка
f = crm.funnel()
print(f'Воронка: {f}')

# 6. Freelancer.com API
try:
    from modules import freelancer_scanner as fs
    jobs, errs = fs.scan_fl({})
    print(f'Freelancer.com: {len(jobs)} заказов, ошибок: {len(errs)}')
except Exception as e:
    print(f'Freelancer.com: ОШИБКА - {e}')

# 7. OpenCode сервер
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', 3000))
    sock.close()
    print(f'OpenCode сервер (порт 3000): {"РАБОТАЕТ" if result == 0 else "НЕДОСТУПЕН"}')
except:
    print('OpenCode сервер: НЕДОСТУПЕН (не запущен)')