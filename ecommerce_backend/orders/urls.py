from django.urls import path
from .views import (
    UserOrdersAPIView,
    OrderDetailAPIView,
)

urlpatterns = [
    # List all user orders
    path("order-list", UserOrdersAPIView.as_view(), name="user-orders"),

    # Order detail / tracking
    path("<int:order_id>/", OrderDetailAPIView.as_view(), name="order-detail"),
]