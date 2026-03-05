from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Avg, Count
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from reviews.models import Review
from .models import Product
from .serializers import (
    ReviewSerializer,
)
from products.pagination import ProductReviewPagination
from .permissions import IsReviewOwnerOrReadOnly


class ProductRatingAPIView(APIView):
    """
    Handle product rating (0–5) for authenticated users.

    - GET: rating summary + current user's rating (if authenticated)
    - POST: create/update rating; rating=0 removes the rating
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)

        aggregates = Review.objects.filter(product=product).aggregate(
            average_rating=Avg("rating"),
            total_ratings=Count("id"),
        )

        user_rating = None
        if request.user.is_authenticated:
            user_review = Review.objects.filter(
                product=product, user=request.user
            ).first()
            if user_review:
                user_rating = user_review.rating

        return Response(
            {
                "average_rating": aggregates.get("average_rating") or 0,
                "total_ratings": aggregates.get("total_ratings") or 0,
                "user_rating": user_rating,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        product = get_object_or_404(Product, slug=slug, is_active=True)

        try:
            rating_value = int(request.data.get("rating", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "Rating must be an integer between 0 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if rating_value < 0 or rating_value > 5:
            return Response(
                {"error": "Rating must be between 0 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            review, created = Review.objects.get_or_create(
                product=product,
                user=request.user,
                defaults={
                    "rating": rating_value,
                    "comment": request.data.get("comment", "").strip(),
                },
            )

            # rating = 0 → delete the rating (and review)
            if rating_value == 0 and not created:
                review.delete()
            else:
                review.rating = rating_value
                comment = request.data.get("comment")
                if comment is not None:
                    review.comment = comment.strip()
                review.save()

            self._invalidate_product_cache(product.slug)

            aggregates = Review.objects.filter(product=product).aggregate(
                average_rating=Avg("rating"),
                total_ratings=Count("id"),
            )

            return Response(
                {
                    "message": "Rating updated successfully.",
                    "average_rating": aggregates.get("average_rating") or 0,
                    "total_ratings": aggregates.get("total_ratings") or 0,
                    "rating": rating_value if rating_value > 0 else None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def _invalidate_product_cache(slug: str) -> None:
        cache.delete(f"product_detail:{slug}")


class ProductReviewListCreateAPIView(APIView):
    """
    List + create reviews for a product.

    - GET: paginated list (5 per page)
    - POST: create or update the current user's review
    """

    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = ProductReviewPagination

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)

        queryset = (
            Review.objects.filter(product=product)
            .select_related("user")
            .order_by("-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        serializer = ReviewSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        product = get_object_or_404(Product, slug=slug, is_active=True)

        comment = (request.data.get("comment") or "").strip()
        if not comment:
            return Response(
                {"error": "Review text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating_value = int(request.data.get("rating", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "Rating must be an integer between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if rating_value < 1 or rating_value > 5:
            return Response(
                {"error": "Rating must be between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            review, created = Review.objects.get_or_create(
                product=product,
                user=request.user,
                defaults={"rating": rating_value, "comment": comment},
            )

            if not created:
                review.rating = rating_value
                review.comment = comment
                review.save()

            serializer = ReviewSerializer(review, context={"request": request})
            ProductRatingAPIView._invalidate_product_cache(product.slug)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductReviewDetailAPIView(APIView):
    """
    Update / delete a single review.
    Only the owner can modify or delete.
    """

    permission_classes = [IsAuthenticated, IsReviewOwnerOrReadOnly]

    def get_object(self, pk):
        review = get_object_or_404(Review.objects.select_related("user", "product"), pk=pk)
        self.check_object_permissions(self.request, review)
        return review

    def put(self, request, slug, pk):
        review = self.get_object(pk)

        if review.product.slug != slug:
            return Response(
                {"error": "Review does not belong to this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = (request.data.get("comment") or "").strip()
        if not comment:
            return Response(
                {"error": "Review text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating_value = int(request.data.get("rating", review.rating))
        except (TypeError, ValueError):
            return Response(
                {"error": "Rating must be an integer between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if rating_value < 1 or rating_value > 5:
            return Response(
                {"error": "Rating must be between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.rating = rating_value
        review.comment = comment
        review.save()

        serializer = ReviewSerializer(review, context={"request": request})
        ProductRatingAPIView._invalidate_product_cache(review.product.slug)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, slug, pk):
        review = self.get_object(pk)

        if review.product.slug != slug:
            return Response(
                {"error": "Review does not belong to this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_slug = review.product.slug
        review.delete()
        ProductRatingAPIView._invalidate_product_cache(product_slug)

        return Response(status=status.HTTP_204_NO_CONTENT)