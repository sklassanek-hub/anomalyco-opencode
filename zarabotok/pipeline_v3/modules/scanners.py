"""Сканеры v2: FL, freelance.ru, TG-каналы (веб + Telethon API), habr-деталки, weworkremotely."""
import asyncio
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modules import http_client as hc
from modules import tg_scrape

TG_CHANNELS = ("frilans", "vorkzavr", "workayte", "findwork", "freelance_orders", "freelancersu",
    "freelance_jobs_tg", "zakaz_freelance", "easy_freelance", "workathome", "remote_ru",
    "distantsiya2", "webfrl", "rabota_freelancee", "theyseeku_it", "noexperience",
    "digital_jobster", "rabota_go",
    "designers_freelance", "figma_jobs", "web_design_orders", "ux_ui_freelance",
    "tilda_freelance", "designer_jobs", "motion_graphics_jobs", "illustrators_ru", "3d_freelance",
    "job_freelancer", "game_dev_jobs")
TG_API_CHANNELS = ("frilanse", "birza_sz", "ProjectAutocad", "freelancechoice", "Koteyka_Freelancer", "freelance_chat_ru", "llm_jobs", "digitalrabota",
    "pro_freelance", "freelance_help", "remote_jobs_ru",
    "freelancetavern", "distantsiya", "freelance_ru", "finder_vc", "creatives_hunt", "design_hunter",
    "freelance_antispam", "er_freelance")
VACANCY_PLATFORMS = {"Habr", "WeWorkRemotely", "TG:findwork", "TG:llm_jobs", "TG:theyseeku_it", "TG:noexperience"}

CONTACT_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")
SKIP_CONTACTS = {
    "telegram", "kwork", "gotoisland", "devkg", "findwork", "llm_jobs",
    "freelance_orders", "frilans", "vorkzavr", "workayte", "freelancersu", "bot",
    "webfrl", "workathome", "remote_ru", "remote_jobs_ru", "zakaz_freelance",
    "easy_freelance", "distantsiya", "distantsiya2", "finder_vc", "figma_jobs",
    "designers_freelance", "tilda_freelance", "freelance_jobs_tg", "theyseeku_it",
    "noexperience", "web_design_orders", "ux_ui_freelance", "motion_graphics_jobs",
    "illustrators_ru", "designer_jobs", "3d_freelance", "digital_jobster",
    "rabota_freelancee", "rabota_go", "creatives_hunt", "design_hunter",
    "freelancetavern", "freelance_ru", "freelance_antispam", "er_freelance",
}


def find_contact(text: str) -> str | None:
    return tg_scrape.contact_of(text)


def kind_of(job: dict) -> str:
    if job.get("kind"):
        return job["kind"]
    return "vacancy" if job.get("platform") in VACANCY_PLATFORMS else "order"

FL_URL = "https://www.fl.ru/projects/"
FR_URL = "https://freelance.ru/project/search/"
HABR_BASE = "https://career.habr.com"
WR_URL = "https://weworkremotely.com/remote-jobs"
WL_URL = "https://www.weblancer.net/projects/"
KWORK_URL = "https://kwork.ru/projects"

RE_TAG = re.compile(r"<[^>]+>")
RE_WS = re.compile(r"\s+")


def _clean(s: str) -> str:
    return RE_WS.sub(" ", RE_TAG.sub("", s or "")).strip()


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def scan_fl() -> list:
    out = []
    r = hc.client("fl.ru").get(FL_URL, timeout=25)
    if r.status_code != 200:
        return out
    for block in re.split(r'class="b-post__grid', r.text)[1:]:
        m = re.search(r'href="/projects/(\d+)/[^"]*"[^>]*>\s*([^<]{4,150})</a>', block)
        if not m:
            continue
        price_m = re.search(r"price[^>]*>\s*<[^>]*>\s*([^<]{2,80})", block)
        desc_m = re.search(r"b-post__txt[^>]*>\s*([\s\S]{20,600}?)</div>", block)
        out.append({
            "platform": "FL",
            "kind": "order",
            "job_id": f"fl:{m.group(1)}",
            "url": f"https://www.fl.ru/projects/{m.group(1)}/",
            "title": _clean(m.group(2)),
            "description": _clean(desc_m.group(1))[:400] if desc_m else "",
            "budget": _clean(price_m.group(1)) if price_m else "",
            "author": "",
            "scanned_at": _now(),
        })
    fl_details(out)
    return out


