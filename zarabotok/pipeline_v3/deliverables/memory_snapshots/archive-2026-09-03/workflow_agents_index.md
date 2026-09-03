# Workflow Agents Index — W7 / W19 Documentation
**Date:** 2026-08-31
**Source:** `.opencode/agents_index.json` (184 agents from `.opencode/agents/*.md`)
**Expanded:** `zarabotok/pipeline_v3/.opencode/agents_index.json`

## Added fields per agent
- `autonomy`: manual / semi-auto / full (derived from L0–L4)
- `validators`: list (quality, security, audit)
- `max_size`: int (5 / 10 / 50 / 200 / 500)
- `level`: L0 / L1 / L2 / L3 / L4

## Level mapping
- L0: manual / excluded from auto-reply
- L1: manual / low autonomy
- L2: semi-auto / manual approval only
- L3: full / allowed auto-reply
- L4: full / high autonomy, max_size 500

## W7 (P1) — completed
Fields added; levels L0–L4 assigned; documented.

## W19 (P2) — partial
184 agents indexed; full 400+ catalog requires additional agent definitions from `.opencode/plans/` and `skills_registry.json`. Next step: merge registry skills as agents and expand.

## Verification
- File paths: `.opencode/agents_index.json`; `zarabotok/pipeline_v3/.opencode/agents_index.json`
- Count: 184
- Levels present: L0, L1, L2, L3, L4
- Validators present: quality, security (L3/L4)
