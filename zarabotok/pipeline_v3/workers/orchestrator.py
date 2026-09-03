import json
import sys
import time

sys.path.insert(0, ".")

from modules import matcher, proposals, scanners as sc, store  # noqa: E402

INTERVAL = 60 * 5
EMBED_TOP = 40  # эмбеддинг-буст только для топа по light_score (экономия LLM)


def _load_cfg():
    try:
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _light_score(j: dict, skills: list) -> float:
    """Лёгкий релевантный скор без LLM (контроль нагрузки)."""
    s = 1.0
    text = ((j.get("title") or "") + " " + (j.get("description") or "")).lower()
    if skills:
        hits = sum(1 for kw in skills if kw and kw.lower() in text)
        s += min(hits, 5) * 0.5
    b = (j.get("budget") or "").lower()
    if any(c.isdigit() for c in b):
        s += 1.0
    if "срочно" in text or "urgent" in text:
        s += 0.5
    return round(s, 2)


def main() -> int:
    print(f"orchestrator v3 start, interval {INTERVAL}s", flush=True)
    cfg = _load_cfg()
    skills = [s for s in (cfg.get("skills") or []) if isinstance(s, str)]
    while True:
        try:
            jobs = store.load("jobs", {"items": []}).get("items", [])
            today = time.strftime("%Y-%m-%d")
            orders = [j for j in jobs if j.get("scanned_at", "").startswith(today)
                      and sc.kind_of(j) == "order"]
            # fl_scan_only: FL не откликаемся — исключаем из пула драфтов
            if cfg.get("sources", {}).get("fl_scan_only"):
                orders = [j for j in orders if (j.get("source") or "") != "FL"
                          and "fl.ru" not in (j.get("url") or "")]
            for j in orders:
                if not j.get("score"):
                    j["score"] = _light_score(j, skills)
            # ограничиваем партию драфтов топом по score (контроль нагрузки на ПК/LLM)
            fresh = sorted(orders, key=lambda x: x.get("score", 0), reverse=True)[:10]
            # ---- embedding-буст релевантности (M2 по ТЗ): топ-40 прогоняем через nomic
            try:
                anchors = {}
                for j in sorted(orders, key=lambda x: x.get("score", 0), reverse=True)[:EMBED_TOP]:
                    txt = ((j.get("title") or "") + " " + (j.get("description") or ""))[:800]
                    boost = matcher.skill_boost(txt, skills, anchors_cache=anchors)
                    if boost:
                        j["score"] = round(float(j.get("score", 0)) + 2.5 * boost, 2)
                if anchors:
                    del anchors
            except Exception:
                pass
            # Тяжёлый LLM-пайплайн агентов отключён в free-фазе (контроль нагрузки):
            # черновики генерит proposals.build_outbox (шаблон + топ-N LLM).
            ar = {"processed": len(fresh), "scam": 0, "dup": 0, "drafts": 0, "contact": 0}
            drafts = proposals.build_outbox(fresh, max_revise=0, llm_top_n=3)
            print(f"orchestrator: fresh={len(fresh)} агенты={ar.get('processed')} "
                  f"drafts={drafts}", flush=True)
            time.sleep(5)  # пауза после пакета драфтов — охлаждение ПК/LLM
            pending = store.load("outbox", {"items": []}).get("items", [])
            unapproved = sum(1 for x in pending if not x.get("approved"))
            print(f"orchestrator: fresh={len(fresh)} черновиков={drafts} "
                  f"outbox_total={len(pending)} unapproved={unapproved}", flush=True)
        except Exception as e:
            print(f"orchestrator error: {e}", flush=True)
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())