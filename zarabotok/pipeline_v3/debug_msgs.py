import sys
sys.path.insert(0, '.')
from modules import store

msgs = store.load('messages', {'items': []}).get('items', [])
print('Total messages:', len(msgs))
with open('debug_msgs.txt', 'w', encoding='utf-8') as f:
    for m in msgs[-15:]:
        f.write('ts: ' + str(m.get('ts')) + '\n')
        f.write('  direction: ' + str(m.get('direction')) + '\n')
        f.write('  channel: ' + str(m.get('channel')) + '\n')
        f.write('  order: ' + str(m.get('order', 'NONE')) + '\n')
        f.write('  sender: ' + str(m.get('sender', '')) + '\n')
        f.write('  text: ' + str(m.get('text', '')[:100]) + '\n')
        f.write('  replied: ' + str(m.get('replied', False)) + '\n')
        f.write('\n')