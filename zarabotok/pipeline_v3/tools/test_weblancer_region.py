import subprocess, json, os, time
SINGBOX=r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe"
TMP=r"C:\Users\klass\AppData\Local\Temp\opencode\probe_weblancer"
os.makedirs(TMP,exist_ok=True)
# загрузим живые узлы из config.json
import json as j
cfg=j.load(open(r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\config.json",encoding="utf-8"))
nodes=[o for o in cfg["outbounds"] if o["type"] in ("hysteria2","vless")]
print(f"nodes {len(nodes)}")
for idx, node in enumerate(nodes[:6]):
    port=4200+idx
    node2=dict(node); node2["tag"]="main"
    conf={"log":{"level":"error"},"inbounds":[{"type":"socks","tag":"socks-in","listen":"127.0.0.1","listen_port":port}],"outbounds":[node2,{"type":"direct","tag":"direct"}],"route":{"final":"main"},"dns":{"servers":[{"type":"local","tag":"local"}],"final":"local"}}
    path=os.path.join(TMP,f"c{idx}.json")
    open(path,"w",encoding="utf-8").write(j.dumps(conf))
    p=subprocess.Popen([SINGBOX,"run","-c",path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    try:
        r=subprocess.run(["curl.exe","-s","-o","NUL","-w","%{http_code}","--socks5-hostname",f"127.0.0.1:{port}","--max-time","12","https://www.weblancer.net/login/"], capture_output=True, text=True, timeout=15)
        print(f"{node['server']}:{node['server_port']} -> {r.stdout.strip()}")
    except Exception as e:
        print(e)
    finally:
        try: p.terminate(); p.wait(timeout=3)
        except: p.kill()
