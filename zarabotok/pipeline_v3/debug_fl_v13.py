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
    
    page.on('response', lambda r: print(f'RESPONSE: {r.status} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url or 'answer' in r.url or 'project' in r.url or 'offer' in r.url or 'xajax' in r.url else None)
    page.on('request', lambda r: print(f'REQUEST: {r.method} {r.url}') if 'offer' in r.url or 'message' in r.url or 'bid' in r.url or 'answer' in r.url or 'project' in r.url or 'offer' in r.url or 'xajax' in r.url else None)
    
    page.goto('https://www.fl.ru/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', locale='ru-RU', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    ctx.add_cookies(session)
    page.goto('https://www.fl.ru/projects/5519809/', wait_until='domcontentloaded', timeout=60000)
    time.sleep(5)
    
    btn = page.query_selector('a.ui-button:has-text("Откликнуться")')
    print('Button:', btn is not None)
    if btn:
        btn.click()
        print('Clicked')
        
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(3)
        
        print(f'Current URL: {page.url}')
        
        modals = page.query_selector_all('.modal, [role=dialog], .ui-modal, .ui-modal-overlay')
        print(f'Modals: {len(modals)}')
        for m in modals:
            print(f'  Modal: {m.get_attribute("class")}')
        
        overlays = page.query_selector_all('.ui-overlay, .modal-backdrop, .ui-widget-overlay')
        print(f'Overlays: {len(overlays)}')
        
        offer_elements = page.query_selector_all('[class*="offer"], [id*="offer"]')
        print(f'Offer elements: {len(offer_elements)}')
        for i, el in enumerate(offer_elements[:10]):
            tag = el.evaluate('el => el.tagName')
            print(f'  {i}: tag={tag}, id={el.get_attribute("id")}, class={el.get_attribute("class")}')
            ta = el.query_selector('textarea')
            if ta:
                print(f'  Textarea: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        time.sleep(5)
        
        ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea')
        if ta:
            print('Textarea found immediately!')
        else:
            print('No textarea found immediately')
        
        time.sleep(5)
        
        ta = page.query_selector('textarea[name="descr"], textarea[name="text"], textarea[name="message"], #project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea')
        if ta:
            print('Textarea found after wait!')
        else:
            print('No textarea found after wait')
        
        offer_elements = page.query_selector_all('[class*="offer"], [id*="offer"]')
        print(f'Offer elements found: {len(offer_elements)}')
        for i, el in enumerate(offer_elements[:10]):
            tag = el.evaluate('el => el.tagName')
            print(f'  {i}: tag={tag}, id={el.get_attribute("id")}, class={el.get_attribute("class")}')
            ta = el.query_selector('textarea')
            if ta:
                print(f'  Textarea: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}')
        
        time.sleep(5)
        
        modals = page.query_selector_all('.modal, [role=dialog], .ui-modal, .ui-modal-overlay')
        print(f'Modals: {len(modals)}')
        for m in modals:
            print(f'  Modal: {m.get_attribute("class")}')
        
        overlays = page.query_selector_all('.ui-overlay, .modal-backdrop, .ui-widget-overlay')
        print(f'Overlays: {len(overlays)}')
        
        textareas = page.query_selector_all('textarea')
        print(f'Total textareas: {len(textareas)}')
        for j, ta in enumerate(textareas):
            print(f'  {j}: name={ta.get_attribute("name")}, id={ta.get_attribute("id")}, class={ta.get_attribute("class")}')
        
        send_btns = page.query_selector_all('button:has-text("Отправить"), a:has-text("Отправить")')
        print('Send buttons:', len(send_btns))
        for btn in send_btns:
            print(f'  {btn.get_attribute("id")} - {btn.get_attribute("class")} - {btn.inner_text()[:30] if btn.inner_text() else ""}')
        
        input('Press Enter...')
        browser.close()