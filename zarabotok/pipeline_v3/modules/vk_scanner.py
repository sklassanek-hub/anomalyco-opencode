"""Сканер ВКонтакте (vk.com): заказы из публичных сообществ двумя режимами.

Режим A — официальный API wall.get (если в конфиге задан token).
Режим B — без токена: мобильная версия m.vk.com, тексты постов вытаскиваются
регэкспами из встроенных JSON/HTML блоков (несколько запасных паттернов).
Best-effort: любая ошибка превращается в строку errors, модуль никогда не бросает исключений.
"""
import codecs
import json
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from modules import http_client
from modules import tg_scrape

API_BASE = "https://api.vk.com/method"
MOBILE_BASE = "https://m.vk.com"
WALL_URL = "https://vk.com/wall"
API_V = "5.199"
TIMEOUT = 20
MIN_TEXT_LEN = 40  # посты короче — шум

RE_TAG = re.compile(r"<[^>]+>")
RE_WS = re.compile(r"\s+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w]{2,}")
BUDGET_RUB_RE = re.compile(r"(\d[\d\s\u00a0.,]{0,11})\s*(?:₽|руб\.?(?:лей)?|rub\b)", re.IGNORECASE)
BUDGET_THOUSANDS_RE = re.compile(r"(?:до\s*)?(\d+(?:[.,]\d+)?)\s*тыс", re.IGNORECASE)

