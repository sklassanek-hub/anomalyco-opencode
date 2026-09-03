#!/usr/bin/env python3
# Generate release notes / changelog (P2)
import os, json, datetime
from pathlib import Path

# Walk all memory/*.md to find recent changes (today)
today = datetime.date.today().isoformat()
notes = []
for fn in sorted(os.listdir('memory')):
    if not fn.endswith('.md'):
        continue
    p = os.path.join('memory', fn)
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    if today in text or fn == f'{today}.md':
        # Extract first heading
        first_line = next((l.strip('#').strip() for l in text.splitlines() if l.startswith('#')), fn)
        notes.append(f'- **{fn}**: {first_line}')

out = 'RELEASE_NOTES.md'
with open(out, 'w', encoding='utf-8') as f:
    f.write(f'# Release Notes — {today}\n\n')
    f.write('\n'.join(notes) if notes else '- No notes for today')
    f.write('\n')
print(f'Release notes: {out} ({len(notes)} items)')
