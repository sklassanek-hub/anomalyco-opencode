import sys
sys.path.insert(0, '.')

from modules import store, proposals, scanners, ranker, sender as snd, crm

# Full pipeline test
store.save('outbox', {'items': []})
jobs, _ = scanners.scan_all(include_tg=False)
drafts = proposals.build_outbox(jobs[:50], max_revise=0, llm_top_n=0)
print('Drafts:', drafts)

box = store.load('outbox', {'items': []}).get('items', [])
print('Outbox:', len(box))

# Auto-approve
approved_count, approved_items = snd.auto_approve(box)
print('Auto-approved:', approved_count)

# Save approved
if approved_items:
    box = store.load('outbox', {'items': []}).get('items', [])
    for item in box:
        for appr in snd.auto_approve(box)[1]:
            if item.get('url') == appr.get('url'):
                item['approved'] = True
                break
    store.save('outbox', {'items': box})
    print('Saved approved items')

# Funnel
f = crm.funnel()
print('Funnel:', f)