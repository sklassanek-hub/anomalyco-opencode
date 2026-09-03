"""Массовая проверка узлов (vless/hysteria2/trojan/vmess/shadowsocks) на доступ к t.me/api.telegram.org."""
import json
import os
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, unquote, urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SINGBOX = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe"
TMP = r"C:\Users\klass\AppData\Local\Temp\opencode\probe"
BATCH = 8
TIMEOUT = 5
FILES = [
    r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\sub_Vless-Reality-White-Lists-Rus-Mobile.txt",
    r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\sub_WHITE-SNI-RU-all.txt",
    r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\sub_BLACK_SS+All_RUS.txt",
]
os.makedirs(TMP, exist_ok=True)


def parse_link(line):
    line = line.strip()
    uri = urlparse(line)
    scheme = uri.scheme
    q = parse_qs(uri.query)
    get = lambda k, d=None: (q.get(k) or [d])[0]
    if scheme == "vless":
        node = {"type": "vless", "server": uri.hostname, "server_port": uri.port or 443, "uuid": uri.username,
                "packet_encoding": "xudp"}
        sec = get("security", "none")
        if sec in ("reality", "tls"):
            tls = {"enabled": True, "server_name": get("sni", uri.hostname),
                   "utls": {"enabled": True, "fingerprint": get("fp", "chrome")}}
            if sec == "reality":
                tls["reality"] = {"enabled": True, "public_key": get("pbk", ""), "short_id": get("sid", "")}
            node["tls"] = tls
        flow = get("flow")
        if flow:
            node["flow"] = flow
        ttype = get("type", "tcp")
        if ttype == "ws":
            node["transport"] = {"type": "ws", "path": get("path", "/")}
            if get("host"):
                node["transport"]["headers"] = {"Host": [get("host")]}
        elif ttype == "grpc":
            node["transport"] = {"type": "grpc", "service_name": get("serviceName", get("path", ""))}
        elif ttype == "httpupgrade":
            node["transport"] = {"type": "httpupgrade", "path": get("path", "/")}
    elif scheme == "hysteria2":
        node = {"type": "hysteria2", "server": uri.hostname, "server_port": uri.port or 443,
                "password": unquote(uri.username or "") or unquote(uri.hostname or "")}
        tls = {"enabled": True, "server_name": get("sni", uri.hostname)}
        if get("insecure", "0") in ("1", "true"):
            tls["insecure"] = True
        node["tls"] = tls
    elif scheme == "trojan":
        node = {"type": "trojan", "server": uri.hostname, "server_port": uri.port or 443,
                "password": unquote(uri.username or "")}
        if get("security", "tls") in ("tls", "reality"):
            tls = {"enabled": True, "server_name": get("sni", uri.hostname),
                   "utls": {"enabled": True, "fingerprint": get("fp", "chrome")}}
            if get("security") == "reality":
                tls["reality"] = {"enabled": True, "public_key": get("pbk", ""), "short_id": get("sid", "")}
            node["tls"] = tls
        if get("type", "tcp") == "ws":
            node["transport"] = {"type": "ws", "path": get("path", "/"), "headers": {"Host": [get("host", uri.hostname)]}}
    elif scheme == "vmess":
        node = {"type": "vmess", "server": uri.hostname, "server_port": uri.port or 443, "uuid": unquote(uri.username or "")}
        if get("security", "none") in ("tls", "reality"):
            tls = {"enabled": True, "server_name": get("sni", uri.hostname),
                   "utls": {"enabled": True, "fingerprint": get("fp", "chrome")}}
            node["tls"] = tls
        if get("type", "tcp") == "ws":
            node["transport"] = {"type": "ws", "path": get("path", "/"), "headers": {"Host": [get("host", uri.hostname)]}}
    elif scheme == "ss":
        node = {"type": "shadowsocks", "server": uri.hostname, "server_port": uri.port or 8388,
                "method": get("method", "chacha20-ietf-poly1305"), "password": unquote(uri.username or "")}
        if get("plugin"):
            node["plugin"] = get("plugin")
    else:
        return None
    return node


def make_conf(node, port, out_path):
    node = dict(node)
    node["tag"] = "main"
    cfg = {
        "log": {"level": "error", "timestamp": False, "output": out_path + ".log"},
        "inbounds": [{"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": port}],
        "outbounds": [node, {"type": "direct", "tag": "direct"}],
        "route": {"final": "main"},
        "dns": {"servers": [{"type": "local", "tag": "local"}], "final": "local", "strategy": "prefer_ipv4"},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)


def curl(port, url, resolve=None):
    cmd = ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code} %{time_total}", "--socks5-hostname",
           f"127.0.0.1:{port}", "--max-time", str(TIMEOUT), url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 5)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR {e}"


def probe_node(i, node, port, results):
    cfg = os.path.join(TMP, f"m{i}.json")
    make_conf(node, port, cfg)
    try:
        p = subprocess.Popen([SINGBOX, "run", "-c", cfg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)
        r1 = curl(port, "https://t.me/")
        r2 = curl(port, "https://api.telegram.org/")
        r3 = curl(port, "https://www.gstatic.com/generate_204")
    finally:
        try:
            p.terminate(); p.wait(timeout=3)
        except Exception:
            try: p.kill()
            except Exception: pass
    ok_tg = r1[:3] in ("200", "301", "302", "307", "308", "403") or r2[:3] in ("200", "301", "302", "307", "308", "403")
    results.append({"i": i, "proto": node["type"], "server": node.get("server"), "port": node.get("server_port"),
                    "t.me": r1, "api": r2, "gstatic": r3, "tg_ok": ok_tg})
    print(f"{'LIVE ' if ok_tg else '---- '}[{i}] {node['type']:10s} {str(node.get('server'))[:28]:30s} t.me={r1:12s} api={r2:12s} gstatic={r3}", flush=True)


def main():
    seen = {}
    for f in FILES:
        if not os.path.isfile(f):
            continue
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(("vless://", "hysteria2://", "trojan://", "vmess://", "ss://")):
                    try:
                        n = parse_link(line)
                    except Exception:
                        continue
                    if n:
                        key = (n["type"], n.get("server"), n.get("server_port"))
                        seen.setdefault(key, n)
    nodes = list(seen.values())
    print(f"уникальных узлов: {len(nodes)}")
    results = []
    for start in range(0, len(nodes), BATCH):
        batch = nodes[start:start + BATCH]
        threads = []
        for k, node in enumerate(batch):
            t = threading.Thread(target=probe_node, args=(start + k, node, 4100 + (start % 4096) + k, results))
            threads.append(t); t.start()
        for t in threads:
            t.join()
    results.sort(key=lambda r: r["i"])
    alive = [r for r in results if r["tg_ok"]]
    with open(r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\probe_mixed_report.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(results), "alive": len(alive), "results": results}, f, ensure_ascii=False, indent=1)
    print(f"\nИТОГО: {len(alive)}/{len(results)} узлов туннелируют Telegram")
    for r in alive:
        print("  LIVE", r["proto"], r["server"], r["port"])


if __name__ == "__main__":
    main()