import re

_ALLOWED = re.compile(r"[^A-Za-z0-9_.-]+")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CRED = re.compile(r"(?i)(pass(?:word|wd)?|secret|token|пароль|api[_-]?key|hash)\s*[=:]\s*[^\s,;]+")


def sanitize_filename(url: str, max_len: int = 60) -> str:
    s = _ALLOWED.sub("_", str(url or ""))
    s = re.sub(r"\.\.+", "_", s)
    s = s.strip("_")
    if s.lower() in _RESERVED:
        s = "_" + s
    return (s or "order")[:max_len]


def redact(text: str) -> str:
    s = _CRED.sub(lambda m: m.group(1) + "=***", str(text))
    return _EMAIL.sub(lambda m: "***@" + m.group(0).split("@", 1)[1], s)