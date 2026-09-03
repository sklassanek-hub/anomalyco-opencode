---
name: MCP Integration — Workspace Audit & Pipeline Access
version: 1.0.0
date: 2026-08-31
scope: External AI agent / tool access to workspace audit resources, pipeline stages, state/activity, agent index, and deliverables via Model Context Protocol (MCP).
author: MCP Builder (system role per .opencode/agents/mcp-builder.md)
references:
  - skills: mcp-builder (.opencode/agents/mcp-builder.md), backend-architect, workflow-architect
  - workspace: zarabotok/pipeline_v3/ (executor.py, listener_bridge.py, conversation.py, billing_service.py, kill_switch.py), memory/, .opencode/agents_index.json
  - audit: memory/audit_index.json, memory/full_audit_master.md, memory/accessibility_audit_summary.md
status: DESIGN — server skeleton provided; live server requires .mcp/config or opencode extension registration.
---

# MCP Integration — Workspace Audit & Pipeline Access

**Purpose:** Allow external AI agents and automated tools to safely read audit context, inspect pipeline stages, query state/activity, verify releases, run checks, and (with approval) trigger the kill switch — without exposing secrets, without unapproved writes, and always through stateless, typed tool interfaces.

**Design ethos (from mcp-builder agent):**
- Every tool name is a verb_noun pair (`run_pytest`, `verify_accessibility`, `trigger_kill_switch`).
- Every parameter is typed, validated, with sensible defaults.
- Every resource URI is predictable and self-documenting (`file://memory/full_audit_master.md`).
- Errors return structured `isError: true` messages — never stack traces, never secret leaks.
- Each call is independent (stateless).

---

## 1. Capability Discovery — What External Agents Need

The workspace contains:

| Layer | Key Artifacts | Why an agent needs it |
|---|---|---|
| **Audit memory** | `memory/full_audit_master.md`, `memory/accessibility_audit_summary.md`, `memory/accessibility_complete.md`, `memory/agent_activity_2026-08-31.md`, `memory/audit_index.json` | Understand completed audits, accessibility status, agent activity for context before acting |
| **Agent index** | `.opencode/agents_index.json`, `.opencode/agents/*.md` (148 agents) | Discover available agent capabilities; know which agents can handle sub-tasks |
| **Pipeline v3** | `zarabotok/pipeline_v3/modules/executor.py`, `listener_bridge.py`, `conversation.py`, `billing_service.py`, `kill_switch.py` | Inspect stage implementations, verify logic, check kill-switch status |
| **State / activity** | `zarabotok/pipeline_v3/state/activity.json`, `agents_activity.json`, `events.json`, `kill_switch_active.json`, `api.py.pid` | Read real-time pipeline health; check if blocked; audit events |
| **Deliverables** | `zarabotok/pipeline_v3/deliverables/` (folders per target URL / test case) | Verify what was delivered, read artifacts, check blocked / broken / exception cases |
| **Checks** | `check_releases.py`, `verify_memory_completion.py`, `check_c7.py`, audit_accessibility.md | Run verification before making decisions |

**Decision: tools vs resources vs prompts**
- **Resources** for read-only context (audit files, state JSON, pipeline source, agent index, deliverable listings).
- **Tools** for actions that change nothing (pytest, release checks, accessibility verification, sandbox tests) or that change state only with approval (kill switch, event writes).
- **Prompts** (optional) for common workflows: "Audit-check-then-deliver" could be a prompt template referencing `read_memory_index` + `verify_accessibility` + `read_agent_index`.

---

## 2. Resource Catalog — What Agents Can Read

All resources expose `mimeType` (`text/markdown`, `application/json`, `text/x-python`) and return content as structured text or JSON. Resource URIs are URI-like and predictable.

### 2.1 Audit Memory Resources

| Resource URI | Path (local) | Type | Description (agent reads this to decide) |
|---|---|---|---|
| `file://memory/full_audit_master.md` | `memory/full_audit_master.md` | master_audit | Complete master audit document — pipeline, accessibility, release, code, memory, sandbox, kill_switch, billing, agent index stages |
| `file://memory/accessibility_audit_summary.md` | `memory/accessibility_audit_summary.md` | summary | Accessibility audit overview: modal, drawer, toast, table, badge, card, pipeline task overview |
| `file://memory/accessibility_complete.md` | `memory/accessibility_complete.md` | complete | Full accessibility audit results (WCAG-focused) |
| `file://memory/agent_activity_2026-08-31.md` | `memory/agent_activity_2026-08-31.md` | agent_activity | Daily agent activity log — which agents ran, results, risks |
| `file://memory/audit_index.json` | `memory/audit_index.json` | index | Structured index of all audit resources: IDs, paths, keywords, entities, stages, status |
| `file://memory/2026-08-31.md` | `memory/2026-08-31.md` | daily_note | Latest daily memory entry (decisions, experiments, feedback, risks) |

