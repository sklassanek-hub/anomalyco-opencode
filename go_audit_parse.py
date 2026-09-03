import json, re
with open('opencode-src/go_mod_audit.json', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Split by }{ pattern (jsonl-like)
modules = []
parts = re.findall(r'\{[^{}]*\}', text, re.DOTALL)
for p in parts:
    try:
        obj = json.loads(p)
        if 'Path' in obj and 'Version' in obj:
            modules.append((obj['Path'], obj.get('Version', ''), obj.get('GoVersion', '')))
    except Exception:
        pass
print('Modules found:', len(modules))
for path, ver, gover in modules[:15]:
    print(f'  {path} @ {ver} (go {gover})')
