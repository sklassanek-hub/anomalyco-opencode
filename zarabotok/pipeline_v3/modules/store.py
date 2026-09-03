import json
import os
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state")
os.makedirs(STATE, exist_ok=True)

_tlock = threading.RLock()
_fs_depth = 0

_pg_reach_until = 0.0
_pg_reach_ok = False


def _pg_reachable():
    """Кэшированная проверка доступности PostgreSQL (backoff 30с).

    Если PG недоступен, НЕ пытаемся коннектиться на каждый store.load
    (это давало ~3с таймаута на каждый вызов и вешало дашборд).
    """
    global _pg_reach_until, _pg_reach_ok
    now = time.time()
    if now - _pg_reach_until < 30:
        return _pg_reach_ok
    ok = False
    try:
        import psycopg
        p = (_cfg_storage().get("postgres") or {})
        params = {
            "host": p.get("host", "127.0.0.1"),
            "port": int(p.get("port", 5433)),
            "dbname": p.get("db", "pipeline"),
            "user": p.get("user", "pipeline"),
            "password": p.get("password", "pipeline"),
            "connect_timeout": 2,
        }
        c = psycopg.connect(**params)
        c.close()
        ok = True
    except Exception:
        ok = False
    _pg_reach_ok = ok
    _pg_reach_until = now
    return ok


def _path(name):
    return os.path.join(STATE, name + ".json")


def _cfg_storage():
    """storage section of config.json — read fresh each call so the
    json<->postgres switch takes effect immediately."""
    try:
        with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("storage") or {}
    except Exception:
        return {}


def _pg_storage():
    """Return the storage module when PostgreSQL mode is enabled AND reachable, else None."""
    try:
        if _cfg_storage().get("type") != "postgres":
            return None
        if not _pg_reachable():
            return None
        from modules import storage
        return storage
    except Exception:
        return None


def storage_info():
    """dict: mode (postgres|json — actual backend used), ok, error."""
    st = _pg_storage()
    if st is None:
        return {"mode": "json", "ok": True, "error": None}
    try:
        ok = st.ping()
        return {
            "mode": "postgres" if ok else "json",
            "ok": ok,
            "error": None if ok else st.last_error(),
        }
    except Exception as e:
        return {"mode": "json", "ok": False, "error": str(e)}


def _fslock(timeout: float = 30.0, retry: float = 0.1):
    """Неблокирующая попытка с ретраями. Реентерабельна: вложенный вызов
    того же процесса пропускает взять лок (внешний уже защищает запись)."""
    global _fs_depth
    if _fs_depth > 0:
        return None
    handle = None
    try:
        import msvcrt
        lpath = os.path.join(STATE, ".store.lock")
        handle = open(lpath, "a+")
        t0 = time.monotonic()
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                _fs_depth += 1
                return handle
            except OSError:
                if time.monotonic() - t0 > timeout:
                    return handle
                time.sleep(retry)
    except Exception:
        return handle


def _fsunlock(handle):
    global _fs_depth
    if handle is None:
        return
    if _fs_depth > 0:
        _fs_depth -= 1
    try:
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        pass
    try:
        handle.close()
    except Exception:
        pass


def _dashboard_cfg():
    """Dashboard toggles — single source of truth: config.json ->dashboard, fallback legacy state/settings.json."""
    try:
        with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
        d = cfg.get("dashboard") or {}
        if isinstance(d, dict) and d:
            return d
    except Exception:
        pass
    return {}


def _merged_settings(raw: dict) -> dict:
    """Merge legacy state/settings.json with config dashboard (config wins when present)."""
    cfg = _dashboard_cfg()
    if not cfg:
        return raw
    merged = dict(raw) if isinstance(raw, dict) else {}
    for k in ("tg_poll", "show_vacancies", "auto_reply", "tg_session_listener"):
        if k in cfg:
            merged[k] = cfg[k]
    # email lives in config.email_accounts / config.email — legacy settings.email kept for compat
    return merged


def load(name, default=None):
    st = _pg_storage()
    if st is not None:
        try:
            data = st.load(name, default)
            if name == "settings" and isinstance(data, dict):
                data = _merged_settings(data)
            return data
        except Exception:
            pass
    with _tlock:
        path = _path(name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if name == "settings" and isinstance(data, dict):
                        data = _merged_settings(data)
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        if name == "settings":
            cfg = _dashboard_cfg()
            if cfg:
                return dict(cfg)
        return default if default is not None else {}


def _atomic_replace(tmp: str, path: str, tries: int = 6, delay: float = 0.4):
    """os.replace на Windows падает, если целевой файл кем-то открыт — повторяем."""
    for i in range(tries):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(delay)


def _persist_dashboard_to_cfg(data: dict):
    """Mirror dashboard toggles to config.json ->dashboard (single source of truth)."""
    try:
        cfg_path = os.path.join(BASE, "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
        dash = cfg.setdefault("dashboard", {})
        changed = False
        for k in ("tg_poll", "show_vacancies", "auto_reply", "tg_session_listener"):
            if k in data and dash.get(k) != data[k]:
                dash[k] = data[k]
                changed = True
        if changed:
            tmp = cfg_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=1)
            _atomic_replace(tmp, cfg_path)
    except Exception:
        pass


def save(name, data):
    if name == "settings" and isinstance(data, dict):
        _persist_dashboard_to_cfg(data)
    st = _pg_storage()
    if st is not None:
        try:
            return st.save(name, data)
        except Exception:
            pass
    with _tlock:
        handle = _fslock()
        try:
            tmp = _path(name) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            _atomic_replace(tmp, _path(name))
        finally:
            _fsunlock(handle)


def mutate(name, fn, default=None):
    """load fresh from disk, apply fn(data), save atomically — cross-process safe."""
    st = _pg_storage()
    if st is not None:
        try:
            # need to intercept to persist dashboard -> config
            if name == "settings":
                # load, apply, then persist manually to keep config sync (PG path bypasses file)
                data = st.load(name, default)
                # _merged_settings already applied on load, work on raw?
                res = fn(data)
                if isinstance(data, dict):
                    _persist_dashboard_to_cfg(data)
                st.save(name, data)
                return res
            return st.mutate(name, fn, default)
        except Exception:
            pass
    with _tlock:
        handle = _fslock()
        try:
            path = _path(name)
            data = default
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    data = default
            res = fn(data)
            if name == "settings" and isinstance(data, dict):
                _persist_dashboard_to_cfg(data)
            tmp = _path(name) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            _atomic_replace(tmp, _path(name))
            return res
        finally:
            _fsunlock(handle)


def touch(name, key, value):
    mutate(name, lambda d: d.__setitem__(key, value) or d, {})
    return value


def append(name, item, key="items"):
    st = _pg_storage()
    if st is not None:
        try:
            return st.append(name, item, key)
        except Exception:
            pass

    def _fn(d):
        d.setdefault(key, []).append(item)
        return None
    mutate(name, _fn, {key: []})


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")