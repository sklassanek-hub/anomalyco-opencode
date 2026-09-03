# Auto-fix deliverables manifests
# Recreates manifest.json for each v1/ based on actual files present.
import os, json, hashlib

root = 'zarabotok/pipeline_v3/deliverables'
fixed = 0
for entry in os.listdir(root):
    p = os.path.join(root, entry)
    if not os.path.isdir(p):
        continue
    v1 = os.path.join(p, 'v1')
    if not os.path.isdir(v1):
        continue
    manifest = os.path.join(v1, 'manifest.json')
    files = []
    for f in os.listdir(v1):
        full = os.path.join(v1, f)
        if os.path.isfile(full):
            with open(full, 'rb') as file:
                h = hashlib.sha256(file.read()).hexdigest()
            files.append({'name': f, 'sha256': h, 'size': os.path.getsize(full)})
    data = {'name': entry, 'version': 'v1', 'files': files}
    with open(manifest, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    fixed += 1
    print(f'Fixed manifest: {entry}/v1 ({len(files)} files)')

print(f'---')
print(f'Total manifests regenerated: {fixed}')
