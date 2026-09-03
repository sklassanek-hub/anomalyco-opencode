import os, re
patterns = [r'token', r'secret', r'password', r'api_key', r'apikey']
found = []
for root, dirs, files in os.walk('opencode-src'):
    dirs[:] = [d for d in dirs if d != '.git' and not d.startswith('.opencode')]
    for file in files:
        path = os.path.join(root, file)
        if path.endswith('.go') or path.endswith('.json') or path.endswith('.md'):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for pat in patterns:
                        matches = re.findall(pat, content, re.IGNORECASE)
                        if matches:
                            found.append('{}: {} matches "{}"'.format(path, len(matches), pat))
            except:
                pass
seen = sorted(set(found))
with open('c7_grep_results.txt', 'w', encoding='utf-8') as out:
    for s in seen[:30]:
        out.write(s + '\n')
    out.write('Total unique hits (first 30 shown): {}\n'.format(len(seen)))
