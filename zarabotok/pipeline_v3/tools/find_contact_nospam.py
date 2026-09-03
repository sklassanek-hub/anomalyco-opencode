import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store
box = store.load('outbox', {'items':[]})
spam_users = {'cabinetjarvisbot','archeishere'}
cands=[]
for i in box['items']:
    if i.get('sent') or i.get('skip_reason') in ('paid','dead','spam','scam-stop','bad'):
        continue
    if (i.get('score') or 0) <3:
        continue
    contact = (i.get('contact') or i.get('to') or '').lower()
    if not contact:
        continue
    user = contact.replace('tg:@','').replace('tg:','')
    if user in spam_users:
        continue
    t=(i.get('title','')+' '+i.get('description','')).lower()
    if any(x in t for x in ['тильд','tilda','вордпрес','wordpress']):
        continue
    is_site = any(k in t for k in ['сайт','лендинг','одностранич','визитка','верстк'])
    # покажем все с контактом не спам
    cands.append((is_site, i))
print(f"не спам с контактами score>=3: {len(cands)}")
for is_site, i in sorted(cands, key=lambda x: (x[0], x[1].get('score',0)), reverse=True):
    print(f"{'SITE' if is_site else '    '} score={i.get('score')} {i.get('contact') or i.get('to')} | {i.get('title','')[:60]} | {i.get('url')[:50]}")
# также email контакты
email_cands = [i for i in box['items'] if (i.get('to') and '@' in i.get('to')) and not i.get('sent') and i.get('skip_reason') not in ('paid','dead','spam')]
print(f"\nemail контактов: {len(email_cands)}")
for i in email_cands[:5]:
    print(i.get('to'), i.get('title')[:50])
