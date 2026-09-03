import sys
sys.path.insert(0, '.')
from modules import listener as ls, store, tg_common, http_client

# Test poll_telegram with debug
session = store.load('settings', {}).get('tg_session_listener', 'telegram_session_listener')
print('Session:', session)

client = tg_common.tg_client(tg_common.session_path(session), proxy=http_client.socks_args())

try:
    with tg_common.tg_lock():
        client.start()
        for dialog in client.iter_dialogs(limit=10):
            ts = dialog.date.timestamp()
            msg = getattr(dialog, 'message', None)
            if msg is None or getattr(msg, 'out', False):
                continue
            uname = getattr(getattr(dialog, 'entity', None), 'username', None)
            if uname:
                peer = '@' + uname.lower()
            else:
                peer = 'tg:' + str(dialog.name)
            text = (msg.text if msg else '')[:80]
            print('Peer:', peer, 'TS:', ts, 'Text:', text)
finally:
    client.disconnect()