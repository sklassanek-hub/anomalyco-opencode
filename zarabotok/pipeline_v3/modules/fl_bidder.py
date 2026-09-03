"""Отклики на fl.ru через Playwright + Edge. Сессия: fl_cookies.json (поднималась из браузера).
Паттерн: сначала главная fl.ru (браузер сам проходит DDoS-Guard JS-челлендж),
затем подставляются сессионные куки и открывается страница заказа."""
import json
import os
import time

COOKIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fl_cookies.json")

SESSION_KEYS = ("PHPSESSID", "XSRF-TOKEN", "id", "name", "pwd", "user_device_id", "cookies_accepted")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _load_session_cookies() -> list[dict]:
    try:
        with open(COOKIES, encoding="utf-8") as f:
            c = json.load(f)
    except Exception:
        return []
    out = []
    for name in SESSION_KEYS:
        if name in c and c[name]:
            out.append({"name": name, "value": c[name], "domain": ".www.fl.ru", "path": "/"})
    return out


def _save_context_cookies(ctx):
    """Сохраняет обновлённые fl.ru куки после сеанса (PHPSESSID мог продлиться)."""
    try:
        fl = {x["name"]: x["value"] for x in ctx.cookies() if "fl.ru" in x.get("domain", "")}
        old = json.load(open(COOKIES, encoding="utf-8")) if os.path.exists(COOKIES) else {}
        old.update(fl)
        with open(COOKIES, "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def bid_fl(url: str, text: str, timeout: int = 180) -> bool:
    """Отправляет отклик на fl.ru заказ. True = отклик виден на странице, 'paid' = нужна оплата."""
    from playwright.sync_api import sync_playwright

    session = _load_session_cookies()
    if not session:
        raise RuntimeError("fl_cookies.json пуст — нужно поднять сессию из браузера (extract_fl_cookies.py)")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            ctx = browser.new_context(user_agent=UA, locale="ru-RU",
                                      viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            # 1) главная — браузер сам проходит DDoS-Guard челлендж и получает свои __ddg*
            page.goto("https://www.fl.ru/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            # 2) подставляем сессию аккаунта
            try:
                ctx.add_cookies(session)
            except Exception:
                pass
            # 3) страница заказа
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # 4) кнопка «Откликнуться» — если ведёт на /payed/, отклик платный
            btn_open = None
            for _ in range(15):
                btn_open = page.query_selector('a.ui-button:has-text("Откликнуться")')
                if btn_open:
                    break
                time.sleep(1)
# 4) кнопка «Откликнуться» — если ведёт на /payed/, отклик платный
            btn_open = None
            for _ in range(15):
                btn_open = page.query_selector('a.ui-button:has-text("Откликнуться")')
                if btn_open:
                    break
                time.sleep(1)
            if btn_open:
                href = btn_open.get_attribute("href") or ""
                if "/payed/" in href:
                    _save_context_cookies(ctx)
                    return "paid"
                try:
                    if btn_open.is_visible() and btn_open.get_attribute("href").strip("#") == "":
                        btn_open.click(force=True)
                        # Ждём загрузку формы отклика через AJAX
                        time.sleep(3)
                except Exception:
                    pass
            # 5) ждём появления формы отклика (подгружается через AJAX)
            # Пробуем найти форму в разных возможных контейнерах
            ta = None
            for _ in range(60):
                # Ищем textarea в контейнере отклика
                ta = page.query_selector(
                    '#project-offer-block textarea, '
                    '#my-offer textarea, '
                    '[id*="offer"] textarea, '
                    '.project-offer-block textarea, '
                    'form[id*="offer"] textarea, '
                    'form[class*="offer"] textarea, '
                    '#project-offer-block- textarea, '
                    '.project-offer textarea'
                )
                if ta:
                    break
                # Проверяем, не появилась ли форма в модальном окне
                modal_ta = page.query_selector('.ui-modal textarea, .ui-dialog textarea, [role=dialog] textarea')
                if modal_ta:
                    ta = modal_ta
                    break
                time.sleep(1)
            if not ta:
                _save_context_cookies(ctx)
                return False
            pfx = ""
            ta.fill(text)
            time.sleep(1)
            # 6) способ оплаты (radio) — выбираем первый
            try:
                pay = page.query_selector('input[name=pay]:not([type=hidden])')
                if pay and not pay.is_checked():
                    pay.check(force=True)
                    time.sleep(1)
            except Exception:
                pass
            # 7) обязательные срок/цена, если видимы и пусты
            for fname, fval in (("cost_from", "20000"), ("time_from", "10")):
                try:
                    el = page.query_selector(f'input[name={fname}]')
                    if el and el.is_visible() and not el.input_value():
                        el.fill(fval)
                except Exception:
                    pass
            # 8) кнопка отправки
            btn = None
            for sel in ('button:has-text("Отправить отклик")', 'button:has-text("Отправить")',
                        'button.ui-button._success:has-text("Отправить")',
                        'input[type=submit][value*="Отправит"]'):
                btn = page.query_selector(sel)
                if btn:
                    break
            if not btn:
                _save_context_cookies(ctx)
                return False
            btn.click()
            time.sleep(5)
            body = page.inner_text("body")
            ok = "ваш отклик" in body.lower() and ("редактировать" in body.lower() or "отказаться" in body.lower())
            _save_context_cookies(ctx)
            return ok
        finally:
            browser.close()


def is_fl_url(url: str) -> bool:
    return isinstance(url, str) and "fl.ru" in url


def _open_context(page):
    """1) главная (проход DDoS-Guard) -> 2) сессия -> 3) goto url. Возвращает page."""
    page.goto("https://www.fl.ru/", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    try:
        page.context.add_cookies(_load_session_cookies())
    except Exception:
        pass


def poll_messages() -> list[dict]:
    """Открывает /messages/ и возвращает непрочитанные диалоги: [{peer, text, ts, url}]."""
    from playwright.sync_api import sync_playwright

    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            ctx = browser.new_context(user_agent=UA, locale="ru-RU",
                                      viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            _open_context(page)
            page.goto("https://www.fl.ru/messages/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(6)
            body = page.inner_text("body")
            if "чатов не найдено" in body:
                return out
            for a in page.query_selector_all("a[href*='/messages/']"):
                href = a.get_attribute("href") or ""
                if href in ("/messages/", "/messages") or "/messages/" not in href:
                    continue
                txt = (a.inner_text() or "").strip()
                if len(txt) > 4:
                    out.append({"peer": txt[:80], "text": txt[:500], "url": href})
        finally:
            try:
                _save_context_cookies(ctx)
            except Exception:
                pass
            browser.close()
    return out


def send_dialog(url: str, text: str, timeout: int = 180) -> bool:
    """Отправляет сообщение в диалог fl.ru (/messages/<id>/). True = textarea очистилась (отправка прошла)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            ctx = browser.new_context(user_agent=UA, locale="ru-RU",
                                      viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            _open_context(page)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector("textarea", timeout=25000)
            except Exception:
                return False
            ta = page.query_selector("textarea")
            if not ta:
                return False
            ta.fill(text)
            time.sleep(1)
            btn = page.query_selector('button:has-text("Отправить"), button.js-send-message, input[type=submit]')
            if not btn:
                return False
            btn.click()
            time.sleep(7)
            return (page.query_selector("textarea").input_value() or "").strip() == ""
        finally:
            try:
                _save_context_cookies(ctx)
            except Exception:
                pass
            browser.close()