def fl_details(jobs: list) -> None:
    s = hc.client("fl.ru")
    for j in jobs[:10]:
        try:
            r = s.get(j["url"], timeout=20)
            if r.status_code != 200:
                continue
            m = re.search(r'href="/users/([^"]+)"', r.text)
            if m:
                j["author"] = m.group(1)
            if not j["description"]:
                d = re.search(r'<div[^>]*class="[^"]*b-ph__txt[^"]*"[^>]*>([\s\S]{20,900}?)<', r.text)
                if d:
                    j["description"] = _clean(d.group(1))[:400]
        except Exception:
            pass


def scan_fl_rss() -> list:
    """Официальный RSS-фид fl.ru: свежие заказы всех категорий + контакт из описания."""
    out = []
    r = hc.client("fl.ru").get("https://www.fl.ru/rss/all.xml", timeout=25)
    if r.status_code != 200:
        return out
    for item in re.split(r"<item>", r.text)[1:]:
        t = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item, re.S)
        l = re.search(r"<link>(.*?)</link>", item)
        d = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item, re.S)
        if not t or not l:
            continue
        m = re.search(r"/projects/(\d+)/", l.group(1))
        if not m:
            continue
        desc = _clean(d.group(1))[:500] if d else ""
        out.append({
            "platform": "FL", "kind": "order",
            "job_id": f"fl:{m.group(1)}",
            "url": f"https://www.fl.ru/projects/{m.group(1)}/",
            "title": _clean(t.group(1))[:140],
            "description": desc,
            "budget": "", "author": "",
            "contact": find_contact((t.group(1) or "") + " " + desc),
            "scanned_at": _now(),
        })
    return out


def scan_gh_bounty() -> list:
    """GitHub issues с меткой bounty — оплачиваемые задачи (заказы с наградой)."""
    out = []
    r = hc.client("api.github.com").get(
        "https://api.github.com/search/issues"
        "?q=label:bounty+state:open+type:issue&sort=created&per_page=30",
        timeout=25)
    if r.status_code != 200:
        return out
    for it in r.json().get("items", []):
        body = it.get("body") or ""
        m = re.search(r"\$\s?(\d[\d,]{2,})", body)
        budget = ("$" + m.group(1)) if m else ""
        out.append({
            "platform": "GitHub", "kind": "order",
            "job_id": f"gh:{it['id']}",
            "url": it["html_url"],
            "title": (it.get("title") or "")[:140],
            "description": re.sub(r"\s+", " ", body)[:500],
            "budget": budget,
            "author": (it.get("user") or {}).get("login", ""),
            "contact": "",
            "scanned_at": _now(),
        })
    return out


def scan_fr() -> list:
    out = []
    r = hc.client("freelance.ru").get(FR_URL, timeout=25)
    if r.status_code != 200:
        return out
    for block in re.split(r'class="task-card"', r.text)[1:]:
        m = re.search(r'href="(/task/view/\d+)"[^>]*>\s*([\s\S]{5,200}?)</a>', block)
        if not m:
            continue
        price_m = re.search(r"\d[\d\s]{1,6}\s*(?:₽|руб(?:лей)?)|Стоимость[^<]{0,40}", block)
        author_m = re.search(r'href="/(?:users?|u)/[^"]*"[^>]*>\s*([^<]{2,60})<', block)
        desc_m = re.search(r'<p[^>]*>([\s\S]{20,400}?)</p>', block)
        out.append({
            "platform": "freelance.ru",
            "kind": "order",
            "job_id": f"fr:{m.group(1).rsplit('/', 1)[-1]}",
            "url": "https://freelance.ru" + m.group(1),
            "title": _clean(m.group(2))[:140],
            "description": _clean(desc_m.group(1))[:300] if desc_m else "",
            "budget": _clean(price_m.group(0)) if price_m else "",
            "author": _clean(author_m.group(1)) if author_m else "",
            "scanned_at": _now(),
        })
    return out


