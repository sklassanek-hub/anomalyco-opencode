# Orders frontend fix — complete log

## Before (reported holes)
- Orders not visible / not informative: table had only URL, source, title, budget, score, raw status badge, stage — no agent, no message preview, no quick actions.
- No auto-response: `autoreply.py` checks `store.load('settings', {}).get('auto_reply')`; settings file missing or `auto_reply` false; `DIALOG_COOLDOWN_MIN` = 15.
- Agent handoff not configured: no button / link in Orders modal or table; `conversation.py` and `listener_bridge.py` existed but not exposed in UI.
- Modal lacking thread / agent actions / auto-reply info; footer had only CRM / raw / force / close.
- No `aria-label` on action buttons; missing `aria-label` on links.

## Changes made

### 1. Orders.tsx (table & modal)
- File: `zarabotok/pipeline_v3/ui/src/pages/Orders.tsx`
- Columns expanded (lines 160–238): added `status` column with `stageRu` + `Badge` + raw status; added `agent` column with link to `/agent/<name>` or "Назначить"; added `lastMessage` column with snippet (70 chars) or message count; added `actions` column with Reply / Assign / Escalate buttons (`size="sm"`, `aria-label`, `stopPropagation`).
- Existing `url`, `source`, `title`, `budget`, `score` kept; `filter` / `stage` merged into clear `status` column.
- Modal title kept; added `aria-label` to `url` link; footer buttons got `aria-label`; added `AgentTransfer` button navigating to `/transfer?url=`.
- Modal body (line ~56–122): added conversation/thread grid with open-thread link and conversation key snippet; added auto-reply status row (`Badge` ok/gray, note on `store.load('settings').get('auto_reply') === true`); added agent linkage count.
- Agent activity list enhanced with `<a>` links to agent profile (`/agent/<agent>`), `aria-label` per item.
- Accessibility preserved: no `Modal` / `Drawer` / `Toast` props broken; existing `useToast`, `useOrder`, `useOrders` unchanged.

### 2. Auto-reply settings
- File: `zarabotok/pipeline_v3/config/settings.json` (new dir/file) — `{"auto_reply": true, "dialog_cooldown_min": 5}`.
- File: `zarabotok/pipeline_v3/state/settings.json` — already `auto_reply: true`; kept.
- File: `zarabotok/pipeline_v3/modules/autoreply.py` — edited comments/config near line 256 (`store.load('settings', {}).get('auto_reply')` must be true). Added comment block above `cycle()` noting requirement of `config/settings.json` or `state/settings.json`; `DIALOG_COOLDOWN_MIN` can be overridden by settings `dialog_cooldown_min` (documented, not hard-enforced in code because settings load via `store`).

### 3. Agent handoff / transfer
- File: `memory/orders_handoff.md` — new documentation with backend refs.
- UI: `AgentTransfer` button in modal footer; `Assign` button in table actions.
- Backend refs documented: `modules/conversation.py` (`Conversation.link_message`, `link_by_chat_id`, etc., lines 61–352); `modules/listener_bridge.py` (`poll_and_link`, `_link_message`, lines 22–97).

### 4. Memory / documentation
- File: `memory/orders_frontend_fix.md` — this file.
- File: `memory/orders_handoff.md` — handoff refs.
- File: `memory/complete_worklist.md` — W14 (`metrics_funnel`), W15 (`billing`) referenced as related; no direct edit required but noted.

## Before/after per requirement
| Requirement | Before | After |
|---|---|---|
| Clear status column (stageRu + badge) | `filter` column raw text only, `stage` at end; not informative | `status` column with `stageRu` + `Badge` + raw text; first after title |
| Agent assignment display | None | `agent` column with link / "Назначить"; modal shows linkage count + links |
| Quick action buttons | None | `actions` column with Reply / Assign / Escalate, `aria-label`, `stopPropagation` |
| Table shows url, status, agent, last message | url only, no agent, no message | All present; message snippet or count |
| Modal more informative | description + metadata + messages + invoice + exec_task only | + conversation/thread link + auto-reply status + agent linkage; agent activity linked |
| Auto-reply enabled | `store.load('settings')` may miss; no config at `config/settings.json` | `config/settings.json` created; comment in `autoreply.py`; `state/settings.json` kept |
| Agent handoff configured | No UI reference | `AgentTransfer` button + `Assign`; `memory/orders_handoff.md` with `conversation.py` / `listener_bridge.py` refs |

## Remaining gaps
- `/transfer` endpoint not implemented in `dashboard.py` or `workers/`; needs route that calls `conversation.Conversation.link_message()` or updates `agents_activity.json`.
- `conversation.py` `needs_linking` queue should be cleared after manual handoff (`clear_needs_linking()`).
- `autoreply.py` does not dynamically read `config/settings.json`; relies on `store.load('settings')`. Ensure `store` loads from `config/settings.json` or merge both.
- No automatic sync between `exec_task.agents` and order agent assignment in UI; needs `crm.set_status()` hook.
- `metrics_funnel.json` (W14) and `billing.py` (W15) not fully linked to Orders page; out of scope for this fix but noted.
- `Table.tsx` keyboard navigation (ArrowUp/ArrowDown) still placeholder per `complete_worklist.md` A3; not broken by this edit.
- `focus-trap` for nested `showRaw` modal still needs library (A22); existing basic modal works.

## Files changed / added
- Modified: `zarabotok/pipeline_v3/ui/src/pages/Orders.tsx`
- Modified: `zarabotok/pipeline_v3/modules/autoreply.py`
- Created: `zarabotok/pipeline_v3/config/settings.json`
- Created: `memory/orders_frontend_fix.md`
- Created: `memory/orders_handoff.md`
- Unchanged but referenced: `memory/complete_worklist.md` (W14, W15)
