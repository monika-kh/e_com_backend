from django.urls import path
from .views import (
    PlaceOrderAPIView,
    UserOrdersAPIView,
    OrderDetailAPIView,
)

urlpatterns = [
    path("create/", PlaceOrderAPIView.as_view(), name="order-create"),
    path("order-list", UserOrdersAPIView.as_view(), name="user-orders"),
    path("<int:order_id>/", OrderDetailAPIView.as_view(), name="order-detail"),
]