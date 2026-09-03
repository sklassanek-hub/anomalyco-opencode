# Kanban Tracking — 78 Worklist Items (TrackingAgent / 2026-08-31)
**Source:** `memory/complete_worklist.md` (78 checkboxes verified by Select-String)  
**Evidence sources:** `p0_fixes_summary.md`, `accessibility_complete.md`, `workflow_completion.md`, `memory_completion.md`, `release_completion.md`, `spm_review.md`, `sd_execution.md`, `backend_execution.md`, `db_execution.md`, `mcp_execution.md`, `search_optimizer.md`  
**Agent:** TrackingAgent  
**Status legend:** Backlog = unstarted / spec only; Agent/Code = edited / compile OK; Manual Verify = needs evidence screenshot/log/command; Done = all exit criteria met + evidence file saved.

---

## Swimlane: Accessibility (A) — 22 items
| ID | Item (spec line) | Status | File / Line Ref | Agent Assign | Evidence Link |
|---|---|---|---|---|---|
| A1 | Modal/Drawer `role="dialog"` + focus-trap + restore | Agent/Code | `Modal.tsx` 11–87; `Drawer.tsx` 10–32 | AccessibilityCompletionAgent | `p0_fixes_summary.md` §1; `accessibility_complete.md` §2 |
| A2 | Toast `aria-live="polite"` + `aria-label` | Agent/Code | `Toast.tsx` 38–44 | AccessibilityCompletionAgent | `p0_fixes_summary.md` §1; `accessibility_complete.md` §2 |
| A3 | Table `ArrowUp/ArrowDown` vertical nav | Agent/Code | `Table.tsx` 55–67; `<tbody onKeyDown>` | AccessibilityCompletionAgent | `accessibility_complete.md` §2.2; `p0_fixes_summary.md` §1 |
| A4 | Pipeline `ArrowLeft/ArrowRight` DOM loop | Agent/Code (partial) | `Pipeline.tsx` 82–104 + 36–48; placeholder 111–113 | AccessibilityCompletionAgent | `accessibility_complete.md` §2.1; `p0_fixes_summary.md` §25 |
| A5 | Task/Input `aria-invalid` + `aria-describedby` | Agent/Code | `Task.tsx` 156; `Input.tsx`; `Select.tsx` | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A5) |
| A6 | Skip-link `<a href="#main">` + `id="main"` + dynamic title | Agent/Code | `Layout.tsx`; `pages/*.tsx`; `DocumentTitle.tsx` | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A6/A16) |
| A7 | `focus-visible` outline + `prefers-reduced-motion` | Agent/Code | `styles.css` 137–149; 465–476; 825–831 | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A7/A11) |
| A8 | NavLink `aria-current="page"` | Agent/Code | `Layout.tsx` (Link + useLocation) | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A8) |
| A9 | Tabs `ArrowLeft/ArrowRight` + `aria-selected` + `tabIndex={-1}` | Agent/Code (partial / placeholder) | `Pipeline.tsx` arrow loop; `Tabs.tsx` not edited | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A9) |
| A10 | Overview / Pipeline remove emoji / `aria-label` | Agent/Code | `Overview.tsx` 103–114; `Pipeline.tsx` 122–142 | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A10) |
| A11 | `prefers-reduced-motion` media query | Done | `styles.css` bottom (targets `.btn-spinner`, `.toast`) | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A11) |
| A12 | Contrast audit tokens (`--text-faint` #667080 etc.) | Backlog / Manual Verify | `styles.css` tokens; needs axe color-check | AccessibilityCompletionAgent + Design | `accessibility_complete.md` §2.1 (A12 deferred); `spm_review.md` §3 (CP-3) |
| A13 | FunnelMetrics `aria-label` + `aria-describedby` KPI links | Agent/Code | `FunnelMetrics.tsx`; `Pipeline.tsx` 122–142; `state/metrics_funnel.json` | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A13) |
| A14 | KanbanBoard `role="grid"` / keyboard nav | Backlog | `components/KanbanBoard.tsx` — deferred | — | `accessibility_complete.md` §2 (A14 ❌) |
| A15 | LLMFilter checkbox `aria-label` + `aria-checked` | Agent/Code | `LLMFilter.tsx` 288–305 | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A15) |
| A16 | Dynamic `<title>` per page (`DocumentTitle`) | Agent/Code | `pages/*.tsx`; `components/DocumentTitle.tsx` | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A16) |
| A17 | Button `focus-visible` confirmation | Agent/Code | `Button.tsx` + `styles.css` | AccessibilityCompletionAgent | `accessibility_complete.md` §2 (A17) |
| A18 | Chart/DealDetail `aria-label` / `role="img"` | Backlog | `Chart.tsx`; `DealDetail.tsx` — deferred | — | `accessibility_complete.md` §2 (A18 ❌) |
| A19 | Full `axe-core` CI for each PR | Backlog | Needs `.github/workflows/` config; not edited | — | `accessibility_complete.md` §3.1 (recommended) |
| A20 | Manual NVDA / VoiceOver / JAWS verification (Key: Pipeline, Order, Billing) | Manual Verify | No log attached (`p0_fixes_summary.md` §25; `spm_review.md` §3 CP-3) | — | `p0_fixes_summary.md` §25; `spm_review.md` §3 CP-3 |
| A21 | Contrast verification via `axe` / `color-contrast-checker` | Manual Verify | Depends on A12 token fix | — | `accessibility_complete.md` §3.3 |
| A22 | `focus-trap-react` library for nested modals | Backlog | `showRaw`, `ReplyModal`; library not integrated | — | `p0_fixes_summary.md` §26; `accessibility_complete.md` §3.3 |