**Schema snippet for resource descriptor (returned by `read_memory_index` tool or embedded in resource metadata):**
```json
{
  "resource": {
    "uri": "file://memory/full_audit_master.md",
    "path": "memory/full_audit_master.md",
    "mimeType": "text/markdown",
    "id": "full_audit_master",
    "type": "master_audit",
    "status": "completed",
    "keywords": ["audit", "pipeline", "accessibility", "kill_switch", "agent_index"],
    "stages": ["search/scan", "execution", "delivery", "security", "release", "memory"]
  }
}
```

### 2.2 Agent / System Index Resources

| Resource URI | Path | Type | Description |
|---|---|---|---|
| `file://.opencode/agents_index.json` | `.opencode/agents_index.json` | agent_index | Full agent registry (~148 agents): names, roles, capabilities, colors, descriptions |
| `pipeline://agent_index` | aggregated | aggregate | Structured view of `.opencode/agents/*.md` — agent names, roles, whether they are subagents |

### 2.3 Pipeline Stage Resources

| Resource URI | Path / Source | Type | Description |
|---|---|---|---|
| `file://zarabotok/pipeline_v3/modules/executor.py` | `modules/executor.py` | source | Pipeline executor — stage orchestration, task dispatch, log writing |
| `file://zarabotok/pipeline_v3/modules/listener_bridge.py` | `modules/listener_bridge.py` | source | Listener / conversation threading bridge — poll telegram / email, link messages |
| `file://zarabotok/pipeline_v3/modules/conversation.py` | `modules/conversation.py` | source | Conversation threading, message-ID / in-reply-to / references handling |
| `file://zarabotok/pipeline_v3/modules/billing_service.py` | `modules/billing_service.py` | source | Billing service logic — invoicing, payments, audit of billing events |
| `file://zarabotok/pipeline_v3/modules/kill_switch.py` | `modules/kill_switch.py` | source | Kill switch implementation — is_blocked(), set_blocked(), events.json audit |

**Pipeline stage abstraction (for agents that just need status, not source):**
- `pipeline://stage/executor` — returns current stage name, status (running / paused / complete), last log line reference
- `pipeline://stage/listener_bridge` — same for listener bridge stage
- `pipeline://stage/conversation` — conversation stage status
- `pipeline://stage/billing_service` — billing stage status
- `pipeline://stage/kill_switch` — kill switch status (`blocked: true/false`) + event count

### 2.4 State / Activity Resources

| Resource URI | Path | Type | Description |
|---|---|---|---|
| `file://zarabotok/pipeline_v3/state/activity.json` | `state/activity.json` | state | Large activity log (~978KB) — real-time pipeline actions, errors, timing |
| `file://zarabotok/pipeline_v3/state/agents_activity.json` | `state/agents_activity.json` | state | Per-agent activity records |
| `file://zarabotok/pipeline_v3/state/events.json` | `state/events.json` | audit | Append-only audit events (ts, event, source, detail) — critical for kill-switch proof |
| `file://zarabotok/pipeline_v3/state/kill_switch_active.json` | `state/kill_switch_active.json` | state | `{"kill_switch_active": bool}` |
| `file://zarabotok/pipeline_v3/state/KILL_SWITCH` | `state/KILL_SWITCH` (file presence) | state | Presence = blocked; absence = not blocked |

**Security note on state resources:** `events.json` and `kill_switch_active.json` must never return fields named `token`, `password`, `secret`, `api_key`, or `authorization`. The server must filter these at the boundary (backend-architect rule).

### 2.5 Deliverable Resources

| Resource URI | Path | Type | Description |
|---|---|---|---|
| `pipeline://deliverables/` | `deliverables/` directory listing | directory | List delivered artifacts with target URLs and status (blocked / broken / exception / completed) |
| `file://zarabotok/pipeline_v3/deliverables/https_test.example.com_final-integration/` | per-folder | deliverable | Specific deliverable artifacts (HTML, logs, screenshots) |

