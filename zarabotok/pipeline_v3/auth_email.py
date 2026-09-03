"""Проверка почты: ввод SMTP/IMAP настроек в state/settings.json и тест.

Запуск: python auth_email.py
Поддерживает gmail.com / yandex.ru / mail.ru (нужен пароль приложения).
"""
import getpass
import json
import smtplib
import sys

from modules import store

PROVIDERS = {
    "gmail": {"smtp_host": "smtp.gmail.com", "smtp_port": 465, "imap_host": "imap.gmail.com", "imap_port": 993},
    "yandex": {"smtp_host": "smtp.yandex.ru", "smtp_port": 465, "imap_host": "imap.yandex.ru", "imap_port": 993},
    "mailru": {"smtp_host": "smtp.mail.ru", "smtp_port": 465, "imap_host": "imap.mail.ru", "imap_port": 993},
}


def main() -> int:
    settings = store.load("settings", {})
    email_cfg = settings.get("email", {})
    address = input(f"Адрес почты [{email_cfg.get('smtp_user', '')}]: ").strip() or email_cfg.get("smtp_user", "")
    if not address:
        print("адрес обязателен")
        return 1
    passwd = getpass.getpass("Пароль приложения (для gmail/yandex — отдельный пароль для приложений): ")
    domain = address.split("@")[-1]
    prov = "mailru" if domain == "mail.ru" else "yandex" if domain == "yandex.ru" else "gmail"
    cfg = dict(PROVIDERS[prov])
    cfg.update({"smtp_user": address, "smtp_pass": passwd})
    try:
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=20) as smtp:
            smtp.login(address, passwd)
            print(f"SMTP OK ({cfg['smtp_host']})")
    except Exception as e:
        print(f"SMTP FAIL: {e}")
        return 1
    settings["email"] = cfg
    store.save("settings", settings)
    print("Настройки сохранены в state/settings.json. Отклики на почту отправляются после approved=True.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())