import os

# Check for Freelancer.com API related code in scanners.py
with open('modules/scanners.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("=== Freelancer references in scanners.py ===")
for i, line in enumerate(content.splitlines(), 1):
    if 'freelancer' in line.lower():
        print(f'{i}: {line.strip()[:150]}')

print("\n=== API-related code ===")
for i, line in enumerate(open('modules/scanners.py', 'r', encoding='utf-8').read().splitlines(), 1):
    if any(kw in line.lower() for kw in ['api', 'oauth', 'freelancer.com', 'client_id', 'client_secret']):
        print(f'{i}: {line.strip()[:150]}')