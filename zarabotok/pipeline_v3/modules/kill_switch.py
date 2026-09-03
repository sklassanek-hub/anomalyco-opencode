"""P0 W2 — Kill Switch + events.json + audit log.
References: modules/executor.py (lines 212-226 kill-state read), WORKFLOW.md §25.
Files:
- state/KILL_SWITCH (presence = blocked)
- state/kill_switch_active.json (json: {"kill_switch_active": bool})
- state/events.json (append-only audit: {"ts":..., "event":..., "source":..., "detail":...})
"""
import json
import os
import time
from typing import Any, Dict, Optional

logger = __import__("logging").getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(_BASE_DIR, "state")
KILL_SWITCH_FILE = os.path.join(STATE_DIR, "KILL_SWITCH")
KILL_STATE_FILE = os.path.join(STATE_DIR, "kill_switch_active.json")
EVENTS_FILE = os.path.join(STATE_DIR, "events.json")

# ---------- Global block ----------

def is_blocked() -> bool:
    """Return True if kill switch is active (global block)."""
    if os.path.exists(KILL_SWITCH_FILE):
        return True
    try:
        if os.path.exists(KILL_STATE_FILE):
            with open(KILL_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("kill_switch_active") is True:
                return True
    except Exception as e:
        logger.warning("kill_switch: error reading %s: %s", KILL_STATE_FILE, e)
    return False

def set_blocked(active: bool = True) -> None:
    """Set kill switch globally; update file + events.json audit."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except Exception:
        pass
    if active:
        # Presence file = immediate block (executor checks this first)
        with open(KILL_SWITCH_FILE, "w", encoding="utf-8") as f:
            f.write(f"kill_switch_active={time.time()}")
    else:
        if os.path.exists(KILL_SWITCH_FILE):
            try:
                os.remove(KILL_SWITCH_FILE)
            except Exception:
                pass
    # Sync JSON state (executor reads this too)
    state = {"kill_switch_active": active, "updated": time.time(), "source": "kill_switch.set_blocked"}
    with open(KILL_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    # Audit event
    write_event({
        "ts": time.time(),
        "event": "kill_switch_set",
        "source": "modules/kill_switch.py",
        "detail": {"active": active, "kill_path": KILL_SWITCH_FILE, "state_path": KILL_STATE_FILE}
    })

def clear_block() -> None:
    """Explicit clear (wrapper)."""
    set_blocked(False)

# ---------- events.json writer (audit log) ----------

def write_event(event: Dict[str, Any]) -> None:
    """Append event to state/events.json (line-delimited JSON objects or JSON array)."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except Exception:
        pass
    events = []
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    events = data
        except Exception:
            events = []
    events.append(event)
    # Trim to last 500 events to keep file bounded
    if len(events) > 500:
        events = events[-500:]
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    logger.info("kill_switch: event written (%s) ts=%.3f", event.get("event"), event.get("ts"))

# ---------- Delivery / executor audit (wired into delivery) ----------

# ---------- Scanner / Store audit (P0 extension: not just executor) ----------

def audit_scanner(source_url: str, status: str, detail: Optional[str] = None) -> None:
    """Audit scanner events (poll, extract, block) and link to delivery audit."""
    audit_delivery(source_url, status, f"scanner:{detail or ''}")
    write_event({
        "ts": time.time(),
        "event": "scanner_audit",
        "source": "modules/kill_switch.py",
        "detail": {
            "source_url": source_url,
            "status": status,
            "kill_active": is_blocked(),
            "message": detail or ""
        }
    })

def audit_store(key: str, action: str, status: str, detail: Optional[str] = None) -> None:
    """Audit store/dedup events (mutate, dedup, filter) — extends kill_switch beyond executor."""
    write_event({
        "ts": time.time(),
        "event": "store_audit",
        "source": "modules/kill_switch.py",
        "detail": {
            "key": key,
            "action": action,
            "status": status,
            "kill_active": is_blocked(),
            "message": detail or ""
        }
    })

def audit_delivery(url: str, status: str, detail: Optional[str] = None) -> None:
    """Write delivery audit event for executor/delivery pipeline."""
    write_event({
        "ts": time.time(),
        "event": "delivery_audit",
        "source": "modules/kill_switch.py",
        "detail": {
            "url": url,
            "status": status,
            "kill_active": is_blocked(),
            "message": detail or ""
        }
    })

# ---------- Init ----------
# Ensure events file exists
if not os.path.exists(EVENTS_FILE):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass
