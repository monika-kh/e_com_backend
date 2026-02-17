from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from products.models import Product
from orders.models import Order, OrderItem


class CartAPIView(APIView):
    """
    GET: Get current user's cart
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related("product").all()
        
        # Return cart items in the format expected by frontend
        data = []
        for item in items:
            data.append({
                "product_id": item.product.id,
                "productId": item.product.id,
                "quantity": item.quantity,
                "price": float(item.product.price) if item.product.price else 0,
            })
        
        return Response(data, status=status.HTTP_200_OK)


class AddToCartAPIView(APIView):
    """
    POST: Add product to cart
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
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            # Product already in cart - add to quantity
            cart_item.quantity += quantity
        else:
            # New item
            cart_item.quantity = quantity

        # Cap quantity at 5
        cart_item.quantity = min(cart_item.quantity, 5)
        cart_item.save()

        return Response({
            "product_id": product.id,
            "quantity": cart_item.quantity,
            "price": float(product.price) if product.price else 0,
        }, status=status.HTTP_201_CREATED)


class UpdateCartAPIView(APIView):
    """
    PATCH: Update cart item quantity
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
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {"error": "Cart item not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        cart_item.quantity = quantity
        cart_item.save()

        return Response({
            "product_id": product_id,
            "quantity": cart_item.quantity,
            "price": float(cart_item.product.price) if cart_item.product.price else 0,
        }, status=status.HTTP_200_OK)


class RemoveFromCartAPIView(APIView):
    """
    DELETE: Remove product from cart
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
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
            cart_item.delete()
            return Response(
                {"success": True},
                status=status.HTTP_200_OK
            )
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
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
            cart.items.all().delete()
            return Response(
                {"success": True},
                status=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return Response(
                {"success": True},
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

        cart.items.all().delete()

        return Response({
            "message": "Order placed successfully",
            "order_id": order.id
        }, status=status.HTTP_201_CREATED)
    