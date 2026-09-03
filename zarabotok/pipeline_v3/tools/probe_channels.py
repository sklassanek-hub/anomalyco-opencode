"""Проверка TG-каналов-кандидатов: доступность, активность, доля постов с контактами."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from modules import http_client as hc

CANDIDATES = [
    "freelancetavern", "distantsiya", "freelance_ru", "workathome",
    "finder_vc", "freelancechoice", "zakaz_freelance", "it_freelance",
    "python_jobs_ru", "frontend_freelance", "backend_orders", "qa_freelance",
    "devops_jobs", "mobile_dev_jobs", "data_science_freelance",
    "freten", "frilans_uslugi_vakansii", "theyseeku", "Koteyka_Freelancer",
    "designer_jobs", "smm_freelance", "target_jobs", "context_freelance",
    "seo_freelance_ru", "pr_marketing_jobs", "gdejob", "workzilla_free",
    "digital_brother", "freelancej", "hr_ai", "piter_work", "rabota_na_udalenke",
    "zakazy_frilans", "bpo_work", "freelancers_world", "upwork_ru",
    "kwork_fre", "webdev_stuff", "python_developers_jobs",
]

MAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TG_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")
SKIP = ("telegram", "kwork", "вк", "vk.com", "сайт")

def probe(ch):
    try:
        r = hc.client("t.me").get(f"https://t.me/s/{ch}", timeout=15)
    except Exception as e:
        return None, f"err {type(e).__name__}"
    if r.status_code != 200:
        return None, f"http {r.status_code}"
    posts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]{10,1500}?)</div>', r.text)
    if not posts:
        return None, "no posts"
    texts = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip() for p in posts]
    n_mail = sum(1 for t in texts if MAIL_RE.search(t))
    n_tg = 0
    for t in texts:
        for m in TG_RE.finditer(t):
            if m.group(1).lower() not in ("telegram", "kwork"):
                n_tg += 1
                break
    dates = re.findall(r'datetime="([^"]+)"', r.text)
    newest = max(dates) if dates else "?"
    return (len(posts), n_tg, n_mail, newest, texts[0][:80].replace("\n", " ")), "ok"

results = []
for ch in CANDIDATES:
    data, status = probe(ch)
    if status != "ok":
        results.append((ch, status))
        continue
    total, n_tg, n_mail, newest, sample = data
    flag = "OK " if (n_tg + n_mail >= 3 and newest >= "2026-08-14") else "   "
    results.append((ch, f"{flag}{status} posts={total} tg={n_tg} mail={n_mail} new={newest[:10]} sample={sample[:60]}"))

for r in sorted(results, key=lambda x: (x[1].startswith("OK "), x[0]), reverse=True):
    print(r[0], "|", r[1])