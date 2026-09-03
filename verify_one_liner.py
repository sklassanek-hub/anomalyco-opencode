import sqlite3, time, os
DB = 'zarabotok/pipeline_v3/state/pipeline_state.db'
assert os.path.exists(DB), 'DB missing'
conn = sqlite3.connect(DB); conn.execute('PRAGMA foreign_keys=ON'); c = conn.cursor()
t = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
assert t >= {'activities','exec_tasks','orders','payments','events','funnel_metrics','log_archive'}, 'table missing'
idx = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()}
for i in ['idx_activities_ts','idx_activities_agent_event','idx_orders_status_created','idx_payments_order_url','idx_events_ts_event','idx_funnel_metrics_updated']: assert i in idx, f'index {i} missing'
for tbl,expected in [('events',3),('exec_tasks',21),('orders',8),('funnel_metrics',4),('log_archive',3)]:
    c.execute(f'SELECT COUNT(*) FROM {tbl}'); assert c.fetchone()[0]>=expected, f'{tbl} count low'
c.execute('PRAGMA journal_mode'); assert c.fetchone()[0]=='wal', 'not WAL'
c.execute("SELECT sql FROM sqlite_master WHERE name='payments'"); assert 'REFERENCES orders' in c.fetchone()[0]
start = time.perf_counter(); c.execute("EXPLAIN QUERY PLAN SELECT * FROM events WHERE ts>0 AND event='kill_switch_set' LIMIT 10"); plan = ' '.join(str(p[3]) for p in c.fetchall() if len(p)>3); assert 'INDEX' in plan; print('PASS:', plan[:80]); print('TIME:', round(time.perf_counter()-start,4)); conn.close()
