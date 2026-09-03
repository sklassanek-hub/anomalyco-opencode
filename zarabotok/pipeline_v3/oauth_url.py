import urllib.parse

# Try with exact redirect_uri from app config
client_id = 'ecf7fe17-3c6e-4a59-aa86-10d889f4c948'
redirect_uri = 'https://127.0.0.1:8765/callback'
scope = 'basic'

url = f'https://accounts.freelancer.com/oauth/authorize?client_id={client_id}&prompt=consent&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope={urllib.parse.quote(scope)}'

print('Попробуйте эту ссылку (только basic scope):')
print(url)
print()
print('Если не работает - приложение в статусе "Pending Approval",')
print('нужно написать в api-support@freelancer.com для одобрения.')