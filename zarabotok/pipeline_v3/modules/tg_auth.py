"""Авторизация Telegram как модуль (используется дашбордом и CLI)."""
import asyncio
import json
import os
import time

from telethon.errors import PhoneCodeExpiredError, PhoneCodeInvalidError, SessionPasswordNeededError

from modules import http_client, store, tg_common

AUTH_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "tg_auth.json")


def load_ctx() -> dict:
    try:
        with open(AUTH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_ctx(d: dict):
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def _client(session: str):
    return tg_common.tg_client(tg_common.session_path(session), proxy=http_client.socks_args())


async def check_auth(session: str) -> tuple[bool, str]:
    client = _client(session)
    await client.connect()
    ok = await client.is_user_authorized()
    me = ""
    if ok:
        try:
            me = str((await client.get_me()).username)
        except Exception:
            pass
    await client.disconnect()
    return ok, me


async def send_code(session: str, phone: str) -> str:
    client = _client(session)
    await client.connect()
    try:
        result = await client.send_code_request(phone)
    except Exception as e:
        await client.disconnect()
        return f"ОШИБКА: {type(e).__name__}: {str(e)[:120]}"
    save_ctx({"phone": phone, "hash": result.phone_code_hash, "session": session})
    await client.disconnect()
    return "Код отправлен в Telegram"


async def sign_in_code(session: str, code: str) -> str:
    client = _client(session)
    await client.connect()
    ctx = load_ctx()
    try:
        await client.sign_in(phone=ctx.get("phone", ""), code=code, phone_code_hash=ctx.get("hash", ""))
    except SessionPasswordNeededError:
        await client.disconnect()
        return "Нужен пароль 2FA (поле пароль_2fa)"
    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        await client.disconnect()
        return f"Код неверный/истёк: {e}"
    except Exception as e:
        await client.disconnect()
        return f"ОШИБКА: {type(e).__name__}: {str(e)[:120]}"
    me = await client.get_me()
    await client.disconnect()
    settings = store.load("settings", {})
    settings["tg_poll"] = True
    store.save("settings", settings)
    return f"ГОТОВО: авторизован ({me.first_name} @{me.username})"


async def sign_in_pwd(session: str, pwd: str) -> str:
    client = _client(session)
    await client.connect()
    try:
        await client.sign_in(password=pwd)
    except Exception as e:
        await client.disconnect()
        return f"ОШИБКА 2FA: {str(e)[:120]}"
    me = await client.get_me()
    await client.disconnect()
    return f"ГОТОВО: авторизован ({me.first_name} @{me.username})"


async def qr_login(session: str, timeout: float = 180.0, on_qr=None) -> tuple[str, bytes]:
    """QR-вход с автообновлением токена: если QR истёк до сканирования,
    генерируется новый и on_qr вызывается повторно с новой картинкой.
    Возвращает (статус, PNG). Статусы: 'ok: …' — авторизован; '2fa: …' — нужен пароль;
    'timeout'; 'error: …'."""
    import io

    import qrcode

    client = _client(session)
    try:
        await client.connect()
    except Exception as e:
        return f"error: {type(e).__name__}: {str(e)[:120]}", b""
    try:
        me = await client.get_me()
        settings = store.load("settings", {})
        settings["tg_poll"] = True
        store.save("settings", settings)
        return f"ok: {me.first_name} @{me.username} (уже авторизован)", b""
    except Exception:
        pass
    deadline = time.monotonic() + timeout
    png_bytes = b""
    while time.monotonic() < deadline:
        try:
            qr = await client.qr_login()
            buf = io.BytesIO()
            qrcode.make(qr.url).save(buf, format="PNG")
            png_bytes = buf.getvalue()
            if on_qr:
                try:
                    on_qr(png_bytes)
                except Exception:
                    pass
            await qr.wait(min(45.0, deadline - time.monotonic()))
        except asyncio.TimeoutError:
            continue
        except SessionPasswordNeededError:
            await client.disconnect()
            return "2fa: учётка защищена паролем — введи его в форму 2FA на дашборде", png_bytes
        except Exception as e:
            await client.disconnect()
            return f"error: {type(e).__name__}: {str(e)[:120]}", png_bytes if png_bytes else b""
        try:
            me = await client.get_me()
        except Exception as e:
            await client.disconnect()
            return f"error: {type(e).__name__}: {str(e)[:120]}", png_bytes
        await client.disconnect()
        settings = store.load("settings", {})
        settings["tg_poll"] = True
        store.save("settings", settings)
        return f"ok: {me.first_name} @{me.username}", png_bytes
    await client.disconnect()
    return "timeout", png_bytes