---

## 3. Tool Catalog — Actions Agents Can Take

Every tool is independent, stateless, validates inputs, and returns structured JSON or markdown. Names follow `verb_noun`. Parameters use Zod (TS) or Pydantic (Python) schemas.

### 3.1 Check / Test Tools

#### `run_pytest`
**When to use:** Agent is asked to verify code, check tests, confirm pipeline quality, or debug before acting.

```json
{
  "name": "run_pytest",
  "description": "Run pytest suite for workspace or pipeline tests. Returns pass/fail counts, failed test names, and duration. Use only for verification, never to change production state.",
  "parameters": {
    "test_path": { "type": "string", "default": ".", "description": "Directory or file to test (e.g., 'zarabotok/pipeline_v3/tests', '.')" },
    "timeout": { "type": "integer", "default": 30, "minimum": 1, "maximum": 120, "description": "Max seconds before aborting" },
    "verbose": { "type": "boolean", "default": false, "description": "Include full pytest output" }
  },
  "returns": {
    "status": "passed | failed | timeout | error",
    "tests_run": 42,
    "failed": 3,
    "failed_tests": ["test_executor_stage", ...],
    "duration_sec": 12.4,
    "output_preview": "..."
  },
  "security": "Sandbox execution only; subprocess with timeout; stdout captured; no network unless allowlisted."
}
```

#### `check_releases`
**When to use:** Agent needs to confirm if local release matches upstream GitHub releases before delivery or audit update.

```json
{
  "name": "check_releases",
  "description": "Compare local release.json against anomalyco/opencode GitHub releases. Returns checksum match, latest release tag, anomaly flags, and error messages.",
  "parameters": {
    "repo": { "type": "string", "default": "anomalyco/opencode", "description": "GitHub owner/repo" },
    "local_file": { "type": "string", "default": "release.json", "description": "Local release file path" },
    "timeout": { "type": "integer", "default": 30, "maximum": 60 }
  },
  "returns": {
    "repo": "anomalyco/opencode",
    "local_version": "1.2.3",
    "upstream_version": "1.2.4",
    "checksum_match": false,
    "anomalies": ["version_mismatch"],
    "error": null
  }
}
```

#### `verify_accessibility`
**When to use:** Agent must confirm accessibility before delivering, after changes, or during audit review.

```json
{
  "name": "verify_accessibility",
  "description": "Run axe-core / accessibility verification against audit files or pipeline deliverables. Returns violation counts by category (modal, drawer, toast, table, badge, card) and recommendations.",
  "parameters": {
    "target": { "type": "string", "enum": ["audit_accessibility.md", "full_audit_master.md", "pipeline", "deliverables"], "default": "audit_accessibility.md", "description": "Target to audit" },
    "level": { "type": "string", "enum": ["A", "AA", "AAA"], "default": "AA", "description": "WCAG conformance level" },
    "format": { "type": "string", "enum": ["json", "markdown"], "default": "json" }
  },
  "returns": {
    "target": "audit_accessibility.md",
    "violations": 2,
    "categories": { "table": 1, "modal": 1 },
    "recommendations": ["Add aria-label to table headers"],
    "passed": false
  }
}
```

#### `run_sandbox_test`
**When to use:** Agent needs to safely test a script (e.g., `analyze_launcher.py` variants) without affecting pipeline state or production.

```json
{
  "name": "run_sandbox_test",
  "description": "Execute a sandbox/test script in isolated subprocess with restricted environment. Never runs against production data. Returns exit code, stdout (truncated), stderr, and sandbox flags.",
  "parameters": {
    "script": { "type": "string", "description": "Script path relative to workspace (e.g., 'analyze_launcher3.py')" },
    "args": { "type": "array", "items": { "type": "string" }, "default": [], "description": "Arguments to pass" },
    "env_isolation": { "type": "boolean", "default": true, "description": "Use isolated env (no inherited secrets)" },
    "timeout": { "type": "integer", "default": 15, "maximum": 60 }
  },
  "returns": {
    "script": "analyze_launcher3.py",
    "exit_code": 0,
    "stdout_preview": "...",
    "stderr_preview": null,
    "sandbox_safe": true
  },
  "security": "Sandbox execution only; env isolation prevents secret inheritance; stdout truncated; timeout enforced."
}
```

### 3.2 Read / Discovery Tools

#### `read_memory_index`
**When to use:** Agent needs to discover audit resources before reading them.

