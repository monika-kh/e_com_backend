from rest_framework import serializers
from .models import Cart, CartItem
from products.models import Product
from products.serializers import ProductImageSerializer


class ProductDetailSerializer(serializers.ModelSerializer):
    """Minimal product details for cart display"""
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "price", "stock", "target_gender", "images"]


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    product_stock = serializers.IntegerField(source="product.stock", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_images = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", 
            "product", 
            "product_name", 
            "product_price",
            "product_slug",
            "product_stock",
            "product_images",
            "quantity", 
            "subtotal"
        ]

    def get_product_images(self, obj):
        """Get product images"""
        images = obj.product.images.all()
        return ProductImageSerializer(images, many=True, context=self.context).data

    def get_subtotal(self, obj):
        return float(obj.product.price * obj.quantity)
    
    
class CartSerializer(serializers.ModelSerializer):
    """Full cart with detailed items"""
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price", "total_items", "created_at", "updated_at"]

    def get_total_price(self, obj):
        return float(obj.total_price)
    
    def get_total_items(self, obj):
        return obj.items.aggregate(total=serializers.models.Sum('quantity'))['total'] or 0


class CartItemSimpleSerializer(serializers.Serializer):
    """Simple cart item response for add/update operations"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    product_slug = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    product_images = serializers.ListField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)