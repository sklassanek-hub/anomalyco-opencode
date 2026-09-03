import json
import sys

with open('config.json', encoding='utf-8') as f:
    cfg = json.load(f)

vk_cfg = cfg.get('sources', {}).get('vk', {})
print('VK enabled:', vk_cfg.get('enabled'))
print('Token present:', 'token' in vk_cfg and bool(vk_cfg.get('token')))
print('Token length:', len(vk_cfg.get('token', '')))
print('Groups:', vk_cfg.get('groups', []))
print('Max per group:', vk_cfg.get('max_per_group'))

import sys
sys.path.insert(0, '.')
from modules import vk_scanner as v

jobs, errs = v.fetch_jobs({'vk': cfg['sources']['vk']})
print('VK jobs found:', len(jobs))
print('Errors:', errs)
for j in jobs[:5]:
    print(j.get('title', '')[:60], '|', j.get('contact', 'no-contact')[:50])