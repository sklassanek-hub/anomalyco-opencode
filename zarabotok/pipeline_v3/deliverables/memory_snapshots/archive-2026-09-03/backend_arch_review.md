# Backend Architect Review — Pipeline v3 / Zarabotok / opencode-src
**Agent:** BackendArchitect  
**Review Date:** 2026-08-31  
**Scope:** `zarabotok/pipeline_v3/` + `opencode-src/` + `.opencode/` + `memory/` + `Dockerfile.sandbox`  
**Standard:** Security-first architecture, horizontal scalability, reliability > 99.9%, sub-200ms API p95, audit-compliant  
**Status:** P1 executed (W5, W7, W9, W13, W14, W15, W19 partial); P0 gaps remain critical

---

## 1. Executive Summary

This review evaluates the pipeline stages (scanner → store → ranker → executor → dashboard), isolation/security architecture, integration contracts, scalability bottlenecks, API/service gaps, and containerization readiness. The system is partially functional (W5 billing webhook wired, W7 agents_index updated with autonomy/validators/max_size/L0–L4, W9 spec_matrix live-linked to executor.finish, W13 filter with SHA-256 + embedding, W14 metrics_funnel + FunnelMetrics.tsx with aria-label, W15 billing.py Invoice stub + HMAC, W19 184/400+ agents indexed). However, **critical P0 gaps block production use**: no authentication middleware, no rate limiting, unverified LLM `baseURL`, missing audit log governance, sandbox build not validated, and single-worker dashboard with file-based SQLite/state storage.

**Strategic posture:** The architecture has the right decomposition (modular Python pipeline, Docker isolation layer, webhook billing, conversation threading, kill-switch audit). It lacks the operational backbone: message queuing, DB split (metrics vs. pipeline), auth gateway, webhook retry with exponential backoff, observability/tracing, and production container orchestration.

---

## 2. High-Level Architecture (Mermaid-style Description)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   EXTERNAL INPUTS                            │
│  Telegram (poll_telegram)  │  Email (poll_email_tz)  │  Webhook (yoomoney)   │
│  Scrapers (scanners.py)   │  API clients (http_client)  │  LLM (127.0.0.1:1234) │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INGRESS / LISTENER LAYER                        │
│  listener.py  ──►  listener_bridge.py  ◄──►  conversation.py (threading)      │
│  (poll + mark_seen)        (bridge poll/link)        (Message-ID / threading) │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE STAGES (v3)                            │
│  scanners.py  →  store.py  →  ranker.py  →  executor.py  →  dashboard/API    │
│   (scan)         (dedup)     (score)      (agent run)     (metrics/funnel)   │
│                                                                           │
│  store.db / sqlite  │  state/exec_tasks.json  │  state/metrics_funnel.json    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
             ┌───────────────────────┼───────────────────────┐
             ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SECURITY / ISOL  │  │  BILLING / WEBHO  │  │  AUDIT / KILL    │
│  sandbox.py      │  │  billing_service │  │  kill_switch.py  │
│  Dockerfile.sandbox│  │  billing.py      │  │  events.json     │
│  .docker/compose │  │  verify_hmac()   │  │  audit_delivery  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

**Architecture Pattern:** Modular monolith with service-like modules; no message broker; file-based state (JSON) with SQLite/postgresql fallback in `store.py`; container isolation for executor only (`sandbox.py`); no API gateway.

---

## 3. Pipeline Stage Analysis (scanner → store → ranker → executor → dashboard)

| Stage | Module / File | Function | Data Flow | Critical Notes |
|---|---|---|---|---|
| **Scanner** | `scanners.py`, `ok_scanner.py`, `vk_scanner.py`, `freelancer_scanner.py` | Poll Telegram / VK / freelance sources; extract job URLs + TЗ | Raw messages → `store.mutate("threads")` | No rate-limit per source; `watchdog.pid` unstable (audit: W2); no message-queue backpressure |
| **Store / Dedup** | `store.py`, `filter.py` (W13), `storage.py` | Dedup by hash + embedding (`embeddings_cache.json`); filter scams (`is_scam()` SHA-256 + embedding label) | Threads → `exec_tasks.json`; embeddings cached to file | PostgreSQL mode exists (`store.py` line 64) but rarely active; dedup not formalized globally; `scam_hashes` list static |
| **Ranker / Score** | `ranker.py` (W2 gap) | Score formula (§6.4) — NOT fully implemented; partial in workflow audit | Scored items → `proposals.py` / `executor.create_exec_task()` | Score formula not wired; `audit.py` integration missing |
| **Executor** | `executor.py` (777 lines), `run_agent()` | Pick agents (`pick_agents()` by TЗ keywords), run LLM (LM Studio 127.0.0.1:1234), version deliverables (`v<N>` folders) | `exec_tasks.json` → `deliverables/<order_id>/v<N>/` → review → done/failed | Docker isolation (`DOCKER_ENABLED=True`) but `Dockerfile.sandbox` not built/verified; no retry on LLM timeout; `TASK_TIMEOUT_MULT = 6`; `MAX_ATTEMPTS = 3`; single-worker (no queue worker pool) |
| **Dashboard / Metrics** | `dashboard.py` (errors in `dashboard_new.err.log`), `metrics_funnel.json`, `FunnelMetrics.tsx` (W14) | Aggregate orders + payments + funnel; aria-label added (`MetricsFunnel — агрегированные KPI из Orders и Payment`) | `metrics.json` + `metrics_funnel.json` + `orders_meta.json` + `payments.json` | No separate DB for metrics; SQLite/file-based; no caching layer; single-node dashboard; `metrics_funnel.json` links sources correctly (`state/orders.json`, `state/payments.json`) |

