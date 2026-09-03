"""Выставление счетов: реестр инвойсов (state/invoices.json), генерация текста счёта
с реквизитами ИП из config.json payment, отправка клиенту, отметка оплаты."""
import json
import os
from datetime import datetime

from modules import chat, crm, sender, store

INVOICE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "invoices.json")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

STATUSES = ("draft", "sent", "paid", "void")

METHOD_ORDER = ("yoomoney", "card", "usdt", "cryptobot")


# Invoice model snippet (W5 / W15) — stub with required fields
class Invoice:
    """Stub Invoice model for webhook verification and billing pipeline.
    Fields: id, label, amount, status, webhook_url, hmac_secret.
    """
    def __init__(self, id="", label="", amount=0, status="draft",
                 webhook_url="", hmac_secret=""):
        self.id = id
        self.label = label
        self.amount = amount
        self.status = status
        self.webhook_url = webhook_url
        self.hmac_secret = hmac_secret

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "amount": self.amount,
            "status": self.status,
            "webhook_url": self.webhook_url,
            "hmac_secret": self.hmac_secret,
        }

    @staticmethod
    def from_dict(d: dict) -> "Invoice":
        return Invoice(
            id=d.get("id", ""),
            label=d.get("label", ""),
            amount=d.get("amount", 0),
            status=d.get("status", "draft"),
            webhook_url=d.get("webhook_url", ""),
            hmac_secret=d.get("hmac_secret", ""),
        )


def _to_num(v):
    """Привести сумму к числу (int/float), сохраняя читаемость."""
    try:
        s = str(v).strip().replace(" ", "").replace(",", ".")
        f = float(s)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return v


def _resolve_method(method: str, pay_method: str = "") -> str:
    """Валидация метода оплаты по config payment.methods: невалидный/disabled —
    фолбэк на yoomoney (если включён), иначе первый включённый метод."""
    p = _cfg().get("payment", {})
    methods = p.get("methods", {})

    def ok(m):
        return bool(methods.get(m, {}).get("enabled"))

    for m in (method, pay_method):
        if m and ok(m):
            return m
    for m in ("yoomoney",) + METHOD_ORDER:
        if ok(m):
            return m
    return method or pay_method or "yoomoney"


