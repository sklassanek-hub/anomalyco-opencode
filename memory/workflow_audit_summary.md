# WorkflowAudit Summary — Freelance Autopilot (zarabotok / pipeline_v3)

**Agent:** WorkflowAudit  
**Source:** `WORKFLOW.md` (lines 1–40) + `zarabotok/` tree + `pipeline_v3/` modules  
**Audit date:** 2026-08-31  
**Scope:** 14-step cycle (table in WORKFLOW.md lines 13–26). Inspected subdirs: `state/`, `deliverables/`, `pipeline/`, `pipeline_v3/`, `pipeline_old_20260802/`. Representative files read: `scanners.py` (415 lines), `store.py` (303 lines), `ranker.py`, `audit.py` (root), `proposals.py`, `executor.py`, `billing.py` (318 lines), `billing_service.py` (225 lines), `invoice.py` (171 lines), `conversation.py` (380 lines), `spec_matrix.py`, `sandbox.py` (14447 bytes), `test_exec_pipeline.py` (141 lines), `watchdog.py`. No `inside.txt` found in any pipeline root; `test_exec_pipeline.py` present (pipeline_v3/tests/).

---

## 1. Inspection findings (macro)

| Path | Status | Notes |
|---|---|---|
| `zarabotok/state/` | ⚠️ Minimal | Only `freelancer_token.json` (55 b). No `events.json` / `orders_meta.json` committed at root; `pipeline_v3/state/` holds live JSON. |
| `zarabotok/deliverables/` | ⚠️ Partial | 5 subfolders (`euromebel`, `nazgul`, `novak`, `saffran`, `???` with Cyrillic name). No uniform manifest / archive check. |
| `zarabotok/pipeline/` | ⚠️ Old + v3 split | `modules/`, `tests/`, `scripts/`, `logs/`. Old pipeline lacks `scanners`, `ranker`, `billing` at module level (only `scanners` in `pipeline_old_20260802/modules/`). |
| `zarabotok/pipeline_v3/` | ✅ Active | Full module set (`scanners.py`, `store.py`, `ranker.py`, `proposals.py`, `executor.py`, `billing.py`, `invoice.py`, `billing_service.py`, `conversation.py`, `sandbox.py`, `watchdog.py`, `audit.py`). `tests/test_exec_pipeline.py` exists. `spec_matrix.py` (11.6) exists. `ui/src/` present (React/Vite) but no `funnel` component. |
| `WORKFLOW.md` lines 1–40 | ✅ Source of truth | Defines 14-step cycle, agent isolation rules, kill-switch + button requirements, `state/` + `memory/` persistence, manual confirmation for irreversible actions. |

---

## 2. Stage-by-stage audit (12 main stages + 2 sub-steps covered)

