import sys
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
import json, os, time

COOKIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fl_cookies.json")
SESSION_KEYS = ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

with open(COOKIES, encoding='utf-8') as f:
    c = json.load(f)

session = [{'name': n, 'value': c[n], 'domain': '.www.fl.ru', 'path': '/'} for n in SESSION_KEYS if n in c and c[n]]
print('Cookies loaded:', len(session))

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False)
    ctx = browser.new_context(user_agent=UA, locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.goto('https://www.fl.ru/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    ctx.add_cookies(session)
    page.goto('https://www.fl.ru/projects/5519809/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(3)
    
    # Ищем кнопку
    btn = page.query_selector('a[data-popup="project_answer_popup"], a:has-text("Откликнуться")')
    print('Button found:', btn is not None)
    if btn:
        print('Href:', btn.get_attribute('href'))
        print('Visible:', btn.is_visible())
        btn.click(force=True)
        time.sleep(2)
    
    # Ищем textarea
    ta = page.query_selector('#newoffer textarea[name=descr]') or page.query_selector('#vacancy-offer textarea')
    print('Textarea found:', ta is not None)
    if ta:
        ta.fill('Тестовый отклик для проверки')
        time.sleep(1)
    
    # Ищем кнопку отправки
    btn = page.query_selector('#newoffer button:has-text("Отправить"), #vacancy-offer button:has-text("Отправить")')
    print('Submit button found:', btn is not None)
    if btn:
        btn.click()
        time.sleep(5)
    
    input('Нажми Enter чтобы закрыть браузер...')
    browser.close()