import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import scanners, proposals, store, tg_scrape
# возьмем свежие FL простые
jobs, _ = scanners.scan_all(include_tg=False, habr_ids=[])
# фильтр как раньше но без тильды/WP и только сегодняшние FL простые за сегодня
targets_urls = ['https://www.fl.ru/projects/5519309/','https://www.fl.ru/projects/5519306/','https://www.fl.ru/projects/5519305/']
targets = [j for j in jobs if j['url'] in targets_urls]
print(f"найдено таргетов: {len(targets)}")
for j in targets:
    print(j['title'], '|', j['url'], '|', j.get('budget'))
    # сгенерировать текст
    txt = proposals.template_draft(j)
    print("--- отклик ---")
    print(txt[:300])
    print()
# добавим в outbox как одобренные
box = store.load('outbox', {'items':[]})
by_url = {i['url']:i for i in box.get('items',[])}
to_add = []
for j in targets:
    if j['url'] in by_url:
        item = by_url[j['url']]
        # обновим текст и одобрим если не одобрено
        if not item.get('approved'):
            item['approved'] = True
            item['score'] = 4
            item['text'] = proposals.template_draft(j)
            print(f"обновил {j['url']} -> approved")
        else:
            print(f"уже в outbox {j['url']} approved={item.get('approved')} sent={item.get('sent')} skip={item.get('skip_reason')}")
        continue
    txt = proposals.template_draft(j)
    to_add.append({
        "url": j['url'],
        "title": j['title'],
        "description": j.get('description',''),
        "budget": j.get('budget',''),
        "text": txt,
        "channel": "manual",
        "contact": None,
        "to": None,
        "score": 4,
        "approved": True,
        "sent": False,
        "created_at": store.now(),
    })
if to_add:
    def _fn(d):
        d.setdefault('items',[]).extend(to_add)
        return len(to_add)
    store.mutate('outbox', _fn, {'items':[]})
    print(f"добавлено {len(to_add)} новых")

# также покажем что получилось
box2 = store.load('outbox', {'items':[]})
cands = [i for i in box2.get('items',[]) if i['url'] in targets_urls]
for i in cands:
    print(f"OUTBOX {i['url']} approved={i.get('approved')} sent={i.get('sent')} skip={i.get('skip_reason')} score={i.get('score')}")