---

## Swimlane: Workflow (W) — 23 items
| ID | Item (spec line) | Status | File / Line Ref | Agent Assign | Evidence Link |
|---|---|---|---|---|---|
| W1 | Sandbox `DOCKER_ENABLED=True`; `Dockerfile.sandbox`; isolation | Agent/Code | `Dockerfile.sandbox` 1–29 (`--network none`); `modules/sandbox.py` ~26–29 | WorkflowCompletionAgent / P0ExecutionAgent | `p0_workflow_agent.md`; `worklist` W1; `spm_review.md` §3 CP-1 |
| W2 | Kill Switch `kill_switch.py` + `events.json` + audit consumer | Agent/Code (partial) | `kill_switch.py` 23–56; `events.json` append-only | FixAgent / WorkflowCompletionAgent | `p0_workflow_agent.md`; `worklist` W2 |
| W3 | Conversation bridge `listener_bridge.py` + `accept_inbox()` + `threading` | Agent/Code (partial) | `listener_bridge.py`; `conversation.py` ~336–360 | WorkflowCompletionAgent | `p0_workflow_agent.md`; `worklist` W3 |
| W4 | Scanner / `watchdog.pid` stabilize + `test_ok_scanner.py` | Backlog | `modules/scanner.py`; `watchdog.pid` unstable | — | `full_audit_master.md` §B; `worklist` W4 |
| W5 | Store formalize `is_scam()` + embedding dedup + hash (SHA-256) | Agent/Code | `modules/filter.py`; `store.py`; `state/embeddings_cache.json` | WorkflowCompletionAgent | `workflow_completion.md` §W13; `worklist` W5 |
| W6 | Ranker `Score` formula (§6.4) + `audit.py` integrate | Backlog | `modules/ranker.py`; `audit.py` — NOT EXECUTED | — | `full_audit_master.md` §B; `worklist` W6 |
| W7 | Agents index `.opencode/agents_index.json` L0–L4 + `autonomy`/`validators`/`max_size` | Agent/Code | `.opencode/agents_index.json`; `workflow_agents_index.md` | WorkflowCompletionAgent | `workflow_completion.md` §W7; `worklist` W7 |
| W8 | Billing service `verify_hmac()` + `Invoice` + `label` + webhook wire | Agent/Code | `modules/billing_service.py`; `modules/billing.py` | WorkflowCompletionAgent | `workflow_completion.md` §W5/W15; `worklist` W8 |
| W9 | Executor `spec_matrix.py` live link + `package_manifest.json` + `deliver_lock.json` | Agent/Code | `modules/spec_matrix.py`; `package_manifest.json`; `deliver_lock.json`; `state/` | WorkflowCompletionAgent | `workflow_completion.md` §W9; `worklist` W9 |
| W10 | Pipeline matrix verification `tests/test_exec_pipeline.py` | Backlog | `tests/test_exec_pipeline.py` — NOT EXECUTED | — | `worklist` W10; `p0_workflow_agent.md` §Remaining |
| W11 | Proposals/reviewer agent + `false_alarms` ban | Backlog | `proposals.py`; `judge.py` — NOT EXECUTED | — | `worklist` W11 |
| W12 | Listener unified `inbox` + `threading` + `tg_common.py` | Agent/Code (partial) | `listener.py` — bridge done, main loop deferred | WorkflowCompletionAgent | `p0_workflow_agent.md` §Remaining |
| W13 | Filter formalize `is_scam()` + `embedding` + hash | Agent/Code | `modules/filter.py` | WorkflowCompletionAgent | `workflow_completion.md` §W13; `worklist` W13 |
| W14 | Dashboard `/` v7 metrics funnel + `metrics_funnel.json` + `FunnelMetrics.tsx` | Agent/Code | `state/metrics_funnel.json`; `ui/src/pages/FunnelMetrics.tsx` | WorkflowCompletionAgent | `workflow_completion.md` §W14; `worklist` W14 |
| W15 | Billing `Invoice` model real + webhook verification | Agent/Code | `modules/billing.py`; `billing_service.py` wire | WorkflowCompletionAgent | `workflow_completion.md` §W5/W15; `worklist` W15 |
| W16 | State sync `watchdog.pid` + `activity.json` + `agents_activity.json` | Agent/Code (partial) | `state/agents_activity.json`; `memory/agent_activity_2026-08-31.md` | MemoryRecoveryAgent | `memory_completion.md` §M8; `worklist` W16 |
| W17 | Sandbox isolation test `tests/test_sandbox.py` | Backlog | `tests/test_sandbox.py` — NOT EXECUTED | — | `p0_workflow_agent.md` §Remaining; `worklist` W17 |
| W18 | Docs `docs/recommendations.md` / `plans/` update after fixes | Backlog | Deferred | — | `worklist` W18 |
| W19 | Agents index full 400+ merge `.opencode/skills_registry.json` | Backlog | Only 184 indexed; full catalog deferred | — | `workflow_completion.md` §W19; `worklist` W19 |
| W20 | Auto-reply `autoreply.py` / `chat.py` improvement | Backlog | Deferred | — | `worklist` W20 |
| W21 | Pipeline v3 `d/` clean temporary test folders | Backlog | Deferred | — | `worklist` W21 |
| W22 | Deliverables check `manifest.json` vs `v1/` | Backlog | Deferred | — | `worklist` W22 |
| W23 | State `metrics_funnel.json` link to `agents_activity.json` | Agent/Code | `state/metrics_funnel.json`; `memory/agent_activity_2026-08-31.md` | MemoryRecoveryAgent / WorkflowCompletionAgent | `memory_completion.md` §M7–M8; `worklist` W23 |

