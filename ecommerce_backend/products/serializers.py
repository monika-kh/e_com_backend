from rest_framework import serializers
from reviews.models import Review
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "parent_name", "image"]


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image"]

    def get_image(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None

        # If storage returns an absolute URL (e.g., S3), return it directly.
        url = obj.image.url
        if url.startswith("http"):
            return url

        # Otherwise, if we have a request, build an absolute URI; fallback to the raw URL.
        if request:
            return request.build_absolute_uri(url)

        return url


class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "stock",
            "target_gender",
            "category_name",
            "images",
            "average_rating",
            "ratings_count",
            "is_active",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    total_ratings = serializers.IntegerField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
