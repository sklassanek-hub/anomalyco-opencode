import json
import sys
sys.path.insert(0, '.')

with open('config.json', encoding='utf-8') as f:
    cfg = json.load(f)

from modules import vk_scanner as v

vk_cfg = cfg.get('sources', {}).get('vk', {})
print('VK enabled:', vk.get('enabled'))
print('Token present:', bool(vk.get('token')))
print('Token length:', len(vk.get('token', '')))
print('Groups:', vk.get('groups', []))
print('Max per group:', vk.get('max_per_group'))

# Test scan
jobs, errs = v.fetch_jobs({'vk': cfg['sources']['vk']})
print('VK jobs found:', len(jobs))
print('Errors:', errs)
for j in jobs[:5]:
    print('  ', j.get('title', '')[:60], '|', j.get('contact', 'no-contact')[:50])