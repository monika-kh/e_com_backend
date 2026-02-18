from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, CartItemSimpleSerializer
from products.models import Product
from orders.models import Order, OrderItem


def format_cart_item_response(cart_item):
    """
    Format cart item response with complete product details
    """
    product = cart_item.product
    images = [img.image.url for img in product.images.all()]
    
    return {
        "product_id": product.id,
        "productId": product.id,
        "product_name": product.name,
        "product_slug": product.slug,
        "quantity": cart_item.quantity,
        "price": float(product.price),
        "product_stock": product.stock,
        "product_images": images,
        "subtotal": float(product.price * cart_item.quantity),
    }


class CartAPIView(APIView):
    """
    GET: Get current user's cart with complete product details
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related("product").prefetch_related("product__images").all()
        
        # Return cart items with complete product details
        data = [format_cart_item_response(item) for item in items]
        
        return Response(
            {
                "items": data,
                "total_items": sum(item["quantity"] for item in data),
                "total_price": sum(item["subtotal"] for item in data),
            },
            status=status.HTTP_200_OK
        )


class AddToCartAPIView(APIView):
    """
    POST: Add product to cart
    Request body: {"product_id": 1, "quantity": 2}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity < 1 or quantity > 5:
            return Response(
                {"error": "Quantity must be between 1 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check stock availability
        if product.stock < quantity:
            return Response(
                {
                    "error": f"Insufficient stock. Available: {product.stock}",
                    "available_quantity": product.stock,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Handle potential duplicates: get first matching item or create new one
        # If duplicates exist, merge them by summing quantities and keeping the first
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            created = False
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(cart=cart, product=product, quantity=0)
            created = True
        except CartItem.MultipleObjectsReturned:
            # Handle duplicates: merge all duplicate items into the first one
            duplicate_items = CartItem.objects.filter(cart=cart, product=product)
            cart_item = duplicate_items.first()
            total_quantity = sum(item.quantity for item in duplicate_items)
            cart_item.quantity = total_quantity
            # Delete the other duplicates
            duplicate_items.exclude(id=cart_item.id).delete()
            created = False

        if not created:
            # Product already in cart - add to quantity
            new_quantity = cart_item.quantity + quantity
            
            # Check stock for new quantity
            if product.stock < new_quantity:
                return Response(
                    {
                        "error": f"Insufficient stock. Available: {product.stock}",
                        "available_quantity": product.stock,
                        "current_quantity": cart_item.quantity,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
        else:
            # New item
            cart_item.quantity = quantity

        # Cap quantity at 5 and stock availability
        cart_item.quantity = min(cart_item.quantity, 5, product.stock)
        cart_item.save()

        return Response(
            format_cart_item_response(cart_item),
            status=status.HTTP_201_CREATED
        )


class UpdateCartAPIView(APIView):
    """
    PATCH: Update cart item quantity
    Request body: {"product_id": 1, "quantity": 3}
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity < 0 or quantity > 5:
            return Response(
                {"error": "Quantity must be between 0 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id)
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
        except (Product.DoesNotExist, Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {"error": "Cart item or product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check stock availability for new quantity
        if quantity > 0 and product.stock < quantity:
            return Response(
                {
                    "error": f"Insufficient stock. Available: {product.stock}",
                    "available_quantity": product.stock,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # If quantity is 0, delete the item
        if quantity == 0:
            cart_item.delete()
            return Response(
                {"success": True, "message": "Item removed from cart"},
                status=status.HTTP_200_OK
            )

        cart_item.quantity = quantity
        cart_item.save()

        return Response(
            format_cart_item_response(cart_item),
            status=status.HTTP_200_OK
        )


class RemoveFromCartAPIView(APIView):
    """
    DELETE: Remove product from cart
    Request body: {"product_id": 1}
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        product_id = request.data.get("product_id")

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
            cart_item.delete()
            return Response(
                {"success": True, "message": "Item removed from cart"},
                status=status.HTTP_200_OK
            )
        except CartItem.MultipleObjectsReturned:
            # Handle duplicates: delete all matching items
            CartItem.objects.filter(cart=cart, product_id=product_id).delete()
            return Response(
                {"success": True, "message": "Item removed from cart"},
                status=status.HTTP_200_OK
            )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cart item not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class ClearCartAPIView(APIView):
    """
    POST: Clear entire cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            item_count = cart.items.count()
            cart.items.all().delete()
            return Response(
                {
                    "success": True,
                    "message": f"Removed {item_count} items from cart"
                },
                status=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return Response(
                {
                    "success": True,
                    "message": "Cart is already empty"
                },
                status=status.HTTP_200_OK
            )


class CheckoutAPIView(APIView):
    """
    POST: Checkout and create order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not cart.items.exists():
            return Response(
                {"error": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate stock for all items before creating order
        for item in cart.items.all():
            if item.product.stock < item.quantity:
                return Response(
                    {
                        "error": f"Insufficient stock for {item.product.name}. Available: {item.product.stock}",
                        "product_id": item.product.id,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_price,
            status="pending"
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Reduce stock after order
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()

        return Response(
            {
                "message": "Order placed successfully",
                "order_id": order.id,
                "total_amount": float(order.total_amount),
            },
            status=status.HTTP_201_CREATED
        )
    