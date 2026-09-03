import re
with open('opencode-src/go_mod_audit.json', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
paths = re.findall(r'"Path":\s*"([^"]+)"', text)
versions = re.findall(r'"Version":\s*"([^"]+)"', text)
print('Paths:', len(paths))
print('Versions:', len(versions))
for p, v in list(zip(paths, versions))[:20]:
    print('  ' + p + ' @ ' + v)
