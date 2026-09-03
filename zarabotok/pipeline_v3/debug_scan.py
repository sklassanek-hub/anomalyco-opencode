import sys
sys.path.insert(0, '.')
import json, os
from modules import scanners as s
from collections import Counter

jobs = []
errors = []

# include_sites section
if True:
    for name, fn in (('fl', s.scan_fl), ('flrss', s.scan_fl_rss), ('fr', s.scan_fr), ('wr', s.scan_wr), ('wl', s.scan_wl), ('kw', s.scan_kwork), ('gh', s.scan_gh_bounty)):
        try:
            part = fn()
            print('DEBUG {}: {} jobs'.format(name, len(part)))
            if part:
                print('  first platform: {}'.format(part[0].get('platform')))
            s._enrich(part)
            jobs += part
        except Exception as e:
            errors.append('{}: {}'.format(name, e))
        try:
            part2 = fn()
            print('DEBUG {} (2nd call): {} jobs'.format(name, len(part2)))
            jobs += part2
        except Exception as e:
            errors.append('{}: {}'.format(name, e))

# VK/OK/freelancer section
try:
    _cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath('modules/scanners.py'))), 'config.json')
    with open(_cfg_path, encoding='utf-8') as f:
        _cfg = (json.load(f) or {}).get('sources', {})
except Exception:
    _cfg = {}

for mod_name, key in (('vk_scanner', 'vk'), ('ok_scanner', 'ok'), ('freelancer_scanner', 'freelancer')):
    scfg = _cfg.get(key)
    if not isinstance(scfg, dict) or not scfg.get('enabled'):
        print('SKIP {}: not enabled or not dict'.format(mod_name))
        continue
    print('CALLING {}...'.format(mod_name))
    try:
        module = __import__('modules.{}'.format(mod_name), fromlist=['fetch_jobs'])
        part, errs2 = module.fetch_jobs(scfg)
        print('  {} returned {} jobs'.format(mod_name, len(part)))
        if part:
            print('  first platform: {}'.format(part[0].get('platform')))
        s._enrich(part)
        jobs += part
        errors += errs2
    except Exception as e:
        errors.append('{}: {}: {}'.format(key, type(e).__name__, str(e)[:80]))

print()
print('Total jobs:', len(jobs))
print('Errors:', errs)

cnt = Counter(j.get('platform', '?') for j in jobs)
for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
    print('  {}: {}'.format(k, v))