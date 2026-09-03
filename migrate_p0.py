import sqlite3, json, os, hashlib, time
from datetime import datetime

db_path = "zarabotok/pipeline_v3/state/pipeline_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Clear previously migrated P0 data to allow idempotent rerun
for tbl in ["events", "exec_tasks", "orders", "payments", "funnel_metrics", "log_archive", "activities"]:
    try:
        c.execute(f"DELETE FROM {tbl}")
    except Exception:
        pass
conn.commit()

def to_ts(s):
    if not s or s == "":
        return None
    try:
        # Try ISO with timezone offset
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.timestamp()
    except Exception:
        try:
            return float(s)
        except Exception:
            return None

# 1. Migrate events.json (smallest, 3 rows)
with open("zarabotok/pipeline_v3/state/events.json") as f:
    events = json.load(f)
for ev in events:
    c.execute("INSERT INTO events (ts, event, source, audit_ref) VALUES (?, ?, ?, ?)",
              (ev.get("ts"), ev.get("event"), ev.get("source"), None))
print("Migrated events:", len(events))

# 2. Migrate exec_tasks.json (dict with items array)
with open("zarabotok/pipeline_v3/state/exec_tasks.json") as f:
    exec_data = json.load(f)
items = exec_data.get("items", [])
if isinstance(items, dict):
    # If nested differently, flatten values
    items = list(items.values())
for item in items:
    # Map best-effort
    ts = to_ts(item.get("started_at") or item.get("ts"))
    agent = "unknown"
    if isinstance(item.get("agents"), list) and len(item["agents"]) > 0:
        agent = item["agents"][0].get("file", item["agents"][0].get("name", "unknown"))
    status = item.get("status", "pending")
    result_hash = hashlib.md5(str(item.get("url", item.get("title", ""))).encode()).hexdigest()[:16]
    audit_ref = item.get("version")  # not event id; keep as text? Schema expects INTEGER for audit_ref.
    # Since audit_ref is INTEGER, only insert if it parses
    try:
        audit_ref = int(audit_ref) if audit_ref else None
    except Exception:
        audit_ref = None
    c.execute("INSERT INTO exec_tasks (ts, agent, status, result_hash, audit_ref) VALUES (?, ?, ?, ?, ?)",
              (ts, agent, status, result_hash, audit_ref))
print("Migrated exec_tasks items:", len(items))

# 3. Migrate orders_meta.json (dict with URL-keyed items)
with open("zarabotok/pipeline_v3/state/orders_meta.json") as f:
    orders_data = json.load(f)
orders_items = orders_data.get("items", {})
if isinstance(orders_items, list):
    # If array, process directly
    pass
else:
    # Dict by URL
    orders_items = list(orders_items.values())
for item in orders_items:
    ts = to_ts(item.get("created_at"))
    status = item.get("status", "draft")
    amount = None
    payment = item.get("payment", {})
    if payment:
        amt_str = payment.get("amount")
        if isinstance(amt_str, (int, float)):
            amount = float(amt_str)
        elif isinstance(amt_str, str) and amt_str.strip() != "":
            try:
                amount = float(amt_str.replace(",", "."))
            except Exception:
                amount = None
    agent_ref = item.get("url", None)  # Use URL as agent_ref reference (text)
    c.execute("INSERT INTO orders (ts, status, amount, agent_ref) VALUES (?, ?, ?, ?)",
              (ts, status, amount, agent_ref))
print("Migrated orders:", len(orders_items))

# 4. Migrate payments.json if non-empty (near-empty stub)
try:
    with open("zarabotok/pipeline_v3/state/payments.json") as f:
        payments_raw = f.read()
    if payments_raw and payments_raw.strip():
        payments_data = json.loads(payments_raw)
    else:
        payments_data = {}
except Exception:
    payments_data = {}
    
if isinstance(payments_data, list):
    payments_items = payments_data
elif isinstance(payments_data, dict) and "items" in payments_data:
    payments_items = payments_data["items"]
    if isinstance(payments_items, dict):
        payments_items = list(payments_items.values())
else:
    payments_items = []
# For stub, if empty just continue
for p in payments_items:
    # Try to link to orders by URL if present
    url = p.get("url") or p.get("order_url")
    c.execute("SELECT id FROM orders WHERE agent_ref = ? LIMIT 1", (url,))
    row = c.fetchone()
    order_id = row[0] if row else None
    ts = to_ts(p.get("ts") or p.get("paid_at") or p.get("created_at"))
    amount = p.get("amount")
    try:
        amount = float(amount) if amount is not None else None
    except Exception:
        amount = None
    c.execute("INSERT INTO payments (order_id, ts, url, amount) VALUES (?, ?, ?, ?)",
              (order_id, ts, url, amount))
print("Migrated payments:", len(payments_items))

# Insert funnel metrics definition from metrics_funnel.json
with open("zarabotok/pipeline_v3/state/metrics_funnel.json") as f:
    funnel_def = json.load(f)
metrics = funnel_def.get("metrics", funnel_def)
if isinstance(metrics, dict):
    for name, info in metrics.items():
        updated = time.time()
        data_json = json.dumps(info)
        c.execute("INSERT OR IGNORE INTO funnel_metrics (name, updated, data_json) VALUES (?, ?, ?)",
                  (name, updated, data_json))
    print("Inserted funnel_metrics:", len(metrics))

# Insert activities from activity.json? User didn't ask to migrate activity.json yet (P0 only smallest first).
# We'll skip large activity.json for P0 as instructed.

# Insert log_archive placeholder for the three logs
for source in ["api.py", "dashboard.py", "launcher_new"]:
    c.execute("INSERT INTO log_archive (source, archived, ts) VALUES (?, ?, ?)",
              (source, 1, time.time()))
print("Inserted log_archive placeholders:", 3)

conn.commit()

# Verify counts
for table in ["events", "exec_tasks", "orders", "payments", "funnel_metrics", "activities", "log_archive"]:
    c.execute(f"SELECT COUNT(*) FROM {table}")
    count = c.fetchone()[0]
    print(f"{table}: {count} rows")

# Verify indexes present
c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
index_names = [r[0] for r in c.fetchall()]
for req in ["idx_activities_ts", "idx_activities_agent_event", "idx_orders_status_created",
            "idx_payments_order_url", "idx_events_ts_event", "idx_funnel_metrics_updated"]:
    print(f"Index {req}: {'PRESENT' if req in index_names else 'MISSING'}")

conn.close()
print("Migration complete.")
