from django.shortcuts import render

# Create your views here.
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from cart.models import Cart, CartItem
from cart.serializers import CartSerializer
from products.models import Product

from orders.models import Order, OrderItem

class UserOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by("-created_at")

        data = []
        for order in orders:
            data.append({
                "order_id": order.id,
                "status": order.status,
                "total_amount": order.total_amount,
                "created_at": order.created_at,
            })

        return Response(data)
    
class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        items = order.items.all()

        return Response({
            "order_id": order.id,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": [
                {
                    "product": item.product.name if item.product else None,
                    "quantity": item.quantity,
                    "price": item.price,
                }
                for item in items
            ]
        })