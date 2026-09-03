#!/usr/bin/env python3
"""DB index verification script for pipeline_state.db P0.
Checks schema, indexes, FK constraints, row counts, and query timing."""

import sqlite3, time, os, sys

DB = "zarabotok/pipeline_v3/state/pipeline_state.db"
REQUIRED_TABLES = ["activities", "exec_tasks", "orders", "payments", "events", "funnel_metrics", "log_archive"]
REQUIRED_INDEXES = [
    "idx_activities_ts", "idx_activities_agent_event",
    "idx_orders_status_created", "idx_payments_order_url",
    "idx_events_ts_event", "idx_funnel_metrics_updated",
]

def main():
    if not os.path.exists(DB):
        print("FAIL: DB not found at", DB)
        sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # Schema check
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in c.fetchall()}
    missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
    if missing_tables:
        print("FAIL: Missing tables:", missing_tables)
    else:
        print("PASS: All required tables present.")

    # Index check
    c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
    index_names = {r[0] for r in c.fetchall()}
    missing_idx = [i for i in REQUIRED_INDEXES if i not in index_names]
    if missing_idx:
        print("FAIL: Missing indexes:", missing_idx)
    else:
        print("PASS: All required indexes present.")
    print("Indexes found:", sorted(index_names & set(REQUIRED_INDEXES)))

    # Foreign key schema check (verify FK clauses in table SQL)
    c.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    fk_ok = True
    for sql, in c.fetchall():
        if sql and ("REFERENCES" in sql.upper() or "FOREIGN KEY" in sql.upper()):
            pass  # FKs defined
    # Explicit payments FK to orders
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='payments'")
    payments_sql = c.fetchone()
    if payments_sql and payments_sql[0] and "REFERENCES orders" in payments_sql[0]:
        print("PASS: payments -> orders FK defined.")
    else:
        print("FAIL: payments FK missing.")
        fk_ok = False
    # Explicit exec_tasks FK to events
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exec_tasks'")
    exec_sql = c.fetchone()
    if exec_sql and exec_sql[0] and "REFERENCES events" in exec_sql[0]:
        print("PASS: exec_tasks -> events FK defined.")
    else:
        print("FAIL: exec_tasks FK missing.")
        fk_ok = False

    # Row counts
    for t in REQUIRED_TABLES:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        count = c.fetchone()[0]
        print(f"INFO: {t} rows = {count}")

    # Timing / query plan checks
    queries = [
        ("activities ts index", "SELECT * FROM activities WHERE ts > 0 ORDER BY ts DESC LIMIT 10"),
        ("activities agent_event index", "SELECT * FROM activities WHERE agent = 'test' AND event = 'kill_switch_set' LIMIT 10"),
        ("orders status_created index", "SELECT * FROM orders WHERE status = 'won' ORDER BY ts DESC LIMIT 10"),
        ("payments order_url index", "SELECT * FROM payments WHERE order_id = 1 LIMIT 10"),
        ("events ts_event index", "SELECT * FROM events WHERE ts > 0 AND event = 'kill_switch_set' LIMIT 10"),
        ("funnel_metrics updated index", "SELECT * FROM funnel_metrics WHERE updated > 0 ORDER BY updated DESC LIMIT 10"),
    ]
    for label, sql in queries:
        start = time.perf_counter()
        c.execute(f"EXPLAIN QUERY PLAN {sql}")
        plan = c.fetchall()
        # Check that plan uses index (contains INDEX or PK usage for scan)
        using_index = any("INDEX" in str(p[3] if len(p) > 3 else p) for p in plan)
        # Actually EXPLAIN QUERY PLAN returns (id, parent, notused, detail)
        detail = " ".join(str(p[3]) for p in plan if len(p) > 3)
        using_index = "INDEX" in detail or "USING INDEX" in detail
        elapsed = time.perf_counter() - start
        status = "PASS (index used)" if using_index else "WARN (check plan)"
        print(f"INFO: Query '{label}' -> {status} | time={elapsed:.4f}s | plan snippet: {detail[:120]}")

    # Verify DB pragma settings (WAL, FK on)
    c.execute("PRAGMA journal_mode")
    mode = c.fetchone()[0]
    c.execute("PRAGMA foreign_keys")
    fk_on = c.fetchone()[0]
    print(f"INFO: journal_mode={mode}, foreign_keys={fk_on}")
    if mode != "wal":
        print("WARN: journal_mode is not WAL (recommended for pipeline writes).")

    conn.close()
    print("Verification complete.")

if __name__ == "__main__":
    main()
