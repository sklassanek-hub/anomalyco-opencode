import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store, http_client as hc
import re
box = store.load('outbox', {'items':[]})
# найдем все простые без отправки
cands = [i for i in box['items'] if not i.get('sent') and i.get('skip_reason') not in ('paid','dead','spam','scam-stop','bad') and any(k in (i.get('title','')+i.get('description','')).lower() for k in ['сайт','лендинг','одностранич','визитка','верстк'])]
print(f"кандидатов всего: {len(cands)}")
# проверим у скольких есть контакт
with_contact = [i for i in cands if i.get('contact') or i.get('to')]
print(f"с контактом: {len(with_contact)}")
for i in with_contact[:5]:
    print(i['url'][:50], i.get('contact'), i.get('to'))
# для FL без контакта попробуем вытащить контакт со страницы проекта
import time
s = hc.client('fl.ru')
for i in cands[:5]:
    if 'fl.ru' in i['url'] and not (i.get('contact') or i.get('to')):
        try:
            r = s.get(i['url'], timeout=15)
            m = re.search(r'(?:@|t\.me/)([A-Za-z0-9_]{4,32})', r.text)
            mail = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', r.text)
            print(f"{i['url'].split('/')[-2]} contact found: TG={m.group(1) if m else '-'} mail={mail.group(0) if mail else '-'}")
        except Exception as e:
            print(e)
        time.sleep(1)
