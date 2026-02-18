from django.urls import path
from .views import RegisterAPIView, LoginAPIView, ProfileAPIView, LogoutAPIView, RefreshAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("profile/", ProfileAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", RefreshAPIView.as_view(), name="refresh"),
]
