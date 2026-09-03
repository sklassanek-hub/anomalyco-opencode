"""Скрапер публичных TG-каналов/супергрупп через Telethon (авторизованная сессия).
Читает последние сообщения без подписки. Фолбэк — веб-превью t.me/s."""
import re

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

from modules import http_client, store, tg_common

MAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TG_RE = re.compile(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})")
SKIP_USERS = {
    "telegram", "kwork", "vkontakte", "vk", "site", "сайт", "вк", "youtube",
    "instagram", "google", "yandex", "habr", "fl", "freelance", "бот", "bot",
    "gmail", "vkusvill", "amediateka", "gotoisland", "devkg", "findwork",
    "llm_jobs", "freelance_orders", "frilans", "vorkzavr", "workayte", "freelancersu",
    "webfrl", "distantsiya2", "job_freelancer", "freelance_jobs_tg", "tilda_freelance",
    "designers_freelance", "job_freelancer", "theyseeku_it", "noexperience", "remote_ru",
    "freelance_antispam", "design_hunter", "creatives_hunt", "er_freelance", "freelance_help",
    "pro_freelance", "freelance_chat_ru", "koteyka", "digitalrabota", "remote_jobs_ru",
    "freelancetavern", "distantsiya", "freelance_ru", "finder_vc", "freelancechoice",
    "work_offline", "work_a_da", "remote_work", "weworkremotely",
}
ASK_WORDS = ("отклик", "пиши", "пишите", "напиши", "напишите", "писать", "написать",
             "контакт", "связ", "в лс", "в личку", "личку", "обращайт", "жду в", "тг:")
REJECT_MARKERS = ("[свежие медиа]", "[свежие сервисы]", "[свежие отклики]", "[свежий вкус]",
                  "[свежая вакансия]", "[свежие вакансии]", "[свежий вакансия]",
                  "#резюме", "#помогу", "#предлагаю", "#ищуклиента", "#услуги", "#вакансия")
SCAM_MARKERS = ("курье", "за грамм", "закладк", "клад", "оплатим переезд", "заработ",
                "грамм", "в день", "казино", "дроп", "сигнал", "ставк", "каппер", "бонус",
                "реклам", "подписчик", "накрутк", "рассылк", "продвиж")


CLIENT_MARKERS = ("нужн", "ищу", "ищем", "требует", "сделайте", "сделать", "закаж",
                  "кто может", "кто сделает", "помогите", "оплач", "плачу", "готов заплатить",
                  "ищет разраб", "ищет продр", "ищем разраб", "продвинуть", "разработать",
                  "для сайта", "для бота", "сделать сайт", "сделать бота", "бюджет",
                  "оплата", "напишите", "пишите в", "в лс", "в личку", "лично в")
SERVICE_MARKERS = ("ваканси", "резюме", "набираем", "требуются сотруд", "в команду", "работа на",
                   "ищу работу", "предлагаю", "окажу", "возьму заказы", "возьмусь", "готов выполнить",
                   "выполню", "создаю", "разрабатываю", "услуги", "наша команда", "ищем людей",
                   "нужны люди", "заработ", "в день", "приглашаю", "опыт работы", "требования",
                   "требуется сотрудник", "удаленная работа", "удалённая работа", "гибрид")


def order_kind(text: str) -> str:
    """order — заказчик ищет исполнителя; vacancy — ищут сотрудника/исполнитель предлагает услуги."""
    low = (text or "").lower()
    c = sum(1 for m in CLIENT_MARKERS if m in low)
    v = sum(1 for m in SERVICE_MARKERS if m in low)
    if c > v:
        return "order"
    if v > c:
        return "vacancy"
    return "order" if c else "vacancy"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def contact_of(text: str) -> str | None:
    """Находит контакт заказчика в тексте поста: приоритет — предложению с глаголами отклика,
    фолбэк — email или первое @упоминание (не бот, не рекламный канал)."""
    low = (text or "").lower()
    if any(m in low for m in REJECT_MARKERS):
        return None
    for sent in re.split(r"(?<=[.!?])\s+", text or ""):
        if any(w in sent.lower() for w in ASK_WORDS):
            m = MAIL_RE.search(sent)
            if m:
                return m.group(0)
            m = TG_RE.search(sent)
            if m and m.group(1).lower() not in SKIP_USERS and not m.group(1).lower().endswith("_bot"):
                return "@" + m.group(1)
    m = MAIL_RE.search(text or "")
    if m:
        return m.group(0)
    for m in TG_RE.finditer(text or ""):
        u = m.group(1).lower()
        if u not in SKIP_USERS and not u.endswith("_bot") and "bot" not in u:
            return "@" + m.group(1)
    return None


