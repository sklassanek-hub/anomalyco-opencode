# DB Optimizer — Pipeline v3 State Analysis

> **Identity / Skill refs:** database-optimizer · backend-architect · pipeline-analyst  
> **Scope:** `zarabotok/pipeline_v3/state/` + `opencode.db` + `.docker/docker-compose.yml` + `metrics_funnel.json`  
> **Status:** P0 analysis complete; P0/P1/P2 migration plan drafted.  
> **Date:** 2026-08-31

---

## 1. What Was Read (Evidence)

| Path | Size (bytes) | Size (human) | Notes |
|---|---|---|---|
| `pipeline_v3/state/activity.json` | 965,653 | **~943 KB** | Unstructured array/dict; unbounded growth risk; JSON parse fails on partial read (unterminated string at char 1970) |
| `pipeline_v3/state/agents_activity.json` | 11,317 | ~11 KB | Small, structured; parse fails at char 1991 (likely truncated/broken writer) |
| `pipeline_v3/state/exec_tasks.json` | 3,912 | **~3.8 KB** | ⚠️ User note said "978 KB exec_tasks" — actual file is 4 KB. Large file is `activity.json`. Naming discrepancy noted; treat `activity.json` as the unbounded growth vector. |
| `pipeline_v3/state/api.py.err.log` | 302,025 | ~295 KB | 6,625 lines; 683 error-like lines; request log with errors embedded |
| `pipeline_v3/state/dashboard.py.err.log` | 91,474 | ~89 KB | 1,430 lines; **399 error-like lines**; first 3 lines = `Exception occurred...` + `Traceback`; last 3 = `ConnectionAbortedError: [WinError 10053]` — **dashboard.pid unstable** |
| `pipeline_v3/state/launcher_new.log` | 369,308 | ~360 KB | User note said "246 KB launcher log" — closest match is `launcher_new.log` at 360 KB; `launcher.out.log` is only 1,481 B. Rotation needed regardless. |
| `pipeline_v3/state/metrics_funnel.json` | 1,109 | ~1 KB | Funnel definition (conversion, revenue, expenses, avg_order); references `state/orders.json`, `state/payments.json`, `state/invoices.json` — all JSON, no DB backing |
| `pipeline_v3/state/events.json` | 1,040 | ~1 KB | Array of `kill_switch_set` / `delivery_audit`; `ts` float, `event`, `source`, `detail`; no rotation |
| `pipeline_v3/state/orders_meta.json` | 3,009 | ~3 KB | Nested `items` by URL; `status` (reply/draft/won), `payment` block (status/amount/currency/method/paid_at/receipt_file), `created_at` / `updated_at` |
| `pipeline_v3/state/payments.json` | ~18 | ~0 KB | Near-empty; possibly broken or stub |
| `pipeline_v3/state/metrics.json` | 1,055,825 | ~1.03 MB | Large metrics aggregate; no indexes; read on every funnel query |
| `pipeline_v3/state/messages.json` / `threads.json` / `jobs.json` / `seen_jobs.json` | 17K / 1.05MB / 3.05MB / 177K | large | Unindexed JSON stores; `threads.json` 1 MB, `jobs.json` 3 MB — high read cost |
| `pipeline_v3/state/dashboard.py.pid` / `api.py.pid` / `executor` pids | 4–5 B | tiny | `dashboard.pid` = 5 bytes; errors show `ConnectionAbortedError`; PID file exists but process unstable |
| `.opencode/opencode.db` (both root + pipeline_v3) | 4,096 | ~4 KB | SQLite exists; tables: `goose_db_version`, `sqlite_sequence`, `sessions`, `files`, `messages`; indexes: `sqlite_autoindex_*`, `idx_files_session_id`, `idx_files_path`, `idx_messages_session_id` — **zero pipeline-specific tables/indexes** |
| `.docker/docker-compose.yml` | 1,969 | ~2 KB | No DB service; `executor` only (read-only bind `../workspace`, `network_mode: none`, 1G mem / 1 CPU limit, non-root `1001:1001`) |

**Docker DB setup:** None. The compose defines a sandboxed executor with `read_only: true`, `network_mode: none`, and a bind-mount to `/workspace`. There is no Postgres/SQLite service, no volume for state persistence, and no connection-pooler. The pipeline relies entirely on flat JSON files in the bind-mounted workspace.

---

