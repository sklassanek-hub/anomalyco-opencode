import sys
import traceback
sys.path.insert(0, '.')
import modules.freelancer_scanner as fs
import json

with open('config.json', encoding='utf-8') as f:
    cfg = ((json.load(f) or {}).get('sources') or {}).get('freelancer') or {}

try:
    jobs, errs = fs.fetch_jobs(cfg)
    print('jobs:', len(jobs), 'errors:', errs)
    for j in jobs[:3]:
        print('  ', j['title'][:80], '|', j['budget'])
except Exception as e:
    traceback.print_exc()