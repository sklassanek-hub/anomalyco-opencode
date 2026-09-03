import sys
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
import json, os, time

COOKIES = 'fl_cookies.json'
SESSION_KEYS = ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

with open('fl_cookies.json', encoding='utf-8') as f:
    c = json.load(f)

session = [{'name': n, 'value': c[n], 'domain': '.www.fl.ru', 'path': '/'} for n in ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted') if n in c and c[n]]
print('Cookies loaded:', len(session))

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False)
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    
    page.on('response', lambda r: print(f'RESPONSE: {r.status} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url or 'answer' in r.url else None)
    page.on('request', lambda r: print(f'REQUEST: {r.method} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url else None)
    
    page.goto('https://www.fl.ru/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    ctx.add_cookies(session)
    page.goto('https://www.fl.ru/projects/5519809/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    
    # Click button
    btn = page.query_selector('a.ui-button:has-text("Откликнуться")')
    print('Button:', btn is not None)
    if btn:
        btn.click()
        print('Clicked')
        
        # Wait for response - try to wait for the form to appear
        print('Waiting for form to load...')
        for i in range(60):
            time.sleep(1)
            # Check for form
            forms = page.query_selector_all('form')
            if forms:
                print(f'Forms found: {len(forms)}')
                for f in forms:
                    print(f'  Form: id={f.get_attribute("id")}, class={f.get_attribute("class")}, action={f.get_attribute("action")}')
                    ta = f.query_selector('textarea')
                    if ta:
                        print(f'  Textarea: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
                        break
                if forms:
                    break
            
            # Check for iframes
            iframes = page.query_selector_all('iframe')
            print('Iframes:', len(iframes))
            for i, iframe in enumerate(iframes):
                src = iframe.get_attribute('src')
                print(f'  Iframe {i}: src={src}')
                try:
                    frame = iframe.content_frame()
                    if frame:
                        ta = frame.query_selector('textarea')
                        if ta:
                            print(f'    Textarea in iframe: {ta.get_attribute("name")}')
                except:
                    pass
            
            # Check all elements with "offer" in class/id
            offer_els = page.query_selector_all('[class*="offer"], [id*="offer"]')
            print('Offer elements:', len(offer_els))
            for el in offer_els[:10]:
                tag = el.evaluate('el => el.tagName')
                print(f'  {tag}: id={el.get_attribute("id")}, class={el.get_attribute("class")}')
                ta = el.query_selector('textarea')
                if ta:
                    print(f'  Textarea: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        # Check modals
        modals = page.query_selector_all('.modal, [role=dialog], .ui-modal, .ui-modal-overlay')
        print('Modals:', len(modals))
        for m in modals:
            print(f'  Modal: {m.get_attribute("class")}')
        
        # Check overlays
        overlays = page.query_selector_all('.ui-overlay, .modal-backdrop, .ui-widget-overlay')
        print('Overlays:', len(overlays))
        
        # Check textareas
        textareas = page.query_selector_all('textarea')
        print('Textareas:', len(textareas))
        for ta in textareas:
            print(f'  name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
        
        input('Press Enter...')
        browser.close()