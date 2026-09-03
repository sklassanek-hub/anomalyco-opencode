import sqlite3, json, os, tempfile, shutil, base64
import win32crypt
from Cryptodome.Cipher import AES
LOCAL=os.environ.get("LOCALAPPDATA","")
def chrome_paths(browser):
    if browser=="edge":
        root=os.path.join(LOCAL,"Microsoft","Edge","User Data")
    elif browser=="yandex":
        root=os.path.join(LOCAL,"Yandex","YandexBrowser","User Data")
    else:
        root=os.path.join(LOCAL,"Google","Chrome","User Data")
    return os.path.join(root,"Default","Network","Cookies"), os.path.join(root,"Local State")
def get_key(state_path):
    import json as j
    with open(state_path,"r",encoding="utf-8") as f:
        state=j.load(f)
    key_b64=state["os_crypt"]["encrypted_key"]
    key=base64.b64decode(key_b64)[5:]
    return win32crypt.CryptUnprotectData(key,None,None,None,0)[1]
def decrypt(ev,key):
    if ev[:3]==b"v10":
        nonce=ev[3:15]
        ct=ev[15:]
        cipher=AES.new(key,AES.MODE_GCM,nonce=nonce)
        return cipher.decrypt_and_verify(ct[:-16],ct[-16:])
    if ev[:3]==b"v20":
        nonce=ev[3:15]
        ct=ev[15:]
        cipher=AES.new(key,AES.MODE_GCM,nonce=nonce)
        try:
            return cipher.decrypt_and_verify(ct[:-16],ct[-16:])
        except: return b""
    return win32crypt.CryptUnprotectData(ev,None,None,None,0)[1]

for browser in ["yandex","edge"]:
    cookies_path, state_path = chrome_paths(browser)
    print(f"\n=== {browser} ===")
    if not os.path.exists(cookies_path):
        print("no db")
        continue
    try:
        key=get_key(state_path)
    except Exception as e:
        print("key err",e)
        continue
    tmp=os.path.join(tempfile.gettempdir(),f"cookies_{browser}.db")
    try:
        shutil.copy2(cookies_path, tmp)
    except Exception as e:
        print("copy err",e)
        continue
    con=sqlite3.connect(tmp)
    rows=con.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%freelance.ru' OR host_key LIKE '%weblancer%' OR host_key LIKE '%fl.ru'").fetchall()
    con.close()
    print(f"rows {len(rows)}")
    for host,name,ev in rows[:10]:
        try:
            val=decrypt(ev,key).decode('utf-8')
            print(f" {host} {name}={val[:40]}")
        except Exception as e:
            print(f"  {host} {name} decrypt err {e}")
