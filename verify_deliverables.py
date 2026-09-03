# Deliverables manifest audit (W22)
import os, json
root = 'zarabotok/pipeline_v3/deliverables'
ok = warn = 0
for entry in os.listdir(root):
    p = os.path.join(root, entry)
    if not os.path.isdir(p):
        continue
    v1 = os.path.join(p, 'v1')
    if not os.path.isdir(v1):
        warn += 1
        print('WARN no v1:', entry)
        continue
    manifest = os.path.join(v1, 'manifest.json')
    if not os.path.exists(manifest):
        warn += 1
        print('WARN no manifest.json:', entry)
        continue
    try:
        with open(manifest, 'r', encoding='utf-8', errors='ignore') as f:
            m = json.load(f)
        files = m.get('files', [])
        names = []
        if isinstance(files, list) and files:
            if isinstance(files[0], dict):
                names = [fl.get('name', '') for fl in files]
            elif isinstance(files[0], str):
                names = files
        if not names:
            warn += 1
            print('WARN manifest has no files:', entry)
            continue
        missing = [n for n in names if not n or not os.path.exists(os.path.join(v1, n))]
        if missing:
            warn += 1
            print(f'WARN manifest files missing: {entry}: {missing}')
            continue
        ok += 1
    except Exception as e:
        warn += 1
        print('WARN manifest error:', entry, e)
print(f'OK={ok} WARN={warn} total={ok+warn}')
