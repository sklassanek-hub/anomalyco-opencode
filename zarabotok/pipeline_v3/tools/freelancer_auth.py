"""
Freelancer.com OAuth2 авторизация + API сканер заказов.
Регистрация: https://developers.freelancer.com/
Scopes: basic projects bids users jobs
Redirect URI: https://127.0.0.1:8765/callback
"""
import urllib.parse, urllib.request, json, os, sys

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json")

CLIENT_ID = "ecf7fe17-3c6e-4a59-aa86-10d889f4c948"
CLIENT_SECRET = "9a0075dd64d1ffdfc25da5827006bc7ea877a3d035f12888ce8c70da1aad2f7e625f3b25b6e71a28fac0f157e8c6bdb630c6dec358e143718f52791ffcf49aeb"
REDIRECT_URI = "https://127.0.0.1:8765/callback"
API_BASE = "https://www.freelancer.com/api"

def get_auth_url():
    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "basic projects bids users jobs"
    })
    return f"https://accounts.freelancer.com/oauth/authorize?{urllib.parse.urlencode(params)}"

def exchange_code(code):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def save_token(access_token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            t = json.load(f).get("access_token", "").strip()
            if t:
                return t
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

def save_token(access_token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass

def exchange_code(code):
    if not code or not CLIENT_ID:
        return {"error": "code and client_id required"}
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }).encode()
    req = urllib.request.Request(
        "https://accounts.freelancer.com/oauth/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}

def save_token(access_token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass

def get_token():
    # 1) state/freelancer_token.json
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            t = json.load(f).get("access_token", "").strip()
            if t:
                return t
    except Exception:
        pass
    # 2) config.json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            t = cfg.get("freelancer", {}).get("token", "").strip()
            if t:
                return t
    except Exception:
        pass
    return None

def save_token(access_token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass

# Конфиг
import os, json, urllib.parse, urllib.request, urllib.request, json, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json")

CLIENT_ID = "ecf7fe17-3c6e-4a59-aa86-10d889f4c948"
CLIENT_SECRET = "9a0075dd64d1ffdfc25da5827006bc7ea877a3d035f12888ce8c70da1aad2f7e625f3b25b6e71a28fac0f157e8c6bdb630c6dec358e143718f52791ffcf49aeb"
REDIRECT_URI = "https://127.0.0.1:8765/callback"
API_BASE = "https://www.freelancer.com/api"