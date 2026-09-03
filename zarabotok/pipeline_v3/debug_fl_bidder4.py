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
    page.on('response', lambda r: print(f'RESPONSE: {r.status} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url else None)
    
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
        
        # Check for textarea
        print('Looking for textarea...')
        ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea')
        if ta:
            print('Textarea found immediately!')
        else:
            # Wait for dynamic content
            print('Waiting for dynamic content...')
            for i in range(30):
                time.sleep(1)
                ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea, .project-offer-block textarea')
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
        
        if not ta:
            # Check all textareas
            textareas = page.query_selector_all('textarea')
            print('All textareas:', len(textareas))
            for i, ta in enumerate(textareas):
                print(f'  {i}: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
        
        # Check for form containers
        offer_containers = page.query_selector_all('[id*="offer"], [class*="offer"]')
        print('Offer containers:', len(offer_containers))
        for i, el in enumerate(offer_containers[:10]):
            tag = el.evaluate('el => el.tagName')
            print(f'  {i}: tag={tag}, id={el.get_attribute("id")}, class={el.get_attribute("class")}')
            ta = el.query_selector('textarea')
            if ta:
                print(f'    Found textarea in container: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        # Look for submit buttons
        submit_btns = page.query_selector_all('button:has-text("Отправить отклик"), button:has-text("Отправить"), button.ui-button._success:has-text("Отправить"), input[type=submit][value*="Отправит"]')
        print('Submit buttons found:', len(submit_btns))
        for btn in submit_btns:
            print('  Found submit:', btn.get_attribute('id'), btn.get_attribute('class'))
        
        input('Нажми Enter чтобы закрыть браузер...')
        browser.close()