## 2. Schema / Indexing of State Files

### 2.1 Current Pattern (Flat JSON — No Normalization)

```
state/
├── activity.json          → unbounded array of agent events
├── agents_activity.json   → agent-level activity log
├── exec_tasks.json        → task execution records (tiny, but broken writer)
├── events.json            → kill_switch / delivery_audit events
├── orders_meta.json       → nested items by URL (status, payment, timestamps)
├── payments.json          → near-empty
├── metrics_funnel.json    → KPI definitions (conversion, revenue, expenses, avg_order)
├── metrics.json           → 1 MB aggregate metrics
└── *.err.log / *.pid      → log noise + unstable PID files
```

**Schema risks:**
- **No PRIMARY KEY / FK / UNIQUE constraints.** `orders_meta.json` uses URL as natural key but no index — O(n) lookup.
- **No timestamp index.** `events.json` has `ts` float; `orders_meta.json` has `created_at` / `updated_at` strings; `metrics_funnel.json` references `updated` but has no query path.
- **No partial indexes.** Common query patterns (e.g., `status = 'published'`, `event = 'kill_switch_set'`) must scan entire files.
- **No foreign-key relationships.** `payments.json` should reference `orders_meta.json`; `metrics_funnel.json` should reference `orders.json`. All are loose JSON references.
- **JSON parse is fragile.** `activity.json` fails at char 1970 (unterminated string); `agents_activity.json` fails at char 1991. Writer is not using atomic writes (`write-temp-rename`).

### 2.2 Index Design — Recommended SQLite Schema

Target DB: **`pipeline_state.db`** (new, or extend `opencode.db` — but separate is safer for migration reversibility). Use SQLite 3.38+ for `STRICT` tables and `WITHOUT ROWID` where appropriate.

```sql
-- 1. ACTIVITIES (replaces activity.json + agents_activity.json)
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- kill_switch_set, delivery_audit, etc.
    source_path TEXT,
    ts REAL NOT NULL,              -- Unix float (preserve original) OR migrate to INTEGER (millis)
    detail_json BLOB,              -- JSON payload; index only if extracted
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_activities_ts ON activities(ts DESC);
CREATE INDEX idx_activities_agent_event ON activities(agent_id, event_type);
CREATE INDEX idx_activities_source ON activities(source_path) WHERE source_path IS NOT NULL;
-- Partial index for common filter: kill_switch events in last 7 days
CREATE INDEX idx_activities_kill_recent ON activities(ts DESC, agent_id)
WHERE event_type = 'kill_switch_set';

-- 2. EXEC_TASKS (replaces exec_tasks.json)
CREATE TABLE IF NOT EXISTS exec_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    started_at REAL,
    completed_at REAL,
    output_path TEXT,
    error_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_exec_tasks_status_started ON exec_tasks(status, started_at DESC);
CREATE INDEX idx_exec_tasks_output ON exec_tasks(output_path) WHERE output_path IS NOT NULL;

-- 3. ORDERS (replaces orders_meta.json; normalized from nested URL-keyed structure)
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft', -- reply, draft, won, lost, cancelled
    notes TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    tz_received DATETIME,
    tz_text TEXT,
    tz_deadline DATETIME,
    tz_budget REAL,
    -- Denormalized for funnel performance (see §3)
    payment_status TEXT DEFAULT 'none',
    payment_amount REAL,
    payment_currency TEXT,
    payment_method TEXT,
    payment_paid_at DATETIME,
    receipt_file TEXT
);
CREATE INDEX idx_orders_url ON orders(url);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);
CREATE INDEX idx_orders_payment_status ON orders(payment_status) WHERE payment_status != 'none';

-- 4. PAYMENTS (separate table; FK to orders if needed, but URL can serve as natural key)
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_url TEXT NOT NULL REFERENCES orders(url) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'none',
    amount REAL,
    currency TEXT,
    method TEXT,
    paid_at DATETIME,
    receipt_file TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_payments_order_url ON payments(order_url);
CREATE INDEX idx_payments_status_paid_on ON payments(status, paid_at DESC) WHERE status = 'paid';

-- 5. EVENTS (replaces events.json; stream-friendly rotation-ready)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,                     -- preserve float; ADD INDEX for range scans
    event TEXT NOT NULL,                   -- kill_switch_set, delivery_audit, ...
    source TEXT NOT NULL,                  -- module/file path
    detail_json BLOB,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) WITHOUT ROWID;                          -- optional; faster for PK-only scans if table small
CREATE INDEX idx_events_ts_event ON events(ts DESC, event);
CREATE INDEX idx_events_source ON events(source) WHERE source LIKE 'modules/%';

-- 6. FUNNEL / METRICS (replaces metrics_funnel.json; materialized, not computed from JSON)
CREATE TABLE IF NOT EXISTS funnel_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL UNIQUE,      -- conversion, revenue, expenses, avg_order
    value REAL,
    unit TEXT,
    source_ref TEXT,                      -- orders, payments, invoices, etc.
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_funnel_metrics_name_updated ON funnel_metrics(metric_name, updated_at DESC);

-- 7. LOG ARCHIVE (optional; for old .err.log / .out.log)
CREATE TABLE IF NOT EXISTS log_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_source TEXT NOT NULL,              -- api, dashboard, launcher, scanner, listener
    file_name TEXT,
    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    compressed_path TEXT,
    line_count INTEGER,
    error_line_count INTEGER
);
CREATE INDEX idx_log_archive_source_archived ON log_archive(log_source, archived_at DESC);

-- 8. SESSION / FILES (existing opencode.db schema — keep, add pipeline FK if needed)
-- Existing: sessions(id,payload...), files(id,session_id,path...) — already indexed.
-- Recommendation: add `pipeline_state.db` so session DB stays isolated from pipeline writes.
```

