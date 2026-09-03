with open('zarabotok/pipeline_v3/modules/executor.py', encoding='utf-8') as f:
    lines = f.read().splitlines()
insert_lines = [
    '    # Auth middleware wire (P0) - token validation + audit + rate_limit',
    '    try:',
    '        if auth is not None:',
    '            auth.init_auth_guard()',
    '    except Exception as e:',
    '        import logging',
    '        logging.getLogger(__name__).warning("auth init guard skipped: %s", e)',
    ''
]
insert_idx = None
for i, line in enumerate(lines):
    if 'kill_switch_active at create_exec_task' in line:
        for j in range(i, min(i+10, len(lines))):
            if 'return {"ok": False' in lines[j] or '"status": "stopped"' in lines[j]:
                insert_idx = j + 1
                break
        break
if insert_idx is None:
    insert_idx = 225
new_lines = lines[:insert_idx] + insert_lines + lines[insert_idx:]
with open('zarabotok/pipeline_v3/modules/executor.py', 'w', encoding='utf-8') as f:
    for line in new_lines:
        f.write(line + '\n')
print('inserted at', insert_idx)
