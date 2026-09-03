import json
import os
import sys
import time

sys.path.insert(0, ".")

from modules import sender  # noqa: E402


def auto_send_enabled() -> bool:
    try:
        with open("config.json", encoding="utf-8") as f:
            return bool(json.load(f).get("sender", {}).get("auto_send", False))
    except Exception:
        return False


INTERVAL = 60


def main() -> int:
    if not auto_send_enabled():
        print("sender v3: автоотправка отключена (auto_send=false) — сплю до включения", flush=True)
        while True:
            time.sleep(3600)
    print("sender v3 start (только одобренные отклики)", flush=True)
    while True:
        try:
            sent = sender.run_cycle()
            if sent:
                print(f"sender: sent {sent}", flush=True)
            else:
                print("sender: пусто", flush=True)
        except Exception as e:
            print(f"sender error: {e}", flush=True)
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())