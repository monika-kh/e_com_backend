from django.db import models
from users.models import User
from products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user.email}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())
    
class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [['cart', 'product']]

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

    @property
    def subtotal(self):
        return self.product.price * self.quantity
    
    # @property
    # def total_price(self):
    #     return sum(item.subtotal for item in self.items.all())