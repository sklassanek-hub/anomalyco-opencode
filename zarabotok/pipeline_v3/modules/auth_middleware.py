"""
Auth middleware — P0 full stub (from backend_arch_review.md §7.1, §7.2).
- Token validation (env PIPELINE_AUTH_TOKEN + Bearer header).
- Structured audit log (ts, actor, action, resource, result, detail) -> events.json via kill_switch.
- Rate-limit decorator @rate_limit(max_calls=10, window=60).
- Wire into executor.py start (see module import + init guard).
References: kill_switch.py (write_event, audit_delivery), sd_review.md §6.
"""
import os
import time
import logging
import functools
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

EXPECTED_TOKEN = os.getenv("PIPELINE_AUTH_TOKEN")

# ---------- Rate-limit decorator ----------
_rate_windows: Dict[str, list] = {}

def rate_limit(max_calls: int = 10, window: int = 60):
    """In-memory sliding-window rate limiter. Key derived from func+first-arg id."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__name__}:{id(args[0]) if args else 'global'}"
            now = time.time()
            window_start = now - float(window)
            _rate_windows.setdefault(key, [])
            _rate_windows[key] = [t for t in _rate_windows[key] if t > window_start]
            if len(_rate_windows[key]) >= max_calls:
                audit_event(
                    "system", "rate_limit", func.__name__, "blocked",
                    {"max_calls": max_calls, "window": window, "key": key}
                )
                raise PermissionError(
                    f"Rate limit exceeded: {max_calls} calls per {window}s (key={key})"
                )
            _rate_windows[key].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ---------- Audit log (structured + events.json integration) ----------

def audit_event(actor: Optional[str], action: str, resource: str,
                result: str, detail: Optional[Any] = None) -> Dict[str, Any]:
    """Structured audit event per kill_switch.py / sd_review §3.4, §5.7."""
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actor": actor or "unknown",
        "action": action,
        "resource": resource,
        "result": result,
        "detail": detail,
        "source": "modules/auth_middleware.py",
        "auth_version": "stub-v1",
    }
    logger.info("AUDIT %s", event)
    # Append to pipeline audit file (same schema as kill_switch.py write_event)
    try:
        from modules import kill_switch as ks
        ks.write_event(event)
    except Exception as e:
        logger.warning("auth_middleware: could not append to events.json: %s", e)
    return event

# ---------- Token validation ----------

def validate_token(token: Optional[str]) -> bool:
    if not EXPECTED_TOKEN:
        audit_event("system", "token_check", "auth_middleware", "blocked",
                  "PIPELINE_AUTH_TOKEN missing in env")
        return False
    if not token or not isinstance(token, str):
        audit_event("unknown", "token_check", "auth_middleware", "blocked",
                  {"reason": "missing_or_non_string"})
        return False
    # Normalize: strip whitespace and Bearer prefix if present
    cleaned = token.strip()
    if cleaned.startswith("Bearer "):
        cleaned = cleaned[len("Bearer "):].strip()
    if cleaned != EXPECTED_TOKEN:
        audit_event("unknown", "token_check", "auth_middleware", "blocked",
                  {"reason": "token_mismatch", "token_length": len(cleaned)})
        return False
    audit_event("request", "token_check", "auth_middleware", "allowed",
              {"token_length": len(cleaned)})
    return True

# ---------- Middleware ----------

class AuthMiddleware:
    """WSGI/ASGI-style middleware with token validation + audit + rate limit."""

    def __init__(self, app=None):
        self.app = app

    @rate_limit(max_calls=10, window=60)
    def __call__(self, environ, start_response):
        # Extract token from headers
        token = (
            environ.get("HTTP_X_PIPELINE_AUTH_TOKEN")
            or environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "").strip()
        )
        if not validate_token(token):
            # Block with audit already written
            start_response("401 Unauthorized", [("Content-Type", "text/plain")])
            return [b"Invalid or missing auth token (audit logged)"]
        # Allowed — audit success already in validate_token
        audit_event("request", "auth_check", "middleware", "allowed",
                  {"resource_path": environ.get("PATH_INFO", "/")})
        if self.app:
            return self.app(environ, start_response)
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"Auth OK (stub with validation + audit + rate_limit)"]

# ---------- Role stub (server-side) ----------

def require_role(role: Optional[str] = None,
                 allowed: Optional[list] = None) -> bool:
    allowed = allowed or ["admin", "operator", "viewer"]
    # TODO: enforce against server-side session / JWT claims (per sd_review §6)
    # Do NOT encode role only in localStorage (Layout.tsx gap)
    audit_event("system", "require_role", "auth_middleware", "allowed",
              {"requested_role": role, "allowed": allowed})
    return True

# ---------- Wire into executor start ----------
# Import guard for pipeline startup; validates env token presence.
# Called by executor.py at module load (see bottom of module).

def init_auth_guard() -> bool:
    """Called at pipeline/executor start to enforce token presence."""
    if not EXPECTED_TOKEN:
        audit_event("system", "init_auth_guard", "executor_start", "blocked",
                  "PIPELINE_AUTH_TOKEN not set — pipeline authentication disabled")
        logger.error("auth_middleware.init_auth_guard: PIPELINE_AUTH_TOKEN missing")
        return False
    audit_event("system", "init_auth_guard", "executor_start", "allowed",
              {"token_configured": True, "token_length": len(EXPECTED_TOKEN) if EXPECTED_TOKEN else 0})
    return True

# Auto-run guard on import if executed as module (not import-only)
if __name__ != "__main__" and os.getenv("PIPELINE_AUTH_TOKEN") is not None:
    try:
        init_auth_guard()
    except Exception as e:
        logger.warning("auth_middleware: init guard exception: %s", e)
