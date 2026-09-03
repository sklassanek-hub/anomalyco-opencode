from playwright.sync_api import sync_playwright
import os
LOCAL=os.environ.get("LOCALAPPDATA","")
user_data = os.path.join(LOCAL, "Yandex", "YandexBrowser", "User Data")
print("launch persistent", user_data)
with sync_playwright() as p:
    # use chromium with user_data_dir
    ctx = p.chromium.launch_persistent_context(user_data_dir=user_data, headless=True, args=['--disable-blink-features=AutomationControlled'])
    page = ctx.new_page()
    page.goto("https://freelance.ru/", wait_until="domcontentloaded", timeout=30000)
    print("freelance title", page.title()[:60])
    print("cookies", len(ctx.cookies()))
    for c in ctx.cookies():
        if "freelance" in c["domain"]:
            print(c["name"], c["value"][:40])
    ctx.close()