**Pipeline reliability gaps:**
- No message queue (RabbitMQ / Redis Streams / SQS) between stages → backpressure on scanner collapses executor.
- `store.py` writes JSON with `mutate()` but no transaction isolation; concurrent scanner + executor = corruption risk.
- `executor.py` uses direct `subprocess` + `subprocess.Popen` for agent runs; no container orchestration (K8s / Docker Swarm) for horizontal scaling.
- `dashboard.py` writes to `dashboard_new.err.log` / `dashboard_new.log`; PID file `dashboard.py.pid`; single process only.
- `watchdog.pid` unstable per `full_audit_master.md` (WorkflowAudit, W2 gap).

---

## 4. Isolation & Security Architecture

### 4.1 Sandbox / Execution Isolation

| Layer | Implementation | File / Config | Status |
|---|---|---|---|
| **Windows Job Object** | `ctypes.windll.kernel32` Job Object with `KILL_ON_CLOSE`, memory/CPU limits (`_make_job`) | `sandbox.py` lines 203–223 | Active; requires Windows host |
| **Sitecustomize socket block** | `_SITECUSTOMIZE_NO_NET` patches `socket.socket` → raises `_Blocked` | `sandbox.py` lines 80–89 | Active; prevents network in sandbox process |
| **Docker isolation** | `Dockerfile.sandbox` (python:3.11-slim, `--network none`, `--memory=1g`, read-only fs except `/workspace`) | `zarabotok/pipeline_v3/Dockerfile.sandbox` | **NOT BUILT / NOT VALIDATED** — `DOCKER_ENABLED=True` in `sandbox.py` line 25 but build not verified; `.docker/docker-compose.yml` exists (executor service only) but not integrated into pipeline startup |
| **Path / binary / macro checks** | `_SAFE_REL`, `_DANGEROUS_RE`, `_FORBIDDEN_BINARIES`, `_MACRO_DOCS`, AV stub (`clamscan` / `python-clamd`) | `sandbox.py` lines 34–39, 118–149 | AV stub returns `True` (pass-through) when scanner unavailable — **security gap**
| **Clean env / secret purge** | Removes `AWS_ACCESS_KEY_ID`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, etc. from subprocess env | `sandbox.py` line 285 | Good defense; no host secrets in container env |

**Critical P0:** `Dockerfile.sandbox` must be built and validated (`docker build -f Dockerfile.sandbox -t pipeline-v3-sandbox .`) before any production execution. The `.docker/docker-compose.yml` defines `executor` with `network_mode: none`, `read_only: true`, `user: "1001:1001"`, memory limits — but only for executor, not full pipeline (scanners/store/dashboard run uncontainerized). **Recommendation:** Extend compose to include `scanner`, `store-db`, `redis` (message queue), `dashboard`, and `nginx` (auth gateway).

### 4.2 Kill Switch + Audit Events

| Component | File / State | Behavior | Gaps |
|---|---|---|---|
| **Kill switch presence** | `state/KILL_SWITCH` (file presence = blocked) | `is_blocked()` checked at `executor.create_exec_task()` line 217 | Global block covers execution only; does not stop scanner/store/ranker |
| **Kill state JSON** | `state/kill_switch_active.json` | `set_blocked()` writes sync JSON + event | Good |
| **Audit log** | `state/events.json` (append-only, trimmed to last 500) | `write_event()` for kill_switch, delivery_audit | **No auth audit** (who triggered); no structured query (only JSON array); no log rotation outside 500-trim; no forwarding to SIEM / ELK |
| **Delivery audit** | `audit_delivery(url, status, detail)` wired into `executor.py` | Writes event with `ts`, `event`, `source`, `detail` | Only covers delivery; no execution audit (agent run start/finish/error); no audit for scanner/store/ranker |

**P0 fix required:** Add `auth.audit()` middleware that logs all API / CLI access to `events.json`; implement log shipping (syslog / fluent-bit); extend `events.json` schema with `user_id`, `ip`, `action`, `resource`, `outcome`; do NOT rely solely on file-trim (500 events = minutes of traffic at scale).

