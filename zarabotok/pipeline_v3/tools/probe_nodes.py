"""Массовая проверка vless-узлов на доступность t.me и api.telegram.org.
Параллельно, батчами по BATCH (порт на узел). Отчёт в tools/probe_nodes_report.json.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3"
SINGBOX = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe"
SUB = os.path.join(BASE, "tools", "subscription.txt")
TMP = r"C:\Users\klass\AppData\Local\Temp\opencode\probe"
BATCH = 8
TIMEOUT = 5

sys.path.insert(0, BASE)
from tools.gen_singbox_config import parse_link  # noqa: E402

os.makedirs(TMP, exist_ok=True)


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


def curl(port, url):
    try:
        r = subprocess.run(
            ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code} %{time_total}", "--socks5-hostname",
             f"127.0.0.1:{port}", "--max-time", str(TIMEOUT), url],
            capture_output=True, text=True, timeout=TIMEOUT + 5)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR {e}"


def probe_node(i, node, port, results):
    cfg = os.path.join(TMP, f"n{i}.json")
    make_conf(node, port, cfg)
    try:
        p = subprocess.Popen([SINGBOX, "run", "-c", cfg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)
        r1 = curl(port, "https://t.me/")
        r2 = curl(port, "https://api.telegram.org/")
        r3 = curl(port, "https://www.gstatic.com/generate_204")
    finally:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    tag = node.get("tag", "?")
    ok_tg = r1.startswith(("200", "301", "302", "307", "308", "403")) or r2.startswith(("200", "301", "302", "307", "308", "403"))
    results.append({
        "i": i, "tag": tag, "server": node.get("server"), "port": node.get("server_port"),
        "t.me": r1, "api.telegram.org": r2, "gstatic": r3, "tg_ok": ok_tg,
    })
    flag = "LIVE " if ok_tg else "---- "
    print(f"{flag}[{i}] {tag[:40]:42s} t.me={r1:14s} api={r2:14s} gstatic={r3}", flush=True)


def main():
    with open(SUB, encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip().startswith("vless://")]
    nodes = []
    for l in lines:
        n = parse_link(l)
        if n:
            n["tag"] = os.path.basename(SUB) + f"#{len(nodes)}"
            nodes.append(n)
    print(f"узлов: {len(nodes)}")
    results = []
    base_port = 4100
    for start in range(0, len(nodes), BATCH):
        batch = nodes[start:start + BATCH]
        threads = []
        for k, node in enumerate(batch):
            t = threading.Thread(target=probe_node, args=(start + k, node, base_port + (start % 4096) + k, results))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    results.sort(key=lambda r: r["i"])
    alive = [r for r in results if r["tg_ok"]]
    with open(os.path.join(BASE, "tools", "probe_nodes_report.json"), "w", encoding="utf-8") as f:
        json.dump({"total": len(results), "alive": len(alive), "results": results}, f, ensure_ascii=False, indent=1)
    print(f"\nИТОГО: {len(alive)}/{len(results)} узлов туннелируют Telegram")
    for r in alive:
        print("  LIVE", r["server"], r["tag"][:50])


if __name__ == "__main__":
    main()