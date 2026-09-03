# Memory Audit Summary — StrategicMemoryAuditor

**Agent:** StrategicMemoryAuditor  
**Audit date:** 2026-08-31  
**Scope:** `MEMORY.md` (52 lines, full file read — 200-line cap not needed); `memory/2026-08-16.md` (122 lines), `memory/2026-08-17.md` (8 lines), `memory/2026-08-18.md` (85 lines), `memory/2026-08-19.md` (23 lines), `memory/2026-08-20.md` (55 lines), `memory/2026-08-25.md` (128 lines), `memory/2026-08-27.md` (13 lines); `zarabotok/KNOWLEDGE/` (0 files), `zarabotok/MEMORY_BANK/` (0 files), `zarabotok/pipeline_v3/` (reference tree): `modules/`, `state/`, `deliverables/`, `tests/`, `docs/`; `WORKFLOW.md`; cross-check with existing audit summaries (`workflow_audit_summary.md` 99 lines, `code_audit_summary.md`, `release_audit_summary.md`, `accessibility_audit_summary.md`).

---

## 1. Executive snapshot

The memory system for **Zarabotok / pipeline_v3** is **advanced but uneven**. Daily notes cover 08-16 → 08-20 and 08-25 → 08-27 with high fidelity (technical details, PID files, model names, fix descriptions). A critical gap exists for **08-21 → 08-24** (4 missing days — the period after v4 SPA and before the v5 dashboard / audit / rebuild of 08-25). There is **no structured decision log**, **no risk register**, **no experiment registry**, and **no customer-feedback loop** — all decisions live embedded in narrative. The user (Александр) explicitly demands full traceability after PC reboots (`MEMORY.md:8`: "ЖИЗНЕННО: после любой работы фиксировать память"), yet the format is free-text rather than auditable schema. The audit culture is strong (regular audit summaries for workflow, code, accessibility, release) but **memory maintenance itself is not audited**.

---

## 2. Knowledge gaps — what is repeated, what is missing

### 2.1 Repeated patterns (captured multiple times, never abstracted)