### 4.3 Sandbox Build Verification (P0)

- `Dockerfile.sandbox` references `pipeline_v3/config.json` but copy uses `|| true`; image lacks pipeline modules; no `RUN pip install` for dependencies; `CMD` is print-only.
- `.docker/Dockerfile` (used by compose) likely defines `executor` image but not reviewed here.
- **Action:** Build `pipeline-v3-sandbox`, run smoke test (`python -c "print('sandbox ok')"`), verify `sitecustomize` blocks network inside container, verify `clamscan` available or replace with `clamav` service.

---

## 5. Integration Patterns

### 5.1 Conversation ↔ Listener Bridge (`listener_bridge.py`)

- **Pattern:** Bridge class (`ListenerBridge`) polls `listener.py` (`poll_telegram`, `poll_email_tz`) and links messages into `conversation.py` threading (`build_thread_key`, `link_message`, `set_in_reply_to`).
- **Files:** `listener_bridge.py` (98 lines), `conversation.py` (402 lines), `listener.py`, `tg_common.py`
- **Status:** W3 (P0) — bridge exists; `poll_and_link()` returns count linked; `accept_inbox()` feeds messages; thread summaries via `thread_summary()`.
- **Gaps:**
  - Email threading placeholder (line 54–55): `# Placeholder: in production, load email messages from store/email index`
  - No persistent message queue between listener and conversation; if listener crashes, messages lost unless `store.load("threads")` has them.
  - `conversation.py` lacks database persistence; messages stored in-memory or file (`store.load` / `store.mutate`) — no ACID.
  - No authentication on conversation endpoints; any source can inject messages.

**Recommended pattern:** Insert Redis / RabbitMQ between listener and conversation; use `conversation.py` as service (not module) with DB-backed `threads` table; add `message_id` uniqueness constraint; implement `idempotency_key` for webhooks.

### 5.2 Billing ↔ Webhook (`billing_service.py` + `billing.py`)

- **Pattern:** Webhook verification (`verify_hmac()`) with replay protection (`operation_id` duplicate check in `payments.json`); Invoice stub (`billing.py` W5, W15) with `id`, `label`, `amount`, `status`, `webhook_url`, `hmac_secret`; `verify_invoice_webhook()` at end of `billing.py`.
- **Files:** `billing_service.py` (234 lines), `billing.py`, `state/payments.json`, `state/invoices.json`
- **Status:** W5 / W15 executed — HMAC verified; Invoice stub present; webhook wire at end of `billing.py`; label preserved; `verify_hmac_wrapper()` linked.
- **Gaps:**
  - No webhook retry with backoff — if webhook delivery fails, client never notified; `sender.py` / `webhook` logic not shown.
  - No db transaction between `payments.json` write and invoice update; partial failure = inconsistent state.
  - `verify_hmac()` returns `False` when secret empty — for development, but production must enforce secret presence.
  - `payments.json` is file-based; concurrent webhook = corruption.
  - No rate limit on webhook endpoint; open to replay / DoS.
  - `billing_service.py` uses `_secret()` from `config.json`; secret rotation not handled; no key vault integration.

**Recommended pattern:** Webhook endpoint behind auth gateway; queue webhook events to RabbitMQ / SQS; process with idempotency key; retry 3× exponential backoff (1s, 2s, 4s); write to PostgreSQL `payments` table in transaction with `invoices`; rotate secrets via Azure Key Vault / AWS Secrets Manager.

### 5.3 Metrics Funnel ↔ Orders / Payment (`metrics_funnel.json` + UI)

- **Pattern:** `metrics_funnel.json` (`funnel_version: v1`) references sources: `state/orders.json`, `state/payments.json`; links to `Orders.tsx`, `Billing.tsx`, `FunnelMetrics.tsx`; accessibility (`aria-label: MetricsFunnel — агрегированные KPI из Orders и Payment`) added.
- **Files:** `state/metrics_funnel.json`, `ui/src/pages/FunnelMetrics.tsx`
- **Status:** W14 executed — structure complete; aria-label present; source links correct.
- **Gaps:**
  - No separate metrics DB — reads from same `state/` files as pipeline; high read load on dashboard competes with scanner/store writes.
  - No caching (Redis) — every funnel refresh reads JSON from disk.
  - No aggregation pipeline (ETL) — funnel is manual/static reference, not computed from orders/payments.
  - No real-time update mechanism (WebSocket / SSE) — dashboard requires refresh.

**Recommended pattern:** Separate `metrics_db` (PostgreSQL read replica or ClickHouse / TimescaleDB for funnel analytics); ETL job (Airflow / cron) aggregates `orders` + `payments` into `metrics_funnel`; Redis cache for dashboard reads (TTL 30–60s); WebSocket or Server-Sent Events for real-time updates; accessibility audit (axe-core) in CI.