# Паттерны мобильной выдачи: VK встраивает тексты постов в JS/HTML.
# (1) "wall_id":"-GID_PID","text":"..."
RE_WALL_JSON = re.compile(r'"wall_id"\s*:\s*"-(\d+)_(\d+)"\s*,\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
# (3) то же в обратном порядке: сначала text, потом wall_id
RE_WALL_JSON_REV = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"wall_id"\s*:\s*"-(\d+)_(\d+)"')
# (2) ссылка /wall-GID_PID + соседний текстовый блок после неё
RE_WALL_HREF = re.compile(r'href="/wall-(\d+)_(\d+)"')
RE_JS_STR = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
RE_VISIBLE = re.compile(r">([^<>{}\n]{20,600})<")


def _clean(s: str) -> str:
    return RE_WS.sub(" ", RE_TAG.sub("", s or "")).strip()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _decode_js_string(raw: str) -> str:
    """Декодирует \\uXXXX и \" экранирования JS-строки; сбой -> мягкий фолбэк."""
    raw = raw or ""
    try:
        return json.loads('"' + raw + '"')
    except Exception:
        pass
    try:
        txt = codecs.decode(raw.encode("utf-8"), "unicode_escape")
        return txt.encode("latin-1").decode("utf-8", "replace")
    except Exception:
        return raw.replace('\\"', '"').replace("\\n", " ").replace("\\/", "/")


def _extract_budget(text: str) -> str:
    """'Бюджет 25 000 руб' -> '25000 ₽'; kwork-style 'до 30 тыс' -> '30000 ₽'; иначе ''."""
    m = BUDGET_RUB_RE.search(text or "")
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if digits and int(digits) > 0:
            return f"{digits} ₽"
    m = BUDGET_THOUSANDS_RE.search(text or "")
    if m:
        try:
            val = float(m.group(1).replace(",", "."))
        except ValueError:
            return ""
        if val > 0:
            return f"{int(val * 1000)} ₽"
    return ""


def _find_contact(text: str) -> str | None:
    """tg_scrape.contact_of, фолбэк — email, иначе None."""
    c = tg_scrape.contact_of(text or "")
    if c:
        return c
    m = EMAIL_RE.search(text or "")
    return m.group(0) if m else None


def _parse_wall_json(api_items: list[dict]) -> list[dict]:
    """items ответа wall.get -> нормализованные записи {id,text,date,contact,budget}.

    Посты без текста или короче MIN_TEXT_LEN пропускаются.
    """
    out: list[dict] = []
    for it in api_items or []:
        try:
            pid = int(it.get("id"))
        except (TypeError, ValueError):
            continue
        text = _clean(_decode_js_string(str(it.get("text") or "")))
        if len(text) < MIN_TEXT_LEN:
            continue
        out.append({
            "id": pid,
            "text": text,
            "date": it.get("date"),
            "contact": _find_contact(text),
            "budget": _extract_budget(text),
        })
    return out


def _parse_mobile_html(html: str, slug: str) -> list[tuple[str, str]]:
    """HTML страницы m.vk.com/{slug} -> [(post_key '<gid>_<pid>', текст)], дедуп по ключу.

    slug в разборе не участвует (единая сигнатура с остальными парсерами).
    Три запасных паттерна: JSON wall_id+text; JSON в обратном порядке;
    ссылка /wall-GID_PID с соседним текстовым блоком.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(gid: str, pid: str, raw_text: str) -> None:
        text = _clean(_decode_js_string(raw_text))
        key = f"{gid}_{pid}"
        if key in seen or not text:
            return
        seen.add(key)
        out.append((key, text))

    html = html or ""
    for m in RE_WALL_JSON.finditer(html):
        _add(m.group(1), m.group(2), m.group(3))
    for m in RE_WALL_JSON_REV.finditer(html):
        _add(m.group(2), m.group(3), m.group(1))
    for m in RE_WALL_HREF.finditer(html):
        gid, pid = m.group(1), m.group(2)
        if f"{gid}_{pid}" in seen:
            continue
        tail = html[m.end(): m.end() + 1500]
        js = RE_JS_STR.search(tail)
        vis = RE_VISIBLE.search(tail)
        _add(gid, pid, js.group(1) if js else (vis.group(1) if vis else ""))
    return out


def _resolve_owner(s, slug: str, token: str) -> int:
    """slug сообщества -> owner_id (отрицательный id группы).

    Числовой слаг используется как есть с минусом; иначе резолв через
    groups.getById (ответ бывает в старом [..] и новом {groups:[..]} виде).
    """
    if re.fullmatch(r"-?\d+", slug):
        return -abs(int(slug))
    r = s.get(f"{API_BASE}/groups.getById",
              params={"group_id": slug, "v": API_V, "access_token": token},
              timeout=TIMEOUT)
    resp = (r.json() or {}).get("response")
    items = resp.get("groups") if isinstance(resp, dict) else resp
    for cand in items or []:
        try:
            gid = int(cand.get("id") or cand.get("cid") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if gid:
            return -abs(gid)
    raise ValueError("groups.getById: группа не найдена")


def _wall_get(s, owner_id: int, count: int, token: str) -> list:
    r = s.get(f"{API_BASE}/wall.get",
              params={"owner_id": owner_id, "count": max(1, min(int(count), 100)),
                      "v": API_V, "access_token": token},
              timeout=TIMEOUT)
    data = r.json() or {}
    if data.get("error"):
        err = data["error"]
        raise RuntimeError(f"VK API {err.get('error_code')}: {str(err.get('error_msg', ''))[:60]}")
    return ((data.get("response") or {}).get("items")) or []


def _make_job(slug: str, gid: str, pid: str, text: str) -> dict:
    return {
        "platform": "VK",
        "kind": "order",
        "job_id": f"vk:{slug}:{pid}",
        "url": f"{WALL_URL}-{gid}_{pid}",
        "title": text[:140].split("\n")[0],
        "description": text[:600],
        "budget": _extract_budget(text),
        "author": slug,
        "contact": _find_contact(text),
        "scanned_at": _now(),
    }


def fetch_jobs(cfg: dict) -> tuple[list[dict], list[str]]:
    """cfg из config.json -> sources -> vk:
    {"enabled": true, "token": "", "groups": ["freelancejob", ...], "max_per_group": 20}.

    Токен задан -> режим A (официальный API wall.get), иначе режим B (m.vk.com без входа).
    """
    jobs: list[dict] = []
    errors: list[str] = []
    if not cfg or not cfg.get("enabled"):
        return jobs, errors
    groups = cfg.get("groups") or []
    try:
        max_per_group = int(cfg.get("max_per_group") or 20)
    except (TypeError, ValueError):
        max_per_group = 20
    token = str(cfg.get("token") or "").strip()
    try:
        s = http_client.client("vk.com")
    except Exception as e:
        return jobs, [f"vk: client: {type(e).__name__}: {str(e)[:120]}"]
    for raw_slug in groups:
        slug = str(raw_slug).strip().strip("/")
        if not slug:
            continue
        try:
            if token:
                try:
                    owner = _resolve_owner(s, slug, token)
                    posts = _parse_wall_json(_wall_get(s, owner, max_per_group, token))
                except Exception as e:
                    # groups.getById может не найти паблик/страницу — пробуем wall.get по domain
                    try:
                        r = s.get(f"{API_BASE}/wall.get",
                                  params={"domain": slug, "count": max(1, min(int(max_per_group), 100)),
                                          "v": API_V, "access_token": token},
                                  timeout=TIMEOUT)
                        data = r.json() or {}
                        if data.get("error"):
                            raise RuntimeError(f"VK API {data['error'].get('error_code')}: {str(data['error'].get('error_msg',''))[:60]}")
                        posts = _parse_wall_json(((data.get("response") or {}).get("items")) or [])
                    except Exception as e2:
                        raise e
                if not posts:
                    errors.append(f"vk:{slug}: wall.get пуст (нет постов или стена закрыта)")
                for p in posts[:max_per_group]:
                    # owner может быть не определён при fallback — берём из slug
                    gid = str(abs(owner)) if 'owner' in locals() and owner else slug
                    jobs.append(_make_job(slug, gid, str(p["id"]), p["text"]))
            else:
                r = s.get(f"{MOBILE_BASE}/{slug}", timeout=TIMEOUT)
                if r.status_code != 200:
                    errors.append(f"vk:{slug}: HTTP {r.status_code}")
                    continue
                final_url = str(getattr(r, "url", "") or "").lower()
                head = (r.text or "")[:4000].lower()
                if "login" in final_url or "login" in head or "авторизация" in head:
                    errors.append(f"vk:{slug}: группа недоступна без входа (m.vk редирект на login)")
                    continue
                posts = _parse_mobile_html(r.text, slug)[:max_per_group]
                if not posts:
                    errors.append(f"vk:{slug}: посты не найдены (возможно, стена закрыта)")
                    continue
                for key, text in posts:
                    gid, pid = key.split("_", 1)
                    jobs.append(_make_job(slug, gid, pid, text))
        except Exception as e:
            errors.append(f"vk:{slug}: {type(e).__name__}: {str(e)[:80]}")
    return jobs, errors


if __name__ == "__main__":
    import os

    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    cfg = {}
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = ((json.load(f) or {}).get("sources") or {}).get("vk") or {}
    except Exception:
        pass
    jobs, errs = fetch_jobs(cfg or {"enabled": True, "groups": [], "max_per_group": 20})
    print(f"vk: jobs={len(jobs)} errors={errs}")
    for j in jobs[:10]:
        print(f"  [{j['author']}] {j['title'][:70]} | {j['budget']} | {j['contact']}")
