"""Разведка 2: детальный просмотр живых кандидатов + вторая партия каналов с именами из каталогов."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from modules import http_client as hc

SECOND = [
    "freelance_jobs", "freelancejobs", "freelans_birja", "rabota_dlya_frilansera",
    "freelance_rabota", "zakaz_rabot", "fl_jobs", "freelance_it",
    "napishi_text", "copywriter_jobs", "kопирайт", "text_jobs_ru", "perevod_zakaz",
    "ai_orders", "neur_seti_zakaz", "prompt_orders", "chatgpt_rus_work",
    "smm_orders", "design_orders_daily", "work_for_freelancers_ru",
    "freelance_union", "ffr_habr", "remote_freelance", "work_online_ru",
    "tgbot_z", "jobs_it_ru", "lica_freelance", "ostrov_zakazov", "бюро_заказов",
]

MAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TG_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")

def probe(ch):
    try:
        r = hc.client("t.me").get(f"https://t.me/s/{ch}", timeout=15)
    except Exception as e:
        return None, f"err-{type(e).__name__}"
    if r.status_code != 200:
        return None, f"http-{r.status_code}"
    posts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]{10,1500}?)</div>', r.text)
    if not posts:
        return None, "no-posts"
    texts = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip() for p in posts]
    n_mail = sum(1 for t in texts if MAIL_RE.search(t))
    n_tg = 0
    tg_users = []
    for t in texts:
        m = TG_RE.search(t)
        if m and m.group(1).lower() not in ("telegram",):
            n_tg += 1
            tg_users.append(m.group(0))
    dates = re.findall(r'datetime="([^"]+)"', r.text)
    newest = max(dates)[:10] if dates else "?"
    return (len(posts), n_tg, n_mail, newest, texts[0][:70].replace("\n", " ") if texts else ""), "ok"

rows = []
for ch in SECOND:
    data, status = probe(ch)
    if status != "ok":
        rows.append((ch, "dead " + status))
        continue
    total, n_tg, n_mail, newest, sample = data
    hot = "CONTACT" if (n_tg + n_mail >= 3 and newest >= "2026-08-01") else ("warm" if newest >= "2026-08-01" else "old")
    rows.append((ch, f"{hot} posts={total} tg={n_tg} mail={n_mail} new={newest} sample={sample[:60]}"))

for r in sorted(rows, key=lambda x: (x[1].startswith("CONTACT") is False, x[1].split()[0])):
    print(r[0], "|", r[1])