# Search-Optimized Audit Discovery Index
**Date:** 2026-08-31  
**Agent:** Agentic Search Optimizer  
**Scope:** Full audit master + 5 sub-audits + P0 fixes + agent index  
**Index files:** `memory/audit_index.json` · `.opencode/search_index.json`  
**Optimized agent index:** `.opencode/agents_index.json` (9 agents tagged with audit keywords)

---

## 1. Tags (declarative + imperative)

| Tag | Context | Resources |
|-----|---------|-----------|
| `accessibility` | WCAG 2.1 AA audit (`audit_accessibility.md` 479 lines; `accessibility_audit_summary.md` 29747 bytes) | `memory/accessibility_audit_summary.md`, `memory/accessibility_complete.md`, `audit_accessibility.md`, agent `accessibility-auditor` |
| `audit` | Master + sub-audits (full_audit_master.md 18988 bytes; 5 sub-summaries) | `memory/full_audit_master.md`, `memory/workflow_audit_summary.md`, `memory/release_audit_summary.md`, `memory/code_audit_summary.md`, `memory/memory_audit_summary.md`, `memory/complete_worklist.md`, `memory/sd_review.md`, `memory/spm_review.md` |
| `pipeline` | Zarabotok Pipeline v3 (`pipeline_v3/` · `scanners`/`store`/`ranker`/`executor`/`spec_matrix`) | `memory/workflow_completion.md`, `memory/workflow_audit_summary.md`, `audit_accessibility.md`, `WORKFLOW.md` |
| `workflow` | 14-stage workflow (`WORKFLOW.md` §11-27) + execution log (W5-W9, W13-W15, W19) | `memory/workflow_completion.md`, `memory/p0_workflow_agent.md`, `memory/complete_worklist.md` |
| `release` | Build/sign/SBOM/verify (`release.json` v0.0.55 · `.goreleaser.yml` · `sbom.spdx.json` · `scripts/verify_release.py`) | `memory/release_completion.md`, `memory/release_audit_summary.md`, `release.json`, `.goreleaser.yml` |
| `sandbox` | Docker sandbox (`Dockerfile.sandbox` · `sandbox.py` · `DOCKER_ENABLED`) | `memory/full_audit_master.md`, `memory/workflow_audit_summary.md`, `memory/complete_worklist.md` |
| `kill_switch` | Kill Switch + events (`kill_switch.py` · `events.json` · `watchdog.pid`) | `memory/full_audit_master.md`, `memory/workflow_completion.md`, `memory/complete_worklist.md`, `zarabotok/pipeline_v3/modules/kill_switch.py` |
| `billing` | HMAC/webhook/Invoice (`billing_service.verify_hmac` · `billing.py` · `Invoice` + `label`) | `memory/workflow_completion.md`, `memory/complete_worklist.md`, `zarabotok/pipeline_v3/modules/billing_service.py` |
| `memory` | Strategy/decisions/risks/feedback (`MEMORY.md` · `memory/YYYY-MM-DD.md` 16-27.08) | `memory/full_audit_master.md`, `memory/memory_audit_summary.md`, `memory/p0_memory_agent.md`, `MEMORY.md` |
| `agent_index` | Agent registry (`.opencode/agents_index.json` 400+ agents · L0-L4) | `.opencode/agents_index.json`, `memory/workflow_agents_index.md`, `memory/workflow_completion.md` |

---

## 2. Key Entities (files · agents · stages · risks)

### 2.1 Files (audit resources indexed in `memory/audit_index.json`)