---

## Swimlane: Release / Build (R) — 8 items
| ID | Item (spec line) | Status | File / Line Ref | Agent Assign | Evidence Link |
|---|---|---|---|---|---|
| R1 | `check_releases.py` verify + CI add | Agent/Code | `check_releases.py` (rewritten 502 B → ~4.5 KB); `release.json` | ReleasePipelineAgent / FixAgent | `release_completion.md`; `p0_fixes_summary.md` §2 |
| R2 | CI pipeline `.github/workflows/release.yml` + `verify.yml` + `build.yml` untouched | Agent/Code (not triggered) | `.github/workflows/release.yml` 3227 B; `.github/workflows/verify.yml`; `build.yml` untouched | ReleasePipelineAgent | `release_completion.md` §Files; `spm_review.md` §3 CP-5 |
| R3 | Binary sign `opencode.exe`; `.goreleaser.yml` `signs:` + `sbom:`; remove from repo | Agent/Code (config only) | `.goreleaser.yml` updated; `opencode.exe` still in repo; `.gitignore` needed | ReleasePipelineAgent | `release_completion.md` §C1–C7; `release_audit_summary.md` §45; `spm_review.md` §3 CP-2 |
| R4 | `release.json` auto-generate + `checksums.txt` + `sbom.spdx.json` | Agent/Code | `release.json` (v0.0.55); `sbom.spdx.json`; `checksums.txt` | ReleasePipelineAgent | `release_completion.md`; `worklist` R4 |
| R5 | `install.sh` SHA256/HMAC verify before install | Agent/Code | `install.sh` updated (python `hashlib.sha256` block) | ReleasePipelineAgent | `release_completion.md`; `worklist` R5 |
| R6 | `opencode-scheme` / `.opencode.json` version update | Backlog | Deferred | — | `worklist` R6 |
| R7 | `install.sh` `os`/`arch` check + error message + fallback | Agent/Code (partial) | `install.sh` partial; full verification deferred | ReleasePipelineAgent | `worklist` R7 |
| R8 | `README.md` / `opencode-src/README.md` update install/security/audit | Backlog | Deferred | — | `worklist` R8 |