def contacts_in(text: str) -> list:
    out = []
    for m in TG_RE.finditer(text):
        u = m.group(1).replace("+", "")
        if u.lower() not in SKIP_USERS and u.lower() not in (x.lower() for x in out):
            out.append(f"@{u}")
    if not out:
        for m in MAIL_RE.finditer(text):
            out.append(m.group(0))
    return out


async def fetch_channel(client: TelegramClient, username: str, limit: int = 25) -> list[dict]:
    entity = await client.get_entity(username)
    posts = []
    i = 0
    async for msg in client.iter_messages(entity, limit=limit):
        t = _clean(msg.message)
        if not t:
            continue
        posts.append({
            "ts": msg.date.isoformat() if msg.date else "",
            "text": t[:1200],
            "msg_id": msg.id,
        })
        i += 1
        if i >= limit:
            break
    return posts


async def probe_channel(username: str, limit: int = 25) -> dict:
    session = store.load("settings", {}).get("tg_session", "telegram_session_sender")
    with tg_common.tg_lock():
        client = tg_common.tg_client(tg_common.session_path(session), proxy=http_client.socks_args())
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return {"ch": username, "alive": False, "reason": "no auth"}
            posts = await fetch_channel(client, username, limit)
            if not posts:
                return {"ch": username, "alive": True, "reason": "empty"}
            n_contact = 0
            users = []
            for p in posts:
                cs = contacts_in(p["text"])
                if cs:
                    n_contact += 1
                    users += cs[:2]
            newest = max(p["ts"] for p in posts)[:10] if posts else "?"
            return {
                "ch": username, "alive": True, "posts": len(posts),
                "tg_contact": n_contact, "users": users[:6],
                "newest": newest,
                "sample": posts[0]["text"][:90] if posts else "",
                "kind": "channel",
            }
        except Exception as e:
            return {"ch": username, "alive": False, "reason": f"{type(e).__name__}: {str(e)[:80]}"}
        finally:
            await client.disconnect()


async def scan_channel(client: TelegramClient, username: str, jobs: list, limit: int = 25) -> int:
    """Добавляет посты канала в список заказов. Возвращает количество добавленных."""
    posts = await fetch_channel(client, username, limit)
    added = 0
    for p in posts:
        text = p["text"]
        low = text.lower()
        if any(m in low for m in SCAM_MARKERS):
            continue
        kind = order_kind(text)
        if kind != "order":
            continue
        c = contact_of(text)
        if not c:
            continue
        title = re.sub(r"https?://\S+", "", text)[:110] or text[:110]
        if "@" in c:
            contact, to = c, None
        else:
            contact, to = None, c
        jobs.append({
            "platform": "TG:" + username,
            "kind": "order",
            "job_id": f"tgapi:{username}:{p.get('msg_id')}",
            "url": f"https://t.me/{username}/{p.get('msg_id', '')}",
            "title": title,
            "description": text[:400],
            "budget": "",
            "author": "",
            "contact": contact,
            "to": to,
            "scanned_at": store.now(),
        })
        added += 1
    return added


async def scan_many(names: list[str], limit: int = 25) -> list[dict]:
    """Один клиент на все каналы: возвращает заказы с контактами из публичных каналов/супергрупп.
    Держит кросс-процессный лок на сессию всё время соединения."""
    session = store.load("settings", {}).get("tg_session", "telegram_session_sender")
    jobs = []
    with tg_common.tg_lock():
        client = tg_common.tg_client(tg_common.session_path(session), proxy=http_client.socks_args())
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return jobs
            for name in names:
                try:
                    await scan_channel(client, name, jobs, limit)
                except Exception:
                    continue
        finally:
            await client.disconnect()
    return jobs