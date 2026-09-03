import sys
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
import json, os, time, sys

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

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
    
    # Ищем все textarea
    textareas = page.query_selector_all('textarea')
    print('Textareas found:', len(textareas))
    for i, ta in enumerate(textareas):
        print('  {}: name={}, id={}, class={}'.format(i, 
            ta.get_attribute('name'), ta.get_attribute('id'), ta.get_attribute('class')))
    
    # Ищем ссылку "Откликнуться" или кнопку
    reply_links = page.query_selector_all('a:has-text("Откликнуться"), button:has-text("Откликнуться"), a:has-text("Отклик"), button:has-text("Отклик")')
    print('Reply links/buttons found:', len(reply_links))
    for i, link in enumerate(reply_links):
        try:
            text = link.inner_text()[:50]
        except:
            text = '...'
        print('  {}: text={}, class={}, id={}, tag={}'.format(i, text, 
            link.get_attribute('class'), link.get_attribute('id'), link.evaluate('el => el.tagName')))
    
    # Ищем все кнопки
    buttons = page.query_selector_all('button, input[type=submit], input[type=button], a[role=button]')
    print('Buttons/inputs found:', len(buttons))
    for i, btn in enumerate(buttons[:20]):
        try:
            text = btn.inner_text()[:50] if btn.inner_text() else ''
        except:
            text = '...'
        print('  {}: text={}, class={}, id={}, tag={}'.format(i, text[:30], 
            btn.get_attribute('class'), btn.get_attribute('id'), btn.evaluate('el => el.tagName')))
    
    # Ищем форму в контейнере отклика
    offer_containers = page.query_selector_all('[id*="offer"], [class*="offer"], [id*="comment"], [class*="comment"]')
    print('Offer/comment related elements:', len(offer_containers))
    for i, el in enumerate(offer_containers[:10]):
        print('  {}: tag={}, id={}, class={}'.format(i, 
            el.evaluate('el => el.tagName'), el.get_attribute('id'), el.get_attribute('class')))
    
    # Ищем textarea внутри контейнеров
    for container in page.query_selector_all('[id*="offer"], [class*="offer"]'):
        textarea = container.query_selector('textarea')
        if textarea:
            print('Found textarea in container:', textarea.get_attribute('name'), textarea.get_attribute('id'))
    
    # Ищем кнопку отправки
    submit_btns = page.query_selector_all('button:has-text("Отправить"), button:has-text("Отправить отклик"), input[type=submit][value*="Отправит"], button:has-text("Ответить")')
    print('Submit buttons found:', len(submit_btns))
    for btn in submit_btns:
        print('  Found submit:', btn.get_attribute('id'), btn.get_attribute('class'))
    
    input('Нажми Enter чтобы закрыть браузер...')
    browser.close()