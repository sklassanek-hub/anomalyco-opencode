import json
with open('config.json', 'r', encoding='utf-8') as f:
    c = json.load(f)
vk = c.get('sources', {}).get('vk', {})
print('enabled:', vk.get('enabled'))
print('token:', vk.get('token', '')[:30] + '...' if vk.get('token') else 'EMPTY')
print('groups:', vk.get('groups', []))
print('max_per_group:', vk.get('max_per_group'))