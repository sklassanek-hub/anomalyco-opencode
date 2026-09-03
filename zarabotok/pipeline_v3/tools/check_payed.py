import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from modules import http_client as hc
import re, time
urls = [
'https://www.fl.ru/projects/5518870/',
'https://www.fl.ru/projects/5518864/',
'https://www.fl.ru/projects/5518877/',
'https://www.fl.ru/projects/5518838/',
'https://www.fl.ru/projects/5518844/',
'https://www.fl.ru/projects/5518847/',
'https://www.fl.ru/projects/5518816/',
'https://www.fl.ru/projects/5518655/',
'https://www.fl.ru/projects/5518636/',
'https://www.fl.ru/projects/5519309/',
'https://www.fl.ru/projects/5519306/',
'https://www.fl.ru/projects/5519305/',
]
s = hc.client('fl.ru')
for url in urls:
    try:
        r = s.get(url, timeout=20)
        if r.status_code != 200:
            print(url, 'http', r.status_code)
            continue
        m = re.search(r'href=\"([^\"]*payed[^\"]*)\"', r.text)
        has_payed = bool(m)
        # также ищем кнопку Откликнуться
        has_btn = 'Откликнуться' in r.text
        print(f"{url.split('/')[-2]} {'PAYED' if has_payed else 'FREE '} | btn={has_btn} | {r.text[ r.text.find('Откликнуться')-30 : r.text.find('Откликнуться')+80] if has_btn else 'no btn'}")
    except Exception as e:
        print(url, 'err', e)
    time.sleep(1)
