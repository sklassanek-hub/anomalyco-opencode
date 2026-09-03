import sys
sys.path.insert(0, '.')
from modules import freelancer_scanner as fs

cfg = {
    'enabled': True,
    'client_id': 'ecf7fe17-3c6e-4a59-aa86-10d889f4c948',
    'client_secret': '9a0075dd64d1ffdfc25da5827006bc7ea877a3d035f12888ce8c70da1aad2f7e625f3b25b6e71a28fac0f157e8c6bdb630c6dec358e143718f52791ffcf49aeb',
    'redirect_uri': 'https://127.0.0.1:8765/callback',
    'token': '1YS6mZGJUAHJGqLIMYdpJ99GzhJOr8',
    'api_base': 'https://www.freelancer.com/api'
}

jobs, errs = fs.scan_fl(cfg)
print('Freelancer jobs:', len(jobs))
print('Errors:', errs)
for j in jobs[:3]:
    print('  ', j.get('title', '')[:60], '|', j.get('url')[:60])