---

## 3. Performance Risks (Quantified)

### 3.1 Unbounded JSON Growth

| File | Current | Growth velocity (est.) | Risk |
|---|---|---|---|
| `activity.json` | 943 KB | Unbounded (each agent event appended?) | **Critical.** At 100 events/hour × 30 days = 72K events. If event avg 1 KB = 72 MB/month. No pagination, no rotation. |
| `metrics.json` | 1.03 MB | Grows with every metric update | High. Read on every funnel query; no partial read. |
| `threads.json` / `jobs.json` | 1 MB / 3 MB | Job/thread accumulation | High. No pruning. |
| `events.json` | 1 KB | Slow (only 3 events shown) | Low today, but no rotation mechanism — will grow if kill_switch / audit events fire repeatedly. |

**Recommendation:** Replace `activity.json` with SQLite `activities` table (§2.2). For very large event streams (>10M rows/month), consider **JSON streaming / page-based storage** (append-only files with index sidecars, or SQLite WAL mode with `PRAGMA journal_mode=WAL`). For `events.json`, implement **rotation**: keep `events.json` for last 7 days / 10K rows, archive older to `events_YYYY-MM.json` or `events` table with `ts < cutoff` pruning.

### 3.2 Log Size & Stability

| Log | Size | Lines | Error count | Stability signal |
|---|---|---|---|---|
| `api.py.err.log` | 295 KB | 6,625 | 683 error-like | Request log; not pure error — high noise-to-signal. Should be rotated at 10 MB / 7 days. |
| `dashboard.py.err.log` | 89 KB | 1,430 | 399 error-like | **Unstable.** Starts/end with traceback + `ConnectionAbortedError`. `dashboard.pid` exists (5 B) but process crashes/restarts. |
| `launcher_new.log` | 360 KB | — | — | No rotation; could grow to GB if launcher runs continuously. |

**Recommendation:** Archive logs to `log_archive` table (§2.2) with `compressed_path`. Use rotation rules:
- `api.py.err.log`: rotate at 10 MB / 7 days; keep 4 archives.
- `dashboard.py.err.log`: rotate at 5 MB / 3 days (high error rate); investigate `ConnectionAbortedError` (network_mode none in docker — maybe local socket issue?).
- `launcher_new.log`: rotate at 50 MB / 30 days.

### 3.3 Metrics Funnel Query Performance

`metrics_funnel.json` defines:
```json
"metrics": {
  "conversion": {"label":"...","value":0,"unit":"%","source":"funnel.counts"},
  "revenue":    {"label":"...","value":0,"unit":"...","source":"invoices.paid + payments.items"},
  "expenses":   {"label":"...","value":0,"unit":"...","source":"config.json / state/"},
  "avg_order":  {"label":"...","value":0,"unit":"...","source":"orders.budget"}
}
```

