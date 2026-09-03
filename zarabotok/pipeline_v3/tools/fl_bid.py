# -*- coding: utf-8 -*-
"""Отправляет отклик на заказ fl.ru через Playwright-Edge с куками из fl_cookies.json.
Использование: python fl_bid.py <url> "<текст отклика>"
"""
import sys, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

COOKIES = r'C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\fl_cookies.json'
URL = sys.argv[1]
TEXT = sys.argv[2] if len(sys.argv) > 2 else ''

c = json.load(open(COOKIES, encoding='utf-8'))
SESSION = []
for name in ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted'):
    if name in c:
        SESSION.append({'name': name, 'value': c[name], 'domain': '.www.fl.ru', 'path': '/'})

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.goto('https://www.fl.ru/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(8)
    ctx.add_cookies(SESSION)
    page.goto(URL, wait_until='domcontentloaded', timeout=60000)
    time.sleep(6)
    print('title:', page.title()[:90])
    # заполняем textarea формы отклика
    ta = page.query_selector('#vacancy-offer textarea')
    if not ta:
        print('НЕТ формы отклика!')
        browser.close()
        sys.exit(2)
    ta.fill(TEXT)
    time.sleep(1)
    print('текст введён:', len(TEXT), 'символов')
    # жмём кнопку
    btn = page.query_selector('#vacancy-offer button.js-send-button-viewport, button:has-text("Отправить отклик")')
    if not btn:
        print('НЕТ кнопки отправки')
        browser.close()
        sys.exit(3)
    btn.click()
    time.sleep(6)
    body = page.inner_text('body')
    ok_markers = ['Ваш отклик отправлен', 'отклик отправлен', 'Отклик отравлен', 'Спасибо за отклик']
    fail_markers = ['не отправлен', 'ошибка', 'заполните', 'слишком короткий', 'попробуйте еще раз']
    print('--- проверка результата ---')
    low = body.lower()
    for m in ok_markers:
        if m.lower() in low:
            print('УСПЕХ маркер:', m)
    for m in fail_markers:
        if m.lower() in low:
            print('ОШИБКА маркер:', m)
    open(r'C:\Users\klass\AppData\Local\Temp\opencode\fl_bid_result.txt', 'w', encoding='utf-8').write(body)
    print('--- хвост страницы ---')
    print(body[-800:])
    cookie_fl = {x['name']: x['value'] for x in ctx.cookies() if 'fl.ru' in x.get('domain', '')}
    json.dump(cookie_fl, open(COOKIES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    browser.close()