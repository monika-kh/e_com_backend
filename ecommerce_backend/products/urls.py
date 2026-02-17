from django.urls import path
from .views import (
    CategoryListAPIView,
    ProductListAPIView,
    CategoryWiseProductAPIView,
    ProductDetailAPIView,
    ProductFilterAPIView,
    RelatedProductsAPIView
)

urlpatterns = [
    path("categories/", CategoryListAPIView.as_view()),
    path("products/", ProductListAPIView.as_view()),
    path("filter/", ProductFilterAPIView.as_view()),
    path("related/", RelatedProductsAPIView.as_view()),
    path("category/<slug:slug>/", CategoryWiseProductAPIView.as_view()),
    path("<slug:slug>/", ProductDetailAPIView.as_view()),                     #product detail api
]
