import json
import sys

with open('config.json', encoding='utf-8') as f:
    cfg = json.load(f)

vk_cfg = cfg.get('sources', {}).get('vk', {})
print('vk enabled:', vk_cfg.get('enabled'))
print('token present:', 'token' in vk_cfg and bool(vk_cfg.get('token')))
print('token length:', len(vk_cfg.get('token', '')))
print('groups:', vk_cfg.get('groups', []))
print('max_per_group:', vk_cfg.get('max_per_group'))

import json, sys
sys.path.insert(0, '.')
from modules import vk_scanner as v

jobs, errs = v.fetch_jobs({'vk': cfg['sources']['vk']})
print('VK jobs:', len(jobs), 'errs:', errs)
for j in jobs[:5]:
    print(j.get('title', '')[:60], '|', j.get('contact'))