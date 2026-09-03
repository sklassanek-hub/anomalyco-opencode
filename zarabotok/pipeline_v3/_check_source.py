import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = open('workers/dashboard.py', encoding='utf-8').read()
import re
m = re.search(r'SPA = """(.*?)"""', s, re.S)
if m:
    spa = m.group(1)
    # Find the VIEWS array definition
    for i, line in enumerate(spa.splitlines(), 1):
        if 'VIEWS' in line or 'funnel' in line.lower() or 'orders' in line.lower():
            print(i, line[:150])