---

## 6. Scalability Risks

### 6.1 SQLite / File-Based State

- `store.py` references PostgreSQL mode but falls back to JSON file mutations (`store.mutate()`).
- `state/` directory contains 30+ JSON files (`activity.json` 978KB, `agents_activity.json`, `exec_tasks.json`, `metrics.json`, `payments.json`, `threads.json`, `messages.json`, etc.).
- **Risk:** At 100k+ entities (audit requirement: 100k+ entities), JSON file mutations become O(n) reads + full-file rewrites; corruption under concurrency; no backup / replication.
- **Evidence:** `state/activity.json` 978KB; `state/agents_activity.json` 11720 bytes; growth unbounded.

**P1 fix:** Migrate pipeline state to PostgreSQL (`store.py` PostgreSQL mode fully enabled); separate `metrics_db`; implement connection pooling (`sqlalchemy` or `psycopg2` pool); add migrations (`alembic`); backup via `pg_basebackup`; replication to standby.

### 6.2 Single-Worker Dashboard

- `dashboard.py` writes to `.pid`; single process; errors in `dashboard_new.err.log`; no worker pool.
- **Risk:** Dashboard failure = no metrics visibility; cannot handle concurrent requests; no load balancing.

**P1 fix:** Run dashboard as containerized service (`docker-compose`) with 2+ replicas behind nginx; use Gunicorn / Uvicorn with 4+ workers; separate metrics DB reads; add health-check endpoint (`/health`) and readiness probe.

### 6.3 No Message Queue

- Pipeline stages are synchronous (scanner writes file → ranker reads file → executor reads file). No RabbitMQ / Redis Streams / AWS SQS / Kafka.
- **Risk:** Scanner peak load (e.g., Telegram poll surge) overwhelms executor; no backpressure; lost messages if process crashes before persist.

**P1 fix:** Insert Redis / RabbitMQ between stages; scanner publishes to `pipeline.scanner` topic; store consumer writes to DB; ranker consumes from `pipeline.store`; executor consumes from `pipeline.rank`; dashboard queries DB (not file). Use dead-letter queue for failed messages.

### 6.4 No Horizontal Scaling

- `executor.py` picks agents locally (`pick_agents()`); runs LLM locally (`http://127.0.0.1:1234`); writes to `deliverables/` local filesystem.
- **Risk:** Cannot scale beyond single machine; LLM endpoint local only; no multi-region deployment.

**P2 fix:** Containerize executor with `docker-compose` + Kubernetes; external LLM endpoint (OpenAI / Azure OpenAI with verified `baseURL`); shared storage (NFS / S3 / Azure Blob) for `deliverables/`; database replication; load balancer.

---

## 7. API / Service Contract Gaps

### 7.1 No Authentication Middleware

- `opencode-src/` (Go CLI) and `pipeline_v3/` (Python) have no auth middleware.
- `opencode-src/internal/llm/provider/openai.go` has `WithOpenAIBaseURL()` (line 416–418) with no URL validation; `baseURL` passed directly to `option.WithBaseURL()`.
- **Evidence:** `full_audit_master.md` section D: "нет auth middleware + rate limit"; `opencode-src/openai.go` line 50: `if openaiOpts.baseURL != "" { ... option.WithBaseURL(...) }` — no `net/url` parse, no allowed-hosts whitelist, no TLS cert validation override check.
- **Impact:** Any endpoint / CLI can be called without identity; API keys / tokens exposed in config; LLM can be redirected to malicious endpoint.

**P0 fix:**
- Add middleware (`auth.middleware`) to all API endpoints (FastAPI / Express / Go `middleware` package): JWT / OAuth 2.0 / API key validation.
- Validate `baseURL` with `url.Parse()` + allowed-host whitelist (`openai.com`, `api.openai.com`, `azure.openai`, internal endpoints); reject unknown hosts; enforce TLS (`tls.Config` with `InsecureSkipVerify = false`).
- Implement `permission.Service` (already exists in Go) for RBAC; enforce least privilege.

### 7.2 No Rate Limiting

- No `express-rate-limit` or Go `rate.Limiter`; no `token bucket`; no per-IP / per-user quotas.
- **Impact:** Webhook endpoint open to replay / DoS; LLM endpoint can be spammed; scanner can poll infinitely.

**P0 fix:**
- Per-IP: 100 req / 15 min (standard).
- Per-user/API-key: 1000 req / hour; webhook: 10 req / min per `operation_id`; scanner: max 1 poll / 30 sec per source.
- Return `429 Too Many Requests` with `Retry-After` header.
- Log rate-limit hits to `events.json` for security monitoring.

### 7.3 Unverified LLM Endpoint (baseURL)