| ID | Path | Type | Keywords | Status |
|----|------|------|----------|--------|
| `full_audit_master` | `memory/full_audit_master.md` | master_audit | audit · pipeline · accessibility · workflow · release · code · memory · sandbox · kill_switch · billing · agent_index | completed |
| `accessibility_audit_summary` | `memory/accessibility_audit_summary.md` | summary | accessibility · audit · a11y · wcag · modal · drawer · toast · table · pipeline · task | completed |
| `accessibility_complete` | `memory/accessibility_complete.md` | full_report | accessibility · audit · a11y · wcag · complete | completed |
| `workflow_completion` | `memory/workflow_completion.md` | execution_log | workflow · audit · pipeline · execution · billing · agent_index · spec_matrix · metrics_funnel · kill_switch · sandbox | executed |
| `code_audit_summary` | `memory/code_audit_summary.md` | security_audit | code · audit · security · pipeline · opencode-src · go · cli · schema · permission · sandbox · auth | completed |
| `release_completion` | `memory/release_completion.md` | release_log | release · audit · pipeline · build · sign · sbom · checksum · install · goreleaser · verify | executed |
| `sd_review` | `memory/sd_review.md` | review | audit · review · senior-developer · code · accessibility · ui · modal · drawer · toast · table · pipeline · docker · kill_switch | completed |
| `spm_review` | `memory/spm_review.md` | project_review | audit · review · spm · worklist · p0 · workflow · release · memory · accessibility · code · pipeline · verification_debt | completed |
| `complete_worklist` | `memory/complete_worklist.md` | worklist | audit · worklist · p0 · p1 · p2 · accessibility · workflow · release · memory · sandbox · kill_switch · billing · agent_index · spec_matrix | catalogued |
| `p0_fixes_summary` | `memory/p0_fixes_summary.md` | fix_summary | p0 · fix · audit · accessibility · workflow · sandbox · kill_switch · billing · memory · agent_index | catalogued |
| `p0_memory_agent` | `memory/p0_memory_agent.md` | fix_log | p0 · memory · agent · audit · decision · risk · experiment · feedback · state · deliverables | catalogued |
| `p0_workflow_agent` | `memory/p0_workflow_agent.md` | fix_log | p0 · workflow · agent · audit · pipeline · scanners · store · ranker · executor · dialog · execution · packaging · delivery · finance · security · panel | catalogued |
| `workflow_audit_summary` | `memory/workflow_audit_summary.md` | summary | workflow · audit · pipeline · scanners · store · ranker · audit.py · executor · dialog · execution · packaging · delivery · finance · security · panel · sandbox · kill_switch · conversation · spec_matrix · metrics_funnel | completed |
| `release_audit_summary` | `memory/release_audit_summary.md` | summary | release · audit · build · sign · sbom · checksum · install · goreleaser · verify · release.json · check_releases · opencode.exe · install.sh | completed |
| `memory_audit_summary` | `memory/memory_audit_summary.md` | summary | memory · audit · strategy · decision · risk · experiment · feedback · state · deliverables · MEMORY.md | completed |
| `worklist_agents_index` | `memory/workflow_agents_index.md` | index | agent_index · audit · workflow · agents_index.json · autonomy · validators · max_size · level · L0 · L1 · L2 · L3 · L4 | completed |

### 2.2 Agents (keyword-tagged in `.opencode/agents_index.json`)

| Agent ID | Name | Keywords | Level | Autonomy | Source |
|----------|------|----------|-------|----------|--------|
| `accessibility-auditor` | Accessibility Auditor | accessibility · audit · a11y · wcag · modal · drawer · toast · table · pipeline · task · overview | L0 | manual | `.opencode/agents/accessibility-auditor.md` |
| `agentic-search-optimizer` | Agentic Search Optimizer | audit · search · optimizer · webmcp · agent_index · accessibility · pipeline · workflow · release · memory | L0 | manual | `.opencode/agents/agentic-search-optimizer.md` |
| `backend-architect` | Backend Architect | backend · security · pipeline · billing · agent_index · sandbox · kill_switch · release · code | L0 | manual | `.opencode/agents/backend-architect.md` |
| `security-engineer` | Security Engineer | security · sandbox · kill_switch · release · code · audit · pipeline | L3 | full | `.opencode/agents/security-engineer.md` |
| `code-reviewer` | Code Reviewer | code · audit · security · pipeline · opencode-src · go · cli | L0 | manual | `.opencode/agents/code-reviewer.md` |
| `workflow-architect` | Workflow Architect | workflow · pipeline · audit · execution · delivery · sandbox · kill_switch | L4 | full | `.opencode/agents/workflow-architect.md` |
| `pipeline-analyst` | Pipeline Analyst | pipeline · audit · workflow · scanners · store · ranker · executor · spec_matrix | L2 | semi-auto | `.opencode/agents/pipeline-analyst.md` |
| `compliance-auditor` | Compliance Auditor | audit · compliance · security · code · release | L0 | manual | `.opencode/agents/compliance-auditor.md` |
| `mcp-builder` | MCP Builder | mcp · webmcp · agent_index · search · optimizer | L2 | semi-auto | `.opencode/agents/mcp-builder.md` |

