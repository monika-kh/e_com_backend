from django.db import models
from orders.models import Order

class Payment(models.Model):
    PAYMENT_METHODS = (
        ("razorpay", "Razorpay"),
        ("cod", "Cash On Delivery"),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
