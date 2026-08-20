from django.db import models
from orders.models import Order

class Payment(models.Model):
    PAYMENT_METHODS = (
        ("razorpay", "Razorpay"),
        # ("cod", "Cash On Delivery"),
    )
    # PAYMENT_STATUS = (
    #     ("pending", "Pending"),
    #     ("completed", "Completed"),
    #     ("failed", "Failed"),
    # )

    order_id = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="razorpay")
    # transaction_id = models.CharField(max_length=100, blank=True, null=True)
    # amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(
            max_length=255,
            unique=True
        )
    
    razorpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    # payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS)
    payment_status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
