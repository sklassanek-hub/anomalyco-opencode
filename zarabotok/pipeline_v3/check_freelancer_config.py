import json

with open('config.json', 'r', encoding='utf-8') as f:
    c = json.load(f)

freel = c.get('sources', {}).get('freelancer', {})
print('freelancer config:')
print('  enabled:', freel.get('enabled'))
print('  client_id:', freel.get('client_id')[:20] + '...' if freel.get('client_id') else 'EMPTY')
print('  client_secret:', freel.get('client_secret', '')[:20] + '...' if freel.get('client_secret') else 'EMPTY')
print('redirect_uri:', freel.get('redirect_uri'))
print('token:', freel.get('token')[:30] + '...' if freel.get('token') else 'EMPTY')
print('api_base:', freel.get('api_base'))