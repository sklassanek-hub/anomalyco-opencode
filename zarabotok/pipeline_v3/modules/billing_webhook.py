# Billing webhook verification stub
import hmac, hashlib, os

def verify_hmac(payload, secret, expected_sig):
    calc = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return calc == expected_sig

# Wire to billing_service.verify_hmac_wrapper