| # | Stage (WORKFLOW name) | Status | Strong points (modules/files) | Weak points / gaps | Concrete recommendation |
|---|---|---|---|---|---|
| 1 | **Поиск/скан (Search/Scan)** | ✅ / ⚠️ | `scanners.py` v2 (FL, freelance, TG channels, Habr, WeWorkRemotely, Telethon API); `watchdog.py` PID tracking; `test_scanner.py`. | `watchdog.pid` not fully stabilized (WORKFLOW: stabilize + `test_ok_scanner.py`); no unified `scan_all` result manifest; old `pipeline/` lacks scanner module. | Freeze `scanners.py` v2; write `test_ok_scanner.py`; add `scan_result.json` manifest to `state/`; retire `pipeline_old_20260802/` scanner. |
| 2 | **Фильтрация (Filter)** | ⚠️ Partial | `store.py` dedup (`seen_jobs`); `ranker.py` `has_contact()`; `proposals.py` `is_scam()`; `store.load("seen_jobs")`. | No embedding-dedup (WORKFLOW: formalize hashes + embedding); `is_scam` relies on heuristics, not model score; no formal `filter_log`. | Add `embedding_dedup.py` (hash + cosine); formalize `filter_policy.json`; log filtered items with reason code (`scam`, `dup`, `no_contact`). |
| 3 | **Скоринг (Scoring)** | ⚠️ Partial | `ranker.py` `score_job()` (skills match from `config.json`); `audit.py` at pipeline root runs `rank_and_store`; `check_ranking.py`. | Formula from ТЗ §6.4 not fully implemented (WORKFLOW: implement Score formula); no weight for `contact_only`; score range 0–N not normalized. | Implement §6.4 formula (skills + contact + urgency + platform weight); add `score_normalize()`; write `tests/test_score_formula.py`. |
| 4 | **Реестр навыков (Skills Registry)** | ⚠️ Partial | `.opencode/agents_index.json` (400+ agents); `skills_registry.json`; `gen_agents_index.py`; `agents/` directory. | No L0–L4 autonomy levels (WORKFLOW: add `autonomy`, `validators`, `max_size` in model); `.opencode/agents_index.json` is static; no runtime validation against `max_size`. | Add `autonomy: {L0..L4}` and `max_size` fields to agent index schema; create `validators/` folder per agent; implement `pick_agents()` validation (check `max_size` before dispatch). |
| 5 | **Отклик (Response)** | ⚠️ Partial | `proposals.py` (`llm_draft`, `template_draft`, `qa`, `judge_eval`); `judge.py` / `debug_judge.py`; `proposals.build_outbox()`. | No reviewer-agent (WORKSPACE: add reviewer-agent + ban false phrases); `judge_eval` fail-open (passes when LLM fails); false-phrase blacklist missing. | Add `reviewer_agent/` sub-module; implement false-phrase blacklist (`free_test_request`, `scam`, ` Guarantee `); change `judge_eval` default to `fail-closed` (reject if LLM errors). |
| 6 | **Диалог / ТЗ (Dialogue / TZ)** | ❌ / ⚠️ (improved) | **NEW:** `modules/conversation.py` (380 lines) — threading, `link_by_proposal_id`, response classification (`interested`, `spec_sent`, `terms_agreed`, `rejected`, `suspicious`, `free_test_request`); `listener.py`; `tg_common.py`. | **GAP:** No unified inbox service (WORKFLOW: implement Conversation service with threading); `conversation.py` is independent (`import by demand`), not integrated into `listener.py` automatically; no `threading` DB table in `state/` (only `threads` list in store). | **Critical:** Integrate `conversation.py` into `listener.py` / `sender.py` pipeline; create `state/threads.json` with `thread_id`, `proposal_id`, `msg_sequence`; implement `needs_linking` queue; add `conversation_service.run()` to watchdog loop. |
| 7 | **Исполнение (Execution)** | ⚠️ Partial | `executor.py` (sandbox via `sandbox.py`, Docker path, `JobObject`, `lint_code`, `validate_file`, `PLACEHOLDER_RE`, `DANGEROUS_RE`); `tests/test_exec_pipeline.py` (141 lines); `workers/exec_worker.py`. | **No containers / isolation weak:** `sandbox.py` exists but `DOCKER_ENABLED` false by default; `sandbox.network_enabled` false; no container image registry; workspace isolation relies on `JobObject` (Windows only), not Linux containers; no antivirus scan before execution. | Add `docker-compose.sandbox.yml` (Ubuntu + python + limits); enforce `container=True` when `executor.create_exec_task()` called; add `workspace_isolation/` folder per task (`workspace/<url_hash>/`); add `antivirus_scan()` hook (ClamAV or Windows Defender API) before `finish()`. |
| 8 | **Упаковка (Packaging)** | ⚠️ Partial | `tests/test_exec_pipeline.py` validates `.py`, `.json`; `executor.finish()` writes `manifest`; `spec_matrix.py` exists (§11.6); `modules/sandbox.py` `run_smoke()`. | **No TZ↔result matrix linked to execution:** `spec_matrix.py` is a static doc file; not used by `executor.py` to validate output against TZ requirements; no `ready_for_delivery` check in `executor.py` (WORKFLOW: add matrix check); missing `package_zip()` linkage to TZ. | Integrate `spec_matrix.py` into `executor.finish()`: before `finish()`, run `validate_against_matrix(manifest, job_tz)`; add `tests/test_matrix_link.py`; create `package_manifest.json` (file list + TZ item IDs + checksum). |
| 9 | **Доставка (Delivery)** | ⚠️ Partial | `dashboard` (`ui/src/`); `deliver_result()` references in `proposals.py` / `executor.py`; `watchdog.py` monitors delivery; `store.load("outbox")`; `sender.py`. | **No hard lock / mandatory button:** WORKFLOW: add mandatory "Deliver" button + archive re-check; `outbox` items can be sent without `ready_for_delivery`; `dashboard` v7 lacks unified delivery status; no archive checksum verification before send. | Add `deliver_lock.json` in `state/` (`url`, `approved_by`, `archive_sha256`, `timestamp`); implement `deliver_result()` check: pass only if `archive_sha256` matches `files/` record and `spec_matrix` OK; update `ui/src/` with `DeliveryLock` component. |
| 10 | **Финансы (Finance)** | ❌ / ⚠️ (module exists) | `billing_service.py` (HMAC verify, replay protection `operation_id`, `label`, webhook payload parsing, `state/payments.json`); `invoice.py` (Invoice model, QR, HTML); `billing.py` (draft/sent/paid/void, `auto_invoice`); `modules/billing_service.py` has `verify_hmac`. | **Webhook not fully wired:** `billing_service.py` exists but `billing.py` still uses stub `send_to_client()`; `config.json` `payment` may have `webhook_secret` empty; `label` field present but not sent to webhook; no `Invoice` model integration with `billing.py`. | **Implement webhook HMAC end-to-end:** (a) load `webhook_secret` from `config.json` or `state/yoomoney_webhook_secret.json`; (b) in `billing_service.py` expose `handle_webhook()`; (c) in `billing.py` call `billing_service.verify_hmac()` before `mark_paid()`; (d) add `Invoice` model import to `billing.py`; (e) write `tests/test_webhook_hmac.py`. |
| 11 | **Безопасность (Security)** | ⚠️ Partial | `permission.Service` references; `audit` events (`modules/audit.py` at root); `watchdog.py` kill-check (`KILL_SWITCH` + `kill_switch_active.json`); `executor.py` `kill_path` check; `modules/voice.py` `kill_switch` event. | **No global kill-switch with audit:** `KILL_SWITCH` file exists (`state/KILL_SWITCH`) and `kill_switch_active.json` exists, but no unified audit event to `state/events.json`; no `Kill Switch + audit events` integration (WORKFLOW); `permission.Service` not visible in `pipeline_v3/` (only references). | **Add Kill Switch + audit event:** (a) create `modules/kill_switch.py` with `activate()`, `deactivate()`, `status()`; (b) on activate, write `state/KILL_SWITCH` + `state/kill_switch_active.json` + append to `state/events.json` (`severity=critical`, `source=kill_switch`, `text="Global kill activated by operator"`); (c) ensure `watchdog.py`, `executor.py`, `sender.py`, `autoreply.py` check `kill_switch_active.json` at start of loop and abort all tasks if true. |
| 12 | **Панель (Panel)** | ⚠️ Partial | `ui/src/` (React); `dashboard_new.err.log` / `.log`; `check_funnel.py`; `dashboard` references in `executor.py` / `proposals.py`; `config.json`; `release.json`. | **No unified funnel / metrics:** WORKFLOW: aggregate metrics from `Order` + `Payment`; `check_funnel.py` only checks funnel config; no `metrics_funnel.json`; dashboard v7 lacks real-time `Order`, `Payment`, `Scan`, `Execution` aggregation; no `metrics/` folder. | **Create metrics funnel:** (a) add `state/metrics_funnel.json` updated by `watchdog.py` every 60s (`scan_count`, `filter_rejected`, `scored`, `proposals_sent`, `execution_started`, `delivered`, `paid`, `killed`); (b) build `ui/src/components/MetricsFunnel.jsx`; (c) add `tests/test_funnel_metrics.py`; (d) integrate `check_funnel.py` into `watchdog.py`. |

