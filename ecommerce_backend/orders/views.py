from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Sum

from cart.models import Cart
from products.models import Product
from users.models import Address
from orders.models import Order, OrderItem
from payments.models import Payment


class PlaceOrderAPIView(APIView):
    """
    Create an order from the current user's cart and selected address.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            address_id = request.data.get("address_id")
            if not address_id:
                return Response(
                    {"error": "Address is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                address = Address.objects.get(id=address_id, user=request.user)
            except Address.DoesNotExist:
                return Response(
                    {"error": "Invalid address."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                cart = Cart.objects.select_related("user").prefetch_related(
                    "items__product"
                ).get(user=request.user)
            except Cart.DoesNotExist:
                return Response(
                    {"error": "Cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_items = list(cart.items.all())
            if not cart_items:
                return Response(
                    {"error": "Cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                total_amount = sum(
                    (item.product.price or 0) * item.quantity for item in cart_items
                )

                shipping_snapshot = (
                    f"{address.full_name}\n"
                    f"{address.address_line}\n"
                    f"{address.city}, {address.state} - {address.pincode}\n"
                    f"Phone: {address.phone}"
                )

                order = Order.objects.create(
                    user=request.user,
                    shipping_address_text=shipping_snapshot,
                    total_amount=total_amount,
                    status="pending",
                )

                order_items_payload = []
                for item in cart_items:
                    if not item.product or not item.product.is_active:
                        return Response(
                            {
                                "error": f"Product '{item.product}' is no longer available."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    order_items_payload.append(
                        OrderItem(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.price,
                        )
                    )

                OrderItem.objects.bulk_create(order_items_payload)

                # IMPORTANT: Do NOT clear cart here for online payments.
                # Cart should be cleared only when:
                # - COD order is confirmed (if you add COD flow), or
                # - Razorpay payment is successfully verified.

                return Response(
                    {
                        "order_id": order.id,
                        "status": order.status,
                        "total_amount": order.total_amount,
                        "created_at": order.created_at,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            # Optimize only with valid relations. Order has FK to user and O2O to payment/shipping.
            .select_related("user", "payment", "shipping")
            .prefetch_related("items")
            .annotate(total_quantity=Sum("items__quantity"))
            .order_by("-created_at")
        )

        data = [
            {
                "order_id": order.id,
                "delivery_status": order.status,
                "total_amount": order.total_amount,
                "total_quantity": int(order.total_quantity or 0),
                "payment_method": getattr(order.payment, "payment_method", None),
                "payment_status": getattr(order.payment, "status", "pending"),
                "created_at": order.created_at,
            }
            for order in orders
        ]

        return Response(data, status=status.HTTP_200_OK)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("payment").prefetch_related("items__product"),
            id=order_id,
            user=request.user,
        )
        items = order.items.all()
        data = {
                "order_id": order.id,
                "delivery_status": order.status,
                # "payment_method": getattr(order.payment, "payment_method", None),
                # "payment_status": getattr(order.payment, "status", "pending"),
                "total_amount": order.total_amount,
                "total_quantity": sum(i.quantity for i in items),
                "created_at": order.created_at,
                "address": {
                    "snapshot": order.shipping_address_text,
                },
                "items": [
                    {
                        "product_id": item.product.id if item.product else None,
                        "product_name": item.product.name if item.product else None,
                        "product_slug": item.product.slug if item.product else None,
                        "quantity": item.quantity,
                        "price": item.price,
                    }
                    for item in items
                ],
            },
        print(data)
        return Response(
            data,
            status=status.HTTP_200_OK,
        )