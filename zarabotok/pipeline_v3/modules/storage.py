"""PostgreSQL storage layer for the pipeline — drop-in for store.py semantics.

Same interface: load(name, default=None), save(name, data), mutate(name, fn, default=None),
append(name, item, key="items"), now(), _path(name).
Extra helpers: delete(name), event(name, data=None), ping(), last_error().

Layout:
  kv(name text PRIMARY KEY, data jsonb)          — collections are rows (one per state/*.json)
  events(id bigserial, name text, data jsonb, ts timestamptz) — append-only event log

On first connect all state/*.json collections are imported into kv if the row is missing
(idempotent). Missing rows are also lazy-imported on access, so a collection created
later by the live system (JSON mode) is picked up automatically.
"""

import json
import os
import threading
import time

import psycopg
from psycopg.types.json import Jsonb

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state")

_plock = threading.RLock()
_conn = None
_last_error = None
_migrated = False
_cache = {}
_CTTL = 1.0  # секунд — TTL кэша чтения (защита от деградации БД/нагрузки)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    name text PRIMARY KEY,
    data jsonb
);
CREATE TABLE IF NOT EXISTS events (
    id bigserial PRIMARY KEY,
    name text NOT NULL,
    data jsonb,
    ts timestamptz NOT NULL DEFAULT now()
);
"""


class StorageUnavailable(Exception):
    pass


def _params():
    p = {}
    try:
        with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
            p = (json.load(f) or {}).get("storage", {}).get("postgres", {}) or {}
    except Exception:
        pass
    return {
        "host": p.get("host", "127.0.0.1"),
        "port": int(p.get("port", 5433)),
        "dbname": p.get("db", "pipeline"),
        "user": p.get("user", "pipeline"),
        "password": p.get("password", "pipeline"),
        "connect_timeout": 3,
    }


def _close():
    global _conn
    try:
        if _conn is not None:
            _conn.close()
    except Exception:
        pass
    _conn = None


def _read_json(name):
    """Return (data, exists). exists=False if file missing or unparseable."""
    path = os.path.join(STATE, name + ".json")
    if not os.path.exists(path):
        return None, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), True
    except Exception:
        return None, False


def _migrate_all(conn):
    """Idempotent import of every state/*.json collection missing in kv. Returns count."""
    if not os.path.isdir(STATE):
        return 0
    n = 0
    for fn in sorted(os.listdir(STATE)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        if conn.execute("SELECT 1 FROM kv WHERE name=%s", (name,)).fetchone() is not None:
            continue
        data, ok = _read_json(name)
        if not ok:
            continue
        conn.execute(
            "INSERT INTO kv(name, data) VALUES(%s, %s) ON CONFLICT (name) DO NOTHING",
            (name, Jsonb(data)),
        )
        n += 1
    return n


def _connect():
    """Return live connection or None. Reconnects if the old one died."""
    global _conn, _last_error, _migrated
    with _plock:
        if _conn is not None:
            try:
                _conn.execute("SELECT 1")
                return _conn
            except Exception:
                _close()
        try:
            _conn = psycopg.connect(**_params())
            _conn.autocommit = True
            _conn.execute(_SCHEMA)
            if not _migrated:
                _migrate_all(_conn)
                _migrated = True
            _last_error = None
            return _conn
        except Exception as e:
            _last_error = str(e)
            _close()
            return None


def ping():
    return _connect() is not None


def last_error():
    return _last_error


def _lazy_import(name):
    """Ensure the kv row exists (import from state/<name>.json if needed).
    Returns (data, existed): existed=True if a row is present after the call
    (data may be None for a stored NULL)."""
    with _plock:
        conn = _connect()
        if conn is None:
            raise StorageUnavailable(_last_error or "postgres unavailable")
        row = conn.execute("SELECT data FROM kv WHERE name=%s", (name,)).fetchone()
        if row is not None:
            return row[0], True
        data, ok = _read_json(name)
        if ok:
            conn.execute(
                "INSERT INTO kv(name, data) VALUES(%s, %s) ON CONFLICT (name) DO NOTHING",
                (name, Jsonb(data)),
            )
            return data, True
        return None, False


def load(name, default=None):
    now = time.time()
    c = _cache.get(name)
    if c is not None and c[1] > now:
        return c[0]
    with _plock:
        data, existed = _lazy_import(name)
        val = data if existed else (default if default is not None else {})
        _cache[name] = (val, time.time() + _CTTL)
        return val


def _invalidate(name):
    _cache.pop(name, None)


def save(name, data):
    with _plock:
        conn = _connect()
        if conn is None:
            raise StorageUnavailable(_last_error or "postgres unavailable")
        conn.execute(
            "INSERT INTO kv(name, data) VALUES(%s, %s) "
            "ON CONFLICT (name) DO UPDATE SET data=EXCLUDED.data",
            (name, Jsonb(data)),
        )
        _invalidate(name)


def mutate(name, fn, default=None):
    """load fresh, apply fn(data), save — atomic per name (SELECT ... FOR UPDATE)."""
    with _plock:
        conn = _connect()
        if conn is None:
            raise StorageUnavailable(_last_error or "postgres unavailable")
        with conn.transaction():
            row = conn.execute(
                "SELECT data FROM kv WHERE name=%s FOR UPDATE", (name,)
            ).fetchone()
            if row is not None:
                data = row[0]
            else:
                data, ok = _read_json(name)
                if not ok:
                    data = default
            res = fn(data)
            conn.execute(
                "INSERT INTO kv(name, data) VALUES(%s, %s) "
                "ON CONFLICT (name) DO UPDATE SET data=EXCLUDED.data",
                (name, Jsonb(data)),
            )
        return res


def append(name, item, key="items"):
    def _fn(d):
        d.setdefault(key, []).append(item)
        return None

    mutate(name, _fn, {key: []})


def delete(name):
    with _plock:
        conn = _connect()
        if conn is None:
            raise StorageUnavailable(_last_error or "postgres unavailable")
        conn.execute("DELETE FROM kv WHERE name=%s", (name,))
        _invalidate(name)


def event(name, data=None):
    with _plock:
        conn = _connect()
        if conn is None:
            raise StorageUnavailable(_last_error or "postgres unavailable")
        conn.execute("INSERT INTO events(name, data) VALUES(%s, %s)", (name, Jsonb(data)))


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _path(name):
    return os.path.join(STATE, name + ".json")