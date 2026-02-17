from django.db import models

# Create your models here.
from django.db import models
from orders.models import Order

class Shipping(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    courier_name = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_charge = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_delivery = models.DateField(null=True, blank=True)