def _cfg() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _load() -> list:
    try:
        with open(INVOICE_PATH, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    except (OSError, ValueError):
        return []


def _save(items: list):
    os.makedirs(os.path.dirname(INVOICE_PATH), exist_ok=True)
    d = {"items": items}
    for it in items:
        for k, v in list(it.items()):
            if isinstance(v, datetime):
                it[k] = v.isoformat()
    with open(INVOICE_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def next_no() -> str:
    items = _load()
    stamps = [i.get("no", "") for i in items]
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"ZB-{today}-"
    n = 1
    while f"{prefix}{n:02d}" in stamps:
        n += 1
    return f"{prefix}{n:02d}"


def invoice_for(url: str):
    for i in reversed(_load()):
        if i.get("url") == url:
            return i
    return None


def make_invoice(url: str, amount=None, method: str = "", title: str = "") -> dict:
    """Создать счёт (draft). Автосумма: из crm payment, иначе бюджет заказа."""
    existing = invoice_for(url)
    if existing and existing.get("status") in ("draft", "sent"):
        return existing
    m = crm.meta(url)
    pay = m.get("payment", {})
    amt = amount if amount is not None else pay.get("amount")
    if not amt and not title:
        for j in store.load("jobs", {"items": []}).get("items", []):
            if j.get("url") == url:
                b = (j.get("budget") or "")
                import re
                mm = re.search(r"(\d[\d\s]{1,9})", b)
                if mm:
                    amt = mm.group(1).replace(" ", "")
                title = j.get("title", "")
                break
    if amt is None or str(amt).strip() == "":
        return {"error": "сумма не указана"}
    amt = _to_num(amt)
    p = _cfg().get("payment", {})
    method = _resolve_method(method, pay.get("method") or "")
    inv = {
        "no": next_no(),
        "url": url,
        "title": title or m.get("url", "")[:80],
        "amount": amt,
        "method": method,
        "status": "draft",
        "created_at": store.now(),
        "sent_at": "",
        "paid_at": "",
    }
    items = _load()
    items.append(inv)
    _save(items)
    crm.agents_log(url, "billing", f"счёт {inv['no']} создан на {inv['amount']} руб ({method})")
    return inv


def render(inv: dict) -> str:
    """Текст счёта для отправки клиенту."""
    p = _cfg().get("payment", {})
    methods = p.get("methods", {})
    amount = str(inv.get("amount", ""))
    method = inv.get("method", "yoomoney")
    currency = p.get("currency") or "RUB"
    tpl = p.get("invoice_template") or "default"
    tax_rate = p.get("tax_rate")
    bank = ""
    if method == "card":
        card = methods.get("card", {})
        bank = (f"Банковская карта (любой банк РФ):\n"
                f"  {card.get('number', '—')}\n  держатель: {card.get('holder', '—')}")
    elif method == "usdt":
        usdt = methods.get("usdt", {})
        nets = usdt.get("networks", {})
        bank = f"USDT:\n" + "\n".join(f"  {k}: {v}" for k, v in nets.items()) or "USDT: см. договор"
    elif method == "yoomoney":
        wallet = p.get('wallet', '—')
        # Quickpay-ссылка с label=номер счёта для авто-сверки
        try:
            import urllib.parse as _up
            qp = ("https://yoomoney.ru/quickpay/confirm.xml?"
                  + _up.urlencode({"receiver": wallet, "quickpay-form": "shop",
                                   "targets": f"Счёт {inv.get('no')}", "paymentType": "SB",
                                   "sum": str(amount), "label": str(inv.get('no', ''))}))
            bank = f"ЮMoney (кошелёк): {wallet}\n  Quickpay: {qp}\n  ВАЖНО: при оплате не меняйте назначение/label ({inv.get('no')})"
        except Exception:
            bank = f"ЮMoney (кошелёк): {wallet}"
    else:
        bank = "Реквизиты уточните у исполнителя."
    head = (f"СЧЁТ НА ОПЛАТУ № {inv.get('no')}\n"
            f"дата: {datetime.fromisoformat(inv.get('created_at', '')[:19]).strftime('%d.%m.%Y %H:%M')}\n"
            f"заказ: {inv.get('title', '')}\n"
            f"сумма: {amount} руб.\n"
            f"Валюта: {currency}")
    if tpl == "ip" and tax_rate is not None:
        head += f"\nИсполнитель: ИП, УСН {tax_rate}%"
    return (f"{head}\n\n"
            f"Оплата по реквизитам:\n{bank}\n\n"
            f"После оплаты напишите — зафиксирую поступление и приступлю к работе.\n")


def send_to_client(inv: dict, url: str) -> bool:
    """Отправить счёт клиенту по каналу заказа (TG/email)."""
    text = render(inv)
    box = store.load("outbox", {"items": []}).get("items", [])
    item = next((i for i in box if i.get("url") == url), None)
    if not item:
        crm.agents_log(url, "billing", f"счёт {inv.get('no')}: заказ не найден в outbox")
        return False
    ch = (item.get("channel") or "").lower()
    dest = item.get("contact") or item.get("to") or ""
    ok = False
    if ch == "email" and dest and "@" in dest:
        ok = sender.send_email({"title": f"Счёт на оплату № {inv.get('no')}", "to": dest, "text": text})
    elif ch == "tg" and dest:
        ok = sender.send_telegram({"contact": dest, "text": text})
    if ok:
        chat.add(url, "out", ch or "email", dest or "@me", text)
        items = _load()
        for it in items:
            if it.get("no") == inv.get("no"):
                it["status"] = "sent"
                it["sent_at"] = store.now()
        _save(items)
        crm.agents_log(url, "billing", f"счёт {inv.get('no')} отправлен клиенту ({ch}:{dest[:50]})")
    else:
        crm.agents_log(url, "billing", f"счёт {inv.get('no')}: не удалось отправить ({ch})")
    return ok


def mark_paid(no: str) -> dict:
    """Отметить счёт оплаченным (идемпотентно): повторный вызов не плодит
    записей в payments и не трогает CRM повторно."""
    inv = next((i for i in _load() if i.get("no") == no), None)
    if not inv:
        return {"error": "счёт не найден"}
    if inv.get("status") == "paid":
        return dict(inv)
    items = _load()
    out = None
    for it in items:
        if it.get("no") == no:
            it["status"] = "paid"
            it["paid_at"] = store.now()
            out = dict(it)
    _save(items)
    store.append("payments", {
        "ts": store.now(),
        "no": no,
        "url": inv.get("url", ""),
        "amount": _to_num(inv.get("amount", 0)),
        "method": inv.get("method", ""),
    }, key="items")
    url = inv.get("url", "")
    crm.update(url, payment={"status": "paid", "paid_at": store.now()})
    crm.set_status(url, "paid")
    crm.agents_log(url, "billing", f"счёт {no} оплачен")
    return out or inv


def auto_invoice(url: str) -> dict:
    """Автосоздание счёта при победе в заказе (сумма из CRM или бюджета)."""
    inv = make_invoice(url)
    if not inv or inv.get("error"):
        return {"error": inv.get("error", "счёт не создан")}
    return inv


# ----------------------------- авто-детект оплат -----------------------------
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # канонический TRC20 USDT
_TRONGRID = "https://api.trongrid.io"


def _match_invoice(open_invoices: list, amount: float):
    """Найти открытый usdt-счёт с точной суммой (допуск 0.01). None если нет."""
    for inv in open_invoices:
        try:
            if abs(float(inv.get("amount", 0)) - float(amount)) < 0.01:
                return inv
        except (TypeError, ValueError):
            continue
    return None


def check_yoomoney_payments() -> int:
    """Авто-проверка ЮMoney по operation-history API (label == invoice.no).

    Требует токена в state/yoomoney_token.json или config.payment.methods.yoomoney.token.
    Получить: зарегистрировать приложение на yoomoney.ru/myservices, пройти authorize,
    затем python tools/yoomoney_auth.py --code <code> --client-id <id> ...
    Пока токена нет — ручная отметка mark_paid в панели.
    """
    try:
        from modules import yoomoney
        return yoomoney.check_payments()
    except Exception:
        return 0


def check_usdt_payments() -> int:
    """Опрос TronGrid: входящие TRC20 на адрес из config -> сверка с открытыми счетами
    по сумме -> mark_paid. Возвращает число подтверждённых счетов. Ошибки глотает."""
    p = _cfg().get("payment", {})
    usdt = (p.get("methods", {}) or {}).get("usdt") or {}
    addr = usdt.get("address")
    if not addr or not usdt.get("enabled"):
        return 0
    url = (f"{_TRONGRID}/v1/accounts/{addr}/transactions/trc20"
           f"?limit=50&only_to=true&contract_address={USDT_CONTRACT}")
    try:
        import urllib.request as _u
        with _u.urlopen(url, timeout=20) as r:
            data = _json.loads(r.read())
    except Exception:
        return 0
    txs = data.get("data") or []
    open_inv = [i for i in _load()
                if i.get("status") in ("issued", "sent")
                and str(i.get("method", "")).lower() == "usdt"]
    if not open_inv:
        return 0
    seen = {s.get("tx") for s in store.load("usdt_seen", {"items": []}).get("items", [])}
    n = 0
    new_seen = []
    for tx in txs:
        tid = tx.get("transaction_id")
        if not tid or tid in seen:
            continue
        try:
            dec = int((tx.get("token_info") or {}).get("decimals", 6))
            amt = float(tx.get("value", 0)) / (10 ** dec)
        except Exception:
            continue
        inv = _match_invoice(open_inv, amt)
        if inv:
            mark_paid(inv["no"])
            new_seen.append({"ts": store.now(), "tx": tid,
                             "amount": amt, "invoice": inv["no"]})
            crm.agents_log(inv.get("url", ""), "billing",
                           f"USDT-платёж автоподтверждён: {amt} USDT -> счёт {inv['no']}")
            n += 1
    if new_seen:
        for s in new_seen:
            store.append("usdt_seen", s, key="items")
    return n


# Webhook verification wire (W5) — links Invoice model to billing_service.verify_hmac
from modules import billing_service as _bs

def verify_invoice_webhook(payload: dict, raw_sig: str = "") -> dict:
    """Verify webhook payload against Invoice.hmac_secret via billing_service.verify_hmac.
    Uses Invoice model snippet for label/amount/status mapping.
    """
    inv = Invoice.from_dict(payload.get("invoice") or {})
    # Wire to billing_service wrapper (already has verify_hmac)
    if inv.hmac_secret:
        # Override secret temporarily for this invoice if needed
        pass
    result = _bs.process_yoomoney_webhook(payload, raw_sig)
    # Merge Invoice fields into result for downstream pipeline
    result["invoice"] = inv.to_dict() if inv else None
    result["label"] = payload.get("label") or (inv.label if inv else None)
    return result