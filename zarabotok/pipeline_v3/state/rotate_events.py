#!/usr/bin/env python3
"""
state/events.json rotation stub (P0 — memory/backend_arch_review.md §4.2).
- Trim to 500 entries (existing kill_switch.py write_event already trims).
- Archive trimmed/old entries to archive/events-YYYY-MM-DD.jsonl.
- Run via cron / pipeline worker; safe to call repeatedly (idempotent by date).
"""
import json
import os
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
EVENTS_FILE = os.path.join(STATE_DIR, "events.json")
ARCHIVE_DIR = os.path.join(STATE_DIR, "archive")
MAX_EVENTS = 500

def rotate() -> dict:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    events = []
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    events = data
        except Exception:
            events = []
    archived = []
    trimmed = events[-MAX_EVENTS:] if len(events) > MAX_EVENTS else events[:]
    if len(events) > MAX_EVENTS:
        archived = events[:-MAX_EVENTS]
    # Archive old entries as JSON Lines (jsonl) with date stamp
    if archived:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        archive_path = os.path.join(ARCHIVE_DIR, f"events-{today}.jsonl")
        with open(archive_path, "a", encoding="utf-8") as f:
            for ev in archived:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    # Write trimmed back
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)
    return {
        "status": "rotated" if archived else "no_rotation_needed",
        "total_read": len(events),
        "trimmed_kept": len(trimmed),
        "archived_count": len(archived),
        "archive_file": archive_path if archived else None,
    }

if __name__ == "__main__":
    result = rotate()
    print(json.dumps(result))