---

## Swimlane: Code / Security (C) — 10 items
| ID | Item (spec line) | Status | File / Line Ref | Agent Assign | Evidence Link |
|---|---|---|---|---|---|
| C1 | Auth middleware `internal/auth/` or `cmd/` (API-key/token) | Backlog | `internal/auth/` missing per `code_audit_summary.md`; `permission.Service` session-only | — | `code_audit_summary.md` §C1/C2; `spm_review.md` §4 (S-02) |
| C2 | Rate limit middleware `internal/limit/` | Backlog | Not implemented; `worklist` C2 open | — | `code_audit_summary.md` §C2; `release_completion.md` §C2 |
| C3 | `llm/provider/openai.go` `baseURL` validation + endpoint deny | Backlog | Not executed | — | `complete_worklist.md` §C3 |
| C4 | `internal/config/config.go` validation against `opencode-schema.json` | Backlog | Not executed | — | `complete_worklist.md` §C4 |
| C5 | `tests/` expand (`test_openai.go`, `test_request.json`, `test_stream.json`) | Backlog / Partial | `tests/` minimal per `code_audit_summary.md`; `py_compile` only | — | `code_audit_summary.md` §C5; `worklist` C5 |
| C6 | `audit.log` / `events.json` consumer + dashboard reader | Agent/Code (partial) | `events.json` append-only; `kill_switch.py` writes; no consumer | FixAgent / WorkflowCompletionAgent | `p0_workflow_agent.md`; `worklist` C6; `spm_review.md` §5 (S-03) |
| C7 | Secret scan `grep -rni 'token\|secret\|password\|api_key'` + `.env.example` | Backlog | Not shown executed | — | `worklist` C7; `spm_review.md` §5 (S-04) |
| C8 | `opencode-schema.json` add `auth`/`sandbox`/`audit` validation | Backlog | Deferred | — | `worklist` C8 |
| C9 | Workspace clean `sbtest_*/t.py`; restrict access | Backlog | Deferred | — | `worklist` C9 |
| C10 | `go.mod` update + dependency check (`go list -m -json` + `gosec`) | Backlog | Deferred | — | `worklist` C10 |

---

## Swimlane: Memory / Strategy (M) + Quality Gates (QG) — 15 items (M1–M8 + QG1–Q7)
| ID | Item (spec line) | Status | File / Line Ref | Agent Assign | Evidence Link |
|---|---|---|---|---|---|
| M1 | Gap recovery `memory/2026-08-21.md` … `2026-08-24.md` reconstructed | Agent/Code | 4 files reconstructed; quality rated medium; `launcher_new.log` 246 KB cited | MemoryRecoveryAgent | `memory_completion.md` §M1; `spm_review.md` §3 CP-4 |
| M2 | Decisions `memory/decisions/decision-2026-08-31.md` | Done | Template filled (Context/Options/Decision/Consequences/Related) | MemoryRecoveryAgent | `memory_completion.md` §M2 |
| M3 | Risks `memory/risks/risk-2026-08-31.md` | Done | Template filled (Likelihood/Impact/Mitigation/Status) | MemoryRecoveryAgent | `memory_completion.md` §M3 |
| M4 | Experiments `memory/experiments/experiment-2026-08-31.md` | Done | Template filled (Hypothesis/Method/Results/Conclusion) | MemoryRecoveryAgent | `memory_completion.md` §M4 |
| M5 | Feedback `memory/feedback/feedback-2026-08-31.md` | Done | Template filled (Source/Feedback/Action/Owner) | MemoryRecoveryAgent | `memory_completion.md` §M5 |
| M6 | Daily template `memory/YYYY-MM-DD.md` enforced | Done | `memory/2026-08-31.md` + reconstructed 21–24 | MemoryRecoveryAgent | `memory_completion.md` §M6 |
| M7 | `MEMORY.md` updated with audit links + artifact index | Done | Section added (Memory audit conclusions, artifact index, state sync) | MemoryRecoveryAgent | `memory_completion.md` §M7 |
| M8 | State sync `state/agents_activity.json` + `memory/agent_activity_2026-08-31.md` | Done | Backlinks verified (`MEMORY.md` → `full_audit_master.md`; `agent_activity_2026-08-31.md` → `state/`) | MemoryRecoveryAgent | `memory_completion.md` §M8 |
| QG1 | `python -m pytest tests/ -v` — zero errors | Manual Verify | `tests/` minimal; `py_compile` only for `check_releases.py`; needs full run | TrackingAgent / QA | `complete_worklist.md` §112; `spm_review.md` §6.4 |
| QG2 | `python modules/executor.py` — sanity pass | Manual Verify | `executor.py` edited (`deliver_result` killswitch audit) | TrackingAgent / WorkflowAgent | `complete_worklist.md` §113; `spm_review.md` §6.4 |
| QG3 | `python check_releases.py` — OK (SHA256 + match `release.json`) | Manual Verify | `check_releases.py` passes local (11/11); `release.json` updated | TrackingAgent / ReleaseAgent | `complete_worklist.md` §114; `p0_fixes_summary.md` §3 |
| QG4 | Accessibility: `axe-core` CI + manual 8 critical + Arrow cycle + `focus-visible` + `skip-link` | Manual Verify | Code fixed; manual/NVDA/axe pending; A12/A14/A18 deferred | TrackingAgent / AccessibilityAgent | `complete_worklist.md` §115; `spm_review.md` §6.4 |
| QG5 | Security: sandbox isolation + kill_switch + audit log + auth middleware | Manual Verify | Sandbox build/test open; auth/rate deferred P1; `events.json` append-only | TrackingAgent / SecurityAgent | `complete_worklist.md` §116; `spm_review.md` §6.4 |
| QG6 | Workflow: `conversation` works + `spec_matrix` live + delivery blocked without confirmation | Manual Verify | Conversation integrated not main loop; matrix linked untested; kill switch blocks | TrackingAgent / WorkflowAgent | `complete_worklist.md` §117; `spm_review.md` §6.4 |
| QG7 | Memory: no gap >2 days; `decisions/` + `risks/` + `experiments/` + `feedback/`; links to `state/` / `deliverables/` | Manual Verify | M1 reconstructed quality medium; M2–M8 done; 31.08 complete | TrackingAgent / MemoryAgent | `complete_worklist.md` §118; `spm_review.md` §6.4 |

