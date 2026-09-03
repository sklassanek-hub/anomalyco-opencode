with open('modules/sender.py', 'rb') as f:
    content = f.read()

idx = 22872
chunk = content[idx:idx+50]
for i, b in enumerate(chunk):
    ch = chr(b) if 32 <= b < 127 else '.'
    print(f'{i}: {b:02x} ({ch})')