- `executor.py` hardcodes `http://127.0.0.1:1234/v1/chat/completions` (line 65); no verification that endpoint is legitimate LM Studio; no fallback.
- `opencode-src` allows arbitrary `baseURL`; no certificate pinning.
- **P0 fix:** Verify endpoint with health-check (`GET /v1/models`) + TLS cert verification; whitelist endpoints in `config.json`; use environment variable `LLM_ENDPOINT` with validation; implement circuit breaker (stop calling if 5 consecutive failures); fallback to secondary endpoint.

---

## 8. Containerization Assessment

### 8.1 What Exists

| Artifact | Path | Content | Status |
|---|---|---|---|
| **Sandbox Dockerfile** | `Dockerfile.sandbox` | python:3.11-slim, `WORKSPACE=/workspace`, `DOCKER_ENABLED=1`, `SANDBOX_ISOLATED=1`, `nameserver 127.0.0.1`, no pipeline modules copied | **Not validated** — build not run; no `pip install`; no module COPY |
| **Executor Compose** | `.docker/docker-compose.yml` | `executor` service, `network_mode: none`, `read_only: true`, `user: 1001:1001`, memory limits, bind `../workspace` | **Partial** — only executor; no DB / queue / dashboard / nginx |
| **Pipeline Dockerfile** | `.docker/Dockerfile` (not fully read) | Likely base image for pipeline | Unknown — needs validation |
| **Pipeline Compose** | `compose_simple.py` | Python script for compose | Unknown — needs validation |

### 8.2 What Is Missing (P1 / P2)

- **Production compose** (`docker-compose.prod.yml`) with services: `scanner`, `store-db` (PostgreSQL), `redis` (queue + cache), `ranker`, `executor`, `dashboard`, `nginx` (auth gateway + rate limit), `billing-webhook`, `audit-log` (ELK / fluent-bit).
- **Health checks** (`HEALTHCHECK` in Dockerfile) for each service.
- **Secrets management** (`docker secrets` / Kubernetes secrets) — no `.env` committed; config uses `config.json`; secret rotation not handled.
- **CI pipeline** (`.github/workflows/`) — `check_releases.py` broken; no test + vuln-scan + SBOM + sign gates.
- **Image scanning** (`trivy`, `grype`, `snyk`) — no vulnerability scanning.
- **SBOM / signing** — `.goreleaser.yml` missing `sbom`, `signs`, `windows` artifacts (audit: release); `opencode.exe` unsigned.

**P0 container action:** Build `Dockerfile.sandbox` and `.docker/Dockerfile`; run smoke test; validate isolation (`docker run --rm --network none --memory=1g -v $(pwd)/workspace:/workspace pipeline-v3-sandbox python -c 'import socket; socket.socket()'` should raise error); add health checks; create `docker-compose.prod.yml`.

---

## 9. Recommended Architecture Patterns

Based on audit gaps and best practices, implement these patterns in order:

### 9.1 Message Queue for Pipeline (P1)

- **Technology:** Redis Streams (simple, existing infrastructure) or RabbitMQ (durability, retry, dead-letter).
- **Topology:** `scanner` → `queue:pipeline.scan` → `store-consumer` → `queue:pipeline.store` → `ranker-consumer` → `queue:pipeline.rank` → `executor-consumer` → `queue:pipeline.done` → `dashboard-aggregator`.
- **Properties:** Persistent messages; consumer groups (load balance across 2+ workers); acknowledgment after DB write; dead-letter after 3 retries; message TTL for stale jobs.

### 9.2 Separate DB for Metrics (P1)

- **Pipeline DB (PostgreSQL):** `exec_tasks`, `threads`, `orders`, `payments`, `invoices`, `delivery_audit`, `users`.
- **Metrics DB (PostgreSQL read replica or ClickHouse):** `metrics_funnel`, `conversion`, `revenue`, `expenses`, `avg_order`; optimized for analytical queries (indexed, columnar if ClickHouse); refreshed by ETL job every 5 min.
- **Cache (Redis):** Dashboard reads from cache (30s TTL); invalidation on new order/payment.

### 9.3 Auth Gateway (P0)