---

## Status Counters (78 total)
- **Backlog:** A12, A14, A18–A22, W4, W6, W10–W12, W17–W23, R6–R8, C1–C5, C7–C10 = ~29
- **Agent/Code:** A1–A11, A13, A15–A17, W1–W3, W5, W7–W9, W13–W16, R1–R5, C6 = ~35
- **Manual Verify:** A20–A21, W1 (build), W2 (consumer), W9 (test), R2 (trigger), R3 (sign), C6 (consumer), QG1–QG7 = ~14
- **Done:** A11, M2–M8 = 7 (plus partial Done within Agent/Code after verification)
- **Cross-check:** All 78 checkbox IDs from `complete_worklist.md` accounted for; quality gates QG1–QG7 include the 7 checks at §112–120.

## Evidence Index (exact file/line references per claim above)
- `memory/complete_worklist.md`: 78 checkboxes (§P0 §A–D, §P1 §A–C, §P2 §A–D, §112–120)
- `memory/p0_fixes_summary.md`: A1–A10 fixes (§1); A4 placeholder (§25); no NVDA (§25); focus-trap (§26)
- `memory/accessibility_complete.md`: A3 (§2.2); A4 (§2.1); A5–A10 (§2); A12 deferred (§2.1); A14/A18 deferred (§2); axe/NVDA (§3.1–3.3)
- `memory/workflow_completion.md`: W5 (§W5/W15); W7 (§W7); W9 (§W9); W13 (§W13); W14 (§W14); W19 (§W19); remaining (§Remaining)
- `memory/memory_completion.md`: M1 (§M1); M2–M8 (§M2–M8); link verification (§Link verification); format (§Format verification)
- `memory/release_completion.md`: R2 (§Files); R3 (§C1–C7); R4 (§release.json); R5 (`install.sh`); commands (§Commands)
- `memory/spm_review.md`: §2 (14 stages); §3 (CP-1 to CP-5); §4 (Risk register T-01 to S-05, A-R01–A-R05); §6.1–6.4 (Board / Gates); §7 (Evidence Index)
- `memory/sd_execution.md`, `backend_execution.md`, `db_execution.md`, `mcp_execution.md`, `search_optimizer.md`: execution evidence for dataset / backend / DB / MCP / optimizer agents

*No luxury additions. All items reference exact spec lines, edited files, or open gaps per audit evidence. Next manual verification required for all Agent/Code items before closing to Done: build W1, sign R3, trigger R2, NVDA A20, axe QG4, tests QG1, matrix QG6, gap QG7.*
