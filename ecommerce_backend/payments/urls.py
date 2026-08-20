from django.urls import path
from payments.views import RazorpayCreateOrderAPIView, RazorpayVerifyPaymentAPIView

urlpatterns = [
    path("razorpay/order/", RazorpayCreateOrderAPIView.as_view(), name="razorpay-order"),
    path("razorpay/verify/", RazorpayVerifyPaymentAPIView.as_view(), name="razorpay-verify"),
]

