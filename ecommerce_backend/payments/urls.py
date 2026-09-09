from django.urls import path
from payments.views import (
    RazorpayCreateOrderAPIView,
    RazorpayVerifyPaymentAPIView,
    RazorpayWebhookAPIView,
)

urlpatterns = [
    path("razorpay/order/", RazorpayCreateOrderAPIView.as_view(), name="razorpay-order"),
    path("razorpay/verify/", RazorpayVerifyPaymentAPIView.as_view(), name="razorpay-verify"),
    path("razorpay/webhook/", RazorpayWebhookAPIView.as_view(), name="razorpay-webhook"),
]

