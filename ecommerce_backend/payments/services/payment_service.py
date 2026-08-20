import os
from decimal import Decimal

try:
    import razorpay
except Exception:  # pragma: no cover
    razorpay = None


class RazorpayService:
    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

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

