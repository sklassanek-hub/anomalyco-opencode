# Agent Activity Sync — 2026-08-31 (M8)

**Source:** `zarabotok/pipeline_v3/state/agents_activity.json` (404 lines; 27 items from 27.08 through 30.08).
**Sync date:** 2026-08-31.
**Status:** SYNCED — summary created; full JSON preserved at source path; backlink from `MEMORY.md` and `memory/2026-08-31.md` verified.

## Source file info
- Path: `zarabotok/pipeline_v3/state/agents_activity.json`
- Size: 404 lines (JSON array under `items`).
- First entry: `2026-08-27T18:56:32+0300` — agent `crm`, action `статус -> draft`, ok=true, order `https://t.me/s/workayte`.
- Last entry: `2026-08-30T21:07:55+0300` — agent `executor`, action `пайплайн review (файлов: 6, ок: 2, с проблемами: config/settings.py, utils/logger.py, models/error_types.py, main.py); ждёт одобрения человека`, ok=true, order `https%3A%2F%2Ftest%2Fexception`.

## Key agent actions (summarized from JSON)
- **crm (27-30 Aug):** Status transitions `draft → won → reply → won` on multiple orders (`test.url`, `test.example.com/won`, `test-won`, `auto-delivery`, `final-integration`); reply actions at 03:30 and 03:33; sender triggers (`executor` task creation) at 03:31 and 03:33.
- **executor (28-30 Aug):** Task creation for `auto-delivery` (3 agents: senior-developer, backend-architect, ai-engineer) at 03:31; review wait at 03:43 and 04:00; second pipeline (`final-integration`, 4 files) at 03:44; review wait at 04:00; exception pipeline (`test/exception`, 6 files) at 20:46, 20:47, 20:57; final review wait at 21:07 (2 ok, 4 problems: settings, logger, error_types, main).
- **exec_worker (28-30 Aug):** Pipeline runs `plan → implement → validate → repair` starting 03:32 (auto-delivery), 03:44 (final-integration), 20:47 (exception); file-level actions: `api/handlers/delivery.py` (validate fail 1/2 → repair → ok at 03:39), `services/delivery_service.py` (runtime smoke fail → repair → ok at 03:42), `models/delivery_model.py` (ok at 03:43); for exception pipeline: `bot.py` (ok at 20:53 after 2 repair cycles), `handlers/exceptions.py` (ok at 20:57 after 1 repair), `config/settings.py` (ok after 2 repairs), `utils/logger.py` (errors: 1 at 21:07), `models/error_types.py` (generate failed at 21:07), `main.py` (generate failed at 21:07).

## Metrics / patterns noted
- Pipeline cycle time (plan to review): ~11-12 minutes (auto-delivery 03:32→03:43; final-integration 03:44→04:00; exception 20:47→21:07 = 20 min longer due to multiple repair cycles).
- Repair rate: auto-delivery 1/3 files needed repair; final-integration 1/4; exception 4/6 files needed repair (high failure rate on exception test).
- Review wait: executor holds at `wait for human approval` after all files validated; this is expected per pipeline design (`executor.py` review step).
- Agent collaboration: `senior-developer` + `backend-architect` + `ai-engineer` — consistent 3-agent team per task (standard `pick_agents` selection).

## Relationships
- `state/exec_tasks.json` — tasks active 28.08 (auto-delivery, final-integration, broken/blocked/exception tests); matches `agents_activity.json` pipeline runs.
- `state/kill_switch_active.json` — exists but module `modules/kill_switch.py` created 25.08; killed/stopped state not shown in 27-30 activity.
- `state/events.json` — new 25.08; not referenced in 27-30 entries (events file may log kill_switch + access + errors separately).
- `memory/2026-08-25.md` — first real send 08:43; agent activity starts 27.08 (post-buil rebuild stable state).

## Verification (M8 check)
- Source file exists at `zarabotok/pipeline_v3/state/agents_activity.json`.
- Backlink from `MEMORY.md` (§Memory artifact index) verified.
- Backlink from `memory/2026-08-31.md` (Connections to state) verified.
- Backlink from `memory/p0_memory_agent.md` (§Cross-file index — M8 previously NOT SYNCED, now resolved) implicitly satisfied.