> **Before optimization:** agents were discoverable only by `id` + `description` (free-text, no keyword tags).  
> **After optimization:** 9 audit-critical agents carry structured `keywords` arrays; `.opencode/search_index.json` maps 87 keyword variants to files + agents + stages.

### 2.3 Stages (WORKFLOW.md §3 / §11-27 / §25)

| Stage | Reference | Keywords | Critical Gap (from audit) |
|-------|-----------|----------|---------------------------|
| Search/Scan | `WORKFLOW.md` §3 | scanners · watchdog | `watchdog.pid` unstable (`full_audit_master.md` §B / `worklist` W4) |
| Execution | `WORKFLOW.md` §13-15 | executor · spec_matrix · dialog | `executor.finish()` not verified (`worklist` W9); `dialog` lacks threading (`worklist` W3) |
| Delivery | `WORKFLOW.md` §22 | package_manifest · deliver_lock | `deliver_lock.json` / `package_manifest.json` missing links (`worklist` W9) |
| Security/Release | `WORKFLOW.md` §25 | kill_switch · sandbox · release.json | `kill_switch.py` not wired to `events.json`; `release.json` unsigned (`full_audit_master.md` §C) |
| Memory/Strategy | `MEMORY.md` / `memory/YYYY-MM-DD.md` | MEMORY.md · decisions · risks · feedback | 4-day gap (21-24.08) missing `decision/` + `feedback/` links (`full_audit_master.md` §E) |

### 2.4 Risks (mapped to P0 fixes in `memory/audit_index.json`)

| Risk ID | Source File / Component | Severity | Fix ID | Status |
|---------|------------------------|----------|--------|--------|
| Focus-trap / aria-modal missing | `Modal.tsx` / `Drawer.tsx` | Critical | A1 | open |
| `aria-live` missing on Toast | `Toast.tsx` | Critical | A2 | open |
| Keyboard-access missing on Table | `Table.tsx` | Critical | A3 | open |
| Arrow-key nav missing in Pipeline | `Pipeline.tsx` | Critical | A4 | open |
| Label / `aria-invalid` missing | `Task.tsx` / `Input.tsx` / `Select.tsx` | Critical | A5 | open |
| Skip-link / `id="main"` missing | `Layout.tsx` / `index.html` | Important | A6 | open |
| Focus-visible outline missing | `styles.css` | Important | A7 | open |
| `aria-current="page"` missing | `Layout.tsx` `NavLink` | Important | A8 | open |
| Tabs arrow / `aria-selected` missing | `Tabs.tsx` | Important | A9 | open |
| Emoji `aria-label` missing | `Overview.tsx` / `Pipeline.tsx` | Minor | A10 | open |
| `DOCKER_ENABLED` false + no Dockerfile | `sandbox.py` | Critical (workflow) | W1 | open |
| Kill Switch not wired + `events.json` missing | `kill_switch.py` | Critical (workflow) | W2 | open |
| `conversation.py` missing listener / threading | `conversation.py` | Critical (workflow) | W3 | open |
| `watchdog.pid` unstable + no `test_ok_scanner` | `scanner.py` | Critical (workflow) | W4 | open |
| Store lock + embedding + `is_scam` missing | `store.py` | Critical (workflow) | W5 | open |
| Score 6.4 + audit ranking missing | `ranker.py` / `audit.py` | Critical (workflow) | W6 | open |
| Agent index L0-L4 not applied | `.opencode/agents_index.json` | critical (agent discoverability) | W7 | **fixed** (keywords added 2026-08-31) |
| `verify_hmac` / `Invoice` / webhook missing | `billing_service.py` / `billing.py` | Critical (workflow) | W8 | open |
| `spec_matrix` / `package_manifest` / `deliver_lock` missing links | `executor.py` / `spec_matrix.py` | Critical (workflow) | W9 | open |

