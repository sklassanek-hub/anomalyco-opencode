import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
url = "https://freelance.ru/task/view/8268"
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False)
    ctx = browser.new_context(user_agent=UA, locale="ru-RU")
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)
    print("title", page.title())
    print("url", page.url)
    # ищем кнопку откликнуться
    for sel in ['a:has-text("Откликнуться")','a:has-text("Предложить")','button:has-text("Отклик")']:
        el = page.query_selector(sel)
        if el:
            print("found btn", sel, el.inner_text()[:50], el.get_attribute("href"))
            break
    else:
        print("no btn found")
        print(page.content()[:2000])
    input("press enter to close")
    browser.close()
