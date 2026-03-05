from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Avg, Count
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator, EmptyPage
from django.core.cache import cache

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)


class CategoryListAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            qs = Category.objects.all()

            name = request.GET.get("name")
            parent_name = request.GET.get("parent_name")

            if name:
                qs = qs.filter(name__icontains=name)

            if parent_name:
                qs = qs.filter(parent__name__icontains=parent_name)

            serializer = CategorySerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProductListAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            products = (
                Product.objects.filter(is_active=True)
                .annotate(
                    average_rating=Avg("reviews__rating"),
                    ratings_count=Count("reviews", distinct=True),
                )
            )
            serializer = ProductListSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class CategoryWiseProductAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, slug):
        try:
            products = (
                Product.objects.filter(
                    category__slug=slug,
                    is_active=True,
                )
                .annotate(
                    average_rating=Avg("reviews__rating"),
                    ratings_count=Count("reviews", distinct=True),
                )
            )
            serializer = ProductListSerializer(products, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, slug):
        cache_key = f"product_detail:{slug}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        try:
            product = (
                Product.objects.filter(slug=slug, is_active=True)
                .select_related("category")
                .prefetch_related("images")
                .annotate(
                    average_rating=Avg("reviews__rating"),
                    total_ratings=Count("reviews", distinct=True),
                    reviews_count=Count("reviews", distinct=True),
                )
                .get()
            )
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductDetailSerializer(product, context={"request": request})
        cache.set(cache_key, serializer.data, timeout=60 * 5)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductFilterAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):

        # -------------------------
        # Base Queryset (Removed default is_active=True)
        # Because available will now control it
        # -------------------------
        qs = (
            Product.objects
            .select_related("category")
            .annotate(
                average_rating=Avg("reviews__rating"),
                ratings_count=Count("reviews", distinct=True),
            )
        )

        # -------------------------
        # Get Query Params
        # -------------------------
        category_name = request.GET.get("category_name", "").strip().lower()
        target_gender = request.GET.get("target_gender", "").strip().lower()
        available = request.GET.get("available", "").strip()
        price_ranges = request.GET.get("price_ranges", "").strip()
        search = request.GET.get("search", "").strip().lower()
        sort = request.GET.get("sort", "").strip().lower()

        # -------------------------
        # Availability Filter (Based on is_active)
        # available=1 → active
        # available=0 → inactive
        # -------------------------
        if available in ["0", "1"]:
            qs = qs.filter(is_active=bool(int(available)))
        else:
            # Default: only active products
            qs = qs.filter(is_active=True)

        # -------------------------
        # Category Filter
        # -------------------------
        if category_name:
            qs = qs.filter(category__name__iexact=category_name)

        # -------------------------
        # Target Gender Filter
        # Example: target_gender=MEN,Women
        # -------------------------
        if target_gender:
            genders = [
                g.strip()
                for g in target_gender.split(",")
                if g.strip()
            ]
            if genders:
                qs = qs.filter(target_gender__in=genders)

        # -------------------------
        # Price Range Filter (FIXED LOGIC)
        # 1 = <= 500
        # 2 = 500 - 999
        # 3 = 1000 - 4999
        # 4 = 5000+
        # -------------------------
        if price_ranges:
            try:
                range_ids = [
                    int(p.strip())
                    for p in price_ranges.split(",")
                    if p.strip().isdigit()
                ]

                price_filter = Q()
                for rid in range_ids:
                    if rid == 1:
                        price_filter |= Q(price__lte=500)
                    elif rid == 2:
                        price_filter |= Q(price__gte=500, price__lte=999)
                    elif rid == 3:
                        price_filter |= Q(price__gte=1000, price__lte=4999)
                    elif rid == 4:
                        price_filter |= Q(price__gte=5000)

                if price_filter:
                    qs = qs.filter(price_filter)

            except Exception:
                pass

        # -------------------------
        # Search Filter
        # -------------------------
        if search:
            qs = qs.filter(name__icontains=search)

        # -------------------------
        # Sorting
        # -------------------------
        sort_map = {
            "price-asc": "price",
            "price-desc": "-price",
            "alpha-asc": "name",
            "alpha-desc": "-name",
        }

        qs = qs.order_by(sort_map.get(sort, "-created_at"))

        # -------------------------
        # Pagination
        # -------------------------
        page_number = request.GET.get("page", 1)
        page_size = int(request.GET.get("page_size", 20))

        paginator = Paginator(qs, page_size)

        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            return Response(
                {"message": "No more data available"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductListSerializer(page_obj, many=True,context={"request": request})

        return Response({
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": int(page_number),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class RelatedProductsAPIView(APIView):
    """
    Get related products based on category or child_category
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            category = request.GET.get("category", "").strip()
            child_category = request.GET.get("child_category", "").strip()
            exclude_slug = request.GET.get("exclude_slug", "").strip()
            limit = int(request.GET.get("limit", 6))

            cache_key = f"related_products:{category}:{child_category}:{exclude_slug}:{limit}"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

            # Base queryset - only active products
            qs = Product.objects.filter(is_active=True).select_related("category")

            # Filter by category if provided
            if category:
                qs = qs.filter(
                    Q(category__name__iexact=category)
                    | Q(category__slug__iexact=category)
                )

            # Filter by child category if provided
            if child_category:
                qs = qs.filter(
                    Q(category__name__iexact=child_category)
                    | Q(category__slug__iexact=child_category)
                )

            # Exclude a specific product if requested
            if exclude_slug:
                qs = qs.exclude(slug=exclude_slug)

            # If no filters provided, return random products
            if not category and not child_category:
                qs = qs.order_by("?")
            else:
                qs = qs.order_by("-created_at")

            # Limit results
            qs = qs[:limit]

            serializer = ProductListSerializer(
                qs, many=True, context={"request": request}
            )

            data = {
                "results": serializer.data,
                "count": len(serializer.data),
            }
            cache.set(cache_key, data, timeout=60 * 5)

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
