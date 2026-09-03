import re, os
# Extract Aug 21-24 events from multiple sources
events = {'21': [], '22': [], '23': [], '24': []}
for path in [
    'zarabotok/pgdata/pg.log',
    'zarabotok/pipeline/state/threads.json',
    'zarabotok/pipeline/tools/singbox/config.new.json.log',
    'zarabotok/pipeline_old_20260802/state/threads/tg_frilans_1065_15.json',
    'zarabotok/pipeline_v3/state/jobs.json',
    'zarabotok/pipeline_v3/state/watchdog.log',
]:
    if not os.path.exists(path):
        continue
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception:
        continue
    for day in events:
        # Match various date formats
        for pat in [
            rf'{day}\.08\.\d{{4}}.{{0,150}}',
            rf'2026-08-{day}.{{0,150}}',
        ]:
            for m in re.finditer(pat, text):
                snippet = m.group(0)[:200]
                events[day].append(f'{os.path.basename(path)}: {snippet}')

# Save to memory
with open('memory/cp4_memory_gap_extracted.md', 'w', encoding='utf-8') as f:
    f.write('# CP-4 Memory Gap Reconstruction — Aug 21-24\n\n')
    f.write('Extracted from logs/state across the workspace.\n\n')
    for day in ['21', '22', '23', '24']:
        f.write(f'## Aug 21 (day {day})\n\n')
        if events[day]:
            for e in events[day][:20]:
                f.write('- ' + e + '\n')
        else:
            f.write('- No direct events found\n')
        f.write('\n')

# Also update 2026-08-21..24.md with snippets
for day, fname in [('21', '2026-08-21.md'), ('22', '2026-08-22.md'), ('23', '2026-08-23.md'), ('24', '2026-08-24.md')]:
    p = 'memory/' + fname
    with open(p, 'a', encoding='utf-8') as f:
        f.write(f'\n\n## Reconstructed from logs (CP-4)\n\n')
        for e in events[day][:10]:
            f.write('- ' + e + '\n')
        if not events[day]:
            f.write('- No direct log entries for this day\n')
print('CP-4 reconstruction done: events extracted to memory/cp4_memory_gap_extracted.md and updated 2026-08-21..24.md')
print('Per-day counts:', {d: len(events[d]) for d in events})
