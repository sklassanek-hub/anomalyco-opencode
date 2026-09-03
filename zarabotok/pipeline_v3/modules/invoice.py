"""Модель счёта Invoice (PDF/HTML) с номером, датой, label, QR-кодом и реквизитами.

Не ломает существующий billing.py — используется как независимый модуль.
"""
import base64
import io
import os
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

try:
    import qrcode
    from PIL import Image
    _QR_OK = True
except Exception:  # pragma: no cover
    _QR_OK = False


def _load_cfg() -> dict:
    import json
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


class Invoice:
    """Модель счёта для pipeline_v3 (§13 fusion-response)."""

    def __init__(
        self,
        no: str = "",
        url: str = "",
        title: str = "",
        amount: float = 0.0,
        method: str = "yoomoney",
        label: str = "",
        currency: str = "RUB",
        customer_id: str = "",
        details: str = "",
    ):
        self.no = no or self._next_no()
        self.url = url
        self.title = title
        self.amount = float(amount)
        self.method = method
        self.label = label or self.no  # label — уникальный идентификатор заказчика/счёта
        self.currency = currency
        self.customer_id = customer_id or self.label
        self.details = details
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status = "draft"

    @staticmethod
    def _next_no() -> str:
        """Простой генератор номера (без доступа к billing._load, чтобы не конфликтовать)."""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"INV-{today}-"
        import random
        return f"{prefix}{random.randint(1000, 9999)}"

    def to_dict(self) -> dict:
        return {
            "no": self.no,
            "url": self.url,
            "title": self.title,
            "amount": self.amount,
            "method": self.method,
            "label": self.label,
            "currency": self.currency,
            "customer_id": self.customer_id,
            "details": self.details,
            "created_at": self.created_at,
            "status": self.status,
        }

    def qr_base64(self) -> str:
        """QR-код с реквизитами счёта (HTML встраивается как data:image/png;base64,...)."""
        if not _QR_OK:
            return ""
        payload = (
            f"invoice_no={self.no}\n"
            f"label={self.label}\n"
            f"amount={self.amount} {self.currency}\n"
            f"method={self.method}\n"
            f"url={self.url}\n"
            f"title={self.title}"
        )
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    def render_html(self) -> str:
        """HTML-счёт с номером, датой, label, QR-кодом и реквизитами."""
        p = _load_cfg().get("payment", {})
        wallet = p.get("wallet", "4100119458306656")
        currency = self.currency or p.get("currency", "RUB")
        tax_rate = p.get("tax_rate")
        bank_text = ""
        if self.method == "yoomoney":
            bank_text = f"ЮMoney (кошелёк): {wallet}\nLabel для сверки: {self.label}"
        elif self.method == "card":
            card = (p.get("methods", {}) or {}).get("card", {})
            bank_text = f"Карта: {card.get('number', '—')}\nДержатель: {card.get('holder', '—')}"
        else:
            bank_text = "Реквизиты уточните у исполнителя."
        qr_tag = ""
        qr_b64 = self.qr_base64()
        if qr_b64:
            qr_tag = (
                f'<div style="margin-top:16px;">'
                f'<img src="data:image/png;base64,{qr_b64}" '
                f'style="width:160px;height:160px;border:1px solid #ccc;" '
                f'alt="QR {self.no}" />'
                f'</div>'
            )
        tax_line = f"\nИсполнитель: ИП, УСН {tax_rate}%" if tax_rate is not None else ""
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Счёт № {self.no}</title>
<style>
body {{ font-family: "Segoe UI", Arial, sans-serif; max-width: 720px; margin: 40px auto; padding: 24px; color: #222; background: #fafafa; }}
.paper {{ background: #fff; padding: 32px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
h1 {{ font-size: 22px; border-bottom: 2px solid #4a90e2; padding-bottom: 8px; margin-bottom: 24px; }}
.meta {{ margin-bottom: 20px; line-height: 1.6; }}
.label-box {{ display: inline-block; padding: 4px 10px; background: #eef6ff; border: 1px solid #4a90e2; border-radius: 4px; font-weight: 600; color: #1a3a5c; }}
.details {{ margin-top: 16px; padding: 12px; background: #f7f7f7; border-left: 3px solid #4a90e2; }}
.bank {{ margin-top: 20px; padding: 14px; background: #fffdf5; border: 1px solid #e6c47a; border-radius: 6px; }}
.qr {{ text-align: center; margin-top: 20px; }}
.footer {{ margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
</style>
</head>
<body>
<div class="paper">
<h1>СЧЁТ НА ОПЛАТУ № {self.no}</h1>
<div class="meta">
  <strong>Дата:</strong> {self.created_at}<br>
  <strong>Заказ:</strong> {self.title or self.url}<br>
  <strong>Сумма:</strong> {self.amount} {self.currency}<br>
  <strong>Способ:</strong> {self.method}<br>
  <strong>Label (идентификатор заказчика):</strong> <span class="label-box">{self.label}</span><br>
  <strong>Клиент ID:</strong> {self.customer_id}<br>
</div>
{f'<div class="details">{self.details}</div>' if self.details else ''}
<div class="bank">
  <strong>Реквизиты для оплаты:</strong><br>
  <pre style="margin-top:8px; white-space:pre-wrap;">{bank_text}</pre>
</div>
<div class="qr">{qr_tag}</div>
<div class="footer">
  Счёт сгенерирован автоматически. {tax_line}. Для вопросов пишите исполнителю.
</div>
</div>
</body>
</html>"""
        return html

    def save_pdf_path(self) -> str:
        """Путь для сохранения PDF (без генерации PDF — для ручного экспорта из HTML)."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "deliverables",
            f"invoice_{self.no}.html",
        )
