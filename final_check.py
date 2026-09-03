import os
items = {
    'DB': 'zarabotok/pipeline_v3/state/pipeline_state.db',
    'Backup dir': 'zarabotok/pipeline_v3/state/backup/',
    'Verify script': 'scripts/verify_db_indexes.py',
    'Execution doc': 'memory/db_execution.md',
    'Original events': 'zarabotok/pipeline_v3/state/events.json',
    'Original exec_tasks': 'zarabotok/pipeline_v3/state/exec_tasks.json',
    'Original orders_meta': 'zarabotok/pipeline_v3/state/orders_meta.json',
}
for k,v in items.items():
    exists = os.path.exists(v)
    size = os.path.getsize(v) if exists else 'N/A'
    status = 'OK' if exists else 'MISSING'
    print(k + ': ' + status + '  (' + v + ') size=' + str(size))
