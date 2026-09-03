#!/usr/bin/env python3
# Agent metrics ETL (P2)
# Reads state/agents_activity.json + pipeline_state.db -> memory/agent_metrics.json
import json, os, sys
sys.path.insert(0, '.')
from zarabotok.pipeline_v3 import db

# Load state/agents_activity.json
state_path = 'zarabotok/pipeline_v3/state/agents_activity.json'
data = []
if os.path.exists(state_path):
    try:
        with open(state_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
    except Exception:
        data = []

# Aggregate by agent
metrics = {}
for entry in data:
    if not isinstance(entry, dict):
        continue
    agent = entry.get('agent', 'unknown')
    if agent not in metrics:
        metrics[agent] = {'count': 0, 'success': 0, 'error': 0, 'last_ts': None}
    metrics[agent]['count'] += 1
    status = entry.get('status', '').lower()
    if status in ('ok', 'success', 'done'):
        metrics[agent]['success'] += 1
    elif status in ('error', 'fail', 'failed'):
        metrics[agent]['error'] += 1
    ts = entry.get('ts')
    if ts and (not metrics[agent]['last_ts'] or ts > metrics[agent]['last_ts']):
        metrics[agent]['last_ts'] = ts

# Also pull from DB
try:
    p = db.pool()
    rows = p.query("SELECT agent, COUNT(*) as c FROM activities GROUP BY agent")
    for r in rows:
        agent, c = r[0], r[1]
        if agent not in metrics:
            metrics[agent] = {'count': 0, 'success': 0, 'error': 0, 'last_ts': None}
        metrics[agent]['count'] += c
    p.close()
except Exception as e:
    print('DB ETL skipped:', e)

out = 'memory/agent_metrics.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(metrics, f, ensure_ascii=False, indent=2)
print(f'Agent metrics ETL: {len(metrics)} agents -> {out}')
for k, v in list(metrics.items())[:5]:
    print(f'  {k}: {v}')
