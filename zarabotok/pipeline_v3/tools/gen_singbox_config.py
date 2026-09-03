"""Generate sing-box config from a vless:// subscription file (igareck style)."""
import json
import sys
from urllib.parse import parse_qs, unquote, urlparse

INBOUND_SOCKS = {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 4067, "users": []}

DNS = {
    "servers": [
        {"type": "local", "tag": "local"},
        {"type": "udp", "tag": "remote", "server": "8.8.8.8", "server_port": 53, "detour": "auto"},
    ],
    "rules": [
        {"domain_suffix": ["t.me", "telegram.org", "telegram.me", "web.telegram.org"], "server": "remote"},
        {"query_type": ["A", "AAAA"], "server": "remote", "disable_cache": True},
    ],
    "final": "remote",
    "strategy": "prefer_ipv4",
}


def parse_link(line: str):
    uri = urlparse(line.strip())
    if uri.scheme != "vless":
        return None
    host = uri.hostname
    port = uri.port or 443
    uuid = uri.username
    q = parse_qs(uri.query)
    get = lambda k, d=None: (q.get(k) or [d])[0]
    name = unquote(uri.fragment or "") or f"{host}:{port}"
    out = {
        "type": "vless",
        "tag": name,
        "server": host,
        "server_port": port,
        "uuid": uuid,
        "packet_encoding": "xudp",
    }
    sec = get("security", "none")
    fp = get("fp", "firefox")
    sni = get("sni", host)
    if sec in ("reality", "tls"):
        tls = {"enabled": True, "server_name": sni, "utls": {"enabled": True, "fingerprint": fp}}
        alpn = get("alpn")
        if alpn:
            tls["alpn"] = [a for a in alpn.split(",") if a]
        if sec == "reality":
            tls["reality"] = {
                "enabled": True,
                "public_key": get("pbk", ""),
                "short_id": get("sid", ""),
            }
        out["tls"] = tls
    flow = get("flow")
    if flow:
        out["flow"] = flow
    ttype = get("type", "tcp")
    if ttype == "ws":
        out["transport"] = {"type": "ws", "path": get("path", "/")}
        host_h = get("host")
        if host_h:
            out["transport"]["headers"] = {"Host": [host_h]}
    elif ttype == "grpc":
        out["transport"] = {"type": "grpc", "service_name": get("serviceName", get("path", ""))}
    elif ttype == "httpupgrade":
        out["transport"] = {"type": "httpupgrade", "path": get("path", "/")}
    return out


def main() -> int:
    sub_path, out_path = sys.argv[1], sys.argv[2]
    nodes = []
    with open(sub_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("vless://"):
                node = parse_link(line)
                if node:
                    nodes.append(node)
    if not nodes:
        print("no nodes parsed")
        return 1
    tags = []
    for n in nodes:
        base = n["tag"]
        tag, idx = base, 1
        while tag in tags:
            idx += 1
            tag = f"{base} #{idx}"
        tags.append(tag)
        n["tag"] = tag
    config = {
        "log": {"level": "info", "timestamp": True, "output": str(out_path) + ".log"},
        "dns": DNS,
        "inbounds": [INBOUND_SOCKS],
        "outbounds": nodes
        + [
            {"type": "direct", "tag": "direct"},
            {
                "type": "urltest",
                "tag": "auto",
                "outbounds": tags,
                "url": "https://www.gstatic.com/generate_204",
                "interval": "3m0s",
                "tolerance": 300,
            },
        ],
        "route": {
            "default_domain_resolver": {"server": "remote", "strategy": "prefer_ipv4"},
            "rules": [
                {"domain_suffix": ["getsavesafe.net"], "outbound": "direct"},
                {"ip_cidr": ["127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16"], "outbound": "direct"},
            ],
            "final": "auto",
        },
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=1)
    print(f"parsed {len(nodes)} nodes -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())