---
name: Workspace Audit + Pipeline MCP Integration
version: 1.0.0
date: 2026-08-31
description: External AI agent / tool access to workspace audit resources, pipeline v3 stages (executor.py, listener_bridge.py, conversation.py, billing_service.py, kill_switch.py), state/activity, agent index (.opencode/agents_index.json), and deliverables via MCP server.
mode: subagent
color: '#10B981'
---

# Workspace Audit + Pipeline MCP Integration

This agent/reference connects external AI agents to the workspace through the MCP (Model Context Protocol) server defined in `.mcp/config.json` and skeletons `mcp_server.py` / `mcp_server.ts`.

## References
- Design document: `memory/mcp_integration.md`
- Skeleton server (Python): `mcp_server.py`
- Skeleton server (TypeScript): `mcp_server.ts`
- Config: `.mcp/config.json`
- Skills: `mcp-builder` (.opencode/agents/mcp-builder.md), `backend-architect`, `workflow-architect`

## Resources Available (predictable URIs)
- `file://memory/full_audit_master.md`
- `file://memory/accessibility_audit_summary.md`
- `file://memory/accessibility_complete.md`
- `file://memory/agent_activity_2026-08-31.md`
- `file://memory/audit_index.json`
- `pipeline://stage/executor` | `listener_bridge` | `conversation` | `billing_service` | `kill_switch`
- `file://zarabotok/pipeline_v3/state/activity.json`
- `file://zarabotok/pipeline_v3/state/events.json`
- `file://zarabotok/pipeline_v3/state/kill_switch_active.json`
- `file://.opencode/agents_index.json`
- `pipeline://deliverables/`

## Tools Available (agent-friendly names)
- `run_pytest` — verification only; sandbox isolation; timeout enforced
- `check_releases` — compare local `release.json` against `anomalyco/opencode`
- `verify_accessibility` — axe-style verification; returns violations by category
- `run_sandbox_test` — isolated subprocess; env isolation; never production
- `read_memory_index` — discover audit IDs from `audit_index.json`
- `read_agent_index` — list agents; filter by role
- `get_pipeline_stage` — stage status or source snippet (secret-filtered)
- `trigger_kill_switch` — requires `approval_token` matching `KILL_SWITCH_APPROVAL`; writes audit events with hash only

## Security Rules (backend-architect / workflow-architect)
- All calls require `MCP_AUTH_TOKEN` env / header.
- Sandbox tools (`run_pytest`, `run_sandbox_test`) run in subprocess with timeout and stdout truncation.
- No secret exposure: resource/filter boundary removes `token`, `password`, `secret`, `api_key`.
- Audit files (`memory/*.md`, `.opencode/agents/*.md`) are read-only.
- Writes to `state/` only through `trigger_kill_switch` with approval token; token never stored raw (only SHA-256 hash in `events.json`).

## How to Use (Agent Workflow)
1. Read context: `read_memory_index` → `file://memory/full_audit_master.md`
2. Check pipeline health: `get_pipeline_stage` (kill_switch) → `file://zarabotok/pipeline_v3/state/kill_switch_active.json`
3. Verify quality: `run_pytest` / `verify_accessibility` / `check_releases`
4. Discover agents: `read_agent_index`
5. Act with approval: if block needed → `trigger_kill_switch` (approval_token + reason)

## Status
- Design complete (`memory/mcp_integration.md`)
- Skeletons provided (`mcp_server.py`, `mcp_server.ts`)
- Config defined (`.mcp/config.json`)
- **Not deployed**: requires `npm install @modelcontextprotocol/sdk` or `pip install fastmcp pydantic`; env vars set; server started.

## Deployment Notes
- Transport: `stdio` (local desktop agent). For remote/web, upgrade to SSE or streamable HTTP.
- Start: `python mcp_server.py` or `node mcp_server.js` after compiling.
- Verify: agent picks correct tool by name/description → sends typed params → receives structured JSON → takes next action.