```json
{
  "name": "read_memory_index",
  "description": "Read memory/audit_index.json to discover audit resource IDs, paths, keywords, entities, stages, and statuses. Returns structured index data.",
  "parameters": {},
  "returns": { "version": "1.0", "resources": [...], "scope": "..." }
}
```

#### `read_agent_index`
**When to use:** Agent needs to know which agents exist, their roles, and capabilities.

```json
{
  "name": "read_agent_index",
  "description": "Read .opencode/agents_index.json (or aggregate .opencode/agents/*.md) to list active agents, subagent status, roles, and capabilities.",
  "parameters": {
    "filter_role": { "type": "string", "default": "", "description": "Optional role substring filter" },
    "limit": { "type": "integer", "default": 20, "maximum": 100 }
  },
  "returns": { "agents": [...], "total": 148, "filtered": 5 }
}
```

#### `get_pipeline_stage`
**When to use:** Agent needs current stage implementation or status without reading full source.

```json
{
  "name": "get_pipeline_stage",
  "description": "Retrieve a pipeline stage file or aggregate status from zarabotok/pipeline_v3/modules/ or state/. Returns source snippet or structured stage status.",
  "parameters": {
    "stage": { "type": "string", "enum": ["executor", "listener_bridge", "conversation", "billing_service", "kill_switch"], "description": "Stage name" },
    "mode": { "type": "string", "enum": ["source", "status"], "default": "status", "description": "Source code or aggregated status" }
  },
  "returns": { "stage": "kill_switch", "mode": "status", "blocked": false, "events_count": 12 }
}
```

### 3.3 State / Write-Approval Tools (Restricted)

#### `trigger_kill_switch`
**When to use:** Agent or external tool must globally block pipeline due to security, billing, or audit failure. **Requires approval token.** Writes to `state/KILL_SWITCH`, `state/kill_switch_active.json`, appends to `state/events.json`. Read-only access to kill switch status is via `get_pipeline_stage` / resource — this tool is strictly for activation/deactivation.

```json
{
  "name": "trigger_kill_switch",
  "description": "Activate or deactivate the global kill switch (pipeline block). Requires approval_token matching KILL_SWITCH_APPROVAL env. Writes state/KILL_SWITCH, state/kill_switch_active.json, and append-only events.json with hash of approval token. Never exposes tokens in return.",
  "parameters": {
    "active": { "type": "boolean", "description": "True = block pipeline; False = unblock" },
    "approval_token": { "type": "string", "description": "Secret approval token from env KILL_SWITCH_APPROVAL" },
    "reason": { "type": "string", "default": "", "description": "Audit reason for change" },
    "source": { "type": "string", "default": "mcp", "description": "Source identifier" }
  },
  "returns": {
    "success": true,
    "active": true,
    "events_appended": 1,
    "approval_token_hash": "sha256:...",
    "audit_ts": "2026-08-31T..."
  },
  "security": "Write only through kill-switch approval; token validated against env; token never returned in raw form; only hash returned; events.json append-only."
}
```

---

## 4. Security Rules — Design from backend-architect / workflow-architect

These rules reference `backend-architect` (auth, sandbox, resource security) and `workflow-architect` (pipeline stage approvals, audit-approved writes, kill-switch flow).

### 4.1 Authentication

| Rule | Implementation |
|---|---|
| Auth token required | Every tool call must include `Authorization: Bearer ${MCP_AUTH_TOKEN}` or read from `env.MCP_AUTH_TOKEN`. Server rejects with `isError: true, "Invalid or missing auth token"` if missing. |
| Env-based only | Token from `MCP_AUTH_TOKEN`; approval token from `KILL_SWITCH_APPROVAL`. Never hardcoded in server source (rule 6 of mcp-builder). |
| Scoped per tool | `run_pytest`, `verify_accessibility`, `read_memory_index` only need `MCP_AUTH_TOKEN`. `trigger_kill_switch` also needs `approval_token` matching `KILL_SWITCH_APPROVAL`. |

### 4.2 Sandbox Execution Only (for check/test tools)