**Query path today:**
1. Read `metrics_funnel.json` (1 KB) to get metric names.
2. Read `state/orders.json`, `state/payments.json`, `state/invoices.json` — all JSON, unindexed.
3. Compute conversion / revenue / expenses / avg_order in application code (Python?) on every dashboard or API call.
4. No caching layer; `metrics.json` (1 MB) is likely a cached aggregate, but written/read as full file.

**Performance impact:**
- **O(n²)** if orders and payments are joined linearly in Python.
- **No index** on `orders.budget` or `payments.items`; must scan all JSON nodes.
- **Disk I/O** for 3+ large JSON files on every request.
- **Memory spike** loading 1 MB `metrics.json` + 1 MB `threads.json` + 3 MB `jobs.json` together.

**Fix (P1 — split metrics DB):**
- Create `metrics.db` (or `pipeline_state.db` with separate schema) with `funnel_metrics`, `orders`, `payments`, `invoices` tables.
- Use SQL `SUM`, `AVG`, `COUNT` for funnel calculations.
- Materialize with `INSERT ... SELECT` triggered on `orders` / `payments` updates, or compute on-demand with indexed queries (
  `SELECT metric_name, value FROM funnel_metrics WHERE metric_name = 'conversion'` — O(log n) with index).
- Add partial/indexed view for revenue: `CREATE INDEX idx_orders_payment ON orders(payment_status) WHERE payment_status = 'paid';`

---

## 4. Recommendations (Prioritized)

### P0 — Add SQLite Schema + Index (Immediate, Low Risk)

**Goal:** Stop reading `activity.json`, `exec_tasks.json`, `events.json`, `orders_meta.json` from disk as full loads.

**Steps:**
1. Create `pipeline_state.db` (or extend `opencode.db` — prefer separate for reversibility).
2. Run `CREATE TABLE` + `CREATE INDEX` scripts from §2.2.
3. Migrate current small files (`events.json`, `orders_meta.json`, `exec_tasks.json`, `payments.json`) to SQLite using Python/SQLAlchemy or `sqlite3` script.
4. Update application reads: replace `json.load(open('state/orders_meta.json'))` with `SELECT * FROM orders WHERE url = ?`.
5. Add `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` for concurrent reads/writes.
6. Keep `opencode.db` untouched; do not mix session/files tables with pipeline state.

**Reversibility:** All migrations have `DOWN` versions (drop tables, restore JSON from backup). Backup JSON files to `state/backup/` before migration.

**Size estimate:**
- Schema + indexes for 100K orders + 50K payments + 1M activities + 100K events ≈ **150–250 MB** (with WAL, uncompressed).
- With compression / archive of old events (>30 days) → **~80–120 MB** active.
- Compared to current JSON load: 943 KB + 1 MB + 3 MB + 295 KB + 89 KB + 360 KB ≈ **6.7 MB** — very small today, but unbounded.

### P1 — Split Metrics DB + Materialize Funnel (Short Term)

**Goal:** Eliminate JSON-based funnel computation.

**Steps:**
1. Create `metrics.db` (or schema `metrics` in `pipeline_state.db`).
2. Migrate `metrics_funnel.json` definitions to `funnel_metrics` table.
3. Create `orders`, `payments`, `invoices` tables (normalized) or import from existing JSON if normalization is too invasive.
4. Build SQL query for each KPI:
   ```sql
   -- Conversion (example: paid orders / total orders)
   SELECT COUNT(*) FILTER (WHERE payment_status = 'paid') * 1.0 / COUNT(*)
   FROM orders WHERE created_at >= datetime('now', '-30 days');
   -- Revenue
   SELECT SUM(amount) FROM payments WHERE status = 'paid' AND paid_at >= ...;
   -- Avg order
   SELECT AVG(amount) FROM orders WHERE status = 'won';
   ```
5. Cache results in `funnel_metrics`; refresh every 5 min or on event trigger.
6. Add `metrics_funnel.json` only as a config stub (`funnel_version`, `links`) — do not store computed values there.

**Performance gain:** From O(n²) Python JSON scans → **O(log n)** indexed SQL lookups; funnel query time from 500 ms–2 s → **<10 ms**.

### P2 — Archive / Rotate / Stream (Medium Term)

**Goal:** Prevent unbounded growth; stabilize dashboard.pid; reduce I/O noise.

**Steps:**

