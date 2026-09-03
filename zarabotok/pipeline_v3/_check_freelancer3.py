import os

with open('modules/scanners.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for freelancer-related code
for i, line in enumerate(content.splitlines(), 1):
    if 'freelancer' in line.lower() or 'freelancer.com' in line.lower():
        print(f'{i}: {line.strip()[:200]}')

# Also check for API-related code
print("\n=== API related ===")
for i, line in enumerate(open('modules/scanners.py', 'r', encoding='utf-8').read().splitlines(), 1):
    if any(kw in line.lower() for kw in ['api', 'oauth', 'freelancer.com', 'client_id', 'client_secret']):
        print(f'{i}: {line.strip()[:200]}')