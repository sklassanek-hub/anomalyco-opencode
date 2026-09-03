import sqlite3, os

db_path = "zarabotok/pipeline_v3/state/pipeline_state.db"
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("PRAGMA journal_mode=WAL;")
c.execute("PRAGMA foreign_keys=ON;")
c.execute("PRAGMA synchronous=NORMAL;")

# Activities
c.execute("CREATE TABLE activities (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, event TEXT, meta TEXT, kill_active INTEGER DEFAULT 0)")
c.execute("CREATE INDEX idx_activities_ts ON activities(ts DESC)")
c.execute("CREATE INDEX idx_activities_agent_event ON activities(agent, event)")

# Exec tasks (audit_ref FK to events)
c.execute("CREATE TABLE exec_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, status TEXT, result_hash TEXT, audit_ref INTEGER, FOREIGN KEY (audit_ref) REFERENCES events(id) ON DELETE SET NULL)")

# Orders
c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, status TEXT, amount REAL, agent_ref TEXT)")
c.execute("CREATE INDEX idx_orders_status_created ON orders(status, ts DESC)")

# Payments
c.execute("CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, ts REAL, url TEXT, amount REAL, FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE)")
c.execute("CREATE INDEX idx_payments_order_url ON payments(order_id, url)")

# Events
c.execute("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, event TEXT, source TEXT, audit_ref INTEGER)")
c.execute("CREATE INDEX idx_events_ts_event ON events(ts DESC, event)")

# Funnel metrics
c.execute("CREATE TABLE funnel_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, updated REAL, data_json TEXT)")
c.execute("CREATE INDEX idx_funnel_metrics_updated ON funnel_metrics(updated DESC)")

# Log archive
c.execute("CREATE TABLE log_archive (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, archived INTEGER DEFAULT 0, ts REAL)")

conn.commit()
conn.close()
print("Created", db_path)
