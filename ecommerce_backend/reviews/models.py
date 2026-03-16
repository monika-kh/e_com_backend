from django.db import models
from users.models import User
from products.models import Product


class Review(models.Model):
    """
    Combined rating + review model.

    - One rating per user per product
    - Review text is optional and can be managed independently
    - Rating is an integer from 0–5 (0 = no rating)
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
    # 0 means "no rating yet" so that review text can exist without a rating
    rating = models.PositiveIntegerField(default=0)
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