---

## 3. Cross-cutting gaps (not tied to single stage)

| Gap | Evidence | Impact | Fix |
|---|---|---|---|
| **No unified Conversation / inbox service** | `conversation.py` exists (independent) but not integrated into `listener.py`; `threads` only as list in store; no `thread_id` linking to `proposal_id` automatically. | TZ messages get lost / mislinked; no threading for multi-turn dialogue. | Integrate `conversation.py` into `listener.py`; create `state/threads.json`; add `needs_linking` queue; test with `tests/test_conversation_threading.py`. |
| **No container isolation in execution** | `sandbox.py` exists but `DOCKER_ENABLED` false; `executor.py` uses `JobObject` fallback; `sandbox.network_enabled` false by default; no `.docker/` image registry in `pipeline_v3/` (only `.docker/` folder, no `Dockerfile`). | Client code can access network / filesystem; risk of malicious execution. | Add `Dockerfile.sandbox`, `docker-compose.sandbox.yml`; enforce `container=True` when `exec_task` created; add `workspace_isolation/` per URL hash. |
| **No matrix TZ↔result linked to execution** | `spec_matrix.py` is static doc (11.6); `executor.finish()` does not call `validate_against_matrix()`; no `package_manifest.json`. | Delivery can ship incomplete / incorrect results; no proof of TZ fulfillment. | Integrate `spec_matrix.py` into `executor.finish()`; create `tests/test_matrix_link.py`; require `spec_matrix_ok` flag for `deliver_result()`. |
| **No webhook HMAC + Invoice model integration** | `billing_service.py` has `verify_hmac()` but `billing.py` does not import it; `invoice.py` has `Invoice` class but `billing.py` uses raw dict; `label` not sent. | Payment confirmation unreliable; invoice generation manual; webhook replay risk. | Wire `billing_service.verify_hmac()` into `billing.mark_paid()`; import `Invoice` in `billing.py`; add `label` to webhook payload; write `tests/test_webhook_hmac.py`. |
| **No global Kill Switch + audit events** | `KILL_SWITCH` file and `kill_switch_active.json` exist; `watchdog.py` checks them; but no `state/events.json` entry; `permission.Service` not visible. | Operator cannot audit why system stopped; no centralized incident log. | Create `modules/kill_switch.py`; on activate, write file + `state/events.json` (`severity=critical`); ensure all loops (watchdog, executor, sender, autoreply) abort on `kill_switch_active.json=true`. |
| **No unified metrics / funnel** | `check_funnel.py` exists; `ui/src/` has no `MetricsFunnel`; `state/metrics_funnel.json` missing; `release.json` exists but not aggregated. | Dashboard is blind to pipeline health; no KPI tracking. | Create `state/metrics_funnel.json`; build `MetricsFunnel.jsx`; integrate `check_funnel.py` into `watchdog.py`; write `tests/test_funnel_metrics.py`. |
| **No archive checksum / delivery lock** | `deliver_result()` not enforcing `ready_for_delivery`; `outbox` items have `status` but no `archive_sha256` check; `files/` folder exists but checksum not verified. | Wrong archive can be delivered; no proof of correct artifact. | Add `archive_sha256` to `files/` records; implement `deliver_lock.json`; enforce `archive_sha256` match + `spec_matrix_ok` + `manual_confirm` before send. |

