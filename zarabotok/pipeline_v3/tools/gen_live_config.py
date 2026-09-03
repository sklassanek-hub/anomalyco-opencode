"""Сборка sing-box конфига из живых (tg_ok) узлов: парсим исходники, фильтруем по отчётам пробников."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from probe_mixed import parse_link, FILES as MIXED_FILES

OUT = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\config.new.json"
REPORTS = [
    r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\probe_mixed_report.json",
    r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\probe_nodes_report.json",
]
VLESS_LINE = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\tools\subscription.txt"


def collect_nodes():
    nodes = {}
    for f in MIXED_FILES:
        if not os.path.isfile(f):
            continue
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith(("vless://", "hysteria2://", "trojan://", "vmess://", "ss://")):
                    continue
                try:
                    n = parse_link(line)
                except Exception:
                    continue
                if n:
                    nodes[(n["type"], n["server"], n["server_port"])] = n
    with open(VLESS_LINE, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if "18.239.134.69" in line:
                n = parse_link(line.strip())
                if n:
                    nodes[(n["type"], n["server"], n["server_port"])] = n
    return nodes


def main():
    pool = collect_nodes()
    alive = set()
    for rep in REPORTS:
        if not os.path.isfile(rep):
            continue
        data = json.load(open(rep, encoding="utf-8"))
        for r in data.get("results", []):
            if r.get("tg_ok"):
                proto = r.get("proto") or "vless"
                alive.add((proto, r.get("server"), r.get("port")))
    picked = []
    for key in alive:
        if key in pool:
            n = dict(pool[key])
            n["tag"] = f"{n['type']}-{n['server']}:{n['server_port']}"
            picked.append(n)
    cfg = {
        "log": {"level": "info", "timestamp": True, "output": OUT + ".log"},
        "inbounds": [{"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 4067}],
        "outbounds": picked + [
            {"type": "urltest", "tag": "auto", "outbounds": [n["tag"] for n in picked],
             "url": "https://www.gstatic.com/generate_204", "interval": "30s", "tolerance": 50},
            {"type": "direct", "tag": "direct"},
        ],
        "route": {
            "default_domain_resolver": {"server": "local", "strategy": "prefer_ipv4"},
            "rules": [{"ip_cidr": ["127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16"], "outbound": "direct"}],
            "final": "auto",
        },
        "dns": {"servers": [{"type": "local", "tag": "local"}], "final": "local", "strategy": "prefer_ipv4"},
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    print("nodes:", len(picked))
    for n in picked:
        print(" ", n["type"], n["server"], n["server_port"])


if __name__ == "__main__":
    main()