def scan_tg(channel: str) -> list:
    out = []
    r = hc.client("t.me").get(f"https://t.me/s/{channel}", timeout=15)
    if r.status_code != 200:
        return out
    for m in re.finditer(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]{10,1200}?)</div>', r.text):
        text = _clean(m.group(1))
        if not text:
            continue
        out.append({
            "platform": "TG:" + channel,
            "kind": "vacancy" if channel in ("findwork", "llm_jobs") else "order",
            "job_id": f"tg:{channel}:{len(out)}",
            "url": f"https://t.me/s/{channel}",
            "title": text[:110],
            "description": text[:400],
            "budget": "",
            "author": "",
            "contact": find_contact(text),
            "scanned_at": _now(),
        })
    return out[:12]


def scan_habr(ids: list) -> list:
    out = []
    s = hc.client("habr.com")
    for jid in ids[:30]:
        try:
            r = s.get(f"{HABR_BASE}/vacancies/{jid}", timeout=20)
            if r.status_code != 200 or "Ошибка 404" in r.text:
                continue
            t = r.text
            h1 = re.search(r"<h1[^>]*>([^<]{3,180})</h1>", t)
            og = re.search(r'twitter:title" content="([^"]+)"', t)
            title = _clean(h1.group(1)) if h1 else (_clean(og.group(1)) if og else "")
            if not title or title.lower().startswith("вакансия в городе") or title.lower().startswith("вакансия ,"):
                continue
            comp = re.search(r"компании «([^»]+)»", t)
            sal = re.search(r'basic-salary[^>]*>([^<]{2,80})<', t)
            desc = re.search(r'<div class="vacancy-description__text"[^>]*>([\s\S]{30,800}?)</div>', t)
            out.append({
                "platform": "Habr",
                "kind": "vacancy",
                "job_id": f"habr:{jid}",
                "url": f"{HABR_BASE}/vacancies/{jid}",
                "title": title[:120],
                "description": (_clean(desc.group(1))[:400] if desc else "") or "",
                "budget": _clean(sal.group(1)) if sal else "",
                "author": comp.group(1) if comp else "",
                "scanned_at": _now(),
            })
        except Exception:
            continue
    return out


def scan_wr() -> list:
    out = []
    r = hc.client("weworkremotely.com").get(WR_URL, timeout=25)
    if r.status_code != 200:
        return out
    for m in re.finditer(r'<li class="[^"]*new-listing[^"]*"', r.text):
        seg = r.text[m.start() : m.start() + 2500]
        job_m = re.search(r'href="(/remote-jobs/[^"]+)"', seg)
        aria = re.search(r'aria-label="([^"]+)"', seg)
        if not job_m:
            continue
        label = aria.group(1) if aria else ""
        title, company = label, ""
        if " is hiring a remote " in label:
            company, title = label.split(" is hiring a remote ", 1)
            title = title.replace(" at We Work Remotely", "").replace(".", "")
        out.append({
            "platform": "WeWorkRemotely",
            "kind": "vacancy",
            "job_id": f"wr:{job_m.group(1).rstrip('/').rsplit('/', 1)[-1] or len(out)}",
            "url": "https://weworkremotely.com" + job_m.group(1),
            "title": _clean(title)[:110],
            "description": "",
            "budget": "",
            "author": _clean(company),
            "scanned_at": _now(),
        })
    return out[:15]


def scan_wl() -> list:
    out = []
    r = hc.client("weblancer.net").get(WL_URL, timeout=25)
    if r.status_code != 200:
        return out
    text = r.text
    parts = text.split('href="/freelance/')[1:]
    for p in parts:
        url_end = p.split('">', 1)
        if len(url_end) < 2:
            continue
        path = url_end[0]
        title = _clean(url_end[1].split("</a>", 1)[0])
        jid = re.search(r"-(\d+)/(-)?$", path)
        if len(path) > 160 or not jid:
            continue
        price_m = re.search(r'"budget":(\d+)', p)
        budget = str(int(price_m.group(1))) + " ₽" if price_m and price_m.group(1) != "0" else ""
        out.append({
            "platform": "Weblancer",
            "kind": "order",
            "job_id": f"wl:{jid.group(1)}",
            "url": "https://www.weblancer.net/freelance/" + path,
            "title": title[:120],
            "description": "",
            "budget": budget,
            "author": "",
            "scanned_at": _now(),
        })
        if len(out) >= 20:
            break
    return out


