"""Финальная разведка каналов: паузы между запросами, ретраи, JSON-отчёт."""
import json
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from modules import http_client as hc

EXISTING = ["frilans", "vorkzavr", "workayte", "llm_jobs", "findwork", "freelance_orders", "freelancersu"]
CONFIRMED = ["freelancechoice", "Koteyka_Freelancer", "theyseeku", "piter_work", "target_jobs", "freelancers_world"]

MORE = [
    "freelance_jobs", "freelancejobs", "freelans_birja", "rabota_dlya_frilansera", "zakaz_rabot",
    "fl_jobs", "freelance_it", "napishi_text", "copywriter_jobs", "text_jobs_ru", "perevod_zakaz",
    "ai_orders", "neur_seti_zakaz", "prompt_orders", "chatgpt_rus_work", "smm_orders",
    "design_orders_daily", "work_for_freelancers_ru", "remote_freelance", "work_online_ru",
    "tgbot_z", "jobs_it_ru", "lica_freelance", "ostrov_zakazov", "freelance_birja",
    "zakazy_frilans", "bpo_work", "freelancers_world", "upwork_ru", "kwork_fre", "webdev_stuff",
    "python_developers_jobs", "python_jobs_ru", "qa_freelance", "frontend_freelance",
    "backend_orders", "devops_jobs", "mobile_dev_jobs", "data_science_freelance", "it_freelance",
    "findwork", "digital_brother", "freelancej", "hr_ai", "rabota_na_udalenke", "gdejob",
    "freten", "frilans_uslugi_vakansii", "theyseeku", "designer_jobs", "smm_freelance",
    "target_jobs", "context_freelance", "seo_freelance_ru", "pr_marketing_jobs", "workzilla_free",
]

MAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TG_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")
SKIP = {"telegram", "kwork", "vk", "tvrg", "site", "сайт", "вк"}


def probe(ch, retries=2):
    for attempt in range(retries + 1):
        try:
            r = hc.client("t.me").get(f"https://t.me/s/{ch}", timeout=20)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(3)
    return None


def analyze(ch):
    html = probe(ch)
    if html is None:
        return {"ch": ch, "alive": False, "reason": "network"}
    posts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]{10,1500}?)</div>', html)
    if not posts:
        return {"ch": ch, "alive": True, "reason": "no posts"}
    texts = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip() for p in posts]
    n_tg, n_mail, tg_users = 0, 0, []
    for t in texts:
        if MAIL_RE.search(t):
            n_mail += 1
        for m in TG_RE.finditer(t):
            u = m.group(1).lower()
            if u not in SKIP:
                n_tg += 1
                tg_users.append(m.group(0))
                break
    dates = re.findall(r'datetime="([^"]+)"', html)
    newest = max(dates)[:10] if dates else "?"
    return {
        "ch": ch, "alive": True, "posts": len(posts),
        "tg_contact": n_tg, "mail": n_mail, "newest": newest,
        "sample": texts[0][:90].replace("\n", " ") if texts else "",
        "users": tg_users[:3],
    }


def main():
    channels = list(dict.fromkeys(EXISTING + CONFIRMED + MORE))
    results = []
    for i, ch in enumerate(channels):
        r = analyze(ch)
        results.append(r)
        flag = "HIT " if (r.get("tg_contact", 0) + r.get("mail", 0) >= 3 and (r.get("newest") or "0000") >= "2026-08-01") else ""
        print(f"[{i+1}/{len(channels)}] {flag}{ch}: alive={r.get('alive')} posts={r.get('posts')} tg={r.get('tg_contact')} mail={r.get('mail')} new={r.get('newest')}"
              + (f" | {r.get('sample')}" if r.get("alive") else f" | {r.get('reason')}"), flush=True)
        time.sleep(2.0)
    with open("state/channel_probe.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("отчёт → state/channel_probe.json")


if __name__ == "__main__":
    main()