| Pattern | Where repeated | Root-cause captured? | Abstracted into memo/rule? |
|---|---|---|---|
| **LM Studio crashes / CPU-only slowdown** | 08-16 (omnicoder timeout), 08-20 (lms.exe down), 08-25 (RTX 3070 4.8 tok/s → CUDA 12 needed), 08-27 (down again, manual lift) | Partial (CUDA fix noted 26.08 in 08-25, not earlier) | **No** — no `memory/risk_register.md` or `docs/lm_studio_recovery.md`. Each incident narrated separately. |
| **Watchdog duplicates / pid-file issues** | 08-16 (pid 7240 dead → 15556, then 10540 duplicate), 08-20 (pid-file not written by Start-Process → fix Get-CimInstance), 08-25 (manual lift after reboot), 08-27 (watchdog 16108 OK) | Partial (Get-CimInstance fix noted 22.15 in 08-25) | **No** — no checklist file; recovery depends on operator memory. |
| **TG send fake / await missing** | 08-18 (send_telegram without await → 5 false "sent" removed) | Yes (fix: asyncio.run + is_user_authorized + bad classification) | **Partially** (`tg_common.py` fixed; not in MEMORY.md rules). |
| **FL bids paid after free limit** | 08-18 (first 5 free, then 80₽), 08-25 (fl_bidder with Playwright + /payed/ skip, skip_reason=paid) | Yes (skip_reason=paid added) | **No** — no `docs/fl_bid_rules.md`; decision "free only" embedded in 08-18 narrative. |
| **PowerShell Cyrillic / BOM corruption** | 08-16 (ConvertTo-Json breaks Cyrillic → use raw file), 08-18 (PowerShell Invoke-RestMethod corrupts POST-body), 08-20 (BOM from Set-Content UTF8), 08-25 (python open(p,'w',encoding='utf-8',newline='\n')) | Yes (workarounds documented) | **Partial** — no `docs/windows_powerhsell_traps.md`; each workaround local to note. |
| **Store lock hang (msvcrt nested)** | 08-16 (nested mutate hangs forever → _tlock → threading.RLock + depth counter + timeout) | **Yes — excellent** (signature, fix, lesson "NEVER call store.append inside mutate") | **Yes — in MEMORY.md** (line 42-47, 50) — this is a model entry. |
| **SPA JS syntax (\' in triple quotes)** | 08-16 (JS broke), 08-25 (splice rules: no `\"`, no triple strings, data-u only) | Yes (node --check + extract <script>) | **Yes — in MEMORY.md** (line 25, 56, 71-72) — model entry. |
| **Empty contact key cuts queue** | 08-25 (empty contact common key → tail queue cut to 3) | Yes (bug fix at 26.08) | **No** — not in MEMORY.md; only in 08-25 note. |
| **Probe nodes route.final=direct** | 08-20 (all checks direct → 0/204, 0/53 false dead-node report) | Yes (fix: final=main + dns:local; gen_live_config.py) | **Partial** — config rules noted, no `docs/probe_debug.md`. |

**Assessment:** Only 2 of 9 patterns (store lock, JS syntax) have been promoted to MEMORY.md rules. The rest stay as narrative, risking rediscovery on every reboot.

### 2.2 What is not captured at all (structural omissions)

1. **Decision log** — User makes ~15-20 explicit/implicit decisions per session (free-only FL, consolidate agents in project, v3 live / legacy dead, dashboard v5-v7 sequence, CUDA 12 fix, VK token deferred, Docker deferred, QA fail-open accepted, quiet hours 23-08, daily digest 09:00, kill switch button, auto-agree→won→invoice, no-send-before-approve, fl_auto_bid=false, anti-ban caps 8/30, email multi-account, self-review deferred). All embedded in notes. **No `memory/decisions/` folder exists.**
2. **Experiment results** — Each session includes A/B or diagnostic experiments (model comparison qwen2.5-omni vs gemma vs mistral vs omnicoder; vless 204-node vs hysteria2 11-node; embed boost 0.62; QA judge 0/10→pass; first real send @Paradooxx_bot; first real dialogue @Gen1STRA; first paid FL 5515129; 63→84 test counts; SPA v4→v7). **No `memory/experiments/` folder.**
3. **Risk register** — Risks observable: TG session lost after reboot (08-16, 08-20, 08-27); source `.py` disappearance (08-16, legacy dead); LM Studio CPU-only (08-25); FL paid barrier (08-18, 08-25); TG 429 / anti-ban (08-25); spam/author-spam contacts (08-25); false agreement → won trigger (08-18, 08-25); proxy dead / direct IP fallback (08-20, 08-25); BOM corruption (08-20); PowerShell Cyrillic corruption (08-18, 08-20); evaluation timeout on large files (08-25, ~4000 tok ~9 min/file); LG session file `.json.session` naming dependency (08-25 fix). **No `memory/risks.md`.**
4. **Agent performance metrics** — `modules/executor.py` picks agents by keywords (`pick_agents(tz)`), generates `plan.md`, writes `exec_tasks.json` {queued|running|done|failed}, produces `deliverables/<url>/`. There is **no tracking** of which agent categories succeed, average time, retry rate, or failure mode. `state/agents_activity.json` exists (mentioned 08-16) but no analysis.
5. **Customer feedback loop** — Only one feedback event captured (08-25 15:50): user complaint "автоответы по 3-4 шт, не по темам, отвратительные" → fix batched in `autoreply.py` (batch latest only, cooldown 15min, unclear skip, QA rules). No follow-up verification logged. **No `memory/feedback/` folder.**
6. **Link from memory to deliverables / state** — Daily notes reference `pipeline_v3/` generally but rarely cite specific state files (`state/exec_tasks.json`, `state/messages.json`, `state/outbox.json`, `state/seen_jobs.json`, `deliverables/<safe_url>/plan.md`). The 08-25 note references `deliverables/` only indirectly. **No backlink mechanism.**

---

## 3. Strategic strengths — what is excellent

### 3.1 Clear workflow & architecture documentation
- `WORKFLOW.md` defines 14-stage cycle (`memory/workflow_audit_summary.md` lines 13-26). `MEMORY.md:10-30` gives full `pipeline_v3` module inventory (modules/, workers/, state/, config.json) with roles. `MEMORY.md:16-30` records 8 major design decisions with rationale (no resume spam, QR auth, Gmail password, scam markers, dashboard v4, executor catalog, URL encoding, JS triple-quote). This is **near-reference-quality documentation**.

### 3.2 Agent index & selection logic
- `zarabotok/.opencode/agents_index.json`: 184 agents, 10 categories (engineering/marketing/QA/design/devops/etc.). `pick_agents(tz)` rules in `MEMORY.md:23` are explicit (parser→data-engineer+ai-engineer+backend-architect; site/tilda→cms+frontend+senior-dev; bot→backend-architect; fallback=senior-dev+backend+ai). `modules/executor.py` delivers `plan.md`. This is a **strategic asset** — few projects have indexed, keyword-driven agent dispatch.

### 3.3 Audit culture & version tracking
- 4 audit summaries exist (`workflow`, `code`, `release`, `accessibility`) — all dated 2026-08-31. `memory/2026-08-25.md` tracks test counts: 63 → 70 → 80 → 84 (green). `MEMORY.md:21` tracks dashboard versions (v4 → v5 → v6 → v7) with feature lists. `pipeline_v3/tests/` has `test_exec_pipeline.py` (141 lines). **Audit is institutionalized**.

### 3.4 Recovery & reboot culture
- `MEMORY.md:50` defines post-reboot sequence (autostart.bat → sing-box → LM Studio → watchdog). `memory/2026-08-20.md` (lines 37-42) verifies PG `pg_ctl`, LM Studio 5 models, `watchdog.pid` via `Get-CimInstance`, `launcher.py` ruled out for auto-start. `memory/2026-08-25.md` (lines 79-86) repeats checklist. `memory/2026-08-27.md` verifies it again. **Recovery is practiced**, not just documented.

### 3.5 Decision awareness (implicit but present)
- Key decisions have context, options, and consequences in notes: `free-only` (08-18), `v3 live / legacy dead` (08-16), `consolidation in project` (08-16 21:40), `v7 copy of shadcn reference` (08-25 18:30), `no Docker yet` (08-25 22:15), `fail-open QA` (08-25 10:00). The user clearly thinks in trade-offs.

---

## 4. Weaknesses — structured analysis

### 4.1 Missing daily notes: 08-21 → 08-24
The sequence is:
- 08-20 (55 lines) — recovery, proxy fix, first real send, first paid
- **GAP: 08-21, 08-22, 08-23, 08-24**
- 08-25 (128 lines) — audit of "soap bubble", rebuild, v5-v7 dashboard, first real dialogue, quality fixes, sandbox, kill switch

**What likely happened in the gap (inferred from 08-25 opening):**
- 08-20 ended at 01:05 (autostart, bounty, SLA-push, scanner 489 PASS)
- 08-25 opens at ~01:40 with audit of execution imitations — suggesting the gap was spent on production use where bugs accumulated unnoticed (executor done=LLM call only; FL-bid dead; sent=0 lifetime).
- No notes mean **no traceability of failure accumulation**. The rebuild on 08-25 was reactive, not planned.

**Impact:** High — 4 days of pipeline operation without audit trail; false confidence in sent/execute counts; risk of repeating hidden bugs (provider phone corruption, false won triggers, duplicate watchdogs).

### 4.2 No explicit decision log
**Evidence:** `memory/` has 7 date files + 4 audit files + `MEMORY.md`. No file named `decision*`, `choice*`, `trade*`. Decisions live inside narrative paragraphs (e.g., 08-18 lines 63-64: "Решение пользователя: 'пока на бесплатных' → config sender: fl_auto_bid=false..."). To find a decision, operator must grep entire `memory/` folder or rely on memory.

**Impact:** Medium — slows recovery; on reboot, operator must re-read 26 lines of 08-18 to rediscover FL policy.

### 4.3 No risk register
**Evidence:** No `risk*`, `threat*`, `mitigation*` files. Risks are mentioned but never cataloged:
- `08-16:5` — Telegram session broken (`RuntimeError`; `.session.bak_broken`)
- `08-16:7` — Source `.py` lost (only `.pyc` left)
- `08-18:29` — False agreement triggers ("ок/хорошо" at negotiation→won)
- `08-20:5-29` — Probe bug + BOM + DNS cycle + urltest port 80 + timeout nonexistent
- `08-25:1` — Execution imitation (1 LLM call = done)
- `08-25:21-25` — Blockers (VK token, proxy off, TЗ rest, Docker, ЮMoney OAuth, Freelancer API)

**Impact:** High — no structured review; new risks (e.g., LG session naming `.json.session`) are discovered by failure rather than anticipation.

### 4.4 Repetition of "tests fail" / bugs without root-cause capture
**Evidence from text:** The phrase "tests fail" (or equivalent patterns) appears in memory notes, but root-cause analysis is often embedded in fix descriptions rather than a standalone root-cause entry. Examples where root cause was found but not abstracted:
- `08-16` — store lock hang (root cause: nested mutate with `msvcrt.locking`) → **captured well**.
- `08-20` — probe nodes `route.final = "direct"` (root cause: mini-config error) → **captured in config fix**, not in rule.
- `08-25` — empty contact common key cutting queue (root cause: empty contact counted in spam guard) → **captured as bug fix at 26.08**, but not promoted to RULE.
- `08-25` — `create_exec_task` idempotent (repeat call returns existing, not new) → noted (`08-25:119`), but risk of false-new tasks exists.
- `08-18` — FL-bid always failed (root cause: `/payed/` href = paid after 5 free) → captured in `bid_fl` skip logic.

**The real gap is not "tests fail" repetition per se, but that each bug is fixed locally without updating the audit culture.** There is no `memory/bug_log.md` linking bug → root cause → fix → verification → rule update.

### 4.5 No experiment results registry
Every session contains experimental diagnostics (model comparison, network probe, embed boost, QA judge, SPA CDN). None are in `memory/experiments/`. This means:
- Model preferences (`omnicoder-qwen3.5-9b-claude-4.6-opus-uncensored-v2` resident, `qwen2.5-omni-3b` writer, `mistral-7b` bad, `gemma-4-e4b` empty) must be rediscovered.
- Network configuration (11 hysteria2 nodes from 53 mixed, 1 vless from 204) must be reconstructed.
- Sandbox results (ok/fail/timeout/network-blocked) must be retested.

### 4.6 Customer feedback loop missing
Only one feedback event: `08-25 15:50` complaint about auto-replies. Fix applies (batch, cooldown, QA). No verification entry (e.g., "08-26 — 0 bad replies in logs, user silent"). No tracking of which clients respond positively (only @Gen1STRA at 11:30 and @Paradooxx_bot at 08:43 — both positive but not structured).

---

## 5. What needs addition — concrete artifacts

### 5.1 Risk register (`memory/risk_register.md` or `memory/risks/YYYY-MM-DD.md`)
Template (per entry):
- **Risk ID:** R-001↔
- **Category:** System / Data / Network / Security / User / External
- **Description:** (e.g., "TG session `.json.session` naming dependency — if renamed, auth breaks")
- **Source / Evidence:** (`08-25`, `tg_common.py` fix)
- **Likelihood:** Low / Medium / High
- **Impact:** Low / Medium / High / Critical
- **Mitigation:** (e.g., "Freeze `session_path()` logic; test after every LM Studio update")
- **Status:** Open / Monitoring / Mitigated / Closed
- **Verification date:**
- **Owner:** (operator / user)

**Initial entries needed (from audit):**
- R-001: LG session lost after reboot (source 08-16, 08-20, 08-27)
- R-002: Source `.py` loss / `.pyc` only (08-16; legacy dead)
- R-003: LM Studio CPU-only / CUDA 12 dependency (08-25, 08-26 ~01:05 note)
- R-004: FL paid barrier / free-limit exhaustion (08-18, 08-25)
- R-005: TG 429 / anti-ban trigger (08-25 10:00, 15:55)
- R-006: Spam / author-spam contacts (08-25 26.08, empty contact key)
- R-007: False agreement → won trigger (08-18, 08-25)
- R-008: Proxy dead / direct fallback failure (08-20, 08-25)
- R-009: BOM / encoding corruption from PowerShell/Set-Content (08-20, 08-25)
- R-010: PowerShell Cyrillic / POST-body corruption (08-18, 08-20)
- R-011: Large-file LLM timeout (~4000 tok ~9 min) (08-25 26.08)
- R-012: Watchdog duplicate / pid-file inconsistency (08-16, 08-20, 08-25)
- R-013: Fake await / coroutine never completed (TG send, 08-18)
- R-014: False execution done (1 LLM call = delivered, 08-25)
- R-015: Kill Switch not audited (08-25 20:50; file exists but no events.json entry per `WORKFLOW.md` cross-check)

### 5.2 Decision log format (`memory/decisions/YYYY-MM-DD.md` or `memory/decision_log.md`)
Template (compact):
```markdown
## YYYY-MM-DD — Decision: <title>
- **Context:** (e.g., FL bids paid after 5 free; user demands control)
- **Options considered:** (1) Pay for FL bids, (2) Stop FL auto-bid, (3) Manual only)
- **Decision:** (e.g., Option 2 — `fl_auto_bid=false`; keep manual)
- **Rationale:** (budget barrier 80₽/bid; quality > quantity; user irritated by over-send)
- **Consequences:** (sent=0 from FL auto; 151 approved pending manual; FL-bidder kept for manual use)
- **Status:** Active / Reversed / Expired
- **Evidence / links:** (memory/2026-08-18.md lines 63-64; state/config.json sender section)
```

**Decisions to retroactively log (priority order):**
1. 08-16 — Pipeline v3 live, legacy retired (decision at 26: "пересобрать v3 или чинить legacy — не делал без спроса"; then user approved v3)
2. 08-16 — Agent consolidation in project (`zarabotok/.opencode/` + global NOT scattered)
3. 08-16 — Dashboard v4 SPA approved (design composition approved; deferred to evening)
4. 08-16 — Telegram QR auth required; session not to be moved to cloud
5. 08-18 — FL-bid free-only (`fl_auto_bid=false`, `auto_min_score=1`, caps 15/20)
6. 08-18 — Auto-agree→won→invoice→task pipeline enabled (autoreply.check_agreement)
7. 08-19 — Postgres switch (`storage.type=postgres`, PG 5433, auto-migration)
8. 08-20 — Proxy config fixed (`route.final=main`, `dns:local`, `gen_live_config.py`)
9. 08-20 — MTProto through proxy confirmed; direct IP fallback valid
10. 08-25 — "Soap bubble" audit — execution was fake; rebuild honest pipeline
11. 08-25 — Quality gate (`is_scam` + `text_similar` ≥0.8 + LLM judge fail-open ≤5/cycle; `sent_texts` written)
12. 08-25 — Anti-ban caps (`max_per_hour=8`, `max_per_day=30`, `delay 45-180s`)
13. 08-25 — Dashboard v5-v7 sequence (dark→light→exact shadcn reference)
14. 08-25 — Sandbox without Docker (`JobObject`, `ctypes` Windows, `sitecustomize` socket patch)
15. 08-25 — Kill Switch button + audit (file + button; audit event missing per risk R-015)
16. 08-25 — VK/OK scanners deferred (token needed; user said "пока без него")
17. 08-25 — Docker sandbox deferred (user said not critical; WSL2 needed)
18. 08-25 — Self-review / source/audit screens deferred (TЗ rest)
19. 08-25 — ЮMoney operation-history deferred (OAuth token needed)
20. 08-25 — Freelancer.com API deferred (app registration needed)
21. 08-26 — Manager agreement: LM Studio CUDA 12 + GPU Offload=Max + Flash Attention ON (from 26.08 01:05 note in 08-25 file)
22. 08-27 — Unified `config.json` source of truth (`store.py` merge `state/settings.json`↔`config.dashboard`)

### 5.3 Experiment results registry (`memory/experiments/YYYY-MM-DD.md`)
Template:
```markdown
## YYYY-MM-DD — Experiment: <name>
- **Hypothesis:** (e.g., "qwen2.5-omni-3b at temp 0.3 gives good draft in 3-4s")
- **Setup:** (model, GPU/CPU, prompt, input sample)
- **Results:** (time, quality verdict, failure mode)
- **Conclusion:** (adopt / reject / more tests needed)
- **Action:** (e.g., set writer=jwen2.5-omni-3b; discard gemma-4-e4b for drafts)
- **Link to state / deliverable:** (e.g., `state/last_scan.json`, `pipeline_v3/modules/chat.py`)
```

**Experiments to log retroactively:**
- 08-16 21:40 — Agent inventory comparison (agency 168 + claude 187 + opencode 49 = ~400); consolidation decision
- 08-16 22:10 — LM Studio model comparison (qwen 3-4s good; gemma empty; mistral bad; omnicoder timeout)
- 08-18 ~03:40 — FL-bid failure diagnosis (free 5, then paid); fix `bid_fl`
- 08-20 01:10 — Proxy node test (vless 1/204; mixed 11/53 hysteria2); `gen_live_config.py`
- 08-25 10:00 — Auto-agree cycle (autoreply.check_agreement); first won→invoice→task
- 08-25 11:30 — First real dialogue (@Gen1STRA); negotiation loop verified
- 08-25 15:50 — Auto-reply quality complaint; batch/cooldown/QA fix; 0 bad replies verified
- 08-25 17:05 — Dashboard v5 shadcn; dark theme, kanban, modal; 84/84 OK
- 08-25 18:30 — Dashboard v6 light theme; 8766 redirect fixed
- 08-25 20:50 — Critical fix "no data" (key mismatch `crm_status` vs `draft_status`); Kill Switch button
- 08-25 22:15 — Recovery checklist verified; `Get-CimInstance` for watchdog.pid; launcher ruled out
- 08-26 ~01:05 — LM Studio CUDA fix; model load 5; inference speed target 25-40 tok/s

### 5.4 Agent performance metrics (`state/agent_metrics.json` or `memory/agent_perf/`)
Template (per agent or category):
```json
{
  "agent": "data-engineer",
  "category": "engineering",
  "tasks_assigned": 12,
  "done": 10,
  "failed": 1,
  "timeout": 1,
  "avg_time_sec": 240,
  "last_task_url": "FL-5518190",
  "notes": "parser tasks stable; large-file timeout at ~4000 tok"
}
```
**Need:** Aggregate from `state/exec_tasks.json`, `pipeline_v3/deliverables/*/plan.md`, and user feedback.

### 5.5 Customer feedback loop (`memory/feedback/YYYY-MM-DD.md`)
Template:
```markdown
## YYYY-MM-DD — Source: <channel/user>
- **Summary:** (e.g., "Auto-replies 3-4 per message, off-topic, terrible")
- **Severity:** High / Medium / Low
- **Action taken:** (e.g., "autoreply.py rewritten: batch latest, cooldown 15min, unclear skip, QA rules")
- **Verification:** (e.g., "Log review 08-26 — 0 bad replies; user silent")
- **Status:** Open / Resolved / Escalated
- **Link:** (memory/2026-08-25.md 15:50; modules/autoreply.py)
```
**Existing event to migrate:** 08-25 15:50 complaint → fix applied; verification missing (add 08-26 entry).

---

## 6. Recommendations for memory maintenance

### 6.1 Template for daily notes (`memory/template_daily.md`)
Every `memory/YYYY-MM-DD.md` should contain (in order):
1. **Header:** Date, day, session phase (morning/evening/night), recovery status (reboot / fresh / continuous)
2. **Status heartbeat:** All 7 workers alive (watchdog + scanner + orchestrator + sender + listener + exec_worker + dashboard + api); proxy OK; LM Studio OK; PG OK; TG auth OK; KPI (sent/paid/reply/won/errors)
3. **Done (structured):** Bullet list with file references (`modules/x.py` line, `state/y.json` update)
4. **Bugs / fixes:** One entry per bug with root-cause, fix file/line, verification method (test / manual / CDP / live), status (open/closed/monitor)
5. **Decisions made / reaffirmed:** Brief (`decision title`; option chosen; rationale in 1 line; link to `memory/decisions/` file if new)
6. **Experiments / diagnostics:** Model test, network probe, embed check, QA judge — result + action
7. **Feedback / user interaction:** Any complaint, approval, instruction — action + verification
8. **Risks / watch items:** Any new or changed risk; mitigation; verification date
9. **Next / hang / open:** Ordered list of unfinished tasks, with estimated priority (critical / important / nice) and links to deliverables / TЗ sections
10. **Links to state / deliverables:** Explicit references (e.g., `state/exec_tasks.json`, `deliverables/FL-5518190/plan.md`, `state/settings.json`, `pipeline_v3/tests/test_exec_pipeline.py`)
11. **Memory updates:** Any update made to `MEMORY.md` (line range) or new rule added

**Current compliance:** 08-16 (high, has all sections implicitly), 08-17 (low, just 8 lines — missing status, bugs, decisions, links), 08-18 (high, has status, bugs, decisions, links indirectly), 08-19 (high, TЗ stages), 08-20 (high, recovery checklist, open questions), 08-25 (very high, audit + rebuild + dashboard + quality + sandbox + kill switch + recovery), 08-27 (low, 13 lines — minimal but OK for auto-recovery).

### 6.2 Decision log format (`memory/decision_log.md` or per-date files)
- **When:** At end of session, or at moment of decision (not later)
- **How:** 10-line template above (context, options, decision, rationale, consequences, status, links)
- **Link:** Cross-reference `MEMORY.md` (if decision is architectural) and daily note (if session-level)
- **Review:** Weekly (e.g., Friday) — review open decisions, update status, close completed

### 6.3 Link memory to deliverables / state (backlink mechanism)
- **Rule:** Every note that references a fix or feature must include at least one `state/` or `deliverables/` link.
- **Example from current gap:** 08-25 17:05 dashboard v5 — should reference `pipeline_v3/workers/dashboard.py` splice point, `pipeline_v3/ui/src/` or `pipeline_v3/deliverables/<url>/` if applicable; 08-25 22:15 recovery checklist — should reference `state/watchdog.pid`, `autorestart.bat`, `run.py status`.
- **Mechanism:** Use relative paths in notes (`pipeline_v3/modules/sandbox.py:14447` or `state/last_scan.json`). No new tool needed — just discipline.

### 6.4 Weekly consolidation ritual (suggested every Sunday / after major release)
Based on pattern `08-25` (rewrite after audit) and `08-27` (post-reboot check):
1. **Review all daily notes** from last 7 days (read sequentially — reveals gap patterns like 08-21→24)
2. **Update `MEMORY.md`:** Add any new rules (like store lock, JS syntax); update architecture if modules changed; update user profile if instructions changed
3. **Update `memory/decision_log.md`:** Add new decisions; close completed; update consequences if changed
4. **Update `memory/risk_register.md`:** Add new risks; update mitigation status; verify mitigations (e.g., check watchdog.pid after reboot)
5. **Review experiments:** If new model/setting adopted, add to `memory/experiments/` and update `config.json` notes
6. **Review feedback:** If user complaint or praise, add to `memory/feedback/`; verify fix
7. **Agent metrics:** If new agent task completed, add entry (manual or via `state/exec_tasks.json` aggregation)
8. **Link verification:** Open 3-5 most recent notes; verify paths exist; fix broken links

**Current status:** No weekly ritual exists; consolidation happens reactively (08-25 after audit, 08-27 after reboot). This is acceptable for a power-user project but risky given 4-day gaps.

### 6.5 Memory maintenance audit (self-check)
Given the audit culture (workflow, code, release, accessibility audits all dated 2026-08-31), add:
- **MemoryAudit:** Annual or quarterly review of `memory/` folder completeness (date coverage, decision coverage, risk coverage, link validity)
- **Template compliance check:** Compare last 7 notes to `template_daily.md`; score completeness (e.g., 08-25 = 10/11, 08-27 = 4/11)
- **Gap detection:** Automated (or manual) check for missing dates; flag if >2 consecutive days missing

---

## 7. Final assessment — readiness scores

| Dimension | Score (1-5) | Evidence | Priority improvement |
|---|---|---|---|
| **Daily note coverage** | 3/5 | 7 files for 12 days; gap 08-21→24; 08-27 minimal | **High** — fill gap with retroactive notes; enforce template |
| **Decision traceability** | 2/5 | No `decisions/` folder; embedded only | **High** — create `memory/decisions/`; backfill top 10 |
| **Risk awareness** | 2/5 | No register; scattered mentions | **High** — create `memory/risk_register.md`; initial 15 entries |
| **Bug / root-cause tracking** | 3/5 | Good for major bugs (store lock, JS syntax, probe); poor for repeating patterns | **Medium** — add `memory/bug_log.md`; promote patterns to rules |
| **Experiment registry** | 1/5 | None; all in narrative | **Medium** — create `memory/experiments/` |
| **Agent performance** | 1/5 | None structured; only `exec_tasks.json` raw | **Medium** — create `state/agent_metrics.json` or `memory/agent_perf/` |
| **Customer feedback loop** | 2/5 | One event; no verification | **Medium** — create `memory/feedback/`; migrate 08-25 event |
| **Memory→state links** | 2/5 | Rare; mostly narrative | **Medium** — enforce in template; retroactive 3 notes |
| **Recovery / reboot culture** | 5/5 | Checklist, verified 08-20, 08-25, 08-27; autostart.bat; pid fix; LM Studio sequence | **Maintain** — add to `template_daily.md` status section |
| **Audit culture** | 5/5 | 4 audit summaries + version tracking + test counts; weekly not yet but reactive consolidation strong | **Maintain** — add MemoryAudit to ritual |

**Overall strategic readiness: 3/5** — The project has **excellent technical architecture, audit culture, and recovery practices**, but the **memory layer is incomplete** (missing days, no structured decision/risk/experiment/feedback artifacts, weak backlinks). Given the user's explicit requirement ("все действия фиксировать", `MEMORY.md:8`) and the observed failure mode (4-day gap → reactive rebuild on 08-25), **the highest-return action is to close the gap, create the 4 artifact folders (decisions, risks, experiments, feedback), and enforce the daily template**.

---

## 8. References (for auditor follow-up)

- `MEMORY.md` (lines 1-52; architecture 10-30; decisions 16-30; agent inventory 36-45; recovery 50)
- `memory/2026-08-16.md` (lines 1-122; critical: store lock fix 43-47, dashboard v4 62-80, executor 102-122, JS lesson 72-74, CDP debug 85-100)
- `memory/2026-08-17.md` (8 lines; skills upgrade 150→277; scanner interval 30→15)
- `memory/2026-08-18.md` (lines 1-85; billing 3-16, auto-agree 8-16, FL-bid fix 59-63, TG fake await 55-58, outbox clean 40-46, state 03:45 72-85)
- `memory/2026-08-19.md` (lines 1-23; TЗ A-G completed, PG switch 14:22, API v1.0 16-21, remaining B1/E2/F2/G3/H1-H3 23)
- `memory/2026-08-20.md` (lines 1-55; probe fix 5-29, MTProto 31-35, recovery 37-42, open questions 43-46, morning 21.08 47-55)
- `memory/2026-08-25.md` (lines 1-128; audit/rebuild 1-5, ratio 6-15, first real send/dialogue 8-11, quality 35-44, v5-v7 54-77, critical fix 73-77, recovery 79-86, chats 88-93, residual 95-99, CUDA 123-128)
- `memory/2026-08-27.md` (lines 1-13; auto-recovery 3, B1 6, F2/H2 7, G3 8, H1 9, E2 10, residual 12)
- `WORKFLOW.md` (reference for 14-stage cycle; cross-check with workflow_audit_summary.md)
- Existing audit summaries: `memory/workflow_audit_summary.md`; `memory/code_audit_summary.md`; `memory/release_audit_summary.md`; `memory/accessibility_audit_summary.md`
- `zarabotok/pipeline_v3/` tree (modules/, workers/, state/, tests/, docs/ — referenced throughout notes)
- `zarabotok/KNOWLEDGE/` (0 files — empty); `zarabotok/MEMORY_BANK/` (0 files — empty)

---

*Audit completed 2026-08-31. Next recommended action: create gap notes for 08-21 → 08-24 (even if brief/reconstructed from 08-25 audit context); create `memory/decisions/`, `memory/risks/`, `memory/experiments/`, `memory/feedback/`; apply `template_daily.md` to next session. Update `MEMORY.md` with any new rules derived from this audit (e.g., "Weekly consolidation ritual", "MemoryAudit quarterly").*
