"""Обмен code -> access_token для ЮMoney. Запуск: python tools/yoomoney_auth.py --code <code> --client-id <id> [--client-secret <sec>] [--redirect-uri <uri>]

Также можно вызвать интерактивно: python tools/yoomoney_auth.py (спросит поля).
"""
import argparse
import sys
sys.path.insert(0, ".")
from modules import yoomoney

def main():
    p = argparse.ArgumentParser(description="ЮMoney OAuth: code -> access_token")
    p.add_argument("--code", help="временный code из redirect_uri")
    p.add_argument("--client-id", dest="client_id", help="client_id приложения")
    p.add_argument("--client-secret", dest="client_secret", default="", help="client_secret если с проверкой подлинности")
    p.add_argument("--redirect-uri", dest="redirect_uri", default="", help="redirect_uri как при authorize")
    a = p.parse_args()
    code = a.code or input("code: ").strip()
    client_id = a.client_id or input("client_id: ").strip()
    client_secret = a.client_secret or ""
    if not client_secret:
        # спросить опционально
        try:
            cs = input("client_secret (Enter если без него): ").strip()
            client_secret = cs
        except Exception:
            pass
    redirect_uri = a.redirect_uri or input("redirect_uri: ").strip()
    res = yoomoney.exchange_code(code, client_id, client_secret, redirect_uri)
    print(res)
    if "access_token" in res:
        print("Токен сохранён в state/yoomoney_token.json и config.json")
        return 0
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
