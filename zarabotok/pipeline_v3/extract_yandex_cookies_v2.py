import sqlite3
import json
import os
import shutil

cookie_path = os.path.expandvars(r'%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default\Network\Cookies')
temp_path = r'C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\Cookies_temp'

shutil.copy2(cookie_path, temp_path)

conn = sqlite3.connect(temp_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly, is_persistent
    FROM cookies
    WHERE host_key LIKE '%fl.ru%' OR host_key LIKE '%freelancer.com%'
    ORDER BY host_key, name
""")

cookies = {}
for row in cursor.fetchall():
    name, value, host, path, expires, secure, httponly, persistent = row
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

with open('fl_cookies_from_yandex.json', 'w', encoding='utf-8') as f:
    json.dump(cookies, f, ensure_ascii=False, indent=2)

print("Saved to fl_cookies_from_yandex.json with VALUES")

# Create simple cookie dicts for the bidders
fl_session = {}
for host, host_cookies in cookies.items():
    if 'www.fl.ru' in host or host == '.www.fl.ru':
        for name in ['PHPSESSID', 'XSRF-TOKEN', 'id', 'name', 'pwd', 'user_device_id', 'cookies_accepted', 'hidetopprjlenta', 'new_pf0', 'new_pf10']:
            if name in host_cookies:
                fl_session[name] = host_cookies[name]['value']

freelancer_session = {}
for host, host_cookies in cookies.items():
    if 'freelancer.com' in host:
        for name in ['GETAFREE_AUTH_HASH_V2', 'GETAFREE_USER_ID', 'GETAFREE_LANGUAGE', 'XSRF-TOKEN', 'session2', '_tracking_session', 'uniform_id_linked']:
            if name in host_cookies:
                freelancer_session[name] = host_cookies[name]['value']

# Also get .freelancer.com cookies
for host, host_cookies in cookies.items():
    if host == '.freelancer.com':
        for name in ['GETAFREE_AUTH_HASH_V2', 'GETAFREE_USER_ID', 'GETAFREE_LANGUAGE', 'XSRF-TOKEN']:
            if name in host_cookies:
                freelancer_session[name] = host_cookies[name]['value']

with open('fl_cookies.json', 'w', encoding='utf-8') as f:
    json.dump(fl_session, f, ensure_ascii=False, indent=2)
print("Updated fl_cookies.json")

with open('freelancer_cookies.json', 'w', encoding='utf-8') as f:
    json.dump(freelancer_session, f, ensure_ascii=False, indent=2)
print("Created freelancer_cookies.json")

print("\nFL.ru cookies:")
for k, v in fl_session.items():
    print(f"  {k}: {v[:30]}...")

print("\nFreelancer.com cookies:")
for k, v in freelancer_session.items():
    print(f"  {k}: {v[:30]}...")

os.remove(temp_path)