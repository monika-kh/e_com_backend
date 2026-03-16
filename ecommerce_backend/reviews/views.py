from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Avg, Count
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from reviews.models import Review
from .models import Product
from .serializers import ReviewSerializer
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

        # Only count ratings where rating > 0
        aggregates = Review.objects.filter(product=product, rating__gt=0).aggregate(
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
            comment_raw = request.data.get("comment")
            comment = comment_raw.strip() if isinstance(comment_raw, str) else ""

            review, _ = Review.objects.get_or_create(
                product=product,
                user=request.user,
                defaults={
                    "rating": max(rating_value, 0),
                    "comment": comment if comment else "",
                },
            )

            # Rating endpoint is responsible only for rating.
            # rating = 0 → clear rating but keep review record (and any existing comment).
            review.rating = max(rating_value, 0)
            review.save(update_fields=["rating", "updated_at"])

            self._invalidate_product_cache(product.slug)

            aggregates = Review.objects.filter(product=product, rating__gt=0).aggregate(
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

        # Only reviews that actually have non-empty text should be listed.
        queryset = (
            Review.objects.filter(product=product)
            .exclude(comment="")
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

        rating_raw = request.data.get("rating", None)
        rating_value = None

        if rating_raw is not None:
            try:
                rating_value = int(rating_raw)
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
                defaults={
                    "rating": rating_value if rating_value is not None else 0,
                    "comment": comment,
                },
            )

            if not created:
                # Always update review text
                review.comment = comment

                # Only update rating if explicitly provided; otherwise keep existing rating
                if rating_value is not None:
                    review.rating = rating_value

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

        rating_raw = request.data.get("rating", None)
        rating_value = None

        if rating_raw is not None:
            try:
                rating_value = int(rating_raw)
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

        review.comment = comment
        if rating_value is not None:
            review.rating = rating_value
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

        # Deleting a review should only remove the text, not the rating.
        review.comment = ""
        review.save(update_fields=["comment", "updated_at"])

        ProductRatingAPIView._invalidate_product_cache(review.product.slug)

        return Response(
            {"message": "Review text deleted. Rating has been kept."},
            status=status.HTTP_200_OK,
        )