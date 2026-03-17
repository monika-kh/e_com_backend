from django.urls import path
from .views import (
    RegisterAPIView,
    LoginAPIView,
    ProfileAPIView,
    LogoutAPIView,
    RefreshAPIView,
    UserAddressListCreateAPIView,
    UserAddressDeleteAPIView,
    UserAddressUpdateAPIView,
)

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("profile/", ProfileAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", RefreshAPIView.as_view(), name="refresh"),
    path("addresses/", UserAddressListCreateAPIView.as_view(), name="address-list-create"),
    path("addresses/<int:address_id>/", UserAddressDeleteAPIView.as_view(), name="address-delete"),
    path(
        "addresses/<int:address_id>/update/",
        UserAddressUpdateAPIView.as_view(),
        name="address-update",
    ),
]
