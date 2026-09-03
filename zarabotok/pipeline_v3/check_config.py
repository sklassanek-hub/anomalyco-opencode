import json

with open('config.json', 'r', encoding='utf-8') as f:
    c = json.load(f)

print('VK token:', c.get('sources', {}).get('vk', {}).get('token', '')[:30] + '...' if c.get('sources', {}).get('vk', {}).get('token') else 'EMPTY')
print('VK groups:', c.get('sources', {}).get('vk', {}).get('groups', []))
print('Freelancer enabled:', c.get('sources', {}).get('freelancer', {}).get('enabled'))
print('Freelancer client_id:', c.get('sources', {}).get('freelancer', {}).get('client_id', '')[:20])
print('Freelancer token:', c.get('sources', {}).get('freelancer', {}).get('token', '')[:30])
print('VK token:', c.get('sources', {}).get('vk', {}).get('token', '')[:30])
print('VK groups:', c.get('sources', {}).get('vk', {}).get('groups', []))