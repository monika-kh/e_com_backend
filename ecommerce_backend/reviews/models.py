from django.db import models
from users.models import User
from products.models import Product


class Review(models.Model):
    """
    Combined rating + review model.

    - One review (and rating) per user per product
    - Rating is an integer from 0–5
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product")
        indexes = [
            models.Index(fields=("product", "created_at")),
            models.Index(fields=("user", "product")),
        ]

    def __str__(self) -> str:
        return f"{self.product} - {self.rating}"
