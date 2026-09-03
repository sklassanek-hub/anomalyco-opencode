import sys
sys.path.insert(0, '.')
from modules import store

sent = store.load('sent_log', {'items': []}).get('items', [])
print('Sent log entries:', len(sent))
for s in sent[-5:]:
    print('  ', s.get('ts'), '|', s.get('channel'), '|', s.get('url', '')[:60])