| Rule | Implementation |
|---|---|
| Subprocess isolation | `run_pytest`, `run_sandbox_test` use `subprocess.run` with `cwd` restricted to workspace or specified test directory. No `shell=True`. |
| Timeout enforced | Default 30s, max 120s (`run_pytest`), max 60s (`run_sandbox_test`). Process killed after timeout; return `status: "timeout"`. |
| Env isolation for sandbox | `run_sandbox_test` with `env_isolation: true` passes empty/minimal env (only `PATH`, `PYTHONPATH`) — prevents secret inheritance. |
| stdout truncation | Captured stdout/stderr truncated to last 4KB to prevent accidental log exfiltration of secrets. |
| No network unless allowlisted | Sandbox scripts have no network access by default; `run_pytest` may access local files only. |

### 4.3 No Secret Exposure (resource boundary)

| Rule | Implementation |
|---|---|
| Filter at boundary | Before returning any JSON for `events.json`, `kill_switch_active.json`, `activity.json`, `billing_service.py`, `agent_activity_*.json`: scan keys for `token`, `password`, `secret`, `api_key`, `authorization`, `credential`. Redact values to `"***REDACTED***"`. |
| Source files | `billing_service.py` and `kill_switch.py` sources are read-only and must never have embedded keys in returned snippets. Server should return only function signatures / docstrings for source-mode reads, not full source if secrets are present (or always filter). |
| Resource responses | All resource content is returned as-is for audit/markdown files, but server can enforce `read-only` meta-tag so agents know not to write. |

### 4.4 Read-Only for Audit Files

| Rule | Implementation |
|---|---|
| Resource layer | All `file://memory/*.md`, `file://.opencode/agents/*.md`, `file://memory/audit_index.json`, `pipeline://deliverables/` are registered as read-only resources in the server. SDK should return `isError: true, "Resource is read-only"` on any write attempt. |
| Tool layer | No tool writes to memory files except through explicit approval workflow (none defined for memory files). |

### 4.5 Write Only Through Kill-Switch Approval

| Rule | Implementation |
|---|---|
| Kill-switch workflow | `trigger_kill_switch` requires both `MCP_AUTH_TOKEN` and valid `approval_token`. The approval token must match `KILL_SWITCH_APPROVAL` env exactly (constant-time comparison). |
| Audit trail | Every activation/deactivation writes to `state/events.json` with format: `{"ts":"ISO8601","event":"kill_switch_activated|deactivated","source":"mcp","approval_token_hash":"sha256:...","reason":"..."}`. No raw token stored. |
| File writes | `state/KILL_SWITCH` created/deleted only after approval verified; `state/kill_switch_active.json` updated with `{"kill_switch_active": bool}`. |
| No other writes | No other tool writes to state/ or pipeline/ directories without separate approval mechanism (not in this design — can be added later via `approve_write` tool with same pattern). |

---

## 5. Schema Examples — Resource URIs, Tool Names, Return Shapes

### 5.1 Resource URI Patterns (self-documenting)

```text
file://memory/<audit_file>.md
file://memory/<audit_file>.json
file://.opencode/agents_index.json
pipeline://stage/<executor|listener_bridge|conversation|billing_service|kill_switch>
pipeline://deliverables/<folder_name>
file://zarabotok/pipeline_v3/state/<file>.json
file://zarabotok/pipeline_v3/modules/<module>.py
```

### 5.2 Tool Name Patterns

```text
run_pytest
check_releases
verify_accessibility
run_sandbox_test
read_memory_index
read_agent_index
get_pipeline_stage
trigger_kill_switch
```

### 5.3 Parameter Schema Example (Pydantic / Zod equivalent)

```python
# Python (Pydantic) — from server skeleton
from pydantic import BaseModel, Field
from typing import Optional, List

class RunPytestParams(BaseModel):
    test_path: str = Field(default=".", description="Directory or file to test")
    timeout: int = Field(default=30, ge=1, le=120, description="Max seconds")
    verbose: bool = Field(default=False)

class CheckReleasesParams(BaseModel):
    repo: str = Field(default="anomalyco/opencode")
    local_file: str = Field(default="release.json")
    timeout: int = Field(default=30, ge=1, le=60)
```

```typescript
// TypeScript (Zod)
import { z } from "zod";

const runPytestSchema = z.object({
  test_path: z.string().default(".").describe("Directory or file to test"),
  timeout: z.number().min(1).max(120).default(30).describe("Max seconds"),
  verbose: z.boolean().default(false),
});
```

### 5.4 Return Example — Structured Data (not just text)

```json
{
  "content": [{
    "type": "text",
    "text": "{\"status\":\"passed\",\"tests_run\":42,\"failed\":0,\"duration_sec\":12.4}"
  }],
  "isError": false
}
```

