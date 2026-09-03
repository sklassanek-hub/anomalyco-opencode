"""Структурированные JSONL-логи + события в store (state/events.json).

log_event(worker, level, msg, **fields):
  - пишет строку {ts, worker, level, msg, fields} в logs/YYYY-MM-DD.jsonl
    (папка logs/ из config.json logging.dir, создаётся при необходимости);
  - дублирует запись как событие в state/events.json через store.append.
"""
import json
import os

from modules import store

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = ("info", "warning", "error")


def _cfg():
    try:
        with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
            return (json.load(f) or {}).get("logging") or {}
    except Exception:
        return {}


def _scalar(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return v


def log_event(worker: str, level: str, msg: str, **fields):
    """JSONL-запись в logs/YYYY-MM-DD.jsonl + событие в store events."""
    if level not in LEVELS:
        level = "info"
    cfg = _cfg()
    if not cfg.get("jsonl", True):
        return
    ts = store.now()
    line = {
        "ts": ts,
        "worker": worker,
        "level": level,
        "msg": str(msg),
        "fields": {k: _scalar(v) for k, v in fields.items()},
    }
    logdir = os.path.join(BASE, cfg.get("dir", "logs"))
    os.makedirs(logdir, exist_ok=True)
    path = os.path.join(logdir, ts[:10] + ".jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    store.append("events", {"ts": ts, "severity": level, "source": worker, "text": str(msg), **fields}, key="items")