- **Pattern:** Reverse proxy (`nginx` or `traefik`) with JWT / OAuth 2.0 / API key validation before reaching `api.py`, `dashboard.py`, `billing.py` webhook endpoint.
- **Layers:**
  1. TLS termination (`certbot` / Let's Encrypt).
  2. Rate limit (`nginx limit_req_zone` or `traefik` rate limits).
  3. Auth (`jwt` validation, `OAuth` introspection, `API key` header).
  4. IP allowlist (internal services, webhook source IPs).
  5. Audit log (request method, path, user, outcome, latency).
- **File references:** Add `nginx/auth_gateway.conf`, `middleware/auth.py` (Python) / `internal/auth/` (Go).

### 9.4 Webhook Retry with Exponential Backoff (P1)

- **Pattern:** Webhook delivery to client endpoint (`webhook_url`) with retry policy:
  - Attempt 1: immediate
  - Attempt 2: 1s delay
  - Attempt 3: 2s delay
  - Attempt 4: 4s delay (max 4)
- **Storage:** Queue webhook events; process with worker; log result to `events.json`; alert if final failure.
- **Idempotency:** Client must provide `idempotency_key`; server verifies against `operations` table.
- **File references:** `billing_service.py` (add `retry_webhook()`); `sender.py` (add queue); `state/events.json` (add webhook_delivery events).

### 9.5 Observability & Tracing (P2)

- **Metrics:** Prometheus / Grafana for pipeline stage latency, error rate, queue depth, DB connection pool.
- **Tracing:** OpenTelemetry (Go `otel`, Python `opentelemetry`) with spans: `scanner.poll`, `store.write`, `ranker.score`, `executor.run_agent`, `dashboard.read`.
- **Logging:** Structured JSON (not plain text) to stdout; collect with fluent-bit / Filebeat; ship to ELK / Loki.
- **File references:** Add `observability/` directory; update `logger.py`; add `metrics.py`.

---

## 10. File References (Evidence Base)

All references verified in workspace (`C:\Users\klass\OneDrive\Desktop\work\`):

### Pipeline / Workflow
- `memory/workflow_completion.md` — P1 execution (W5, W7, W9, W13, W14, W15, W19 partial)
- `memory/full_audit_master.md` — master audit (P0/P1/P2 priorities; 5 subagent reports; accessibility, workflow, release, code, memory)
- `zarabotok/pipeline_v3/modules/scanners.py` — scanner stage
- `zarabotok/pipeline_v3/modules/store.py` — store/dedup; PostgreSQL mode reference
- `zarabotok/pipeline_v3/modules/ranker.py` — score formula gap (W2)
- `zarabotok/pipeline_v3/modules/executor.py` — execution (777 lines); `DOCKER_ENABLED`; `TASK_TIMEOUT_MULT`; `pick_agents()`; `run_agent()`; `deliverables_dir()`
- `zarabotok/pipeline_v3/modules/dashboard.py` — dashboard errors (`dashboard_new.err.log`); PID file
- `zarabotok/pipeline_v3/modules/filter.py` — W13 `is_scam()` with SHA-256 + embedding
- `zarabotok/pipeline_v3/modules/chat.py`, `conversation.py`, `listener_bridge.py` — conversation threading
- `zarabotok/pipeline_v3/modules/billing_service.py` — webhook HMAC (234 lines); replay protection; `verify_hmac()`
- `zarabotok/pipeline_v3/modules/billing.py` — Invoice stub + webhook wire (W5, W15)
- `zarabotok/pipeline_v3/modules/kill_switch.py` — kill switch + events.json audit (118 lines)
- `zarabotok/pipeline_v3/modules/sandbox.py` — isolation (330 lines); Job Object; `DOCKER_ENABLED=True`; AV stub
- `zarabotok/pipeline_v3/modules/spec_matrix.py` — live link to `executor.finish()` (W9)
- `zarabotok/pipeline_v3/modules/agents.py` — agent index; `agent_index()`

### State / Data
- `zarabotok/pipeline_v3/state/metrics_funnel.json` — funnel source links (orders, payments); aria-label
- `zarabotok/pipeline_v3/state/exec_tasks.json` — execution tasks; `items`; `status`; `attempts`
- `zarabotok/pipeline_v3/state/payments.json` — billing records; replay protection
- `zarabotok/pipeline_v3/state/events.json` — audit events; trimmed to 500
- `zarabotok/pipeline_v3/state/KILL_SWITCH`, `kill_switch_active.json` — kill state
- `zarabotok/pipeline_v3/state/threads.json`, `messages.json`, `messages_fixed.json` — conversation storage
- `zarabotok/pipeline_v3/state/activity.json` (978KB) — unbounded growth evidence

### UI / Accessibility
- `zarabotok/pipeline_v3/ui/src/pages/FunnelMetrics.tsx` — W14 aria-label + source links
- `memory/accessibility_audit_summary.md` — 8 critical, 9 important accessibility gaps

### Container / Deploy
- `zarabotok/pipeline_v3/Dockerfile.sandbox` — sandbox Dockerfile (29 lines)
- `zarabotok/pipeline_v3/.docker/docker-compose.yml` — executor isolation (45 lines)
- `zarabotok/pipeline_v3/.docker/Dockerfile` — pipeline base (not fully read)
- `zarabotok/pipeline_v3/compose_simple.py` — compose script

### Config / Index
- `.opencode/agents_index.json` — W7 / W19 updates (autonomy, validators, max_size, L0–L4)
- `zarabotok/pipeline_v3/.opencode/agents_index.json` — same
- `memory/workflow_agents_index.md` — documentation
- `zarabotok/pipeline_v3/config.json` — config; sandbox settings; LLM endpoint; secret paths

### Security / Code (opencode-src)
- `opencode-src/internal/llm/provider/openai.go` — `baseURL` unverified (line 22, 50–51, 416–418)
- `opencode-src/opencode.exe` — unsigned binary (audit: release)
- `.goreleaser.yml` — missing sbom/signs/windows artifacts
- `check_releases.py` — broken (audit: release)

---

## 11. Priority Fixes (P0 / P1 / P2)

### P0 — Block Production / Security / Reliability (Fix Immediately)

| # | Fix | Evidence / File | Recommended Implementation | Verification |
|---|---|---|---|---|
| 1 | **Auth middleware + rate limit** | `full_audit_master.md` D; `opencode-src/` no auth | Add `auth.middleware` (JWT/OAuth/API key); rate limit per IP/user (100/15min, webhook 10/min); validate `baseURL` with `url.Parse()` + whitelist | Test: `curl -H "Authorization: Bearer bad"` → 401; `curl` 101st req → 429; `baseURL=http://evil.com` → rejected |
| 2 | **Audit log + events governance** | `kill_switch.py` (events.json only 500 events, no auth) | Extend `events.json` schema with `user_id`, `ip`, `action`; ship to ELK/fluent-bit; do NOT rely solely on file-trim | Test: audit event written with full schema; log forwarded to ELK; 500-trim not data loss at scale |
| 3 | **Sandbox build + validation** | `Dockerfile.sandbox` unbuilt; `sandbox.py` AV stub passes | Build image; validate `sitecustomize` blocks network; verify `clamscan` or replace with `clamav`; run smoke test | `docker build -f Dockerfile.sandbox -t pipeline-v3-sandbox .`; `docker run --rm --network none ... python -c 'import socket'` raises `_Blocked` |
| 4 | **LLM endpoint verification** | `executor.py` hardcoded `127.0.0.1:1234`; `opencode-src/openai.go` baseURL unverified | Whitelist endpoints in `config.json`; verify with `/v1/models`; enforce TLS; circuit breaker after 5 failures; fallback endpoint | Health-check passes; malicious `baseURL` rejected; fallback triggers on failure |
| 5 | **Kill switch global coverage** | `kill_switch.py` covers execution only | Extend to scanner/store/ranker/dashboard; add `kill_switch.check()` at pipeline stage entry | Test: `KILL_SWITCH` file stops all stages |

### P1 — Quality / Scale / Integration (Fix Before Scale)

| # | Fix | Evidence / File | Recommended Implementation | Verification |
|---|---|---|---|---|
| 6 | **Message queue for pipeline** | No queue; synchronous file-based stages | Redis Streams / RabbitMQ between scanner→store→rank→executor→dashboard; consumer groups; dead-letter; ACK after DB write | Test: scanner publishes; consumer processes; crash + restart = resume from last ACK |
| 7 | **Separate DB for metrics + pipeline** | `store.py` JSON-only; `metrics_funnel.json` file-based; `activity.json` 978KB | PostgreSQL for pipeline; Postgres read replica / ClickHouse for metrics; Redis cache (30s TTL); ETL job | DB migration runs; metrics query <100ms; dashboard reads from cache |
| 8 | **Webhook retry + backoff + idempotency** | `billing_service.py` no retry; `payments.json` replay only | Queue webhook events; retry 3× (1s, 2s, 4s); idempotency key; transaction with `invoices` | Test: webhook fails → retry succeeds; duplicate `operation_id` blocked; final failure alerts |
| 9 | **DB migration + connection pool** | `store.py` JSON mutations; no migrations | `alembic` migrations; `sqlalchemy` pool; backup (`pg_basebackup`); replication | Migration runs; concurrent writes safe; backup restores |
| 10 | **Conversation persistence + auth** | `conversation.py` in-memory/file; `listener_bridge.py` email placeholder | DB `threads` table; `message_id` unique; auth on conversation endpoints; email threading implemented | Conversation persists across restarts; email threading works; unauthorized access blocked |
| 11 | **Dashboard multi-worker + health** | `dashboard.py` single process; `dashboard_new.err.log` errors | Containerized with 2+ replicas; Gunicorn/Uvicorn 4+ workers; `/health` endpoint; nginx load balance | Health check passes; load test 100 req/s passes |

### P2 — Observability / Tracing / Scale (Fix for Growth)

| # | Fix | Evidence / File | Recommended Implementation | Verification |
|---|---|---|---|---|
| 12 | **Observability + tracing** | No metrics/tracing files; `logger.py` basic | Prometheus metrics; OpenTelemetry spans; structured JSON logging; Grafana dashboard | Metrics visible; trace spans show pipeline latency |
| 13 | **Agent index full + levels** | W19 partial (184/400+); `.opencode/agents_index.json` has L0–L4 + autonomy/validators/max_size | Complete 400+ agents; validate levels; document autonomy rules | Index loads 400+ agents; all fields present |
| 14 | **Accessibility CI** | 8 critical gaps (`accessibility_audit_summary.md`) | axe-core in CI; focus-trap for Modal/Drawer; `aria-live` for Toast; keyboard navigation for Table/Kanban; `skip-link`; `focus-visible`; `prefers-reduced-motion` | axe-core passes; manual NVDA/keyboard test passes |
| 15 | **Release CI + SBOM + signing** | `check_releases.py` broken; `opencode.exe` unsigned; `.goreleaser.yml` missing | Fix `check_releases.py`; CI (test + vuln-scan + SBOM + sign); sign binary; add releases with digests | Release passes CI; binary signed; SBOM generated |
| 16 | **Memory registries** | `memory/` 4-day gap; no `decision/`, `risks/`, `experiments/`, `feedback/` | Create registries; daily notes template; backlink to `state/`/`deliverables/`; experiment register | Registries created; daily notes updated |

---

## 12. Action Plan — Execution Order

### Immediate (Today / This Session)

1. **Read this review** with team; confirm P0 list; assign owners.
2. **Build `Dockerfile.sandbox`**; run smoke; verify isolation.
3. **Add auth middleware** (start with `nginx/auth_gateway.conf` + `middleware/auth.py`); block unauthorized access to `api.py`, `dashboard.py`, webhook endpoint.
4. **Add rate limiting** to webhook endpoint and API; configure `nginx` limits.
5. **Fix `baseURL` validation** in `opencode-src/internal/llm/provider/openai.go` and `executor.py`; add whitelist.
6. **Extend `kill_switch.py`** to cover scanner/store/ranker/dashboard; verify global block.
7. **Write extended `events.json`** event for auth/rate-limit/audit; ship to ELK.

### Short Term (Next Sprint — 1–2 Weeks)

8. **Migrate `store.py`** to PostgreSQL fully; add `alembic` migrations; create DB schema; migrate `exec_tasks.json`, `threads.json`, `payments.json`.
9. **Insert message queue** (Redis Streams); update pipeline stages to publish/consume.
10. **Implement webhook retry** with backoff in `billing_service.py`; add queue worker.
11. **Create metrics DB**; implement ETL; update `metrics_funnel.json` generation.
12. **Build production `docker-compose.prod.yml`**; add `nginx`, `postgres`, `redis`, `dashboard` replicas.

### Medium Term (Next Month)

13. **Add observability** (Prometheus + Grafana; OpenTelemetry tracing); update `logger.py`.
14. **Complete agent index** (400+); validate autonomy/validators/levels.
15. **Fix accessibility** (axe-core CI; focus-trap; keyboard nav; `aria-label` completeness).
16. **Fix release pipeline** (`check_releases.py`; CI gates; sign binary; SBOM).
17. **Write daily memory notes**; create `memory/decisions/`, `risks/`, `experiments/`, `feedback/`; backlink.

---

## 13. Strategic Notes (Architect Mind)

- **Security is not a feature — it is the foundation.** Every module reading `config.json` must validate secrets; every endpoint must authenticate; every sandbox must build and prove isolation.
- **Scalability is not an afterthought — it is a design constraint.** The pipeline must handle 10× peak load (audit: 10× traffic success). That requires queue-based backpressure, DB split, cache, and horizontal container scaling from day one.
- **Reliability requires redundancy.** Single-worker dashboard, single-file state, no message queue — these are single points of failure. Redundancy (DB replication, queue persistence, multi-worker, load balance) must be in the architecture, not added later.
- **Audit is evidence, not decoration.** `events.json` trimmed to 500 events with no user/IP/action is insufficient for incident response. Structured, forwarded, retained audit logs are required for security and compliance.
- **Accessibility is usability.** 8 critical accessibility errors (`Modal` focus-trap, `Table` keyboard nav, `Toast` aria-live) mean the pipeline is unusable for a significant user segment. Fix before scaling.
- **Containerization must be validated, not declared.** `DOCKER_ENABLED=True` with unbuilt `Dockerfile.sandbox` is a false sense of security. Build, test, verify network block, and integrate into production compose.

---

*Review compiled by BackendArchitect agent.*  
*Evidence base: memory/workflow_completion.md, memory/full_audit_master.md, zarabotok/pipeline_v3/modules/ (executor.py, sandbox.py, listener_bridge.py, kill_switch.py, billing_service.py, conversation.py), .opencode/agents_index.json updates (W7/W19), Dockerfile.sandbox, state/metrics_funnel.json, opencode-src/ llm provider (baseURL verification gap). All file paths verified in workspace.*  
*Next step: Confirm P0 action plan with team; execute auth + sandbox build + audit extension; schedule P1 queue + DB split; plan P2 observability + accessibility + release CI.*
