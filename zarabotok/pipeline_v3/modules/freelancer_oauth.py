"""
Freelancer.com OAuth2 authorization flow.
Generates auth URL, handles callback, exchanges code for access_token.
Saves token to state/freelancer_token.json and updates config.json.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import store

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")
TOKEN_PATH = os.path.join(STATE_DIR, "freelancer_token.json")

# OAuth endpoints
AUTH_URL = "https://accounts.freelancer.com/oauth/authorize"
TOKEN_URL = "https://accounts.freelancer.com/oauth/token"
API_BASE = "https://www.freelancer.com/api"

# Scopes needed for project search and bidding
SCOPES = [
    "basic",           # Basic profile info
    "projects",        # Read/write projects
    "bids",            # Read/write bids
    "messages",        # Read/write messages
]


def _load_freelancer_cfg():
    """Load freelancer config from config.json"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f) or {}
            return cfg.get("sources", {}).get("freelancer", {})
    except Exception:
        return {}


def _save_freelancer_cfg(cfg: dict):
    """Update freelancer config in config.json"""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        full = json.load(f)
    full.setdefault("sources", {})["freelancer"] = cfg
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=1)


def generate_auth_url() -> str:
    """Generate OAuth authorization URL with proper scopes."""
    cfg = _load_freelancer_cfg()
    client_id = cfg.get("client_id", "")
    redirect_uri = cfg.get("redirect_uri", "https://127.0.0.1:8765/callback")
    
    if not client_id:
        raise ValueError("client_id not found in config.json sources.freelancer")
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "prompt": "consent",  # Force consent to get refresh_token
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange authorization code for access_token."""
    cfg = _load_freelancer_cfg()
    client_id = cfg.get("client_id", "")
    client_secret = cfg.get("client_secret", "")
    redirect_uri = cfg.get("redirect_uri", "https://127.0.0.1:8765/callback")
    
    if not code or not client_id or not client_secret:
        return {"error": "code, client_id, and client_secret required"}
    
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }).encode()
    
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}


def save_token(token_data: dict):
    """Save token data to state/freelancer_token.json and update config.json"""
    os.makedirs(STATE_DIR, exist_ok=True)
    
    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)
    
    if not access_token:
        raise ValueError("No access_token in response")
    
    # Save to state file
    token_obj = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", " ".join(SCOPES)),
    }
    
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_obj, f, ensure_ascii=False, indent=1)
    
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass
    
    # Update config.json
    cfg = _load_freelancer_cfg()
    cfg["token"] = access_token
    _save_freelancer_cfg(cfg)
    
    print(f"✓ Token saved to {TOKEN_PATH}")
    print(f"✓ Config updated with access_token")
    if refresh_token:
        print(f"✓ Refresh token received (expires_in: {expires_in}s)")


def refresh_access_token() -> bool:
    """Refresh access_token using refresh_token."""
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            token_data = json.load(f)
    except Exception:
        return False
    
    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        return False
    
    cfg = _load_freelancer_cfg()
    client_id = cfg.get("client_id", "")
    client_secret = cfg.get("client_secret", "")
    
    if not client_id or not client_secret:
        return False
    
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            new_token = json.loads(r.read().decode())
        save_token(new_token)
        return True
    except Exception as e:
        print(f"Token refresh failed: {e}")
        return False


# ---- Callback HTTP Server ----

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        print(f"[DEBUG] Callback received: {self.path}")
        if parsed.path == "/callback":
            query = parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            error = query.get("error", [None])[0]
            
            if error:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h1>OAuth Error: {error}</h1>".encode())
                self.server.auth_code = None
                self.server.auth_error = error
            elif code:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <html><body style="font-family: system-ui; text-align: center; padding: 50px;">
                <h1>\u2713 Authorization successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
                """
                self.wfile.write(html.encode("utf-8"))
                self.server.auth_code = code
                self.server.auth_error = None
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_callback_server(port: int = 8765, timeout: int = 120) -> str | None:
    """Run local callback server to receive OAuth redirect."""
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.auth_code = None
    server.auth_error = None
    
    def serve():
        server.serve_forever()
    
    thread = Thread(target=serve, daemon=True)
    thread.start()
    
    print(f"Waiting for OAuth callback on http://127.0.0.1:{port}/callback...")
    print(f"Timeout: {timeout} seconds")
    
    import time
    start = time.time()
    while server.auth_code is None and server.auth_error is None:
        if time.time() - start > timeout:
            server.shutdown()
            print("Timeout waiting for callback")
            return None
        time.sleep(0.5)
    
    server.shutdown()
    
    if server.auth_error:
        print(f"OAuth error: {server.auth_error}")
        return None
    
    return server.auth_code


def main():
    """Main OAuth flow: generate URL, open browser, handle callback, save token."""
    print("=" * 60)
    print("Freelancer.com OAuth2 Authorization")
    print("=" * 60)
    
    cfg = _load_freelancer_cfg()
    if not cfg.get("enabled"):
        print("Freelancer source not enabled in config.json")
        return 1
    
    # Step 1: Generate auth URL
    auth_url = generate_auth_url()
    print(f"\n1. Authorization URL:")
    print(f"   {auth_url}")
    
    # Step 2: Open in browser
    print("\n2. Opening browser for authorization...")
    import webbrowser
    webbrowser.open(auth_url)
    
    # Step 3: Wait for callback
    print("\n3. Waiting for callback...")
    code = run_callback_server()
    
    if not code:
        print("Failed to get authorization code")
        return 1
    
    print(f"   Received code: {code[:20]}...")
    
    # Step 4: Exchange code for token
    print("\n4. Exchanging code for access_token...")
    token_data = exchange_code(code)
    
    if "error" in token_data:
        print(f"Token exchange failed: {token_data['error']}")
        return 1
    
    # Step 5: Save token
    print("\n5. Saving token...")
    save_token(token_data)
    
    print("\n" + "=" * 60)
    print("OAuth flow completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())