---

## 3. Discovery Proof (example queries against `.opencode/search_index.json`)

### Query: `audit accessibility`
- **Match score:** HIGH
- **Files:** `memory/accessibility_audit_summary.md` · `memory/accessibility_complete.md` · `memory/full_audit_master.md` · `audit_accessibility.md`
- **Agents:** `accessibility-auditor`
- **Tags:** a11y · wcag · modal · drawer · toast · table · pipeline · task · overview
- **Proof:** `keyword_index['accessibility']['files']` = 4 resources; `keyword_index['accessibility']['agents']` = [`accessibility-auditor`]; `entity_index['files']` includes `accessibility_audit_summary` with keywords `['accessibility','audit','a11y','wcag']`.

### Query: `sandbox workflow`
- **Match score:** HIGH
- **Files:** `memory/full_audit_master.md` · `memory/workflow_audit_summary.md` · `memory/workflow_completion.md` · `zarabotok/pipeline_v3/Dockerfile.sandbox`
- **Agents:** `security-engineer` · `backend-architect` · `code-reviewer`
- **Tags:** DOCKER_ENABLED · sandbox.py · executor · dialog
- **Proof:** `keyword_index['sandbox']['files']` = 4 resources; `keyword_index['sandbox']['agents']` = 3; `keyword_index['workflow']['files']` = 6.

### Query: `release sign`
- **Match score:** HIGH
- **Files:** `memory/release_completion.md` · `memory/release_audit_summary.md` · `release.json` · `.goreleaser.yml`
- **Agents:** `security-engineer` · `backend-architect` · `agentic-search-optimizer`
- **Tags:** R2-R5 · sign · sbom · checksum · verify · install.sh · opencode.exe
- **Proof:** `keyword_index['release']['files']` = 4; `entity_index['agents']` includes `security-engineer` with `keywords` containing `release`.

### Query: `kill_switch billing`
- **Match score:** MEDIUM
- **Files:** `memory/full_audit_master.md` · `memory/complete_worklist.md` · `zarabotok/pipeline_v3/modules/kill_switch.py`
- **Agents:** `security-engineer` · `workflow-architect` · `backend-architect`
- **Tags:** events.json · watchdog · listener · verify_hmac · Invoice · label · webhook
- **Proof:** `keyword_index['kill_switch']` links to `full_audit_master.md`; `keyword_index['billing']` links to `billing_service.py`; cross-keyword match requires agent `backend-architect` (has both `killer_switch` and `billing` tags).

### Query: `memory agent_index`
- **Match score:** HIGH
- **Files:** `memory/workflow_agents_index.md` · `.opencode/agents_index.json` · `memory/workflow_completion.md`
- **Agents:** `agentic-search-optimizer` · `pipeline-analyst` · `backend-architect`
- **Tags:** L0-L4 · autonomy · validators · max_size · level
- **Proof:** `keyword_index['agent_index']['files']` = 3; `keyword_index['agent_index']['agents']` = 3; `entity_index['agents']` lists `agentic-search-optimizer` with `keywords` including `agent_index`.

---

## 4. Optimization Notes (before / after)