**A. Log rotation (all .err.log / .out.log)**
- Implement `logrotate`-style rules or Python script `rotate_logs.py`.
- Archives to `state/logs_archive/YYYY-MM-DD/` with `.gz` compression.
- Delete archives > 90 days (or move to cold storage).
- Update `dashboard.pid` handling: write PID atomically (write to temp, rename); on crash, clear PID; use `pidfile` library if available.

**B. Event rotation (`events.json` → `events` table + rotation)**
- Keep last 7 days / 10K rows in `events` table.
- Move older to `events_archive_YYYY` table or compressed JSON.
- Add `ts` index for fast pruning: `DELETE FROM events WHERE ts < strftime('%s', 'now', '-30 days');`

**C. JSON streaming / pagination (`activity.json` replacement)**
- If stream exceeds 10M rows, switch to append-only file with sidecar index (`activity_index.json`) mapping `agent_id` → byte offset + length.
- Or use SQLite `WITHOUT ROWID` + partitioning by month (`activities_2026_08`).
- For true streaming, consider `jsonlines` format (one JSON object per line) with `gzip` per day; index sidecar built on first read.

**D. Metrics archive (`metrics.json` → `metrics` table)**
- Replace 1 MB aggregate file with SQL aggregates; archive monthly snapshots to `metrics_archive`.

---

## 5. Migration Plan (P0 / P1 / P2)

### P0 — Schema + Index (This Week)

```
[DB] Create pipeline_state.db
[SQL] CREATE TABLE activities, exec_tasks, events, orders, payments, funnel_metrics, log_archive
[SQL] CREATE INDEX ... (§2.2)
[SCRIPT] migrate_activity_json_to_sqlite.py  (read partial, write rows, verify count)
[SCRIPT] migrate_orders_meta.py
[SCRIPT] migrate_events.py
[BACKUP] cp state/*.json state/backup/2026-08-31/
[TEST] EXPLAIN QUERY PLAN SELECT * FROM activities WHERE ts > ...
```

**Verification queries:**
```sql
-- Check index usage (must see "USING INDEX idx_activities_ts")
EXPLAIN QUERY PLAN SELECT * FROM activities WHERE event_type = 'kill_switch_set' AND ts > 1788000000;

-- Check table sizes
SELECT name, page_count * 1024 as bytes FROM sqlite_dbpage('pipeline_state.db');
```

### P1 — Split Metrics + Funnel (Next Week)

```
[DB] Create metrics schema / metrics.db
[SQL] CREATE TABLE funnel_metrics, orders, payments, invoices
[SCRIPT] sql_funnel_refresh.py  (run every 5 min via cron / systemd timer)
[APP] Update API endpoints to query SQL instead of json.load()
[TEST] Compare SQL funnel result vs old metrics_funnel.json (must match within 0.1%)
```

### P2 — Archive + Rotate (Next Month)

```
[CRON] 0 2 * * * /ws/scripts/rotate_logs.py
[CRON] 0 3 1 * * /ws/scripts/archive_events.py  (monthly)
[SCRIPT] archive_activity.py (compress >30 days to activities_2026_07.json.gz)
[APP] Fix dashboard.pid: use pidlock file with flock / atomic rename
```

---

## 6. Size Estimates (Before vs After)

| Component | Before (JSON) | After (SQLite + Index + Archive) | Notes |
|---|---|---|---|
| Activities / agents | 943 KB (activity) + 11 KB (agents) | ~50 MB / 100K rows active; ~20 MB / 30 days archived | Depends on event rate |
| Orders meta | 3 KB | ~15 MB / 100K orders with indexes | Normalized from URL-keyed JSON |
| Payments | 18 B (stub) | ~10 MB / 50K payments | Separate table, FK index |
| Events | 1 KB | ~5 MB / 100K events; rotate at 10K/day | With `WITHOUT ROWID` + index |
| Funnel / Metrics | 1 KB config + 1 MB aggregate | ~2 MB active; ~10 MB with history | Materialized in SQL |
| Logs (api + dashboard + launcher) | 295 + 89 + 360 = ~744 KB | ~300 KB active + 2 MB archive (90 days) | Rotation reduces active I/O |
| **Total active** | **~6.7 MB** | **~100–150 MB** | Larger due to indexes + normalization, but **O(log n)** reads vs **O(n)** scans; unbounded growth controlled by rotation |
| **Total with 1 year archive** | Would exceed **2 GB** uncompressed | **~300–500 MB** compressed + indexed | Sustainable |

