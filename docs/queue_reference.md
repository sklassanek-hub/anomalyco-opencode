# Message-Queue Reference — Pipeline v3 / Zarabotok
**Source:** memory/backend_arch_review.md §9.1 (Message Queue for Pipeline — P1)  
**Status:** Reference doc; implement RabbitMQ / Redis Streams between stages before production.

---

## 1. Pattern Overview

No message broker exists today (pipeline is file-based JSON synchronous).  
Insert a persistent queue between stages to provide **backpressure**, **replay**, **dead-letter**, and **horizontal worker scaling**.

### Recommended topologies (choose one)

| Technology | Best for | Existing infra | Notes |
|---|---|---|---|
| **Redis Streams** | Simple, existing infrastructure; consumer groups; low overhead | Already used for cache (dashboard) | Requires Redis 5.0+; no persistence guarantee by default (enable AOF) |
| **RabbitMQ** | Durability, retry, dead-letter exchange, pub/sub | New service needed | Requires queue declaration + DLX policy; best for audit/compliance |

**Decision:** Start with **Redis Streams** (faster to deploy); migrate to **RabbitMQ** if durability / DLX requirements grow (billing webhooks, audit logs).

---

## 2. Pipeline Stage Queue Topology

Based on `zarabotok/pipeline_v3/` modules (scanners → store → ranker → executor → dashboard):

```
scanner (scanners.py / ok_scanner / vk_scanner / freelancer_scanner)
    │ publish
    ▼
queue:pipeline.scan     [Redis Stream / RabbitMQ topic]
    │ consume (1 of N workers)
    ▼
store-consumer (store.py / filter.py / storage.py)
    │ dedup, filter scams (SHA-256 + embedding), write DB
    ▼
queue:pipeline.store
    │ consume
    ▼
ranker-consumer (ranker.py — score formula W2 gap)
    │ score, embed, propose
    ▼
queue:pipeline.rank
    │ consume
    ▼
executor-consumer (executor.py — agent run, deliverables/)
    │ pick_agents(), LLM call, version deliverables
    ▼
queue:pipeline.done
    │ consume
    ▼
dashboard-aggregator (dashboard.py + metrics_funnel.json)
    │ read from DB (not file); cache in Redis 30s TTL
```

---

## 3. Message Schema (JSON — applies to both RabbitMQ payload and Redis Stream fields)

```json
{
  "message_id": "uuid-v4",
  "pipeline_stage": "scanners | store | ranker | executor | dashboard",
  "source": "telegram | vk | freelancer | email | webhook",
  "payload": {
    "url": "https://...",
    "title": "...",
    "tz": "UTC+3",
    "raw_text": "...",
    "hash_sha256": "...",
    "embedding_id": "..."
  },
  "metadata": {
    "created_at": "2026-08-31T12:00:00Z",
    "attempts": 0,
    "idempotency_key": "operation_id_or_url_hash",
    "priority": 1,
    "ttl_seconds": 3600
  },
  "audit": {
    "actor": "scanner_poll_telegram",
    "action": "poll_and_extract",
    "resource": "queue:pipeline.scan",
    "result": "queued",
    "kill_active": false,
    "source_file": "modules/scanners.py"
  }
}
```

### Field descriptions

| Field | Type | Required | Description |
|---|---|---|---|
| `message_id` | string (uuid) | yes | Unique; used for idempotency |
| `pipeline_stage` | enum | yes | Current stage; updated by consumer |
| `source` | enum | yes | Input origin |
| `payload.url` | string | yes | Job / proposal URL |
| `payload.hash_sha256` | string | yes | Dedup key (filter.py W13) |
| `payload.embedding_id` | string | no | Cache key for embeddings_cache.json |
| `metadata.attempts` | int | yes | Retry count; increment on failure |
| `metadata.idempotency_key` | string | yes | Prevent replay / duplicate processing |
| `metadata.ttl_seconds` | int | no | Auto-expire stale jobs (e.g., 1h for scan) |
| `audit.kill_active` | bool | yes | Check `modules/kill_switch.py is_blocked()` before processing |

---

## 4. Consumer Group / Worker Design

### Redis Streams (recommended first)

```python
# scanner produces
redis.xadd("pipeline.scan", {"json": msg_json}, maxlen=10000, approximate=True)

# store-consumer (2 workers)
streams = redis.xreadgroup(groupname="store_consumers", consumername="worker-1",
                          streams={"pipeline.scan": ">"}, block=5000, count=10)
# ACK after DB write (store.mutate / PostgreSQL)
redis.xack("pipeline.scan", "store_consumers", *message_ids)
```

### RabbitMQ (recommended if audit/compliance demands DLX)

```yaml
# Queue declaration (python / rabbitmq admin)
queue: pipeline.scan
  durable: true
  arguments:
    x-dead-letter-exchange: dlx.pipeline.scan
    x-message-ttl: 3600000
  bindings: exchange: pipeline.direct -> routing_key: scan

# Dead-letter exchange: dlx.pipeline.scan -> queue: pipeline.scan.dlq -> alert
```

**Consumer settings:**
- `prefetch_count = 1` (prevent single worker from hogging messages)
- `ack` after DB commit (not after receipt)
- `requeue` on LLM timeout / crash
- `redeliver` after 3 retries -> DLQ; alert `audit_delivery(url, "dead_letter", ...)`

