import sys
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
import json, os, time, sys

COOKIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fl_cookies.json')
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
    time.sleep(5)
    
    # Ищем кнопку "Откликнуться"
    btn_open = page.query_selector('a.ui-button:has-text("Откликнуться")')
    print('Button found:', btn_open is not None)
    if btn_open:
        href = btn_open.get_attribute('href') or ''
        print('Href:', href)
        if '/payed/' in href:
            print('PAID PROJECT')
        btn_open.click(force=True)
        time.sleep(3)
    
    # Ждем появления textarea
    for _ in range(30):
        ta = page.query_selector('#project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer textarea')
        if ta:
            print('Textarea found!')
            break
        time.sleep(1)
    
    if not ta:
        # Попробуем найти все textarea
        textareas = page.query_selector_all('textarea')
        print('All textareas:', len(textareas))
        for i, ta in enumerate(textareas):
            print(f'  {i}: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
    
    # Ищем кнопку отправки
    submit_btns = page.query_selector_all('button:has-text("Отправить отклик"), button:has-text("Отправить"), button.ui-button._success:has-text("Отправить"), input[type=submit][value*="Отправит"]')
    print('Submit buttons found:', len(submit_btns))
    for btn in submit_btns:
        print('  Found submit:', btn.get_attribute('id'), btn.get_attribute('class'))
    
    input('Нажми Enter чтобы закрыть браузер...')
    browser.close()