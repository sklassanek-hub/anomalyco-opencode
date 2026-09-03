"""
Freelancer.com автобиддинг через Playwright + Edge.
Сессия: freelancer_cookies.json (поднимается из браузера один раз).
Паттерн: сначала главная freelancer.com (браузер проходит Cloudflare/JS-челлендж),
затем подставляются куки и открывается страница проекта для размещения бида.
"""
import json
import os
import time
import urllib.parse

COOKIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_cookies.json")

# Ключевые куки для сессии Freelancer.com
SESSION_KEYS = (
    "FLAT",
    "FLRT",
    "FLID",
    "FLSS",
    "FLUS",
    "FLHASH",
    "_ga",
    "_gid",
    "_gat",
    "csrf_token",
    "XSRF-TOKEN",
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _load_session_cookies() -> list[dict]:
    try:
        with open(COOKIES, encoding="utf-8") as f:
            c = json.load(f)
    except Exception:
        return []
    out = []
    for name, value in c.items():
        if value:
            out.append({"name": name, "value": value, "domain": ".freelancer.com", "path": "/"})
    return out


def _save_context_cookies(ctx):
    try:
        fl = {x["name"]: x["value"] for x in ctx.cookies() if "freelancer.com" in x.get("domain", "")}
        old = json.load(open(COOKIES, encoding="utf-8")) if os.path.exists(COOKIES) else {}
        old.update(fl)
        with open(COOKIES, "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def bid_freelancer(project_url: str, description: str, bid_amount: float = None, period_days: int = 7, timeout: int = 180) -> bool:
    """
    Размещает бид на Freelancer.com проект.
    
    Returns:
        True  = бид размещён успешно
        'paid' = проект требует оплату за бид (skip)
        False = ошибка
    """
    from playwright.sync_api import sync_playwright

    session = _load_session_cookies()
    if not session:
        raise RuntimeError("freelancer_cookies.json пуст — нужно поднять сессию из браузера (extract_freelancer_cookies.py)")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            ctx = browser.new_context(user_agent=UA, locale="en-US",
                                      viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            
            # 1) Главная — браузер проходит Cloudflare/JS-челлендж
            page.goto("https://www.freelancer.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            # 2) Подставляем сессию
            try:
                ctx.add_cookies(session)
            except Exception:
                pass
            
            # 3) Страница проекта
            page.goto(project_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            
            # 4) Проверка: уже подали бид?
            try:
                already = page.query_selector('button:has-text("Bid Placed"), a:has-text("View Bid"), [data-test="bid-placed"]')
                if already:
                    _save_context_cookies(ctx)
                    return "already_bid"
            except Exception:
                pass
            
            # 5) Кнопка "Place Bid" / "Bid on Project"
            btn_bid = None
            selectors = [
                'button[data-test="place-bid-button"]',
                'button:has-text("Place Bid")',
                'a:has-text("Place Bid")',
                'button:has-text("Bid on Project")',
                '[data-test="bid-button"]',
            ]
            for sel in selectors:
                try:
                    btn_bid = page.query_selector(sel)
                    if btn_bid and btn_bid.is_visible():
                        break
                except Exception:
                    pass
                btn_bid = None
            
            if not btn_bid:
                # Попробуем найти через текст
                for _ in range(10):
                    btn_bid = page.query_selector('button:has-text("Bid"), a:has-text("Bid")')
                    if btn_bid and btn_bid.is_visible():
                        break
                    time.sleep(1)
            
            if not btn_bid:
                _save_context_cookies(ctx)
                return False
            
            # Проверка на платный бид (redirect to payment)
            href = btn_bid.get_attribute("href") or ""
            if "/pay/" in href or "/payment/" in href:
                _save_context_cookies(ctx)
                return "paid"
            
            try:
                btn_bid.click(force=True)
                time.sleep(2)
            except Exception:
                pass
            
            # 6) Форма бида — textarea для описания
            ta = None
            textarea_selectors = [
                'textarea[name="description"]',
                'textarea[placeholder*="bid" i]',
                'textarea[placeholder*="proposal" i]',
                'textarea[data-test="bid-description"]',
                '#bid-description',
                'textarea.form-control',
            ]
            for sel in textarea_selectors:
                try:
                    ta = page.query_selector(sel)
                    if ta and ta.is_visible():
                        break
                except Exception:
                    pass
                ta = None
            
            if not ta:
                _save_context_cookies(ctx)
                return False
            
            ta.fill(description)
            time.sleep(1)
            
            # 7) Сумма бида (если задана)
            if bid_amount:
                amount_selectors = [
                    'input[name="amount"]',
                    'input[name="bid_amount"]',
                    'input[data-test="bid-amount"]',
                    'input[placeholder*="amount" i]',
                    'input[placeholder*="budget" i]',
                ]
                for sel in amount_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible() and not el.input_value():
                            el.fill(str(bid_amount))
                            time.sleep(0.5)
                            break
                    except Exception:
                        pass
            
            # 8) Период (дни)
            period_selectors = [
                'input[name="period"]',
                'input[name="delivery_time"]',
                'input[data-test="bid-period"]',
                'select[name="period"]',
            ]
            for sel in period_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        if el.tag_name == "select":
                            el.select_option(str(period_days))
                        else:
                            el.fill(str(period_days))
                        time.sleep(0.5)
                        break
                except Exception:
                    pass
            
            # 9) Milestone percentage (если есть)
            try:
                mile = page.query_selector('input[name="milestone_percentage"], input[data-test="milestone-percentage"]')
                if mile and mile.is_visible() and not mile.input_value():
                    mile.fill("50")
                    time.sleep(0.5)
            except Exception:
                pass
            
            # 10) Submit — кнопка "Submit Bid" / "Place Bid"
            submit_selectors = [
                'button[data-test="submit-bid"]',
                'button:has-text("Submit Bid")',
                'button:has-text("Place Bid")',
                'button[type="submit"]:has-text("Bid")',
                'button:has-text("Submit")',
            ]
            for sel in submit_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click(force=True)
                        time.sleep(3)
                        break
                except Exception:
                    pass
            
            # 11) Проверка успеха
            time.sleep(3)
            success = page.query_selector('text="Bid placed", text="Bid submitted", [data-test="bid-success"], .bid-success')
            if success:
                _save_context_cookies(ctx)
                return True
            
            _save_context_cookies(ctx)
            return False
            
        except Exception as e:
            return False


def extract_freelancer_cookies():
    """Запускает браузер для ручного входа и сохранения куков в freelancer_cookies.json"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        ctx = browser.new_context(user_agent=UA, locale="en-US", viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto("https://www.freelancer.com/login", wait_until="domcontentloaded")
        print("Войдите в аккаунт Freelancer.com в открывшемся браузере...")
        print("После входа нажмите Enter здесь.")
        input()
        
        cookies = ctx.cookies()
        fl_cookies = {c["name"]: c["value"] for c in cookies if "freelancer.com" in c.get("domain", "")}
        os.makedirs(os.path.dirname(COOKIES), exist_ok=True)
        with open(COOKIES, "w", encoding="utf-8") as f:
            json.dump(fl_cookies, f, ensure_ascii=False, indent=1)
        print(f"Куки сохранены в {COOKIES}: {len(fl_cookies)} шт.")
        browser.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        extract_freelancer_cookies()
    else:
        print("Usage: python -m modules.freelancer_bidder extract")
        print("   или импортируйте bid_freelancer(url, description, bid_amount, period_days)")