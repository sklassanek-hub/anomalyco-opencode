"""Сканер Одноклассников (ok.ru): публичные обсуждения/темы сообществ с заказами.

Best-effort: работает только с открытыми сообществами без авторизации.
Любая ошибка превращается в строку errors, модуль никогда не бросает исключений.
"""
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from modules import http_client
from modules import tg_scrape

OK_BASE = "https://ok.ru"
TIMEOUT = 20
MAX_DETAIL_GETS = 5  # не более 5 GET страниц топиков за весь вызов

RE_TAG = re.compile(r"<[^>]+>")
RE_WS = re.compile(r"\s+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w]{2,}")
BUDGET_RE = re.compile(r"(\d[\d\s\u00a0.,]{0,11})\s*(?:₽|руб\.?(?:лей)?)", re.IGNORECASE)


def _clean(s: str) -> str:
    return RE_WS.sub(" ", RE_TAG.sub("", s or "")).strip()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _extract_budget(text: str) -> str:
    """Ищет сумму перед ₽/руб: 'Оплата 12 000 руб' -> '12000 ₽'; иначе ''."""
    m = BUDGET_RE.search(text or "")
    if not m:
        return ""
    digits = re.sub(r"\D", "", m.group(1))
    if not digits or int(digits) == 0:
        return ""
    return f"{digits} ₽"


def _find_contact(text: str) -> str | None:
    """tg_scrape.contact_of, фолбэк — email, иначе None."""
    c = tg_scrape.contact_of(text or "")
    if c:
        return c
    m = EMAIL_RE.search(text or "")
    return m.group(0) if m else None


def _parse_topics_html(html: str, slug: str) -> list[tuple[str, str]]:
    """Темы сообщества: [(href, snippet)] по ссылкам вида /{slug}/topic/{id}.

    Несколько запасных паттернов: ссылка с якорным текстом; «голая» ссылка,
    текст рядом после неё. Дедупликация по id темы.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    sre = re.escape(slug)

    def _add(tid: str, snippet: str) -> None:
        if tid and tid not in seen:
            seen.add(tid)
            out.append((f"/{slug}/topic/{tid}", _clean(snippet)))

    # Паттерн 1: <a href="/slug/topic/N">текст</a>
    for m in re.finditer(r'<a[^>]+href="/' + sre + r'/topic/(\d+)"[^>]*>([\s\S]{0,500}?)</a>', html or ""):
        snip = _clean(m.group(2))
        if snip:
            _add(m.group(1), snip)
    # Паттерн 2: href="/slug/topic/N" без якорного текста — берём текст в окне после ссылки
    for m in re.finditer(r'href="/' + sre + r'/topic/(\d+)"', html or ""):
        tid = m.group(1)
        if tid in seen:
            continue
        tail = html[m.end(): m.end() + 1500]
        t = re.search(r">([^<>{}\n]{10,400})<", tail)
        _add(tid, t.group(1) if t else "")
    return out


def _topic_text(html: str) -> str:
    """Текст топика со страницы темы (первые 800 символов), несколько фолбэков."""
    for pat in (
        r'<div[^>]+class="[^"]*media-text__text[^"]*"[^>]*>([\s\S]{10,2500}?)</div>',
        r'<div[^>]+class="[^"]*topic-body[^"]*"[^>]*>([\s\S]{10,2500}?)</div>',
        r'<meta[^>]+property="og:description"[^>]+content="([^"]{10,900})"',
        r'<meta[^>]+content="([^"]{10,900})"[^>]+property="og:description"',
    ):
        try:
            m = re.search(pat, html or "")
        except Exception:
            continue
        if not m:
            continue
        txt = m.group(1).replace("\\n", " ").replace('\\"', '"')
        txt = _clean(txt)
        if len(txt) >= 10:
            return txt[:800]
    return ""


def fetch_jobs(cfg: dict) -> tuple[list[dict], list[str]]:
    """cfg из config.json -> sources -> ok: {"enabled": true, "groups": [...], "max_per_group": 15}."""
    jobs: list[dict] = []
    errors: list[str] = []
    if not cfg or not cfg.get("enabled"):
        return jobs, errors
    groups = cfg.get("groups") or []
    try:
        max_per_group = int(cfg.get("max_per_group") or 15)
    except (TypeError, ValueError):
        max_per_group = 15
    try:
        s = http_client.client("ok.ru")
    except Exception as e:
        return jobs, [f"ok: client: {type(e).__name__}: {str(e)[:120]}"]
    detail_left = MAX_DETAIL_GETS
    for raw_slug in groups:
        slug = str(raw_slug).strip().strip("/")
        if not slug:
            continue
        try:
            r = s.get(f"{OK_BASE}/{slug}/topics", timeout=TIMEOUT)
            if r.status_code != 200:
                errors.append(f"ok:{slug}: HTTP {r.status_code}")
                continue
            topics = _parse_topics_html(r.text, slug)
            if not topics:
                errors.append(f"ok:{slug}: тем не найдено (возможно, требуется вход)")
                continue
            taken = 0
            for href, snippet in topics:
                if taken >= max_per_group:
                    break
                tid = href.rstrip("/").rsplit("/", 1)[-1]
                text = snippet
                if detail_left > 0:
                    detail_left -= 1
                    try:
                        rd = s.get(OK_BASE + href, timeout=TIMEOUT)
                        if rd.status_code == 200:
                            text = _topic_text(rd.text) or text
                    except Exception:
                        pass
                contact = _find_contact(text)
                jobs.append({
                    "platform": "OK",
                    "kind": "order",
                    "job_id": f"ok:{slug}:{tid}",
                    "url": OK_BASE + href,
                    "title": (snippet or text)[:140],
                    "description": text[:600],
                    "budget": _extract_budget(text),
                    "author": slug,
                    "contact": contact,
                    "scanned_at": _now(),
                })
                taken += 1
        except Exception as e:
            errors.append(f"ok:{slug}: {type(e).__name__}: {str(e)[:160]}")
    return jobs, errors


if __name__ == "__main__":
    import json
    import os

    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    cfg = {}
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = ((json.load(f) or {}).get("sources") or {}).get("ok") or {}
    except Exception:
        pass
    jobs, errs = fetch_jobs(cfg or {"enabled": True, "groups": [], "max_per_group": 15})
    print(f"ok: jobs={len(jobs)} errors={errs}")
    for j in jobs[:10]:
        print(f"  [{j['author']}] {j['title'][:70]} | {j['budget']} | {j['contact']}")
