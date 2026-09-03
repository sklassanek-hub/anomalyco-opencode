"""ЮMoney OAuth + проверка оплат по operation-history.

Хранение токена: state/yoomoney_token.json (plain, chmod 600 на Linux; на Windows — ACL по умолчанию).
Получение токена: tools/yoomoney_auth.py или прямой вызов exchange_code().
Проверка оплат: billing.check_yoomoney_payments() вызывает этот модуль.
"""
import json
import os
import urllib.parse
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "yoomoney_token.json")
WALLET = "4100119458306656"


def _load_cfg() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def get_token() -> str | None:
    """Токен из state/yoomoney_token.json или config.payment.methods.yoomoney.token."""
    # 1) файл state
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            d = json.load(f)
            t = (d.get("access_token") or "").strip()
            if t:
                return t
    except Exception:
        pass
    # 2) config
    try:
        p = _load_cfg().get("payment", {}).get("methods", {}).get("yoomoney", {})
        t = (p.get("token") or p.get("access_token") or "").strip()
        if t:
            return t
    except Exception:
        pass
    return None


def save_token(access_token: str):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except Exception:
        pass


def exchange_code(code: str, client_id: str, client_secret: str = "", redirect_uri: str = "") -> dict:
    """Обмен code -> access_token по доке yoomoney.ru/oauth/token.

    Возвращает {"access_token": "..."} при успехе или {"error": "..."}.
    code — одноразовый, при ошибке invalid_grant нужно заново пройти authorize.
    """
    if not code or not client_id:
        return {"error": "invalid_request: code и client_id обязательны"}
    data = {
        "code": code.strip(),
        "client_id": client_id.strip(),
        "grant_type": "authorization_code",
        "redirect_uri": (redirect_uri or "").strip(),
    }
    if client_secret and client_secret.strip():
        data["client_secret"] = client_secret.strip()
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request("https://yoomoney.ru/oauth/token", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode())
    except Exception as e:
        # пробуем прочитать тело ошибки
        try:
            import http.client as _hc
            if hasattr(e, "read"):
                resp = json.loads(e.read().decode())
                return resp
        except Exception:
            pass
        return {"error": f"network: {type(e).__name__}: {str(e)[:120]}"}
    if "access_token" in resp and resp["access_token"]:
        save_token(resp["access_token"])
        # зеркалим в config для удобства (не перезаписываем client_id etc)
        try:
            cfg = _load_cfg()
            ym = cfg.setdefault("payment", {}).setdefault("methods", {}).setdefault("yoomoney", {})
            ym["token"] = resp["access_token"]
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
    return resp


def operation_history(access_token: str, records: int = 20, start_record: str = "") -> dict:
    """POST https://yoomoney.ru/api/operation-history — требует Bearer токена."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"records": str(records)}
    if start_record:
        data["start_record"] = start_record
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request("https://yoomoney.ru/api/operation-history", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def check_payments() -> int:
    """Сверка входящих операций ЮMoney с открытыми счетами по label==invoice.no.

    label должен совпадать с номером счёта (ZB-...); сумма — точное совпадение ±0.01.
    Идемпотентно: уже отмеченные счета пропускает.
    Возвращает число подтверждённых счетов.
    """
    token = get_token()
    if not token:
        return 0
    # загружаем открытые счета
    try:
        from modules import billing, store
    except Exception:
        return 0
    open_inv = [i for i in billing._load() if i.get("status") in ("draft", "sent", "issued")]
    # ЮMoney счета — method yoomoney или без метода но с wallet
    open_inv = [i for i in open_inv if (i.get("method") or "yoomoney").lower() == "yoomoney"]
    if not open_inv:
        return 0
    by_label = {str(i.get("no")).strip(): i for i in open_inv}
    # запрашиваем последние операции
    try:
        data = operation_history(token, records=30)
    except Exception:
        return 0
    ops = data.get("operations") or []
    n = 0
    for op in ops:
        if op.get("direction") != "in" or op.get("status") != "success":
            continue
        label = str(op.get("label") or "").strip()
        if not label or label not in by_label:
            continue
        inv = by_label[label]
        try:
            amt = float(str(op.get("amount", 0)).replace(",", "."))
        except Exception:
            continue
        if abs(amt - float(inv.get("amount", 0))) > 0.01:
            # несовпадение суммы — логируем отдельно, не подтверждаем
            continue
        # идемпотентно
        if inv.get("status") == "paid":
            continue
        billing.mark_paid(inv["no"])
        n += 1
    return n
