from django.urls import path
from .views import (
    CartAPIView,
    AddToCartAPIView,
    UpdateCartAPIView,
    RemoveFromCartAPIView,
    ClearCartAPIView,
    CheckoutAPIView,
)


urlpatterns = [
    # Get logged-in user's cart
    path("cart-list", CartAPIView.as_view(), name="view-cart"),

    # Add product to cart
    path("add-to-cart/", AddToCartAPIView.as_view(), name="add-to-cart"),

    # Update cart item quantity
    path("cart-update/", UpdateCartAPIView.as_view(), name="update-cart"),

    # Remove item from cart
    path("cart-remove/", RemoveFromCartAPIView.as_view(), name="remove-from-cart"),

    # Clear entire cart
    path("cart-clear/", ClearCartAPIView.as_view(), name="clear-cart"),

    # Checkout cart → Create order
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
]