def scan_kwork() -> list:
    """Kwork — бесплатные офферы (без платы за отклик). Best-effort парсер карточек."""
    out = []
    r = hc.client("kwork.ru").get(KWORK_URL, timeout=25)
    if r.status_code != 200:
        return out
    for block in re.split(r'data-id="\d+"', r.text)[1:]:
        m = re.search(r'href="(/projects/\d+[^"]*)"[^>]*>([\s\S]{5,200}?)</a>', block)
        if not m:
            continue
        title = _clean(m.group(2))
        if not title or len(title) < 5:
            continue
        price_m = re.search(r"(\d[\d\s]{1,6})\s*(?:₽|руб)", block)
        desc_m = re.search(r'class="[^"]*kw-card__text[^"]*"[^>]*>([\s\S]{20,400}?)<', block)
        out.append({
            "platform": "Kwork",
            "kind": "order",
            "job_id": f"kw:{m.group(1).rstrip('/').split('/')[-1]}",
            "url": "https://kwork.ru" + m.group(1),
            "title": title[:140],
            "description": _clean(desc_m.group(1))[:300] if desc_m else "",
            "budget": _clean(price_m.group(0)) if price_m else "",
            "author": "",
            "scanned_at": _now(),
        })
    return out[:25]


def scan_all(include_tg=True, habr_ids=None, include_sites=True) -> tuple[list, list]:
    """Сканирование всех источников: TG-каналы, сайты-биржи, VK/OK сообщества.

    Контакт проставляется по тексту заказа (биржи), в outbox попадают только
    заказы с контактом — фильтр стоит в proposals.build_outbox."""

    def _enrich(jobs_part: list) -> None:
        for j in jobs_part:
            if not j.get("contact"):
                j["contact"] = find_contact((j.get("title") or "") + " " + (j.get("description") or ""))

    jobs, errors = [], []
    if include_sites:
        for name, fn in (("fl", scan_fl), ("flrss", scan_fl_rss), ("fr", scan_fr), ("wr", scan_wr), ("wl", scan_wl), ("kw", scan_kwork), ("gh", scan_gh_bounty)):
            try:
                part = fn()
                _enrich(part)
                jobs += part
            except Exception as e:
                errors.append(f"{name}: {e}")
    if include_tg:
        for ch in TG_CHANNELS:
            try:
                jobs += scan_tg(ch)
            except Exception as e:
                errors.append(f"tg:{ch}: {e}")
                try:
                    jobs += scan_tg(ch)
                except Exception as e2:
                    errors.append(f"tg:{ch} retry: {e2}")
        try:
            jobs += asyncio.run(tg_scrape.scan_many(TG_API_CHANNELS))
        except Exception as e:
            errors.append(f"tg-api: {e}")
    # VK / OK / Freelancer сканеры (вне зависимости от include_tg)
    try:
        import json as _json
        _cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        with open(_cfg_path, encoding="utf-8") as _f:
            _cfg = (_json.load(_f) or {}).get("sources", {})
    except Exception:
        _cfg = {}
    for mod_name, key in (("vk_scanner", "vk"), ("ok_scanner", "ok"), ("freelancer_scanner", "freelancer")):
        scfg = _cfg.get(key)
        if not isinstance(scfg, dict) or not scfg.get("enabled"):
            continue
        try:
            module = __import__(f"modules.{mod_name}", fromlist=["fetch_jobs"])
            part, errs2 = module.fetch_jobs(scfg)
            _enrich(part)
            jobs += part
            errors += errs2
        except Exception as e:
            errors.append(f"{key}: {type(e).__name__}: {str(e)[:80]}")
    if habr_ids and include_sites:
        try:
            jobs += scan_habr(habr_ids)
        except Exception as e:
            errors.append(f"habr: {e}")
    return jobs, errors


if __name__ == "__main__":
    from modules import store

    jobs, errors = scan_all(include_tg=True, habr_ids=store.load("habr_ids", {}).get("ids", []))
    print(f"total={len(jobs)} errors={errors}")
    for j in jobs[:25]:
        print(f"  [{j['platform']}] {j['title'][:70]} | {j['budget']} | {j['author']} | {j['description'][:50]}")