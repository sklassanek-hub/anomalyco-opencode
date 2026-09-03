import re
with open('opencode-src/go_mod_audit.json', 'r', encoding='utf-16') as f:
    text = f.read()
print('Size:', len(text))
print('First 200 chars:')
print(text[:200])
paths = re.findall(r'"Path":\s*"([^"]+)"', text)
versions = re.findall(r'"Version":\s*"([^"]+)"', text)
print('Paths:', len(paths))
print('Versions:', len(versions))
for p, v in list(zip(paths, versions))[:20]:
    print('  ' + p + ' @ ' + v)
# Save UTF-8 copy
with open('opencode-src/go_mod_audit_utf8.json', 'w', encoding='utf-8') as f:
    f.write(text)
print('Saved UTF-8 copy')