---

## 5. Backpressure & Reliability Rules

| Rule | Implementation | Evidence from review |
|---|---|---|
| **Queue depth alert** | Monitor `LLEN` / `XLEN` / RabbitMQ management API; alert if > 1000 messages per stage | §6.3 No message queue -> scanner peak collapses executor |
| **Ack after DB write** | Consumer must write to `store.py` / PostgreSQL before `XACK`; crash before ack = replay (idempotent) | §5.1 Conversation bridge missing ACID |
| **Dead-letter after 3 retries** | `attempts` in message metadata; if `>= 3`, route to DLX / archive; call `ks.audit_delivery()` | §9.4 Webhook retry with backoff |
| **Message TTL** | `metadata.ttl_seconds`; stream trims automatically or cron archives | §4.2 events.json trim 500 only; queue needs TTL |
| **Kill-switch gate** | Consumer checks `is_blocked()` at start; if true, ack + log `audit_scanner()` / `audit_store()` / `audit_delivery()` | §4.2 kill switch only covers executor |
| **Idempotency** | `metadata.idempotency_key` = url hash or `operation_id`; DB unique constraint prevents duplicate `exec_tasks` | §5.2 Billing replay protection |

---

## 6. Integration with Pipeline Files

| File | Integration point | Action needed |
|---|---|---|
| `modules/scanners.py` | After `poll_telegram()` / `poll_email_tz()` / `poll_vk()` | `redis.xadd("pipeline.scan", ...)` or `channel.basic_publish()` |
| `modules/store.py` | After `mutate("threads", ...)` / `mutate("exec_tasks", ...)` | Consume from `pipeline.scan`; write DB; ack; publish to `pipeline.store` |
| `modules/ranker.py` | After `score()` (W2 gap — not fully wired) | Consume `pipeline.store`; score; publish `pipeline.rank` |
| `modules/executor.py` | At `create_exec_task()` start (already wired with auth + kill) | Consume `pipeline.rank`; run agent; publish `pipeline.done`; call `audit_delivery()` |
| `modules/dashboard.py` | Refresh / aggregate | Consume `pipeline.done`; aggregate to `metrics_funnel.json`; write to separate metrics DB (§9.2) |
| `state/events.json` | Audit all stages | `audit_scanner()`, `audit_store()`, `audit_delivery()` already extended in `kill_switch.py` |

---

## 7. Security & Isolation (compose + sandbox)

From `memory/backend_arch_review.md` §4.1, §8:

- **Queue service container:** separate from pipeline stages; `network_mode: none` for consumers; `read_only: true`; `user: 1001`; `mem_limit: 1g`
- **Secret management:** Queue credentials (Redis auth / RabbitMQ AMQP) stored in `docker secrets` or Kubernetes secrets; NOT in `config.json` (currently uses `config.json` with `SECRET`)
- **TLS:** Redis `tls-port` or RabbitMQ `amqps://`; verify certs (not `InsecureSkipVerify`)
- **Auth gateway:** `nginx/auth_gateway.conf` validates JWT before allowing queue admin access (`/api/queue/admin`)

---

## 8. Migration Path (P1 → P2)

1. **P1 (immediate):** Deploy `redis-server` container; add `redis` client to `pipeline_v3/requirements`; wire `scanners.py` producer; wire `store.py` + `executor.py` consumers.
2. **P1 (parallel):** Fix `store.py` transaction isolation (currently file-based `mutate()` with corruption risk under concurrency).
3. **P2:** Replace Redis with RabbitMQ if DLX + audit requirements grow; deploy `rabbitmq` service; declare exchanges / queues / policies.
4. **P2:** Separate metrics DB (`metrics_db` PostgreSQL read replica or ClickHouse); ETL job aggregates `pipeline.done` into `metrics_funnel`.

---

## 9. Schema Quick Reference

```yaml
message_schema:
  version: "v1"
  encoding: json
  required_fields: [message_id, pipeline_stage, source, payload.url, payload.hash_sha256, metadata.attempts, metadata.idempotency_key]
  optional_fields: [payload.embedding_id, metadata.ttl_seconds, audit.kill_active, audit.source_file]
  audit_source_file: "modules/kill_switch.py"   # events.json source tag
  rotation: "state/rotate_events.py"               # 500-entry trim + archive
  archive_format: "jsonl"
  archive_path_template: "state/archive/events-YYYY-MM-DD.jsonl"
```

---

## References

- `memory/backend_arch_review.md` §5.1 (Listener Bridge — missing persistent queue)
- `memory/backend_arch_review.md` §6.3 (No Message Queue — backpressure risk)
- `memory/backend_arch_review.md` §9.1 (Message Queue for Pipeline — topology + properties)
- `memory/backend_arch_review.md` §9.2 (Separate DB for Metrics)
- `zarabotok/pipeline_v3/modules/kill_switch.py` — `audit_scanner()`, `audit_store()`, `audit_delivery()`
- `zarabotok/pipeline_v3/modules/executor.py` — `create_exec_task()` consumes from `pipeline.rank`
- `zarabotok/pipeline_v3/state/rotate_events.py` — rotation stub
- `docker-compose.sandbox.yml` — executor isolation (`network_mode: none`, `read_only: true`, `user: 1001`, `mem_limit: 1g`)
