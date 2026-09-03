import sys
sys.path.insert(0, '.')

# Test 5: Autoreply
print('=== TEST 5: Autoreply ===')
from modules import autoreply as ar, store
msgs = store.load('messages', {'items': []}).get('items', [])
targets = [m for m in msgs if m.get('direction') == 'in' and not m.get('replied')]
print('Unreplied messages:', len(targets))
for m in targets:
    cls = ar.classify_message(m.get('text', ''))
    sender = m.get('sender', '')
    print('  {} -> {}'.format(sender[:30], cls))

# Test 6: Dashboard API
print('\n=== TEST 6: Dashboard API ===')
import urllib.request
import json
try:
    with urllib.request.urlopen('http://127.0.0.1:8765/api/overview', timeout=5) as r:
        data = json.loads(r.read().decode())
        print('API overview status:', r.status)
        print('Jobs:', data.get('st', {}).get('jobs', 0))
        print('Drafts:', data.get('st', {}).get('drafts', 0))
        print('Sent:', data.get('st', {}).get('sent', 0))
except Exception as e:
    print('Error:', e)