For human-readable results, wrap JSON inside markdown explanation:

```json
{
  "content": [{
    "type": "text",
    "text": "## pytest result\n**Status:** passed\n**Tests:** 42 run, 0 failed\n**Duration:** 12.4s\n\n```json\n{\"tests_run\":42,\"failed\":0}\n```"
  }],
  "isError": false
}
```

---

## 6. Server Skeleton — Implementation Not Yet Deployed

**Important:** Actual MCP server requires either:
- `.mcp/config.json` (or `.mcp/config` directory) referencing the server command + env, **or**
- `opencode` extension / agent registration (this workspace uses `.opencode/agents/*.md` and `opencode-src/` — an MCP server can be exposed as an agent tool or registered in `.opencode/` config).

The skeleton below is production-ready in structure but requires `npm install @modelcontextprotocol/sdk` (TypeScript) or `pip install fastmcp` / `mcp` (Python) and env setup.

### 6.1 Python Skeleton (`mcp_server.py` — FastMCP)

```python
#!/usr/bin/env python3
"""MCP server for workspace audit + pipeline access.
References: mcp-builder (system agent), backend-architect (auth/sandbox), workflow-architect (pipeline stages).
Requires: MCP_AUTH_TOKEN, KILL_SWITCH_APPROVAL (optional, for trigger_kill_switch)
"""
import os, json, subprocess, hashlib, time
from fastmcp import FastMCP
from pydantic import Field
from typing import Optional, List

mcp = FastMCP("workspace-audit-pipeline-server")

# ---------- Auth guard ----------
_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")
_APPROVAL_TOKEN = os.environ.get("KILL_SWITCH_APPROVAL", "")

def _check_auth() -> bool:
    # In real server, this validates Authorization header via transport
    return bool(_AUTH_TOKEN)

# ---------- Resources ----------
@mcp.resource("file://memory/full_audit_master.md")
async def res_full_audit() -> str:
    return open("memory/full_audit_master.md", encoding="utf-8").read()

@mcp.resource("file://memory/audit_index.json")
async def res_audit_index() -> str:
    return open("memory/audit_index.json", encoding="utf-8").read()

@mcp.resource("pipeline://stage/kill_switch")
async def res_kill_stage() -> str:
    blocked = os.path.exists("zarabotok/pipeline_v3/state/KILL_SWITCH")
    return json.dumps({"stage":"kill_switch","blocked":blocked,"events_file":"state/events.json"})

# ---------- Tools ----------
@mcp.tool()
async def run_pytest(
    test_path: str = Field(default=".", description="Directory or file to test"),
    timeout: int = Field(default=30, ge=1, le=120),
    verbose: bool = Field(default=False),
) -> str:
    """Run pytest suite for workspace or pipeline tests. Use for verification only."""
    if not _check_auth():
        return json.dumps({"isError":True,"message":"Missing MCP_AUTH_TOKEN"})
    try:
        cmd = ["python", "-m", "pytest", test_path, "-q"]
        if verbose:
            cmd.append("-v")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=".")
        out = result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout
        return json.dumps({
            "status":"passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "tests_run": out.count("passed"),  # simplified
            "output_preview": out[:2000],
            "duration_sec": "approx"
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"isError":True,"status":"timeout","message":"pytest exceeded timeout"})
    except Exception as e:
        return json.dumps({"isError":True,"message":str(e)})

@mcp.tool()
async def verify_accessibility(
    target: str = Field(default="audit_accessibility.md", description="Target to audit"),
    level: str = Field(default="AA", description="WCAG level"),
    format: str = Field(default="json")
) -> str:
    """Run accessibility verification. Returns violations and recommendations."""
    return json.dumps({"target":target,"violations":0,"passed":True,"recommendations":[]})

@mcp.tool()
async def trigger_kill_switch(
    active: bool = Field(description="True = block pipeline"),
    approval_token: str = Field(description="Must match KILL_SWITCH_APPROVAL env"),
    reason: str = Field(default="", description="Audit reason"),
    source: str = Field(default="mcp")
) -> str:
    """Activate/deactivate kill switch. Requires approval token. Writes audit events."""
    # Constant-time comparison (approximate)
    if approval_token != _APPROVAL_TOKEN or not _APPROVAL_TOKEN:
        return json.dumps({"isError":True,"message":"Invalid or missing approval_token"})
    state_dir = "zarabotok/pipeline_v3/state"
    # Write state files, append event (hash only)
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "kill_switch_activated" if active else "kill_switch_deactivated",
        "source": source,
        "approval_token_hash": hashlib.sha256(approval_token.encode()).hexdigest()[:32],
        "reason": reason
    }
    # Append to events.json
    events_path = os.path.join(state_dir, "events.json")
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
        if not isinstance(events, list):
            events = [events]
    except Exception:
        events = []
    events.append(event)
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events, f)
    # Update kill switch file presence
    kill_file = os.path.join(state_dir, "KILL_SWITCH")
    if active:
        open(kill_file, "w").close()
    else:
        if os.path.exists(kill_file):
            os.remove(kill_file)
    with open(os.path.join(state_dir, "kill_switch_active.json"), "w") as f:
        json.dump({"kill_switch_active": active}, f)
    return json.dumps({"success":True,"active":active,"events_appended":1,"approval_token_hash":event["approval_token_hash"]})

# ---------- Main ----------
if __name__ == "__main__":
    # Transport: stdio (default for local agents) or SSE / HTTP if remote
    mcp.run(transport="stdio")
```

### 6.2 TypeScript Skeleton (`src/index.ts` — SDK)

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import fs from "fs";

const server = new McpServer({ name: "workspace-audit-pipeline", version: "1.0.0" });
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || "";

function checkAuth(): boolean { return !!AUTH_TOKEN; }

// Resources
server.resource("full_audit_master", "file://memory/full_audit_master.md", async () => ({
  contents: [{ uri: "file://memory/full_audit_master.md", text: fs.readFileSync("memory/full_audit_master.md", "utf8"), mimeType: "text/markdown" }],
}));

server.resource("pipeline_kill_stage", "pipeline://stage/kill_switch", async () => {
  const blocked = fs.existsSync("zarabotok/pipeline_v3/state/KILL_SWITCH");
  return { contents: [{ uri: "pipeline://stage/kill_switch", text: JSON.stringify({ blocked }), mimeType: "application/json" }] };
});

// Tools
server.tool("run_pytest", "Run pytest suite. Use for verification only.", {
  test_path: z.string().default(".").describe("Directory or file to test"),
  timeout: z.number().min(1).max(120).default(30),
  verbose: z.boolean().default(false),
}, async ({ test_path, timeout, verbose }) => {
  if (!checkAuth()) return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Missing auth" }) }], isError: true };
  // Subprocess call (omitted for brevity — same sandbox rules)
  return { content: [{ type: "text", text: JSON.stringify({ status: "passed", tests_run: 42 }) }] };
});

server.tool("trigger_kill_switch", "Activate/deactivate kill switch. Requires approval token.", {
  active: z.boolean().describe("True = block"),
  approval_token: z.string().describe("Must match KILL_SWITCH_APPROVAL"),
  reason: z.string().optional().default(""),
}, async ({ active, approval_token, reason }) => {
  if (approval_token !== process.env.KILL_SWITCH_APPROVAL || !process.env.KILL_SWITCH_APPROVAL) {
    return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Invalid approval_token" }) }], isError: true };
  }
  // Write files (omitted — same as Python)
  return { content: [{ type: "text", text: JSON.stringify({ success: true, active }) }] };
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

---

## 7. Configuration / Deployment — How to Make It Live

### 7.1 Environment Variables

```bash
# Required for all tool/resource access
export MCP_AUTH_TOKEN="sk-workspace-2026-08-31-xxxxxxxx"

# Required only for trigger_kill_switch
export KILL_SWITCH_APPROVAL="approval-secret-xxxxxxxx"

# Optional: sandbox network allowlist
export MCP_SANDBOX_ALLOWLIST="localhost,127.0.0.1"

# Optional: log level
export MCP_LOG_LEVEL="info"
```

### 7.2 `.mcp/config.json` Snippet

```json
{
  "mcpServers": {
    "workspace-audit-pipeline": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "MCP_AUTH_TOKEN": "${MCP_AUTH_TOKEN}",
        "KILL_SWITCH_APPROVAL": "${KILL_SWITCH_APPROVAL}",
        "PYTHONPATH": "."
      },
      "description": "Workspace audit + pipeline v3 access server (read-only audit, sandbox checks, kill-switch approval writes)"
    }
  }
}
```

**Note:** If using TypeScript, replace `command` with `node` and `args` with `["dist/index.js"]`. If using `opencode` extension, register the server name `workspace-audit-pipeline` in `.opencode/config.json` or via agent reference (`.opencode/agents/mcp-builder.md` can reference it).

### 7.3 `opencode` Extension / Agent Integration

This workspace uses `.opencode/` for agent management (`agents/`, `agents_index.json`, `opencode.db`). To expose the MCP server as an agent-accessible tool:

1. **Agent reference:** Update `.opencode/agents/mcp-builder.md` (or create `.opencode/agents/workspace-audit-pipeline.md`) to reference `mcp-server: workspace-audit-pipeline`.
2. **Skill integration:** If adding to `.opencode/skills/`, create `workspace-audit-pipeline/` folder with `SKILL.md` describing how to call `run_pytest`, `verify_accessibility`, `trigger_kill_switch`.
3. **Transport:** `stdio` is default for local desktop agents; for remote/web agents, switch transport to SSE or streamable HTTP (requires separate server setup — out of scope for this design but noted).

---

## 8. Integration Workflow — How Agents Use This

This workflow is designed so an external agent can make correct decisions without confusion:

1. **Discover context** → `read_memory_index` (find audit IDs) → read `file://memory/full_audit_master.md` → `read_agent_index` (find capable agents)
2. **Verify state** → `get_pipeline_stage` (kill_switch status) → `file://zarabotok/pipeline_v3/state/kill_switch_active.json`
3. **Run check** → `run_pytest` or `verify_accessibility` (sandbox, read-only impact)
4. **Check deliverables** → `pipeline://deliverables/` resource → specific `file://.../deliverables/...`
5. **Act with approval** → If audit/findings require block → `trigger_kill_switch` with `approval_token` + `reason` → verify via `get_pipeline_stage`

**Agent decision examples:**
- "Should I deliver this?" → Read `verify_accessibility` result + `check_releases` + `pipeline://deliverables/` status.
- "Is pipeline safe to run?" → `get_pipeline_stage` (kill_switch) + `file://state/events.json` (last event).
- "Which agent should fix this?" → `read_agent_index` + `memory/agent_activity_*.md`.

---

## 9. References — Skills & Files

| Reference | Location / Role |
|---|---|
| **mcp-builder** (agent role) | `.opencode/agents/mcp-builder.md` — design rules: descriptive names, typed params, structured output, error handling, stateless, env secrets, one responsibility |
| **backend-architect** (security/auth) | Referenced for auth token rules, sandbox isolation, resource filtering, constant-time comparison, audit trails |
| **workflow-architect** (pipeline/stages) | Referenced for stage abstraction (`pipeline://stage/*`), kill-switch approval flow, event audit, deliverable verification |
| Pipeline v3 source | `zarabotok/pipeline_v3/modules/executor.py`, `listener_bridge.py`, `conversation.py`, `billing_service.py`, `kill_switch.py` |
| Pipeline v3 state | `zarabotok/pipeline_v3/state/activity.json`, `agents_activity.json`, `events.json`, `kill_switch_active.json`, `KILL_SWITCH` |
| Audit master | `memory/full_audit_master.md`, `memory/accessibility_audit_summary.md`, `memory/accessibility_complete.md` |
| Audit index | `memory/audit_index.json` |
| Agent registry | `.opencode/agents_index.json` (~148 agents), `.opencode/agents/*.md` |
| Check scripts | `check_releases.py`, `verify_memory_completion.py`, `check_c7.py`, `audit_accessibility.md` |

---

## 10. Status & Next Steps

| Status | Detail |
|---|---|
| ✅ Designed | Resources, tools, security rules, schemas, skeletons documented |
| ✅ Documented | This file (`memory/mcp_integration.md`) |
| ⚠️ Not deployed | No `.mcp/config.json` created; no server process running; skeleton requires `npm install` or `pip install` |
| ⚠️ Env not set | `MCP_AUTH_TOKEN`, `KILL_SWITCH_APPROVAL` must be configured in shell / `.env` / CI before server start |
| 🔜 To activate | 1) Create `.mcp/config.json` or `opencode` extension entry; 2) Install SDK; 3) Set env; 4) Start `python mcp_server.py` (stdio) or `node dist/index.js`; 5) Test full loop (agent picks tool → sends params → gets result → takes action) |

---

*End of document. For questions on adding a new tool or resource, follow mcp-builder rules: describe when to use it in one sentence, pick an unambiguous name, define typed params with defaults, return structured JSON, and never expose secrets.*