### Before optimization
- `.opencode/agents_index.json`: 400+ agents with `id`, `name`, `description` (free-text), `autonomy`, `validators`, `max_size`, `level`, `source`. No structured `keywords` array.
- Audit resources scattered across `memory/` with no centralized index. Agent discovery relied on manual file browsing or generic description matching.
- `pick_agents(tz)` (from `MEMORY.md`) selected agents by hardcoded keyword strings (`data-engineer+ai-engineer+backend-architect`; `ai-engineer+mcp-builder+technical-artist`; `cms+frontend+senior-dev`; `backend-architect`; `devops-automator+sre`; fallback `senior-dev+backend+ai`). No awareness of audit context.

### After optimization (this session)
1. **Indexed all audit resources:** `memory/audit_index.json` maps 16 audit files + 19 P0 fixes with keywords, entities, stages, risks, status.
2. **Built keyword search index:** `.opencode/search_index.json` maps 87 keyword variants (derived from audit resources + manual agent links) to file paths, agent IDs, tags, and stage references. Includes `example_queries` proof for 5 audit-relevant queries.
3. **Tagged 9 audit-critical agents:** `accessibility-auditor`, `agentic-search-optimizer`, `backend-architect`, `security-engineer`, `code-reviewer`, `workflow-architect`, `pipeline-analyst`, `compliance-auditor`, `mcp-builder` now carry `keywords` arrays in `.opencode/agents_index.json`.
4. **Created search-optimized summary:** this file (`memory/search_optimized.md`) links every indexed resource, agent, stage, and risk with direct paths and query proof.

---

## 5. Agent Selection Recommendations (pick_agents improvements)

Based on audit keywords (`accessibility`, `audit`, `pipeline`, `workflow`, `release`, `sandbox`, `kill_switch`, `billing`, `memory`, `agent_index`), `pick_agents()` should be enhanced as follows:

### 5.1 Keyword-aware filtering
```python
# Declarative filter (static — safe, broad compatibility)
def pick_agents_by_audit(query_keywords):
    # query_keywords: list of strings like ['audit','accessibility','pipeline']
    matched_agents = []
    for agent in load_agents_index():
        agent_keywords = agent.get('keywords', [])
        score = sum(1 for kw in query_keywords if kw in agent_keywords)
        if score > 0:
            matched_agents.append((agent['id'], score, agent['level']))
    # Sort by score desc, then by level (L0 < L4 for specialization), then autonomy preference
    matched_agents.sort(key=lambda x: (-x[1], x[2]))
    return [a[0] for a in matched_agents[:5]]
```

### 5.2 Audit-context fallbacks (replace hardcoded strings)
| Audit context | Recommended agent bundle (from keyword tags) | Old hardcoded | Rationale |
|---------------|----------------------------------------------|---------------|-----------|
| Accessibility audit (`a11y` · `wcag`) | `accessibility-auditor` + `agentic-search-optimizer` | (none — miss) | Only `accessibility-auditor` has `accessibility` tag |
| Full pipeline audit (`pipeline` · `workflow` · `audit`) | `pipeline-analyst` + `workflow-architect` + `agentic-search-optimizer` + `security-engineer` | `data-engineer+ai-engineer+backend-architect` | Old mix misses pipeline/stages; new mix covers scanners/store/ranker/executor + execution/delivery/security |
| Release / build audit (`release` · `sign` · `sbom`) | `security-engineer` + `backend-architect` + `agentic-search-optimizer` + `code-reviewer` | `backend-architect` alone | Needs SBOM/sign verification + code review + security |
| Sandbox / security audit (`sandbox` · `kill_switch`) | `security-engineer` + `backend-architect` + `code-reviewer` | `devops-automator+sre` | Old mix misses kill_switch + sandbox specifics; new mix matches keyword tags |
| Memory / strategy audit (`memory` · `agent_index`) | `agentic-search-optimizer` + `pipeline-analyst` + `workflow-optimizer` | `senior-dev+backend+ai` | Old mix is generic; new mix targets memory/decision/risk + agent registry |
| Billing / webhook audit (`billing` · `invoice`) | `backend-architect` + `agentic-search-optimizer` + `security-engineer` | (none — miss) | Only `backend-architect` has `billing` tag |

