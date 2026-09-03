import sys
sys.path.insert(0, '.')

import json
import os
import time
from playwright.sync_api import sync_playwright

COOKIES = 'fl_cookies.json'
SESSION_KEYS = ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

with open('fl_cookies.json', encoding='utf-8') as f:
    c = json.load(f)

print('Current cookies:')
for n in ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted'):
    if n in c and c[n]:
        print(f'  {n}: {c[n][:20]}...')

print('Opening browser to login...')

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False)
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.goto('https://www.fl.ru/login', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    
    print('Please log in manually in the browser...')
    print('After logging in, press Enter in THIS terminal...')
    sys.stdin.readline()
    
    # Check if user is logged in
    page_content = page.content()
    if 'Выйти' in page_content or 'Профиль' in page_content:
        print('User appears to be logged in')
    else:
        print('WARNING: User may not be logged in!')
        print('Page title:', page.title())
    
    cookies = ctx.cookies()
    print('All cookies:', [c['name'] for c in cookies])
    fl_cookies = {c['name']: c['value'] for c in cookies if 'fl.ru' in c.get('domain', '')}
    print('All fl.ru cookies:', list(fl_cookies.keys()))
    
    # Also get specific session cookies
    session_cookies = {c['name']: c['value'] for c in cookies if c['name'] in ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted')}
    print('Session cookies:', list(session_cookies.keys()))
    
    if not session_cookies:
        # Fallback: get all fl.ru cookies
        fl_all = {c['name']: c['value'] for c in cookies if 'fl.ru' in c.get('domain', '')}
        print('All fl.ru cookies:', list(fl_all.keys()))
        fl_cookies = fl_all
    else:
        fl_cookies = session_cookies
    
    with open('fl_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(fl_cookies, f, ensure_ascii=False, indent=1)
    print('Cookies saved to fl_cookies.json')
    
    input('Press Enter to close browser...')
    browser.close()