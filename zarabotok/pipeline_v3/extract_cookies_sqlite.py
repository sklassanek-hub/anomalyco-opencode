import sqlite3
import json
import os
import shutil

cookie_file = os.path.expanduser(r'~\AppData\Local\Yandex\YandexBrowser\User Data\Default\Network\Cookies')
temp_file = os.path.join(os.getcwd(), 'temp_cookies.db')
shutil.copy2(cookie_file, temp_file)

conn = sqlite3.connect(temp_file)
cursor = conn.cursor()
cursor.execute('SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key LIKE "%fl.ru%"')
rows = cursor.fetchall()

print('FL.ru cookies:')
for row in cursor.fetchall():
    host_key, name, value, path, expires_utc, is_secure, is_httponly = row
    if name in ('PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted'):
        print(f'  {name}: {value[:50]}...')
    elif 'fl.ru' in host_key:
        print(f'  {name}: {value[:50]}...')

conn.close()
os.remove(temp_file)