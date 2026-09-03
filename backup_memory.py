#!/usr/bin/env python3
# Memory autobackup (P2)
# Copies memory/ to zarabotok/pipeline_v3/deliverables/memory-snapshot-YYYY-MM-DD.md (single concatenated) + dir archive.
import os, datetime, shutil

src = 'memory'
dst_dir = 'zarabotok/pipeline_v3/deliverables/memory_snapshots'
os.makedirs(dst_dir, exist_ok=True)
ts = datetime.datetime.now().strftime('%Y-%m-%d')
out_file = os.path.join(dst_dir, f'memory-snapshot-{ts}.md')

count = 0
with open(out_file, 'w', encoding='utf-8') as out:
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.md'):
            continue
        with open(os.path.join(src, fn), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        out.write(f'\n\n# === {fn} ===\n\n')
        out.write(content)
        count += 1

# Directory archive
archive_dir = os.path.join(dst_dir, f'archive-{ts}')
shutil.copytree(src, archive_dir, dirs_exist_ok=True)
print(f'Memory autobackup: {count} files -> {out_file} + {archive_dir}')
