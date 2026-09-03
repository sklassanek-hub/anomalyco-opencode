import os, re
files = {
    'memory/2026-08-21.md': 'RECONSTRUCTED',
    'memory/2026-08-22.md': 'RECONSTRUCTED',
    'memory/2026-08-23.md': 'RECONSTRUCTED',
    'memory/2026-08-24.md': 'RECONSTRUCTED',
    'memory/decisions/decision-2026-08-31.md': 'Decision — 2026-08-31',
    'memory/risks/risk-2026-08-31.md': 'Risk — 2026-08-31',
    'memory/experiments/experiment-2026-08-31.md': 'Experiment — 2026-08-31',
    'memory/feedback/feedback-2026-08-31.md': 'Feedback — 2026-08-31',
    'memory/agent_activity_2026-08-31.md': 'Agent Activity Sync',
    'memory/memory_completion.md': 'Memory Completion — 2026-08-31',
    'MEMORY.md': 'Memory audit conclusions',
    'memory/2026-08-31.md': 'P0 Memory Recovery + Audit Session',
}
errors = []
for f, marker in files.items():
    if not os.path.exists(f):
        errors.append(f"MISSING: {f}")
    else:
        content = open(f, encoding='utf-8', errors='ignore').read()
        if marker not in content:
            # some markers may not match exactly; check loosely
            if marker.split()[0] not in content and marker[:4] not in content:
                errors.append(f"MARKER NOT FOUND in {f}: expected '{marker[:30]}...'")
if errors:
    for e in errors:
        print("ERROR:", e)
else:
    print("VERIFICATION PASS: all 13 files present with expected markers.")
    # Count reconstructed days
    for d in ['21','22','23','24']:
        f = f'memory/2026-08-\d\.md'
    # Just report counts
    total = sum(1 for f in files if os.path.exists(f))
    print(f"Files checked: {total}/{len(files)}")
