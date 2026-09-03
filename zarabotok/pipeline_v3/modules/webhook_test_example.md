# Пример локальной проверки ЮMoney webhook (curl + HMAC)
# 1. Установите webhook_secret в config.json:
#    config.json -> payment -> methods -> yoomoney -> webhook_secret: "your-secret"
# 2. Сгенерируйте HMAC для теста (Python):
#    python -c "
# import hmac, hashlib
# payload = {'notification_type':'card-incoming','operation_id':'op-001','amount':'500','label':'ZB-20260829-01','currency':'643'}
# msg = '&'.join(f'{k}={v}' for k,v in sorted(payload.items()))
# print('message:', msg)
# print('hmac-sha1:', hmac.new(b'your-secret', msg.encode(), hashlib.sha1).hexdigest())
# "
# 3. Отправьте curl:
#    curl -X POST http://localhost:8765/webhook/yoomoney \
#      -H "Content-Type: application/x-www-form-urlencoded" \
#      -d "notification_type=card-incoming&operation_id=op-001&amount=500&currency=643&label=ZB-20260829-01&hash=<HMAC>"
# 4. Проверка replay-защиты:
#    Повторный вызов с тем же operation_id вернёт {"ok": false, "error": "duplicate_operation"}
