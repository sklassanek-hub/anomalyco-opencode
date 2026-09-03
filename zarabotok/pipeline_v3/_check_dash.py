import sys, re
sys.path.insert(0, '.')
s = open('workers/dashboard.py', encoding='utf-8').read()

# Find the SPA section
m = re.search(r'SPA = """(.*?)"""', open('workers/dashboard.py', encoding='utf-8').read(), re.S)
if m:
    spa = m.group(1)
    # Find view rendering parts
    for i, line in enumerate(spa.splitlines(), 1):
        if 'VIEWS' in line or 'VIEWS' in line or 'funnel' in line.lower() or 'orders' in line.lower():
            print(i, line[:150])