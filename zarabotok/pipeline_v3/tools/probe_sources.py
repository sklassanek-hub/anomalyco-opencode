import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modules import http_client as hc


def probe(name, domain, url, hooks=None):
    s = hc.client(domain)
    try:
        r = s.get(url, timeout=20)
        print(f"{name}: {r.status_code} len={len(r.text)}")
        if hooks:
            for label, pat in hooks.items():
                m = re.findall(pat, r.text)
                print(f"   {label}: {len(m)} | sample: {m[0][:200] if m else '-'}")
        return r.text
    except Exception as e:
        print(f"{name}: ERR {e}")
        return ""


probe("weblancer", "weblancer.net", "https://www.weblancer.net/jobs/")
probe("weworkremotely", "weworkremotely.com", "https://weworkremotely.com/remote-jobs/search?term=python")
probe(
    "habr",
    "habr.com",
    'https://career.habr.com/vacancies?q=%22telegram%22',
    {"vac": r'href="/vacancies/(\d+)"[^>]*>\s*([^<]{4,120})', "price": r"\d[\d\s]{2,7}[\s\S]{0,40}(?:₽|\$|руб)"},
)
probe(
    "fl",
    "fl.ru",
    "https://www.fl.ru/projects/",
    {
        "jobs": r'<a[^>]*href="/projects/(\d+)/[^"]*"[^>]*>([^<]{5,120})</a>',
        "author": r'<a[^>]*href="/users/[^"]*"[^>]*class="[^"]*b-post__nickname[^"]*"[^>]*>([^<]+)<',
        "desc": r'<p[^>]*class="[^"]*b-post__body[^"]*"[^>]*>([\s\S]{20,400}?)</p>',
    },
)