import sqlite3
import json
import os
import shutil
from datetime import datetime

# Path to Yandex Browser cookies
cookie_path = os.path.expandvars(r'%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default\Network\Cookies')
temp_path = r'C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\Cookies_temp'

# Copy the file (browser may have it locked)
shutil.copy2(cookie_path, temp_path)

conn = sqlite3.connect(temp_path)
cursor = conn.cursor()

# Check schema
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

# Cookies table schema
cursor.execute("PRAGMA table_info(cookies);")
for col in cursor.fetchall():
    print(col)

# Query for FL.ru cookies
cursor.execute("""
    SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly, is_persistent
    FROM cookies
    WHERE host_key LIKE '%fl.ru%' OR host_key LIKE '%freelancer.com%'
    ORDER BY host_key, name
""")

cookies = {}
for row in cursor.fetchall():
    name, value, host, path, expires, secure, httponly, persistent = row
    print(f"  {host} / {path} : {name} = {value[:50]}... (expires: {expires}, secure: {secure}, httponly: {httponly}, persistent: {persistent})")
    
    if host not in cookies:
        cookies[host] = {}
    cookies[host][name] = {
        'value': value,
        'path': path,
        'expires_utc': expires,
        'secure': bool(secure),
        'httponly': bool(httponly),
        'persistent': bool(persistent)
    }

conn.close()

# Save to JSON
with open('fl_cookies_from_yandex.json', 'w', encoding='utf-8') as f:
    json.dump(cookies, f, ensure_ascii=False, indent=2)

print("\nSaved to fl_cookies_from_yandex.json")

# Also check for specific session cookies we need
print("\n=== Session cookies for FL.ru ===")
for host, host_cookies in cookies.items():
    if 'fl.ru' in host:
        for name in ['PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted']:
            if name in host_cookies:
                print(f"  {name}: {host_cookies[name]['value'][:50]}...")

print("\n=== Session cookies for Freelancer.com ===")
for host, host_cookies in cookies.items():
    if 'freelancer.com' in host:
        for name, data in host_cookies.items():
            print(f"  {name}: {data['value'][:50]}...")

# Cleanup
os.remove(temp_path)