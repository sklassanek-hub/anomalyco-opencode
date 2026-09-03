# Agent handoff / transfer — Orders modal & backend refs

## What was done
- Added `AgentTransfer` button in `Orders.tsx` modal footer (line ~42) that navigates to `/transfer?url=<order>`.
- Added `AgentTransfer` reference in table actions column (Reply / Assign / Escalate) with `aria-label="Link order to agent via conversation"`.
- Documented backend linkage in this file.

## File refs
- `zarabotok/pipeline_v3/ui/src/pages/Orders.tsx` — modal footer button; actions column; agent link in table.
- `zarabotok/pipeline_v3/modules/conversation.py` — `Conversation.link_message()` (line 289); `link_by_chat_id()`, `link_by_email_thread()`, `link_by_proposal_id()`, `link_by_contact()`, `link_by_semantic_similarity()`; `needs_linking`; `linked_order`.
- `zarabotok/pipeline_v3/modules/listener_bridge.py` — `ListenerBridge.poll_and_link()` (line 29); `_link_message()` (line 59); uses `conv_mod.get_conversation()` and `conv.link_message()` to feed listener inbox into threading.
- `zarabotok/pipeline_v3/state/settings.json` — `auto_reply` must be true for autoreply pipeline; `dialog_cooldown_min` set to 5.

## How linking works (for operator / agent)
1. Message arrives via listener (`listener.py` / `tg_common.py`).
2. `listener_bridge.ListenerBridge.poll_and_link()` feeds message into `conversation.Conversation`.
3. `Conversation.link_message()` attempts `chat_id` → `email_thread` → `proposal_id` → `contact` → `semantic` to bind to order URL.
4. Once `linked_order` set (`conversation.py` line 70), the message is tied to the order thread.
5. For manual handoff: use modal `AgentTransfer` button → `/transfer?url=...` endpoint should call `conversation.Conversation.link_message()` or `listener_bridge.accept_inbox()` with `url` param.

## Remaining gaps
- `/transfer` endpoint not implemented in `dashboard.py` or `modules/`; needs route + `store.mutate` to update `agents_activity.json`.
- No automatic agent assignment from `exec_task.agents`; should sync with `crm.set_status()` or `executor.create_exec_task()`.
- `conversation.py` `needs_linking` queue not cleared after manual handoff; should call `clear_needs_linking()` after linkage.