---

## 4. Recommendations (concrete, ordered by dependency)

### Immediate (this session / next run)
1. **Conversation integration** — import `conversation.py` into `listener.py`; create `state/threads.json`; run `tests/test_conversation_threading.py`.
2. **Kill Switch audit** — create `modules/kill_switch.py`; add `events.json` entry on activate; verify `watchdog.py` abort loop.
3. **Scan stabilization** — stabilize `watchdog.pid`; write `tests/test_ok_scanner.py`; add `scan_result.json` manifest.

### Short-term (next development cycle)
4. **Sandbox containers** — add `Dockerfile.sandbox` + `docker-compose.sandbox.yml`; enforce `container=True`; add `workspace_isolation/<hash>/` per task; add antivirus hook.
5. **Scoring formula** — implement §6.4 score formula in `ranker.py`; normalize score; add `tests/test_score_formula.py`.
6. **Filter formalization** — add embedding-dedup; formalize `filter_policy.json`; log rejects with reason code.
7. **Skills registry L0–L4** — update `agents_index.json` schema; add `autonomy`, `validators`, `max_size`; enforce in `pick_agents()`.

### Medium-term (before production release)
8. **Execution packaging matrix** — integrate `spec_matrix.py` into `executor.finish()`; create `package_manifest.json`; require for `deliver_result()`.
9. **Delivery hard lock** — implement `deliver_lock.json`; add archive checksum; update `ui/src/` with `DeliveryLock`; enforce manual button.
10. **Finance webhook + Invoice** — wire `billing_service.verify_hmac()` into `billing.py`; import `Invoice`; send `label`; write `tests/test_webhook_hmac.py`.
11. **Metrics funnel** — create `state/metrics_funnel.json`; build `MetricsFunnel.jsx`; integrate `check_funnel.py`; add `tests/test_funnel_metrics.py`.
12. **Security audit events** — centralize `audit` to `modules/audit_events.py`; ensure all stages emit to `state/events.json`; add `permission.Service` checks.