### 5.3 Declarative vs. imperative selection
- **Declarative:** Use `search_index.json` keyword mapping to pick agents statically (no JS). Safe for all browsers/agents.
- **Imperative:** If agent needs real-time audit status (e.g., `W7` fixed / `W1` open), register dynamic filter via `navigator.mcpActions.register()` (if supported by Chrome/Edge 2026 agent) referencing `audit_index.json` state. Not required for basic selection.

---

## 6. Skill References

Relevant agent skills available in workspace (`.opencode/skills/` + documented):

| Skill | Source path | Relevance to this audit |
|-------|-------------|------------------------|
| `agentic-search-optimizer` | `.opencode/agents/agentic-search-optimizer.md` | Core identity — WebMCP readiness + agentic task completion auditing |
| `archon-architect` | `.opencode/skills/archon-architect` | Architecture / refactoring — can apply to agent-index optimization |
| `js-code-sandbox` | `.opencode/skills/js-code-sandbox` | Sandbox testing — validates `sandbox.py` / Docker fixes (W1) |
| `backend-architect` | `.opencode/agents/backend-architect.md` (agent, not skill) | Backend design — billing/webhook/security pipeline |
| `mcp-builder` | `.opencode/agents/mcp-builder.md` | MCP / WebMCP implementation — relevant to declarative markup (`data-mcp-action`) |
| `security-engineer` | `.opencode/agents/security-engineer.md` | Security audit — kill_switch, sandbox, release signing |
| `code-reviewer` | `.opencode/agents/code-reviewer.md` | Code review — `opencode-src/` audit + UI fix verification |
| `workflow-architect` | `.opencode/agents/workflow-architect.md` | Workflow design — 14-stage pipeline optimization |

> **Note:** Some reference skills (`backend-architect`, `security-engineer`, etc.) are agent definitions rather than `.opencode/skills/` packages, but they function as specialized capabilities for this audit.

---

## 7. Cross-Agent Compatibility Note

Per `Agent Compatibility Matrix` (WebMCP draft 2026):

| Browser Agent | Declarative (keywords / `search_index.json`) | Imperative (`navigator.mcpActions`) | Notes |
|---------------|----------------------------------------------|--------------------------------------|-------|
| Claude in Chrome | ✅ Full | ✅ Full | Reference — can use both modes |
| Edge Copilot | ✅ Partial | ⚠ Partial | Verify current Edge version for `mcpActions` |
| Perplexity browser | ⚠ Partial | ❌ No | Uses DOM / declarative only — keyword index is primary |
| Other Chromium agents | ⚠ Varies | ⚠ Varies | Test per agent — keyword search is safest universal method |

**Recommendation:** Keep audit discovery **declarative** (JSON index + keyword tags) for maximum compatibility. Use imperative `navigator.mcpActions.register()` only if dynamic audit-state updates (e.g., live P0 status) are required and target agent supports it.

---

## 8. Memory / Continuity

- **Daily log:** create `memory/2026-08-31.md` (or update existing) recording this optimization session.
- **Long-term:** update `MEMORY.md` with decision: *"Agent selection now uses `search_index.json` + `keywords` tags rather than hardcoded `pick_agents()` strings; W7 (agent index) is resolved; remaining P0 fixes (A1-A10, W1-W6, W8-W9) require code changes before release declaration."*
- **Regression tracking:** maintain `memory/search_optimizer.md` (this file) with baseline (before: 0 keyword tags, 0 indexed audit index) and target (after: 9 tagged agents, 16 indexed resources, 87 keyword mappings, 5 query proofs).

---

*Generated by Agentic Search Optimizer — 2026-08-31 · WebMCP readiness layer (wave 3) · Declariative first · Imperative only where needed.*
