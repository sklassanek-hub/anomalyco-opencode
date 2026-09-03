import sys
sys.path.insert(0, '.')
from modules import proposals as p, store

# Get one of the jobs from the outbox
box = store.load('outbox', {'items': []}).get('items', [])
item = box[1]  # t.me item

# Check what job this corresponds to
jobs = store.load('jobs', {'items': []}).get('items', [])
job = next((j for j in jobs if j.get('url') == item.get('url')), None)
if job:
    with open('debug_judge.txt', 'w', encoding='utf-8') as f:
        f.write('Job title: ' + str(job.get('title')) + '\n')
        f.write('Job budget: ' + str(job.get('budget')) + '\n')
        f.write('Item text: ' + str(item.get('text')[:200]) + '\n\n')
        
        # Run judge eval
        result = p.judge_eval(item.get('text'), job)
        f.write('Judge result: ' + str(result) + '\n')
else:
    with open('debug_judge.txt', 'w', encoding='utf-8') as f:
        f.write('Job not found\n')