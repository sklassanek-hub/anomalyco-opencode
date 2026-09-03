import os

# Check for Freelancer API integration in scanners.py
with open('modules/scanners.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for freelancer references
found = False
for i, line in enumerate(content.splitlines(), 1):
    if 'freelancer' in line.lower() or 'freelancer.com' in line.lower():
        print(f'Line {i}: {line.strip()[:200]}')
        found = True

if not any('freelancer' in line.lower() for line in open('modules/scanners.py', 'r', encoding='utf-8').read().splitlines()):
    print('No freelancer references found in scanners.py')

# Check for API/OAuth related code
print('\n=== API/OAuth related code ===')
with open('modules/scanners.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(content.splitlines(), 1):
        if any(kw in line.lower() for kw in ['api', 'oauth', 'freelancer.com', 'client_id', 'client_secret']):
            print(f'{i}: {line.strip()[:200]}')