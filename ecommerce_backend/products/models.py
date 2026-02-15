from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    image = models.ImageField(upload_to="category/", null=True, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("unisex", "Unisex"),
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    target_gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="unisex"
    )
    price = models.DecimalField(max_digits=10, decimal_places=5)
    stock = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