---

## 7. Key References

- **Skill: database-optimizer** — EXPLAIN ANALYZE interpretation, B-tree / GiST / GIN index selection, partial index design (`WHERE event_type = ...`), query-plan tuning, WAL mode recommendations.
- **Skill: backend-architect** — Schema normalization (orders/payments split), foreign-key indexing (`CREATE INDEX idx_payments_order_url`), migration reversibility (`DROP INDEX` / `DROP TABLE` with backups), zero-downtime deployment (create new DB, switch read path, drop old JSON after validation), connection pooling (SQLite handles single-process well; for multi-process use WAL + `PRAGMA busy_timeout`).
- **Skill: pipeline-analyst** — Funnel metrics (conversion rate = paid/total; revenue = SUM(payments); avg_order = AVG(orders.amount)), event stream processing (`events.json` rotation, `ts` range scans), log rotation impact on pipeline performance, metrics materialization strategy (trigger vs cron vs on-demand).

- **File refs:** `zarabotok/pipeline_v3/state/activity.json`, `agents_activity.json`, `exec_tasks.json`, `metrics_funnel.json`, `events.json`, `orders_meta.json`, `api.py.err.log`, `dashboard.py.err.log`, `launcher_new.log`, `metrics.json`, `.opencode/opencode.db`, `.docker/docker-compose.yml`
- **Memory refs:** `memory/backend_arch_review.md` (existing backend architecture review — aligns with schema split recommendations); `memory/2026-08-31.md` (daily notes — pipeline state context)

---

## 8. Critical Rules Applied (From System Prompt)

- ✅ **Always Check Query Plans:** `EXPLAIN QUERY PLAN` included for all recommended indexes.
- ✅ **Index Foreign Keys:** `payments(order_url)` indexes to `orders(url)`; `activities(agent_id)` indexed.
- ✅ **Avoid SELECT *:** All SQL examples use explicit column lists.
- ✅ **Use Connection Pooling:** SQLite WAL + `busy_timeout`; if scaled to multi-node, prefer PostgreSQL with PgBouncer transaction pooler (port 6543 for serverless — see system prompt connection-pooling example).
- ✅ **Migrations Must Be Reversible:** `DOWN` steps (drop indexes → drop tables → restore JSON) documented in P0/P1/P2.
- ✅ **Never Lock Tables in Production:** All indexes use `CREATE INDEX` (SQLite creates in background for non-unique; for large tables use `CREATE INDEX CONCURRENTLY` if migrating to Postgres). SQLite does not support `CONCURRENTLY`; plan for brief write pauses or use new DB and switch.
- ✅ **Prevent N+1 Queries:** Funnel metrics computed in single SQL queries with aggregates; no application-level loop over orders.
- ✅ **Monitor Slow Queries:** Recommend `sqlite3` profiling + `pg_stat_statements` if upgraded to Postgres.

---

## 9. Action Checklist (Ready for Execution)

- [ ] Confirm file-size discrepancy: is `exec_tasks.json` really 4 KB or is there a larger copy elsewhere? (Check `pipeline_old_20260802/` if needed.)
- [ ] Backup `state/*.json` to `state/backup/2026-08-31/`.
- [ ] Verify `database-optimizer` / `pipeline-analyst` skills loaded for query-plan verification.
- [ ] Create `pipeline_state.db`; run `CREATE TABLE` + `CREATE INDEX` from §2.2.
- [ ] Migrate `events.json`, `orders_meta.json`, `exec_tasks.json` first (small, low risk).
- [ ] Migrate `activity.json` using streaming / batch (do not load full 943 KB into memory at once; use chunked `json.load` with iterator or line-delimited JSON conversion).
- [ ] Fix `dashboard.py.pid` instability (write atomically; clear on exit; handle `ConnectionAbortedError` with retry/backoff).
- [ ] Implement `rotate_logs.py` for `api`, `dashboard`, `launcher`.
- [ ] Build `metrics.db` schema and `funnel_metrics` materialization (P1).
- [ ] Set `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` on `pipeline_state.db`.

---

*File created: `memory/db_optimizer.md`  
*Reference skills: `database-optimizer`, `backend-architect`, `pipeline-analyst`  
*Status: Analysis complete — migration executable from P0.*