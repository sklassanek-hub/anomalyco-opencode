"""
Freelancer.com API scanner.
OAuth2 авторизация + сбор проектов через официальный API.
"""
import json
import os
import urllib.parse
import urllib.request
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import http_client as hc

# Конфигурация из config.json
def _load_freelancer_cfg():
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"), encoding="utf-8") as f:
            cfg = json.load(f) or {}
            return cfg.get("freelancer", {})
    except Exception:
        return {}

# --- OAuth2 helpers ---

FL_CLIENT_ID = os.getenv("FL_CLIENT_ID") or ""
FL_CLIENT_SECRET = os.getenv("FL_CLIENT_SECRET") or ""
FL_REDIRECT_URI = os.getenv("FL_REDIRECT_URI", "https://127.0.0.1:8765/callback")
FL_TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json")
API_BASE = "https://www.freelancer.com/api"

def _load_token():
    """Читает токен из state/freelancer_token.json или config.json"""
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            data = json.load(f)
            token = data.get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
            token = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None

def _save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """Обмен code -> access_token."""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
            token = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """Обмен code -> access_token."""
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if t:
                return t
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            token = json.load(f).get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = (cfg.get("freelancer", {}) or {}).get("token", "").strip()
            if t:
                return t
    except Exception:
        pass
    return None

def save_token(access_token: str):
    os.makedirs(os.path.dirname(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), 0o600)
    except Exception:
        pass

# ... дубликат кода удален ...