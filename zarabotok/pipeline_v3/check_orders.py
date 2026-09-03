import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with urllib.request.urlopen('http://127.0.0.1:8765/api/orders') as r:
    data = json.loads(r.read().decode('utf-8'))
    rows = data.get('rows', [])
    print(f'Total orders: {len(data.get("rows", []))}')
    for r in rows[:10]:
        print(f"  {r.get('title', '')[:50]} | status: {r.get('status')} | contact: {r.get('contact')}")