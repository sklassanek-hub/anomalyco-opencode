import json

with open('config.json', encoding='utf-8') as f:
    cfg = json.load(f)

vk = cfg.get('sources', {}).get('vk', {})
print('VK enabled:', vk.get('enabled'))
print('Token present:', 'token' in vk and bool(vk.get('token')))
print('Token length:', len(vk.get('token', '')))
print('Token preview:', vk.get('token', '')[:30] + '...' if vk.get('token') else 'EMPTY')
print('Groups:', vk.get('groups', []))
print('Max per group:', vk.get('max_per_group'))