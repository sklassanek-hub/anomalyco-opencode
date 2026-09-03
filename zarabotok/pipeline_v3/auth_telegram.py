"""CLI-авторизация Telegram (в консоли): auth_telegram.py <session> <phone> | --code <code> | --pwd <пароль>"""
import asyncio
import sys

from modules import tg_auth


async def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print("usage: auth_telegram.py <session> <phone> | auth_telegram.py <session> --code <code> | --pwd <pwd>")
        return 1
    session = args[0]
    ok, me = await tg_auth.check_auth(session)
    if ok:
        print(f"OK: {session} уже авторизован (@{me})")
        return 0
    if args[1] == "--code":
        print(await tg_auth.sign_in_code(session, args[2]))
    elif args[1] == "--pwd":
        print(await tg_auth.sign_in_pwd(session, args[2]))
    else:
        print(await tg_auth.send_code(session, args[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))