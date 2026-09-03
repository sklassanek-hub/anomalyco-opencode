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
    
    # Enable request/response logging
    page.on('response', lambda r: print(f'RESPONSE: {r.status} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url or 'answer' in r.url else None)
    page.on('request', lambda r: print(f'REQUEST: {r.method} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url or 'answer' in r.url else None)
    
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
        
        # Click and wait for network
        print('Clicking button...')
        btn_open.click(force=True)
        print('Clicked, waiting for response...')
        
        # Wait for network to settle
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(3)
        
        # Check for textarea - try to wait for it to appear
        print('Looking for textarea...')
        ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea')
        if ta:
            print('Textarea found immediately!')
        else:
            # Wait for dynamic content
            print('Waiting for dynamic content...')
            for i in range(60):
                time.sleep(1)
                # Try multiple selectors
                ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea, .project-offer-block textarea, .project-offer textarea')
                if ta:
                    print(f'Textarea found at attempt {i+1}!')
                    break
                # Also check for any new textarea
                textareas = page.query_selector_all('textarea')
                if len(textareas) > 2:
                    print(f'  New textareas found: {len(textareas)}')
                    for j, ta in enumerate(textareas):
                        print(f'  {j}: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
                    break
                # Check for form containers
                forms = page.query_selector_all('form[id*="offer"], form[class*="offer"], div[id*="offer"], div[class*="offer"]')
                if forms:
                    print(f'  Forms found: {len(forms)}')
                    for f in forms[:5]:
                        print(f'  Form: id={f.get_attribute("id")}, class={f.get_attribute("class")}, action={f.get_attribute("action")}')
                        ta = f.query_selector('textarea')
                        if ta:
                            print(f'    Found textarea in form: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
                # Check for form containers
                forms = page.query_selector_all('form[id*="offer"], form[class*="offer"], div[id*="offer"], div[class*="offer"]')
                if forms:
                    print(f'  Forms found: {len(forms)}')
                    for f in forms[:5]:
                        print(f'  Form: id={f.get_attribute("id")}, class={f.get_attribute("class")}, action={f.get_attribute("action")}')
                        ta = f.query_selector('textarea')
                        if ta:
                            print(f'    Found textarea in form: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
                # Check for form containers
                forms = page.query_selector_all('form[id*="offer"], form[class*="offer"], div[id*="offer"], div[class*="offer"]')
                if forms:
                    print(f'  Forms found: {len(forms)}')
                    for f in forms[:5]:
                        print(f'  Form: id={f.get_attribute("id")}, class={f.get_attribute("class")}, action={f.get_attribute("action")}')
                        ta = f.query_selector('textarea')
                        if ta:
                            print(f'    Found textarea in form: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        if not ta:
            # Check for any new textareas
            textareas = page.query_selector_all('textarea')
            print(f'Total textareas: {len(textareas)}')
            for j, ta in enumerate(textareas):
                print(f'  {j}: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
            
            # Check for forms
            forms = page.query_selector_all('form')
            print(f'Forms: {len(forms)}')
            for f in forms[:5]:
                print(f'  Form: id={f.get_attribute("id")}, class={f.get_attribute("class")}, action={f.get_attribute("action")}')
                ta = f.query_selector('textarea')
                if ta:
                    print(f'  Textarea in form: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        # Check for submit buttons
        submit_btns = page.query_selector_all('button:has-text("Отправить отклик"), button:has-text("Отправить"), button.ui-button._success:has-text("Отправить"), input[type=submit][value*="Отправит"]')
        print('Submit buttons found:', len(submit_btns))
        for btn in submit_btns:
            print('  Found submit:', btn.get_attribute('id'), btn.get_attribute('class'))
        
        # Check for any buttons with "Отправить" text
        send_btns = page.query_selector_all('button:has-text("Отправить"), a:has-text("Отправить")')
        print('Send buttons:', len(send_btns))
        for btn in send_btns:
            print(f'  {btn.get_attribute("id")} - {btn.get_attribute("class")} - {btn.inner_text()[:30] if btn.inner_text() else ""}')
        
        input('Нажми Enter чтобы закрыть браузер...')
        browser.close()