---

## 5. File references for action

| Module / File | Key lines / functions | Action needed |
|---|---|---|
| `WORKFLOW.md` | 13–26 (table), 9 (kill-switch + button), 35–39 (test commands) | Update status markers after fixes; add `test_ok_scanner.py` to command list. |
| `zarabotok/pipeline_v3/modules/scanners.py` | 1–30, `scan_all()` | Stabilize; add manifest. |
| `zarabotok/pipeline_v3/modules/store.py` | 1–30 (`STATE`, `_tlock`, `_pg_reach_ok`) | Ensure `threads.json`, `metrics_funnel.json`, `events.json` support. |
| `zarabotok/pipeline_v3/modules/ranker.py` | 26–30 (`score_job`) | Implement §6.4 formula. |
| `zarabotok/pipeline_v3/modules/proposals.py` | `is_scam()`, `judge_eval()`, `build_outbox()` | Add reviewer; change fail-open to fail-closed. |
| `zarabotok/pipeline_v3/modules/conversation.py` | 1–30, `link_by_proposal_id()` | Integrate with `listener.py`. |
| `zarabotok/pipeline_v3/modules/executor.py` | 101–113 (Docker path), `finish()`, `kill_path` | Enforce container; add matrix check; add kill-check at loop start. |
| `zarabotok/pipeline_v3/modules/sandbox.py` | 14447 bytes, `run_smoke()`, `_make_job()` | Confirm `DOCKER_ENABLED` true in production config; add `Dockerfile`. |
| `zarabotok/pipeline_v3/modules/billing_service.py` | 1–60 (`verify_hmac`, `label`) | Wire to `billing.py`; test HMAC replay. |
| `zarabotok/pipeline_v3/modules/billing.py` | 1–40 (`STATUSES`, `_resolve_method`) | Import `Invoice`; import `billing_service`; add webhook call. |
| `zarabotok/pipeline_v3/modules/invoice.py` | 29–30 (`class Invoice`) | Integrate into billing flow. |
| `zarabotok/pipeline_v3/modules/spec_matrix.py` | 6–30 (`SPEC_MATRIX`) | Link to `executor.finish()`. |
| `zarabotok/pipeline_v3/modules/audit.py` (root) | 1–22 | Expand to audit events for all stages; add `kill_switch` event. |
| `zarabotok/pipeline_v3/watchdog.py` | `kill_path`, `kill_state_path`, `_voice_bg()` | Add metrics update loop; ensure kill-check at every cycle. |
| `zarabotok/pipeline_v3/tests/test_exec_pipeline.py` | 1–30 (`TestValidate`) | Add matrix-link tests; add webhook tests; add container tests. |

---

*Audit complete. Next action per WORKFLOW line 35: `python -m pytest tests/ -v`; `python modules/executor.py`; `python check_releases.py`. Recommend running these before applying recommendations 1–3.*
