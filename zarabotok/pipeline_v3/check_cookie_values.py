import sqlite3
import os
import shutil

cookie_path = os.path.expandvars(r'%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default\Network\Cookies')
temp_path = r'Cookies_temp'

shutil.copy2(cookie_path, temp_path)

conn = sqlite3.connect(temp_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT name, value, host_key FROM cookies 
    WHERE host_key LIKE '%fl.ru%' OR host_key LIKE '%freelancer.com%' 
    ORDER BY host_key, name
""")

for row in cursor.fetchall():
    name, value, host = row
    print(f'{host} | {name} = {value[:50] if value else "EMPTY"}')

conn.close()
os.remove(temp_path)