import hashlib
import hmac
from decimal import Decimal

from django.conf import settings

try:
    import razorpay
except Exception:  # pragma: no cover
    razorpay = None


class RazorpayService:
    def __init__(self):
        key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)

        if not key_id or not key_secret:
            raise ValueError("Razorpay keys are not configured.")
        if razorpay is None:
            raise ImportError("razorpay SDK not installed. Run: pip install razorpay")

        self.key_id = key_id
        self._client = razorpay.Client(auth=(key_id, key_secret))

    def create_order(self, *, amount: Decimal, receipt: str, currency: str = "INR"):
        # Razorpay expects amount in paise (integer)
        amount_paise = int(Decimal(amount) * 100)
        data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
        return self._client.order.create(data=data)

    def verify_signature(
        self,
        *,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        payload = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        try:
            self._client.utility.verify_payment_signature(payload)
            return True
        except Exception:
            return False

    @staticmethod
    def verify_webhook_signature(*, body: bytes, signature: str) -> bool:
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
        if not webhook_secret or not signature:
            return False

        expected_signature = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

