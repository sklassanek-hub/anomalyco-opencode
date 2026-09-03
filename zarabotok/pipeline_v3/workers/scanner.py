import sys
import time

sys.path.insert(0, ".")

from modules import ranker, scanners, store  # noqa: E402

INTERVAL = 60 * 15


def main() -> int:
    print(f"scanner v3 start, interval {INTERVAL}s", flush=True)
    while True:
        try:
            habr_ids = store.load("habr_ids", {}).get("ids", [])
            jobs, errors = scanners.scan_all(include_tg=True, habr_ids=habr_ids)
            new = ranker.rank_and_store(jobs, min_score=0, contact_only=False)
            by_p = {}
            for j in jobs:
                by_p[j.get("platform", "?")] = by_p.get(j.get("platform", "?"), 0) + 1
            store.save("last_scan", {"ts": store.now(), "total": len(jobs),
                          "errors": [str(e)[:120] for e in errors]})
            print(f"scanned: total={len(jobs)} new={len(new)} platforms={by_p} errors={len(errors)}", flush=True)
            if errors:
                print("errors:", errors, flush=True)
        except Exception as e:
            print(f"scan error: {e}", flush=True)
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())