@echo off
cd /d C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3
python -c "
import json
with open('config.json', 'r', encoding='utf-8') as f:
    c = json.load(f)
c['sources']['freelancer'] = {
    'enabled': True,
    'client_id': 'ecf7fe17-3c6e-4a59-aa86-10d889f4c948',
    'client_secret': '9a0075dd64d1ffdfc25da5827006bc7ea877a3d035f12888ce8c70da1aad2f7e625f3b25b6e71a28fac0f157e8c6bdb630c6dec358e143718f52791ffcf49aeb',
    'redirect_uri': 'https://127.0.0.1:8765/callback',
    'token': '',
    'api_base': 'https://www.freelancer.com/api'
}
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(json.load(open('config.json', encoding='utf-8')), f, ensure_ascii=False, indent=1)
print('Freelancer added to config')
"