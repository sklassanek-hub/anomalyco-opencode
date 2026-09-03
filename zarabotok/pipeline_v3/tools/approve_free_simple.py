import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import store, proposals
box = store.load('outbox', {'items':[]})
# найдем черновики простых сайтов без тильды/WP, score>=3, которые бесплатные (не FL payed)
# одобрим их
to_approve = []
for i in box['items']:
    if not i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=3:
        t = (i.get('title','') + ' ' + i.get('description','')).lower()
        if any(x in t for x in ['тильд','tilda','вордпрес','wordpress']):
            continue
        if not any(k in t for k in ['сайт','лендинг','одностранич','визитка','верстк']):
            continue
        # исключаем FL платные? пока одобряем все, кроме FL которые уже paid
        if i.get('skip_reason') in ('paid','dead','spam'):
            continue
        to_approve.append(i)

print(f"к одобрению бесплатных простых: {len(to_approve)}")
for i in to_approve:
    print(f"  {i.get('url')[:50]} score={i.get('score')} | {i.get('title')[:60]}")

# одобряем
def _approve(d):
    for it in d['items']:
        for cand in to_approve:
            if it['url']==cand['url']:
                it['approved']=True
                # сгенерируем текст если нет
                if not it.get('text') or 'чат-бот' in it.get('text','').lower():
                    # перегенерим под сайт
                    it['text'] = proposals.template_draft(it)
    return len(to_approve)

if to_approve:
    store.mutate('outbox', _approve, {'items':[]})
    print(f"одобрено {len(to_approve)}")

# теперь найдем все одобренные бесплатные простые для отправки
box2 = store.load('outbox', {'items':[]})
free_simple = [i for i in box2['items'] if i.get('approved') and not i.get('sent') and (i.get('score') or 0)>=3 and i.get('skip_reason') not in ('paid','dead','spam','scam-stop','bad') and any(k in (i.get('title','')+i.get('description','')).lower() for k in ['сайт','лендинг','одностранич','визитка','верстк']) and not any(x in (i.get('title','')+i.get('description','')).lower() for x in ['тильд','tilda','вордпрес','wordpress'])]
print(f"\nготовых к отправке бесплатных простых: {len(free_simple)}")
for i in sorted(free_simple, key=lambda x: x.get('score',0), reverse=True)[:10]:
    print(f"score={i.get('score')} {i['url'][:50]} | {i['title'][:60]} | contact={i.get('contact') or i.get('to') or '-'}")
    print("  текст:", i.get('text','')[:150].replace('\n',' '))
