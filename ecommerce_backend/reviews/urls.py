from django.urls import path
from .views import (
    ProductRatingAPIView,
    ProductReviewListCreateAPIView,
    ProductReviewDetailAPIView,
)

urlpatterns = [
    path("<slug:slug>/rating/", ProductRatingAPIView.as_view()),
    path("<slug:slug>/reviews/", ProductReviewListCreateAPIView.as_view()),
    path("<slug:slug>/reviews/<int:pk>/", ProductReviewDetailAPIView.as_view()),
]
