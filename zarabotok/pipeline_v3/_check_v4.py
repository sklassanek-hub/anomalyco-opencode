import re
s = open('workers/dashboard.py', encoding='utf-8').read()
m = re.search(r'SPA = """(.*?)"""', open('workers/dashboard.py', encoding='utf-8').read(), re.S)
if m:
    spa = m.group(1)
    for i, line in enumerate(spa.splitlines(), 1):
        if 'VIEWS' in line or 'funnel' in line.lower() or 'orders' in line.lower():
            print(i, line[:150])